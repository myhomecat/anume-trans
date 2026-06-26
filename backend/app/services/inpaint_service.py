"""Inpainting 서비스 — LaMa(딥러닝) 우선, 실패 시 OpenCV TELEA 폴백"""
import asyncio
import cv2
import numpy as np
from typing import Optional
from PIL import Image

try:
    import torch
    _LAMA_DEVICE = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
except Exception:
    _LAMA_DEVICE = "cpu"

_simple_lama = None


def _get_lama():
    """SimpleLama 지연 로딩 (최초 호출 시 모델 다운로드). 실패하면 None."""
    global _simple_lama
    if _simple_lama is None:
        try:
            from simple_lama_inpainting import SimpleLama
            try:
                _simple_lama = SimpleLama(device=_LAMA_DEVICE)
            except Exception:
                _simple_lama = SimpleLama(device="cpu")  # MPS 미지원 연산 시 CPU
            print(f"[InpaintService] LaMa loaded (device={_LAMA_DEVICE})")
        except Exception as e:
            print(f"[InpaintService] LaMa load 실패 → OpenCV 폴백: {e}")
            _simple_lama = False  # 로드 실패 표시 (재시도 방지)
    return _simple_lama or None


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
        # 1) LaMa 시도 (그림/배경 위 텍스트까지 자연스럽게 복원)
        lama = _get_lama()
        if lama is not None and mask.any():
            try:
                img_rgb = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                mask_pil = Image.fromarray(mask).convert("L")
                out = lama(img_rgb, mask_pil)
                out_np = np.array(out.convert("RGB"))
                # LaMa 출력 크기가 다를 수 있어 원본에 맞춤
                if out_np.shape[:2] != image.shape[:2]:
                    out_np = cv2.resize(out_np, (image.shape[1], image.shape[0]))
                return cv2.cvtColor(out_np, cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"[InpaintService] LaMa inpaint 실패 → OpenCV 폴백: {e}")
        # 2) OpenCV TELEA 폴백
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
