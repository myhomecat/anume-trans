# Anime/Manga Transformer

만화/애니메이션 이미지의 텍스트를 자동으로 번역하는 웹 애플리케이션

## 프로젝트 개요

### 목표
- 만화 이미지에서 텍스트(대사, 효과음 등)를 자동 감지
- 일본어 → 한국어 번역 (다른 언어 확장 가능)
- 원본 텍스트를 지우고 번역된 텍스트로 교체
- **완전 무료**로 운영 가능한 시스템

### 핵심 특징
- **Backend**: Python FastAPI (OCR, 이미지 처리, Claude CLI 호출)
- **Frontend**: Next.js (UI/UX)
- Claude Code CLI를 활용한 고품질 번역 (Claude Code Max 구독 범위 내 무료)
- Cloudflare Tunnel을 통한 외부 접속 지원

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (Browser)                         │
│                    외부 접속 / 로컬 접속                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ HTTPS
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Tunnel (무료)                      │
│                 https://your-domain.trycloudflare.com           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │
            ┌───────────────────┴───────────────────┐
            │                                       │
            ▼                                       ▼
┌───────────────────────┐             ┌───────────────────────────┐
│   Frontend (Next.js)  │             │   Backend (FastAPI)       │
│    localhost:3000     │────────────▶│    localhost:8000         │
│                       │    HTTP     │                           │
│  • UI/UX Components   │             │  • REST API               │
│  • 이미지 업로드       │             │  • manga-ocr (OCR)        │
│  • 결과 표시          │             │  • lama-cleaner (인페인팅) │
│  • 다운로드           │             │  • Pillow (텍스트 렌더링)  │
│                       │             │  • Claude CLI (번역)      │
└───────────────────────┘             └───────────────────────────┘
```

## 기술 스택

### Frontend (Next.js)
| 기술 | 용도 | 비용 |
|------|------|------|
| Next.js 14+ (App Router) | React 프레임워크 | 무료 |
| TypeScript | 타입 안전성 | 무료 |
| Tailwind CSS | 스타일링 | 무료 |
| Axios / Fetch | API 통신 | 무료 |

### Backend (Python FastAPI)
| 기술 | 용도 | 비용 |
|------|------|------|
| FastAPI | 웹 프레임워크 | 무료 |
| manga-ocr | 일본어 만화 OCR | 무료 |
| lama-cleaner | AI 텍스트 제거 | 무료 |
| Pillow | 이미지 처리 | 무료 |
| OpenCV | 이미지 처리 | 무료 |
| Claude Code CLI | 번역 엔진 | Max 구독 포함 |

### Infrastructure
| 기술 | 용도 | 비용 |
|------|------|------|
| Cloudflare Tunnel | 외부 접속 | 무료 |
| 로컬 서버 (내 PC) | 호스팅 | 무료 |

## 디렉토리 구조

```
anime-transformer/
├── frontend/                    # Next.js 프론트엔드
│   ├── app/
│   │   ├── page.tsx            # 메인 페이지
│   │   ├── layout.tsx          # 레이아웃
│   │   └── globals.css         # 글로벌 스타일
│   ├── components/
│   │   ├── ImageUploader.tsx   # 이미지 업로드
│   │   ├── ImagePreview.tsx    # 이미지 미리보기
│   │   ├── TranslationResult.tsx # 번역 결과
│   │   └── ProgressBar.tsx     # 진행 상태
│   ├── lib/
│   │   └── api-client.ts       # 백엔드 API 클라이언트
│   ├── package.json
│   └── next.config.js
│
├── backend/                     # Python FastAPI 백엔드
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 앱 진입점
│   │   ├── config.py           # 설정
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── translate.py    # 번역 API
│   │   │   ├── ocr.py          # OCR API
│   │   │   └── process.py      # 전체 파이프라인 API
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ocr_service.py      # manga-ocr 서비스
│   │   │   ├── translate_service.py # Claude CLI 번역
│   │   │   ├── inpaint_service.py  # 텍스트 제거
│   │   │   └── render_service.py   # 텍스트 렌더링
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── image_utils.py  # 이미지 유틸리티
│   ├── uploads/                # 업로드된 이미지
│   ├── outputs/                # 처리된 이미지
│   ├── fonts/                  # 한글 폰트
│   ├── requirements.txt        # Python 의존성
│   └── run.py                  # 서버 실행 스크립트
│
├── docker-compose.yml          # (선택) Docker 구성
└── README.md
```

## 처리 파이프라인

```
[원본 이미지 업로드]
        │
        ▼ (Frontend → Backend)
┌───────────────────────────────────────┐
│           Backend (FastAPI)           │
│                                       │
│  [1. 이미지 저장]                      │
│         │                             │
│         ▼                             │
│  [2. OCR - manga-ocr]                 │
│         │ 일본어 텍스트 추출            │
│         ▼                             │
│  [3. 번역 - Claude Code CLI]          │
│         │ 한국어로 번역                 │
│         ▼                             │
│  [4. 인페인팅 - lama-cleaner]         │
│         │ 원본 텍스트 제거              │
│         ▼                             │
│  [5. 렌더링 - Pillow]                 │
│         │ 번역된 텍스트 삽입            │
│         ▼                             │
│  [최종 이미지 저장]                    │
│                                       │
└───────────────────────────────────────┘
        │
        ▼ (Backend → Frontend)
[결과 이미지 표시 및 다운로드]
```

## 빠른 시작

### Backend 실행
```bash
cd backend

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend 실행
```bash
cd frontend

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

### 외부 접속 (선택)
```bash
# Frontend를 외부에 노출
cloudflared tunnel --url http://localhost:3000
```

## 포트 구성

| 서비스 | 포트 | 설명 |
|--------|------|------|
| Frontend (Next.js) | 3000 | 웹 UI |
| Backend (FastAPI) | 8000 | REST API |
| API Docs (Swagger) | 8000/docs | API 문서 자동 생성 |

## 관련 문서

- [CHECKLIST.md](./CHECKLIST.md) - 구현 체크리스트
- [TECHNICAL_SPEC.md](./TECHNICAL_SPEC.md) - 상세 기술 명세
- [SETUP_GUIDE.md](./SETUP_GUIDE.md) - 설치 및 배포 가이드
- [API_REFERENCE.md](./API_REFERENCE.md) - API 레퍼런스

## 라이선스

MIT License
