"""OpenCV 기반 Inpainting 서비스"""
import asyncio
import cv2
import numpy as np
from typing import Optional


class InpaintService:
    """OpenCV 기반 텍스트 제거 서비스"""

    def __init__(self):
        self._initialized = True
        print("[InpaintService] Using OpenCV inpainting")

    async def initialize(self):
        """초기화 (OpenCV는 별도 초기화 불필요)"""
        pass

    async def remove_text(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        inpainting_size: int = 1024
    ) -> np.ndarray:
        """
        마스크 영역의 텍스트를 제거 (OpenCV inpainting)

        Args:
            image: BGR 이미지 (np.ndarray)
            mask: 제거할 영역 마스크 (흰색=제거, 검정=유지)
            inpainting_size: 미사용 (호환성 유지)

        Returns:
            텍스트가 제거된 이미지
        """
        # OpenCV TELEA 알고리즘 사용 (반경 증가로 더 완전한 제거)
        result = cv2.inpaint(image, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)
        return result

    def create_text_mask(
        self,
        image: np.ndarray,
        regions: list,
        threshold: int = 200,
        dilate_iterations: int = 2
    ) -> np.ndarray:
        """
        말풍선 영역 내 텍스트 마스크 생성

        Args:
            image: BGR 이미지
            regions: 말풍선 영역 리스트 [{"x": int, "y": int, "w": int, "h": int}, ...]
            threshold: 텍스트 판별 임계값 (이보다 어두우면 텍스트)
            dilate_iterations: 마스크 확장 횟수

        Returns:
            텍스트 마스크 (흰색=텍스트, 검정=배경)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        img_height, img_width = image.shape[:2]

        # 전체 마스크 생성
        mask = np.zeros((img_height, img_width), dtype=np.uint8)

        for region in regions:
            x = region.get("x", 0)
            y = region.get("y", 0)
            w = region.get("w", 0)
            h = region.get("h", 0)

            if w <= 0 or h <= 0:
                continue

            # 테두리 보존을 위한 padding
            padding = 5
            x1 = max(0, x + padding)
            y1 = max(0, y + padding)
            x2 = min(img_width, x + w - padding)
            y2 = min(img_height, y + h - padding)

            if x2 <= x1 or y2 <= y1:
                continue

            # ROI에서 어두운 픽셀(텍스트) 추출
            roi = gray[y1:y2, x1:x2]
            text_mask = (roi < threshold).astype(np.uint8) * 255

            # 마스크 영역에 추가
            mask[y1:y2, x1:x2] = cv2.bitwise_or(mask[y1:y2, x1:x2], text_mask)

        # 마스크 확장 (텍스트 주변 포함)
        if dilate_iterations > 0:
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=dilate_iterations)

        return mask


# 싱글톤 인스턴스
inpaint_service = InpaintService()
