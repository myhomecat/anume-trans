from manga_ocr import MangaOcr
from PIL import Image
from typing import List

from app.models.schemas import Region


class OCRService:
    """manga-ocr 래퍼 서비스"""

    def __init__(self):
        """OCR 모델 초기화 (시간이 걸림)"""
        self.model = MangaOcr()

    def extract_text(self, image_path: str) -> str:
        """
        이미지 전체에서 텍스트 추출

        Args:
            image_path: 이미지 파일 경로

        Returns:
            추출된 텍스트
        """
        img = Image.open(image_path)
        text = self.model(img)
        return text

    def extract_from_pil(self, image: Image.Image) -> str:
        """
        PIL Image에서 텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            추출된 텍스트
        """
        return self.model(image)

    def extract_from_regions(
        self,
        image_path: str,
        regions: List[Region]
    ) -> List[dict]:
        """
        이미지의 특정 영역들에서 텍스트 추출

        Args:
            image_path: 이미지 파일 경로
            regions: 추출할 영역 리스트

        Returns:
            [{"region": Region, "text": str}, ...]
        """
        img = Image.open(image_path)
        results = []

        for region in regions:
            # 영역 크롭
            cropped = img.crop((
                region.x,
                region.y,
                region.x + region.width,
                region.y + region.height
            ))

            # OCR
            text = self.model(cropped)

            results.append({
                "region": region,
                "text": text
            })

        return results
