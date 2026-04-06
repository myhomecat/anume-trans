# Setup & Deployment Guide

이 문서는 Anime Transformer 프로젝트의 설치 및 배포 과정을 상세히 안내합니다.

---

## 목차

1. [사전 요구사항](#1-사전-요구사항)
2. [Backend 설정 (Python FastAPI)](#2-backend-설정-python-fastapi)
3. [Frontend 설정 (Next.js)](#3-frontend-설정-nextjs)
4. [통합 실행](#4-통합-실행)
5. [외부 접속 설정](#5-외부-접속-설정)
6. [프로덕션 배포](#6-프로덕션-배포)
7. [문제 해결](#7-문제-해결)

---

## 1. 사전 요구사항

### 1.1 필수 소프트웨어

#### Python (3.9 - 3.11)
```bash
# 버전 확인
python3 --version

# 설치 (macOS)
brew install python@3.11

# 설치 (Ubuntu/Debian)
sudo apt-get install python3.11 python3.11-venv python3-pip
```

#### Node.js (18.x 이상)
```bash
# 버전 확인
node --version

# 설치 (macOS)
brew install node

# 설치 (Ubuntu/Debian)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

#### Claude Code CLI
```bash
# 설치
npm install -g @anthropic-ai/claude-code

# 로그인
claude login

# 버전 확인
claude --version
```

### 1.2 프로젝트 디렉토리 생성

```bash
mkdir -p anime-transformer/{frontend,backend}
cd anime-transformer
```

---

## 2. Backend 설정 (Python FastAPI)

### 2.1 디렉토리 이동 및 가상환경 생성

```bash
cd backend

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

### 2.2 requirements.txt 생성

```bash
cat > requirements.txt << 'EOF'
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# OCR
manga-ocr==0.1.8
torch>=2.0.0
torchvision>=0.15.0

# Image Processing
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
aiofiles==23.2.1
EOF
```

### 2.3 의존성 설치

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **참고**: manga-ocr 설치 시 PyTorch가 함께 설치됩니다. 시간이 다소 걸릴 수 있습니다.

### 2.4 디렉토리 구조 생성

```bash
mkdir -p app/{routers,services,models,utils}
mkdir -p uploads outputs fonts

touch app/__init__.py
touch app/routers/__init__.py
touch app/services/__init__.py
touch app/models/__init__.py
touch app/utils/__init__.py
```

### 2.5 환경 변수 설정

```bash
cat > .env << 'EOF'
# 서버 설정
DEBUG=true
HOST=0.0.0.0
PORT=8000

# API 인증 (비워두면 인증 비활성화)
API_SECRET_KEY=

# Frontend URL (CORS)
FRONTEND_URL=http://localhost:3000

# Claude CLI 타임아웃 (초)
CLAUDE_TIMEOUT=60
EOF
```

### 2.6 한글 폰트 설정

```bash
# 나눔고딕 폰트 다운로드 (예시)
# 직접 다운로드하여 fonts/ 디렉토리에 배치

# macOS 시스템 폰트 사용 가능
# 경로: /System/Library/Fonts/AppleSDGothicNeo.ttc

# Linux의 경우 나눔폰트 설치
# sudo apt-get install fonts-nanum
```

### 2.7 서버 실행 테스트

```bash
# 간단한 테스트 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

접속 확인:
- http://localhost:8000 - API 루트
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/health - 헬스체크

---

## 3. Frontend 설정 (Next.js)

### 3.1 프로젝트 초기화

```bash
cd ../frontend

# Next.js 프로젝트 생성
npx create-next-app@latest . \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*"
```

### 3.2 추가 의존성 설치

```bash
npm install react-dropzone
```

### 3.3 환경 변수 설정

```bash
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

### 3.4 개발 서버 실행

```bash
npm run dev
```

접속 확인:
- http://localhost:3000

---

## 4. 통합 실행

### 4.1 터미널 2개로 실행

**터미널 1 (Backend):**
```bash
cd anime-transformer/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**터미널 2 (Frontend):**
```bash
cd anime-transformer/frontend
npm run dev
```

### 4.2 실행 스크립트 (선택)

프로젝트 루트에 실행 스크립트 생성:

```bash
# anime-transformer/start.sh
cat > start.sh << 'EOF'
#!/bin/bash

# Backend 시작 (백그라운드)
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Frontend 시작 (백그라운드)
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"

# Ctrl+C 시 정리
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

# 대기
wait
EOF

chmod +x start.sh
```

---

## 5. 외부 접속 설정

### 5.1 Cloudflare Tunnel (추천)

#### 설치

```bash
# macOS
brew install cloudflared

# Linux (amd64)
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/
```

#### 빠른 시작 (임시 URL)

```bash
# Frontend 터널 (별도 터미널)
cloudflared tunnel --url http://localhost:3000
```

출력 예시:
```
Your quick Tunnel has been created! Visit it at:
https://random-words.trycloudflare.com
```

#### 주의사항
- Backend API도 외부에서 접근 가능해야 함
- Frontend의 환경변수에서 API URL을 터널 URL로 변경 필요

### 5.2 두 서비스 모두 터널링

```bash
# 터미널 1: Backend 터널
cloudflared tunnel --url http://localhost:8000

# 터미널 2: Frontend 터널
cloudflared tunnel --url http://localhost:3000
```

Frontend `.env.local` 수정:
```bash
NEXT_PUBLIC_API_URL=https://backend-tunnel-url.trycloudflare.com
```

### 5.3 영구 터널 설정

1. Cloudflare 계정 로그인
```bash
cloudflared tunnel login
```

2. 터널 생성
```bash
cloudflared tunnel create anime-transformer
```

3. 설정 파일 생성 (`~/.cloudflared/config.yml`)
```yaml
tunnel: <TUNNEL_ID>
credentials-file: ~/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: manga-api.yourdomain.com
    service: http://localhost:8000
  - hostname: manga.yourdomain.com
    service: http://localhost:3000
  - service: http_status:404
```

4. DNS 라우팅
```bash
cloudflared tunnel route dns anime-transformer manga.yourdomain.com
cloudflared tunnel route dns anime-transformer manga-api.yourdomain.com
```

5. 터널 실행
```bash
cloudflared tunnel run anime-transformer
```

---

## 6. 프로덕션 배포

### 6.1 Backend 프로덕션 설정

**.env 수정:**
```bash
DEBUG=false
API_SECRET_KEY=your-secure-secret-key
```

**Gunicorn으로 실행 (권장):**
```bash
pip install gunicorn

gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 6.2 Frontend 프로덕션 빌드

```bash
cd frontend

# 빌드
npm run build

# 프로덕션 서버 실행
npm run start
```

### 6.3 systemd 서비스 (Linux)

**Backend 서비스:**
```bash
sudo cat > /etc/systemd/system/anime-backend.service << 'EOF'
[Unit]
Description=Anime Transformer Backend
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/anime-transformer/backend
Environment=PATH=/path/to/anime-transformer/backend/venv/bin
ExecStart=/path/to/anime-transformer/backend/venv/bin/gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable anime-backend
sudo systemctl start anime-backend
```

**Frontend 서비스:**
```bash
sudo cat > /etc/systemd/system/anime-frontend.service << 'EOF'
[Unit]
Description=Anime Transformer Frontend
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/anime-transformer/frontend
ExecStart=/usr/bin/npm start
Restart=on-failure
RestartSec=10
Environment=NODE_ENV=production
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable anime-frontend
sudo systemctl start anime-frontend
```

### 6.4 PM2 사용 (대안)

```bash
npm install -g pm2

# Backend
cd backend
source venv/bin/activate
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name anime-backend

# Frontend
cd ../frontend
pm2 start npm --name anime-frontend -- start

# 상태 확인
pm2 status

# 자동 시작 설정
pm2 startup
pm2 save
```

---

## 7. 문제 해결

### 7.1 manga-ocr 설치 실패

**증상:** `pip install manga-ocr` 실패

**해결:**
```bash
# PyTorch 먼저 설치
pip install torch torchvision

# 그 다음 manga-ocr 설치
pip install manga-ocr
```

### 7.2 Claude Code CLI 응답 없음

**증상:** Claude CLI 호출 후 응답이 없거나 타임아웃

**해결:**
```bash
# 로그인 상태 확인
claude whoami

# 재로그인
claude logout
claude login

# 테스트
claude -p "Hello" --output-format text
```

### 7.3 CORS 에러

**증상:** Frontend에서 "CORS policy" 에러

**해결:**
Backend `app/main.py`의 CORS 설정 확인:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend-domain.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 7.4 한글 깨짐

**증상:** 렌더링된 텍스트가 깨져서 표시

**해결:**
1. fonts/ 디렉토리에 한글 폰트 파일 존재 확인
2. config.py의 FONT_DIR 경로 확인
3. 시스템 폰트 경로 확인:
   - macOS: `/System/Library/Fonts/AppleSDGothicNeo.ttc`
   - Linux: `/usr/share/fonts/truetype/nanum/`
   - Windows: `C:\Windows\Fonts\malgun.ttf`

### 7.5 포트 충돌

**증상:** "Address already in use" 에러

**해결:**
```bash
# 포트 사용 확인
lsof -i :8000
lsof -i :3000

# 프로세스 종료
kill -9 <PID>
```

### 7.6 메모리 부족

**증상:** manga-ocr 실행 중 메모리 에러

**해결:**
```bash
# 스왑 메모리 추가 (Linux)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 7.7 이미지 업로드 실패

**증상:** 413 Payload Too Large

**해결:**
- Backend: MAX_FILE_SIZE 설정 확인
- Frontend: next.config.js에서 크기 제한 확인

---

## 빠른 시작 스크립트

전체 설정을 자동화하는 스크립트:

```bash
#!/bin/bash
# setup.sh

set -e

echo "=== Anime Transformer Setup ==="

# 프로젝트 디렉토리 생성
mkdir -p anime-transformer/{frontend,backend}
cd anime-transformer

# Backend 설정
echo "Setting up Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate

cat > requirements.txt << 'EOF'
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
manga-ocr==0.1.8
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
aiofiles==23.2.1
EOF

pip install --upgrade pip
pip install -r requirements.txt

mkdir -p app/{routers,services,models,utils}
mkdir -p uploads outputs fonts

cat > .env << 'EOF'
DEBUG=true
FRONTEND_URL=http://localhost:3000
CLAUDE_TIMEOUT=60
EOF

# Frontend 설정
echo "Setting up Frontend..."
cd ../frontend
npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*" --yes
npm install react-dropzone

echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Implement Backend code in backend/app/"
echo "2. Implement Frontend code in frontend/src/"
echo "3. Run Backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "4. Run Frontend: cd frontend && npm run dev"
```

실행:
```bash
chmod +x setup.sh
./setup.sh
```
