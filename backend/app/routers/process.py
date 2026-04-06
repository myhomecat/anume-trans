from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import os
import uuid
import aiofiles
from PIL import Image, ImageDraw, ImageFont
import textwrap
import cv2
import numpy as np
from ultralytics import YOLO
from huggingface_hub import hf_hub_download

from app.config import settings
from app.models.schemas import ProcessResponse, TextItem, Region
from app.services.translate_service import translate_service
from app.services.ocr_service import OCRService
from app.services.inpaint_service import inpaint_service
from app.services.sam_service import get_sam_service

router = APIRouter()

# YOLOv8 말풍선 감지 모델 로드
print("Loading YOLOv8 bubble detector model...")
_bubble_model_path = hf_hub_download(
    repo_id="ogkalu/comic-speech-bubble-detector-yolov8m",
    filename="comic-speech-bubble-detector.pt"
)
bubble_detector = YOLO(_bubble_model_path)
print("YOLOv8 bubble detector loaded!")

# OCR 서비스 초기화 (앱 시작 시 한 번만)
print("Loading OCR model...")
ocr_service = OCRService()
print("OCR model loaded!")


def get_font(size: int) -> ImageFont.FreeTypeFont:
    """한글 폰트 로드"""
    font_paths = [
        os.path.join(settings.FONT_DIR, settings.DEFAULT_FONT),
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:\\Windows\\Fonts\\malgun.ttf",
    ]

    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue

    return ImageFont.load_default()


def estimate_original_font_size(text_mask: np.ndarray, region: dict, original_text: str) -> int:
    """
    텍스트 마스크에서 원본 텍스트의 폰트 크기 추정

    Args:
        text_mask: 전체 이미지의 텍스트 마스크
        region: 말풍선 영역 {"x", "y", "w", "h"}
        original_text: 원본 텍스트

    Returns:
        추정된 폰트 크기 (픽셀)
    """
    x = region.get("x", 0)
    y = region.get("y", 0)
    w = region.get("w", 0)
    h = region.get("h", 0)

    if w <= 0 or h <= 0 or not original_text:
        return 16  # 기본값

    # 해당 영역의 텍스트 마스크 추출
    roi_mask = text_mask[y:y+h, x:x+w]

    # 텍스트 픽셀 좌표 찾기
    coords = np.where(roi_mask > 0)
    if len(coords[0]) == 0:
        return 16  # 기본값

    # 텍스트 영역의 bounding box
    text_top = coords[0].min()
    text_bottom = coords[0].max()
    text_left = coords[1].min()
    text_right = coords[1].max()

    text_height = text_bottom - text_top
    text_width = text_right - text_left

    # 글자 수 (공백 제외)
    char_count = len(original_text.replace(" ", "").replace("　", ""))
    if char_count == 0:
        return 16

    # 세로/가로 판단
    is_vertical = h > w * 1.3

    if is_vertical:
        # 세로 텍스트: 높이 / 글자수 = 대략적인 글자 높이
        # 여러 줄일 수 있으므로 너비도 고려
        num_cols = max(1, text_width // max(text_height // max(char_count, 1), 10))
        chars_per_col = max(1, char_count // num_cols)
        estimated_size = int(text_height / chars_per_col) if chars_per_col > 0 else 16
    else:
        # 가로 텍스트: 텍스트 높이 / 줄 수 = 폰트 크기
        # 대략적인 줄 수 추정
        avg_char_width = text_width / char_count if char_count > 0 else 12
        estimated_size = int(min(text_height, avg_char_width * 1.2))

    # 범위 제한 (10 ~ 40)
    return max(10, min(estimated_size, 40))


def detect_speech_bubbles(image_path: str, conf_threshold: float = 0.3) -> list:
    """
    YOLOv8로 말풍선 영역 감지 (딥러닝 기반)

    Returns:
        [(x, y, w, h, None), ...] 말풍선 영역 리스트
    """
    print(f"[DEBUG] Detecting speech bubbles with YOLOv8...")

    # YOLOv8로 감지
    results = bubble_detector.predict(source=image_path, conf=conf_threshold, verbose=False)

    bubbles = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf[0].item()

            x, y = int(x1), int(y1)
            w, h = int(x2 - x1), int(y2 - y1)

            bubbles.append((x, y, w, h, None))
            print(f"[DEBUG] Bubble found: ({x}, {y}, {w}, {h}), conf={conf:.2f}")

    print(f"[DEBUG] Found {len(bubbles)} speech bubbles")

    # y좌표로 정렬 (위에서 아래로, 왼쪽에서 오른쪽으로)
    bubbles.sort(key=lambda b: (b[1] // 40, b[0]))

    return bubbles


def render_text_on_image(
    image_path: str,
    texts: list,
    output_path: str
) -> str:
    """
    말풍선 내부에 번역된 텍스트 렌더링 (단순화 버전)

    1. Claude의 bbox 영역을 흰색으로 채워 원본 텍스트 제거
    2. 해당 영역 크기에 맞춰 텍스트 줄바꿈하여 렌더링
    """
    # PIL 이미지 열기
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    img_width, img_height = img.size
    draw = ImageDraw.Draw(img)

    print(f"[DEBUG] Image size: {img_width}x{img_height}")
    print(f"[DEBUG] Number of text items from Claude: {len(texts)}")

    for i, item in enumerate(texts):
        translated = item.get("translated", "")
        bbox = item.get("bbox")
        print(f"[DEBUG] Item {i}: translated='{translated[:30] if translated else ''}...', bbox={bbox}")

        if not translated or not bbox or len(bbox) != 4:
            continue

        x_pct, y_pct, w_pct, h_pct = bbox

        # bbox 크기를 70%로 축소하고 중심 유지
        shrink = 0.7
        new_w_pct = w_pct * shrink
        new_h_pct = h_pct * shrink
        new_x_pct = x_pct + (w_pct - new_w_pct) / 2
        new_y_pct = y_pct + (h_pct - new_h_pct) / 2

        x = int(img_width * new_x_pct / 100)
        y = int(img_height * new_y_pct / 100)
        w = int(img_width * new_w_pct / 100)
        h = int(img_height * new_h_pct / 100)

        print(f"[DEBUG] Converted (shrunk 70%): x={x}, y={y}, w={w}, h={h}")

        if w <= 10 or h <= 10:
            continue

        # 1. 해당 영역을 흰색으로 채우기 (원본 텍스트 제거)
        draw.rectangle([x, y, x + w, y + h], fill=(255, 255, 255))

        # 2. 번역 텍스트 렌더링 (영역 크기에 맞춰 줄바꿈)
        render_text_in_area(draw, translated, x, y, w, h)

    img.save(output_path)
    return output_path


def render_text_in_area(draw, text: str, x: int, y: int, w: int, h: int):
    """영역 내에 텍스트 렌더링 (가로/세로 자동 판단)"""
    if not text or w <= 0 or h <= 0:
        return

    # 패딩 적용
    padding = 4
    inner_x = x + padding
    inner_y = y + padding
    inner_w = w - padding * 2
    inner_h = h - padding * 2

    if inner_w <= 0 or inner_h <= 0:
        return

    # 세로 말풍선인지 판단 (높이가 너비의 1.5배 이상)
    is_vertical = h > w * 1.5

    if is_vertical:
        # 세로 텍스트: 한 글자씩 줄바꿈
        render_vertical_text(draw, text, inner_x, inner_y, inner_w, inner_h)
    else:
        # 가로 텍스트
        render_horizontal_text(draw, text, inner_x, inner_y, inner_w, inner_h)


def wrap_text_korean(text: str, font, max_width, draw) -> str:
    """
    한글 텍스트를 단어 단위로 줄바꿈 (단어가 잘리지 않게)
    """
    # 공백으로 단어 분리
    words = text.split()
    if not words:
        return text

    lines = []
    current_line = ""

    for word in words:
        # 현재 줄에 단어 추가 시도
        test_line = current_line + (" " if current_line else "") + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= max_width:
            current_line = test_line
        else:
            # 현재 줄이 비어있으면 단어가 너무 긴 것 - 강제로 넣음
            if not current_line:
                current_line = word
            else:
                # 현재 줄 저장하고 새 줄 시작
                lines.append(current_line)
                current_line = word

    # 마지막 줄 추가
    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


def render_horizontal_text(draw, text: str, x: int, y: int, w: int, h: int):
    """가로 텍스트 렌더링 (한글 지원, 단어 단위 줄바꿈)"""
    if not text or w <= 0 or h <= 0:
        return

    text_len = len(text)

    # 초기 폰트 크기 계산 (영역에 맞게)
    font_size = int(min(h * 0.4, w / max(text_len, 1) * 1.8))
    font_size = max(10, min(font_size, 20))
    font = get_font(font_size)

    # 단어 단위 줄바꿈
    wrapped_text = wrap_text_korean(text, font, w, draw)

    # 텍스트 크기 측정
    bbox = draw.textbbox((0, 0), wrapped_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # 텍스트가 영역을 벗어나면 폰트 크기 줄이기
    while (text_w > w or text_h > h) and font_size > 8:
        font_size -= 1
        font = get_font(font_size)
        wrapped_text = wrap_text_korean(text, font, w, draw)
        bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    # 중앙 정렬
    text_x = x + max(0, (w - text_w) // 2)
    text_y = y + max(0, (h - text_h) // 2)

    # 영역을 벗어나지 않도록 보정
    text_x = max(x, min(text_x, x + w - text_w))
    text_y = max(y, min(text_y, y + h - text_h))

    draw.text((text_x, text_y), wrapped_text, font=font, fill=(0, 0, 0))


def render_vertical_text(draw, text: str, x: int, y: int, w: int, h: int):
    """세로 텍스트 렌더링 (위에서 아래로, 오른쪽에서 왼쪽으로)"""
    if not text or w <= 0 or h <= 0:
        return

    text_len = len(text)

    # 폰트 크기 계산 (영역에 맞게) - 보수적으로 설정
    font_size = int(min(w * 0.6, h / max(text_len, 1) * 0.9))
    font_size = max(8, min(font_size, 16))
    font = get_font(font_size)

    # 한 열에 들어갈 글자 수 계산
    line_height = font_size * 1.15
    chars_per_col = max(1, int(h / line_height))

    # 열 수 계산
    num_cols = (text_len + chars_per_col - 1) // chars_per_col
    col_width = font_size * 1.05

    # 폰트 크기 재조정 (영역에 맞게)
    while (num_cols * col_width > w or chars_per_col * line_height > h) and font_size > 6:
        font_size -= 1
        font = get_font(font_size)
        line_height = font_size * 1.15
        chars_per_col = max(1, int(h / line_height))
        num_cols = (text_len + chars_per_col - 1) // chars_per_col
        col_width = font_size * 1.05

    # 시작 위치 (오른쪽 상단에서 시작, 영역 내로 제한)
    total_width = num_cols * col_width
    total_height = min(chars_per_col, text_len) * line_height

    start_x = x + w - col_width - max(0, (w - total_width) // 2)
    start_y = y + max(0, (h - total_height) // 2)

    # 영역 내로 제한
    start_x = max(x, min(start_x, x + w - col_width))
    start_y = max(y, start_y)

    # 글자 그리기
    char_idx = 0
    for col in range(num_cols):
        col_x = start_x - col * col_width
        # 열이 영역을 벗어나면 중단
        if col_x < x:
            break
        for row in range(chars_per_col):
            if char_idx >= text_len:
                break
            char = text[char_idx]
            char_y = start_y + row * line_height
            # 글자가 영역을 벗어나면 중단
            if char_y + font_size > y + h:
                break
            draw.text((col_x, char_y), char, font=font, fill=(0, 0, 0))
            char_idx += 1


def render_text_with_estimated_size(
    draw,
    text: str,
    x: int,
    y: int,
    w: int,
    h: int,
    estimated_font_size: int
):
    """
    추정된 폰트 크기를 사용하여 항상 가로로 텍스트 렌더링

    Args:
        draw: ImageDraw 객체
        text: 렌더링할 텍스트
        x, y, w, h: 렌더링 영역
        estimated_font_size: 원본 텍스트에서 추정된 폰트 크기
    """
    if not text or w <= 0 or h <= 0:
        return

    # 추정된 폰트 크기 사용 (최소/최대 제한) - 최대 24px로 제한
    font_size = max(10, min(estimated_font_size, 24))
    font = get_font(font_size)

    # 한글 평균 문자 폭
    avg_char_width = font_size * 0.95
    chars_per_line = max(1, int(w / avg_char_width))
    wrapped_text = textwrap.fill(text, width=chars_per_line)

    # 텍스트 크기 측정
    bbox = draw.textbbox((0, 0), wrapped_text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # 텍스트가 영역을 벗어나면 폰트 크기 줄이기
    while (text_w > w or text_h > h) and font_size > 8:
        font_size -= 1
        font = get_font(font_size)
        avg_char_width = font_size * 0.95
        chars_per_line = max(1, int(w / avg_char_width))
        wrapped_text = textwrap.fill(text, width=chars_per_line)
        bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

    # 중앙 정렬
    text_x = x + max(0, (w - text_w) // 2)
    text_y = y + max(0, (h - text_h) // 2)

    # 영역을 벗어나지 않도록 보정
    text_x = max(x, min(text_x, x + w - text_w))
    text_y = max(y, min(text_y, y + h - text_h))

    draw.text((text_x, text_y), wrapped_text, font=font, fill=(0, 0, 0))


async def render_text_on_bubbles(
    image_path: str,
    items: list,
    output_path: str
) -> str:
    """
    말풍선 내부에 번역된 텍스트 렌더링 (manga-image-translator Inpainting 방식)

    1. 말풍선 내 텍스트(어두운 픽셀)를 마스크로 생성
    2. manga-image-translator의 딥러닝 inpainting으로 텍스트 제거
    3. 번역된 텍스트 렌더링
    """
    # PIL로 이미지 로드
    img_pil = Image.open(image_path)
    if img_pil.mode != 'RGB':
        img_pil = img_pil.convert('RGB')
    img_width, img_height = img_pil.size

    print(f"[DEBUG] render_text_on_bubbles: {len(items)} items")

    # 1. 각 말풍선 영역을 흰색으로 채우기 (테두리 보존)
    draw = ImageDraw.Draw(img_pil)
    for item in items:
        region = item.get("region", {})
        x = region.get("x", 0)
        y = region.get("y", 0)
        w = region.get("w", 0)
        h = region.get("h", 0)

        if w > 0 and h > 0:
            # 텍스트가 가장자리까지 있을 수 있으므로 전체 영역 채우기
            fill_x1 = x
            fill_y1 = y
            fill_x2 = x + w
            fill_y2 = y + h

            draw.rectangle([fill_x1, fill_y1, fill_x2, fill_y2], fill=(255, 255, 255))
            print(f"[DEBUG] Filled region ({x}, {y}, {w}, {h}) with white")

    # 2. 각 말풍선에 번역 텍스트 렌더링
    for i, item in enumerate(items):
        translated = item.get("translated", "")
        region = item.get("region", {})

        x = region.get("x", 0)
        y = region.get("y", 0)
        w = region.get("w", 0)
        h = region.get("h", 0)

        print(f"[DEBUG] Rendering item {i}: region=({x}, {y}, {w}, {h}), text='{translated[:20]}...'")

        if not translated or w <= 10 or h <= 10:
            continue

        # 패딩 적용 (말풍선 테두리 안쪽으로)
        padding = 8
        inner_x = x + padding
        inner_y = y + padding
        inner_w = w - padding * 2
        inner_h = h - padding * 2

        if inner_w <= 0 or inner_h <= 0:
            continue

        # 세로/가로 판단하여 텍스트 렌더링
        is_vertical = h > w * 1.5

        if is_vertical:
            render_vertical_text(draw, translated, inner_x, inner_y, inner_w, inner_h)
        else:
            render_horizontal_text(draw, translated, inner_x, inner_y, inner_w, inner_h)

    # 저장
    img_pil.save(output_path)
    return output_path


async def render_with_inpainting(
    image_path: str,
    items: list,
    output_path: str
) -> str:
    """
    인페인팅 기반 텍스트 제거 및 번역 렌더링 (MobileSAM 사용)

    1. MobileSAM으로 정확한 말풍선 마스크 생성
    2. 말풍선 마스크 내부에서만 텍스트(어두운 픽셀) 감지
    3. 딥러닝 인페인팅으로 텍스트 제거 (말풍선 형태 완벽 유지)
    4. 번역된 텍스트 렌더링
    """
    print(f"[DEBUG] render_with_inpainting (SAM): {len(items)} items")

    # 이미지 로드 (OpenCV)
    img_cv = cv2.imread(image_path)
    if img_cv is None:
        raise ValueError(f"Failed to load image: {image_path}")

    img_height, img_width = img_cv.shape[:2]

    # 1. SAM 서비스로 정확한 말풍선 마스크 생성
    sam_service = get_sam_service()

    # 바운딩 박스 추출
    boxes = [(item["region"]["x"], item["region"]["y"],
              item["region"]["w"], item["region"]["h"]) for item in items]
    print(f"[DEBUG] Creating SAM-based text mask for {len(boxes)} bubbles...")

    # SAM 마스크 기반 텍스트 감지 (테두리 색상 무관)
    text_mask = sam_service.create_text_mask_with_sam(
        img_cv,
        boxes,
        threshold=180,  # 텍스트 판별 임계값 (더 밝은 픽셀도 텍스트로 인식)
        dilate_iterations=3  # 마스크 확장 증가
    )

    print(f"[DEBUG] SAM text mask created, non-zero pixels: {np.count_nonzero(text_mask)}")

    # 2. SAM 마스크의 외곽 테두리만 감지 (텍스트 테두리 제외)
    bubble_mask = sam_service.get_combined_bubble_mask(img_cv, boxes)

    # SAM 마스크의 외곽선만 추출 (내부 텍스트 테두리 제외)
    kernel = np.ones((3, 3), np.uint8)
    # 마스크 침식 후 원본에서 빼면 외곽선만 남음
    eroded_mask = cv2.erode(bubble_mask, kernel, iterations=2)
    bubble_border = cv2.subtract(bubble_mask, eroded_mask)

    # 원본 이미지에서 테두리 영역의 픽셀 저장
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)

    # 말풍선 외곽 테두리에서만 에지 추출 (텍스트 영역 제외)
    bubble_edges = cv2.bitwise_and(edges, bubble_border)

    print(f"[DEBUG] Bubble border edges detected (excluding text)")

    # 3. 인페인팅으로 텍스트 제거
    print(f"[DEBUG] Running inpainting...")
    inpainted_img = await inpaint_service.remove_text(
        img_cv,
        text_mask,
        inpainting_size=1024
    )
    print(f"[DEBUG] Inpainting completed")

    # 4. 원본 테두리 복원 (인페인팅된 이미지에 원본 테두리 픽셀 덮어쓰기)
    inpainted_img[bubble_edges > 0] = img_cv[bubble_edges > 0]
    print(f"[DEBUG] Original bubble edges restored")

    # 5. PIL로 변환하여 텍스트 렌더링
    img_pil = Image.fromarray(cv2.cvtColor(inpainted_img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    # 6. 각 말풍선에 번역 텍스트 렌더링
    for i, item in enumerate(items):
        translated = item.get("translated", "")
        region = item.get("region", {})

        x = region.get("x", 0)
        y = region.get("y", 0)
        w = region.get("w", 0)
        h = region.get("h", 0)

        print(f"[DEBUG] Rendering item {i}: region=({x}, {y}, {w}, {h}), text='{translated[:20]}...'")

        if not translated or w <= 10 or h <= 10:
            continue

        # 패딩 적용 (말풍선 테두리 안쪽으로) - 더 큰 패딩으로 안전하게
        padding = 12
        inner_x = x + padding
        inner_y = y + padding
        inner_w = w - padding * 2
        inner_h = h - padding * 2

        if inner_w <= 0 or inner_h <= 0:
            continue

        # 모든 텍스트는 가로로 렌더링 (세로 말풍선도 가로 텍스트)
        render_horizontal_text(draw, translated, inner_x, inner_y, inner_w, inner_h)

    # 7. 저장
    img_pil.save(output_path)
    print(f"[DEBUG] Output saved: {output_path}")

    return output_path


@router.post("/process", response_model=ProcessResponse)
async def process_image(
    image: UploadFile = File(...),
    target_language: str = Form(default="한국어"),
    style: str = Form(default="manga"),
):
    """
    만화 이미지 전체 처리 파이프라인 (개선된 버전)

    1. 이미지 저장
    2. OpenCV로 말풍선 영역 감지
    3. manga-ocr로 각 말풍선 텍스트 추출
    4. Claude로 번역 (좌표 추정 X, 번역만)
    5. 말풍선 영역에 번역된 텍스트 렌더링
    """
    # 작업 ID 생성
    job_id = str(uuid.uuid4())

    # 디렉토리 생성
    job_upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    job_output_dir = os.path.join(settings.OUTPUT_DIR, job_id)
    os.makedirs(job_upload_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)

    try:
        # 1. 이미지 저장
        file_ext = os.path.splitext(image.filename)[1] or ".png"
        input_path = os.path.join(job_upload_dir, f"input{file_ext}")

        async with aiofiles.open(input_path, 'wb') as f:
            content = await image.read()
            await f.write(content)

        # 2. OpenCV로 말풍선 영역 감지
        print(f"[DEBUG] Detecting speech bubbles...")
        bubbles = detect_speech_bubbles(input_path)
        print(f"[DEBUG] Found {len(bubbles)} speech bubbles")

        # 3. 각 말풍선에서 manga-ocr로 텍스트 추출
        img_pil = Image.open(input_path)
        if img_pil.mode != 'RGB':
            img_pil = img_pil.convert('RGB')

        extracted_texts = []
        for i, (x, y, w, h, contour) in enumerate(bubbles):
            # 말풍선 영역 크롭
            cropped = img_pil.crop((x, y, x + w, y + h))

            # OCR로 텍스트 추출
            text = ocr_service.extract_from_pil(cropped)
            print(f"[DEBUG] Bubble {i}: region=({x}, {y}, {w}, {h}), text='{text}'")

            if text and text.strip():
                extracted_texts.append({
                    "original": text.strip(),
                    "region": {"x": x, "y": y, "w": w, "h": h},
                    "contour": contour
                })

        # 4. Claude로 번역 (텍스트만, 좌표 추정 X)
        texts = []
        render_items = []

        if extracted_texts:
            # 모든 텍스트를 한 번에 번역 요청
            originals = [item["original"] for item in extracted_texts]
            translations = await translate_service.translate_batch(
                originals,
                target_language=target_language
            )

            print(f"[DEBUG] Translations received: {len(translations)}")

            for i, item in enumerate(extracted_texts):
                translated = translations[i] if i < len(translations) else item["original"]
                region = item["region"]

                texts.append(TextItem(
                    original=item["original"],
                    translated=translated,
                    location=f"({region['x']}, {region['y']})",
                    type="dialogue",
                    region=Region(
                        x=region["x"],
                        y=region["y"],
                        width=region["w"],
                        height=region["h"]
                    )
                ))

                render_items.append({
                    "translated": translated,
                    "original": item["original"],  # 원본 텍스트 추가
                    "region": region,
                    "contour": item["contour"]
                })

        # 5. 이미지 크기 정보
        img_width, img_height = img_pil.size

        # 6. 인페인팅 + 번역 텍스트 렌더링
        output_url = None
        if render_items:
            output_path = os.path.join(job_output_dir, f"output.png")

            # 인페인팅 기반 텍스트 제거 및 렌더링
            await render_with_inpainting(
                input_path,
                render_items,
                output_path
            )

            output_url = f"/outputs/{job_id}/output.png"
            print(f"[DEBUG] Output saved to: {output_url}")

        # 원본 이미지 URL 생성 (uploads 폴더에서 제공)
        original_url = f"/uploads/{job_id}/input{file_ext}"

        return ProcessResponse(
            success=True,
            job_id=job_id,
            texts=texts,
            original_url=original_url,
            output_url=output_url,
            image_width=img_width,
            image_height=img_height
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return ProcessResponse(
            success=False,
            job_id=job_id,
            error=str(e)
        )


@router.get("/download/{job_id}/{filename}")
async def download_result(job_id: str, filename: str):
    """처리된 이미지 다운로드"""
    file_path = os.path.join(settings.OUTPUT_DIR, job_id, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="image/png",
        filename=filename
    )
