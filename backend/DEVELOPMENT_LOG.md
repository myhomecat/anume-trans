# Anime/Manga Translator 개발 문서

## 프로젝트 개요
일본어 만화 이미지를 업로드하면 자동으로 말풍선을 감지하고, 텍스트를 추출하여 한국어로 번역한 후, 원본 텍스트를 제거하고 번역된 텍스트를 렌더링하는 웹 애플리케이션.

## 기술 스택
- **Backend**: Python FastAPI
- **Frontend**: Next.js (TypeScript)
- **말풍선 감지**: YOLOv8 (comic-speech-bubble-detector)
- **말풍선 세그멘테이션**: MobileSAM
- **OCR**: manga-ocr
- **번역**: Claude API
- **텍스트 제거**: OpenCV Inpainting (TELEA 알고리즘)

## 디렉토리 구조
```
/home/pgchae/바탕화면/anume-trans/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 앱 엔트리포인트
│   │   ├── config.py            # 설정
│   │   ├── routers/
│   │   │   └── process.py       # 메인 처리 라우터 (핵심 로직)
│   │   ├── services/
│   │   │   ├── inpaint_service.py   # OpenCV 인페인팅
│   │   │   ├── sam_service.py       # MobileSAM 세그멘테이션
│   │   │   ├── ocr_service.py       # manga-ocr
│   │   │   └── translate_service.py # Claude 번역
│   │   └── models/
│   │       └── schemas.py       # Pydantic 스키마
│   ├── models/
│   │   └── mobile_sam.pt        # MobileSAM 모델 파일
│   ├── uploads/                 # 업로드된 이미지
│   ├── outputs/                 # 처리된 이미지
│   └── venv/                    # Python 가상환경
└── frontend/                    # Next.js 프론트엔드
```

## 처리 파이프라인

### 1. 말풍선 감지 (YOLOv8)
```python
# process.py:118-147
def detect_speech_bubbles(image_path: str, conf_threshold: float = 0.3) -> list:
    results = bubble_detector.predict(source=image_path, conf=conf_threshold, verbose=False)
    # 반환: [(x, y, w, h, None), ...] 바운딩 박스 리스트
```

### 2. 말풍선 세그멘테이션 (MobileSAM)
```python
# sam_service.py
class SAMService:
    def get_mask_from_box(self, box) -> np.ndarray:
        # YOLOv8 바운딩 박스로부터 정확한 말풍선 마스크 생성

    def create_text_mask_with_sam(self, image, boxes, threshold=180, dilate_iterations=2):
        # SAM 마스크 내부에서만 텍스트(어두운 픽셀) 감지
        # threshold 이하의 픽셀을 텍스트로 인식
```

### 3. 텍스트 추출 (manga-ocr)
```python
# ocr_service.py
class OCRService:
    def extract_from_pil(self, image: Image) -> str:
        # PIL 이미지에서 일본어 텍스트 추출
```

### 4. 번역 (Claude API)
```python
# translate_service.py
class TranslateService:
    async def translate_batch(self, texts: list, target_language: str) -> list:
        # 여러 텍스트를 한 번에 번역
```

### 5. 텍스트 제거 및 렌더링 (핵심 함수)
```python
# process.py:472-590
async def render_with_inpainting(image_path, items, output_path):
    # 1. SAM으로 텍스트 마스크 생성
    text_mask = sam_service.create_text_mask_with_sam(img_cv, boxes, threshold=180, dilate_iterations=3)

    # 2. SAM 마스크의 외곽 테두리만 추출 (텍스트 테두리 제외) ★중요★
    bubble_mask = sam_service.get_combined_bubble_mask(img_cv, boxes)
    eroded_mask = cv2.erode(bubble_mask, kernel, iterations=2)
    bubble_border = cv2.subtract(bubble_mask, eroded_mask)
    bubble_edges = cv2.bitwise_and(edges, bubble_border)

    # 3. OpenCV 인페인팅으로 텍스트 제거
    inpainted_img = await inpaint_service.remove_text(img_cv, text_mask)

    # 4. 원본 테두리 복원 (외곽선만)
    inpainted_img[bubble_edges > 0] = img_cv[bubble_edges > 0]

    # 5. 번역된 텍스트 렌더링
    for item in items:
        if is_vertical:
            render_vertical_text(draw, translated, inner_x, inner_y, inner_w, inner_h)
        else:
            render_horizontal_text(draw, translated, inner_x, inner_y, inner_w, inner_h)
```

## 해결한 주요 문제들

### 문제 1: 일본어 텍스트가 지워지지 않음
**증상**: 인페인팅 후에도 일본어 텍스트가 그대로 남아있음

**원인**: 테두리 복원 단계에서 Canny 에지 감지가 텍스트 테두리도 감지함
```python
# 기존 문제 코드
edges = cv2.Canny(gray, 50, 150)
bubble_edges = cv2.bitwise_and(edges, bubble_mask)  # 텍스트 에지도 포함됨
inpainted_img[bubble_edges > 0] = img_cv[bubble_edges > 0]  # 텍스트가 다시 복원됨
```

**해결**: SAM 마스크의 외곽선만 추출하여 내부 텍스트 테두리 제외
```python
# 수정된 코드
eroded_mask = cv2.erode(bubble_mask, kernel, iterations=2)
bubble_border = cv2.subtract(bubble_mask, eroded_mask)  # 외곽선만
bubble_edges = cv2.bitwise_and(edges, bubble_border)  # 외곽선의 에지만
```

### 문제 2: 텍스트가 말풍선을 벗어남
**해결**: 폰트 크기 제한 및 패딩 증가
```python
# render_horizontal_text
font_size = max(8, min(font_size, 14))  # 최대 14px

# render_vertical_text
font_size = max(8, min(font_size, 16))  # 최대 16px

# 패딩
padding = 12  # 말풍선 테두리와의 여백
```

### 문제 3: 말풍선이 네모 모양으로 변함
**원인**: 바운딩 박스를 흰색으로 채우는 방식 사용
**해결**: SAM + 인페인팅 방식으로 변경하여 원본 말풍선 형태 유지

## 핵심 파라미터

### SAM 텍스트 감지
- `threshold=180`: 이 값보다 어두운 픽셀을 텍스트로 인식
- `dilate_iterations=3`: 텍스트 마스크 확장 횟수

### 인페인팅
- `inpaintRadius=7`: OpenCV TELEA 인페인팅 반경
- `flags=cv2.INPAINT_TELEA`: 인페인팅 알고리즘

### 텍스트 렌더링
- 가로 폰트: 8-14px
- 세로 폰트: 8-16px
- 패딩: 12px
- 세로 판단 기준: `h > w * 1.5`

## 서버 실행

```bash
cd /home/pgchae/바탕화면/anume-trans/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API 엔드포인트

### POST /api/process
이미지 업로드 및 번역 처리
- Request: `multipart/form-data` (image, target_language, style)
- Response: `ProcessResponse` (job_id, texts, original_url, output_url)

### GET /api/download/{job_id}/{filename}
처리된 이미지 다운로드

### GET /health
서버 상태 확인

## 디버그 팁

### 디버그 이미지 확인
처리 시 다음 디버그 이미지가 생성됨:
- `outputs/{job_id}/debug_text_mask.png`: SAM 텍스트 마스크
- `outputs/{job_id}/debug_inpainted.png`: 인페인팅 결과 (텍스트 렌더링 전)

### 서버 로그 확인
```bash
tail -f /tmp/uvicorn.log | grep DEBUG
```

## 참고: 이전 작동했던 버전
`/home/pgchae/다운로드/translated (1).png` - 정상 작동 결과 예시

## 날짜
2026-01-06
