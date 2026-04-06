from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional
import textwrap
import os

from app.config import settings
from app.models.schemas import Region


class RenderService:
    """텍스트 렌더링 서비스"""

    def __init__(self):
        self.default_font_path = os.path.join(
            settings.FONT_DIR,
            settings.DEFAULT_FONT
        )

    def get_font(
        self,
        size: int,
        font_path: Optional[str] = None
    ) -> ImageFont.FreeTypeFont:
        """
        폰트 로드

        Args:
            size: 폰트 크기
            font_path: 폰트 파일 경로

        Returns:
            ImageFont 객체
        """
        path = font_path or self.default_font_path

        # 기본 폰트 경로들 시도
        font_paths = [
            path,
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # macOS
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux alternative
            "C:\\Windows\\Fonts\\malgun.ttf",  # Windows
        ]

        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except:
                    continue

        # 폴백: 기본 폰트
        return ImageFont.load_default()

    def calculate_font_size(
        self,
        text: str,
        region: Region,
        max_size: int = 30,
        min_size: int = 10
    ) -> int:
        """
        영역에 맞는 폰트 크기 계산

        Args:
            text: 렌더링할 텍스트
            region: 대상 영역
            max_size: 최대 폰트 크기
            min_size: 최소 폰트 크기

        Returns:
            적절한 폰트 크기
        """
        for size in range(max_size, min_size - 1, -1):
            font = self.get_font(size)

            # 글자당 평균 너비 추정
            avg_char_width = size * 0.6
            chars_per_line = max(1, int(region.width / avg_char_width))

            # 텍스트 줄바꿈
            wrapped = textwrap.fill(text, width=chars_per_line)
            lines = wrapped.split('\n')

            # 높이 계산
            text_height = len(lines) * size * 1.2
            text_width = max(len(line) for line in lines) * avg_char_width

            if text_height <= region.height and text_width <= region.width:
                return size

        return min_size

    def render_text(
        self,
        image_path: str,
        texts: List[dict],
        output_path: str,
        font_path: Optional[str] = None
    ) -> str:
        """
        이미지에 텍스트 렌더링

        Args:
            image_path: 입력 이미지 경로
            texts: [{"text": str, "region": Region, "color": str}, ...]
            output_path: 출력 이미지 경로
            font_path: 폰트 파일 경로

        Returns:
            출력 파일 경로
        """
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        for item in texts:
            text = item["text"]
            region = item["region"]
            color = item.get("color", "black")

            # 폰트 크기 계산
            font_size = self.calculate_font_size(text, region)
            font = self.get_font(font_size, font_path)

            # 텍스트 줄바꿈
            avg_char_width = font_size * 0.6
            chars_per_line = max(1, int(region.width / avg_char_width))
            wrapped_text = textwrap.fill(text, width=chars_per_line)

            # 텍스트 크기 계산
            bbox = draw.textbbox((0, 0), wrapped_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 중앙 정렬
            x = region.x + (region.width - text_width) // 2
            y = region.y + (region.height - text_height) // 2

            # 외곽선 효과 (가독성 향상)
            outline_color = "white" if color == "black" else "black"
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((x + dx, y + dy), wrapped_text, font=font, fill=outline_color)

            # 본문 텍스트
            draw.text((x, y), wrapped_text, font=font, fill=color)

        img.save(output_path)
        return output_path


# 싱글톤 인스턴스
render_service = RenderService()
