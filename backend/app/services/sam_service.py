"""
MobileSAM 기반 말풍선 세그멘테이션 서비스
YOLOv8 바운딩 박스를 받아서 정확한 말풍선 마스크 생성
"""
import os
import numpy as np
import cv2
import torch
from typing import List, Tuple, Optional

# MobileSAM imports
from mobile_sam import sam_model_registry, SamPredictor

class SAMService:
    def __init__(self, model_path: str = None):
        """MobileSAM 모델 초기화"""
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "models", "mobile_sam.pt"
            )

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[SAM] Loading MobileSAM on {self.device}...")

        # MobileSAM 모델 로드
        model_type = "vit_t"  # MobileSAM uses tiny ViT
        self.sam = sam_model_registry[model_type](checkpoint=model_path)
        self.sam.to(device=self.device)
        self.sam.eval()

        self.predictor = SamPredictor(self.sam)
        print("[SAM] MobileSAM loaded successfully!")

    def set_image(self, image: np.ndarray):
        """이미지 설정 (한 번만 호출하면 여러 박스에 대해 마스크 생성 가능)"""
        # BGR to RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            image_rgb = image

        self.predictor.set_image(image_rgb)

    def get_mask_from_box(self, box: Tuple[int, int, int, int]) -> np.ndarray:
        """
        바운딩 박스로부터 세그멘테이션 마스크 생성

        Args:
            box: (x, y, w, h) 형태의 바운딩 박스

        Returns:
            마스크 이미지 (0 또는 255)
        """
        x, y, w, h = box
        # SAM은 xyxy 형태 필요
        input_box = np.array([x, y, x + w, y + h])

        masks, scores, _ = self.predictor.predict(
            point_coords=None,
            point_labels=None,
            box=input_box[None, :],
            multimask_output=True
        )

        # 가장 높은 점수의 마스크 선택
        best_idx = np.argmax(scores)
        mask = masks[best_idx]

        # 0/1 → 0/255 변환
        return (mask * 255).astype(np.uint8)

    def get_masks_from_boxes(
        self,
        image: np.ndarray,
        boxes: List[Tuple[int, int, int, int]]
    ) -> List[np.ndarray]:
        """
        여러 바운딩 박스에 대해 마스크 생성

        Args:
            image: 원본 이미지 (BGR)
            boxes: [(x, y, w, h), ...] 형태의 바운딩 박스 리스트

        Returns:
            마스크 리스트
        """
        self.set_image(image)

        masks = []
        for box in boxes:
            mask = self.get_mask_from_box(box)
            masks.append(mask)

        return masks

    def get_combined_bubble_mask(
        self,
        image: np.ndarray,
        boxes: List[Tuple[int, int, int, int]]
    ) -> np.ndarray:
        """
        모든 말풍선 영역을 합친 마스크 생성

        Args:
            image: 원본 이미지 (BGR)
            boxes: [(x, y, w, h), ...] 형태의 바운딩 박스 리스트

        Returns:
            합쳐진 마스크 (말풍선 영역 = 255)
        """
        h, w = image.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)

        masks = self.get_masks_from_boxes(image, boxes)

        for mask in masks:
            combined_mask = cv2.bitwise_or(combined_mask, mask)

        return combined_mask

    def create_text_mask_with_sam(
        self,
        image: np.ndarray,
        boxes: List[Tuple[int, int, int, int]],
        threshold: int = 180,
        dilate_iterations: int = 2
    ) -> np.ndarray:
        """
        SAM 마스크 내부에서만 텍스트 영역 감지

        Args:
            image: 원본 이미지 (BGR)
            boxes: YOLOv8에서 감지한 바운딩 박스 리스트
            threshold: 텍스트 감지 임계값 (낮을수록 더 많은 픽셀이 텍스트로 인식)
            dilate_iterations: 마스크 확장 반복 횟수

        Returns:
            텍스트 마스크 (텍스트 영역 = 255)
        """
        h, w = image.shape[:2]
        text_mask = np.zeros((h, w), dtype=np.uint8)

        # 그레이스케일 변환
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 각 말풍선에 대해 SAM 마스크 생성 후 내부 텍스트 감지
        self.set_image(image)

        for box in boxes:
            # SAM으로 말풍선 마스크 생성
            bubble_mask = self.get_mask_from_box(box)

            # 말풍선 내부의 어두운 픽셀 = 텍스트
            dark_pixels = (gray < threshold).astype(np.uint8) * 255

            # 말풍선 마스크와 교집합 (말풍선 내부의 텍스트만)
            text_in_bubble = cv2.bitwise_and(dark_pixels, bubble_mask)

            # 결과에 추가
            text_mask = cv2.bitwise_or(text_mask, text_in_bubble)

        # 마스크 확장 (텍스트 주변 포함)
        if dilate_iterations > 0:
            kernel = np.ones((3, 3), np.uint8)
            text_mask = cv2.dilate(text_mask, kernel, iterations=dilate_iterations)

        return text_mask


# 싱글톤 인스턴스
_sam_service: Optional[SAMService] = None

def get_sam_service() -> SAMService:
    """SAM 서비스 싱글톤 인스턴스 반환"""
    global _sam_service
    if _sam_service is None:
        _sam_service = SAMService()
    return _sam_service
