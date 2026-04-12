# Anume Trans (만화 자동 번역기)

일본어 만화를 한국어로 자동 번역하는 웹 애플리케이션. 말풍선을 감지하고, 텍스트를 추출하고, 번역해서 원본 이미지에 합성한다.

## 왜 만들었나

일본 만화를 원서로 읽고 싶은데, 모르는 단어가 나올 때마다 사전 찾기가 귀찮더라.

기존 번역기들은 전체 페이지를 통으로 번역하거나, 말풍선 위치를 무시하고 텍스트만 뽑더라.

말풍선 단위로 감지 → OCR → 번역 → 원본 위치에 합성까지 자동으로 해주는 게 없더라.

그래서 내가 만들기로 했어.

## 동작 방식

```
만화 이미지 업로드
    ↓
말풍선 감지 (YOLOv8 커스텀 모델)
    ↓
텍스트 추출 (manga-ocr)
    ↓
일본어 → 한국어 번역 (Claude API)
    ↓
원본 텍스트 제거 + 한국어 텍스트 합성
    ↓
번역된 이미지 출력
```

## 기술 스택

### Backend
- Python 3.11, FastAPI
- YOLOv8 — 말풍선 영역 감지 (커스텀 학습 모델)
- manga-ocr — 일본어 OCR (torch 기반)
- Claude API — 일→한 번역
- OpenCV, Pillow — 이미지 처리 (텍스트 제거 + 렌더링)

### Frontend
- Next.js, TypeScript
- 이미지 업로드 + 번역 결과 미리보기 UI

## 프로젝트 구조

```
backend/
├── app/              # FastAPI 앱
│   ├── routers/      # API 엔드포인트 (process, translate, ocr)
│   ├── services/     # OCR, 번역, 인페인팅, 렌더링 서비스
│   └── models/       # Pydantic 스키마
├── bubble-detector/  # YOLOv8 말풍선 감지 모델
├── models/           # 학습된 모델 파일
└── run.py

frontend/
├── src/
│   ├── app/          # Next.js 앱
│   ├── components/   # UI 컴포넌트
│   └── lib/          # 유틸리티
```

## 테스트 결과

73장 이상의 만화 이미지로 파이프라인 테스트 완료.
