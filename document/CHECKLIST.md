# Implementation Checklist

다른 Claude Code 세션에서 이 프로젝트를 구현할 때 사용할 체크리스트입니다.

---

## Phase 1: 환경 설정

### 1.1 시스템 요구사항 확인
- [ ] Python 3.9-3.11 설치 확인 (`python3 --version`)
- [ ] Node.js 18+ 설치 확인 (`node --version`)
- [ ] Claude Code CLI 설치 확인 (`claude --version`)
- [ ] Git 설치 확인 (`git --version`)

### 1.2 프로젝트 디렉토리 생성
```bash
mkdir -p anime-transformer/{frontend,backend}
cd anime-transformer
```

---

## Phase 2: Backend 구현 (Python FastAPI)

### 2.1 Backend 초기화
- [ ] backend 디렉토리 이동
  ```bash
  cd backend
  ```
- [ ] 가상환경 생성 및 활성화
  ```bash
  python3 -m venv venv
  source venv/bin/activate  # Windows: venv\Scripts\activate
  ```
- [ ] requirements.txt 생성
  ```bash
  cat > requirements.txt << 'EOF'
  fastapi==0.109.0
  uvicorn[standard]==0.27.0
  python-multipart==0.0.6
  manga-ocr==0.1.8
  torch>=2.0.0
  torchvision>=0.15.0
  Pillow>=10.0.0
  opencv-python>=4.8.0
  numpy>=1.24.0
  python-dotenv==1.0.0
  pydantic==2.5.0
  pydantic-settings==2.1.0
  aiofiles==23.2.1
  EOF
  ```
- [ ] 의존성 설치
  ```bash
  pip install -r requirements.txt
  ```

### 2.2 디렉토리 구조 생성
- [ ] 필요한 디렉토리 생성
  ```bash
  mkdir -p app/{routers,services,models,utils}
  mkdir -p uploads outputs fonts
  touch app/__init__.py
  touch app/routers/__init__.py
  touch app/services/__init__.py
  touch app/models/__init__.py
  touch app/utils/__init__.py
  ```

### 2.3 설정 파일 작성
- [ ] `app/config.py` 작성
- [ ] `.env` 파일 생성
  ```bash
  cat > .env << 'EOF'
  DEBUG=true
  API_SECRET_KEY=
  FRONTEND_URL=http://localhost:3000
  CLAUDE_TIMEOUT=60
  EOF
  ```

### 2.4 Pydantic 스키마 작성
- [ ] `app/models/schemas.py` 작성
  - [ ] TextType, TranslateStyle Enum
  - [ ] Region, TextItem 모델
  - [ ] TranslateRequest/Response 모델
  - [ ] ProcessResponse 모델

### 2.5 서비스 레이어 구현
- [ ] `app/services/ocr_service.py` 작성
  - [ ] OCRService 클래스
  - [ ] extract_text() 메서드
  - [ ] extract_from_regions() 메서드
- [ ] `app/services/translate_service.py` 작성
  - [ ] TranslateService 클래스
  - [ ] translate() 메서드 (Claude CLI 호출)
  - [ ] translate_batch() 메서드
  - [ ] analyze_and_translate_image() 메서드
  - [ ] _call_claude() 프라이빗 메서드
- [ ] `app/services/inpaint_service.py` 작성
  - [ ] InpaintService 클래스
  - [ ] create_mask() 메서드
  - [ ] inpaint_opencv() 메서드
- [ ] `app/services/render_service.py` 작성
  - [ ] RenderService 클래스
  - [ ] get_font() 메서드
  - [ ] calculate_font_size() 메서드
  - [ ] render_text() 메서드

### 2.6 라우터 구현
- [ ] `app/routers/process.py` 작성
  - [ ] POST /api/process 엔드포인트
  - [ ] GET /api/download/{job_id}/{filename} 엔드포인트
- [ ] `app/routers/translate.py` 작성
  - [ ] POST /api/translate 엔드포인트
  - [ ] POST /api/translate/batch 엔드포인트
- [ ] `app/routers/ocr.py` 작성
  - [ ] POST /api/ocr 엔드포인트

### 2.7 메인 앱 구현
- [ ] `app/main.py` 작성
  - [ ] FastAPI 앱 인스턴스
  - [ ] CORS 미들웨어 설정
  - [ ] 라우터 등록
  - [ ] 정적 파일 서빙 (outputs)
  - [ ] lifespan 이벤트 (OCR 모델 로드)
  - [ ] 헬스체크 엔드포인트

### 2.8 실행 스크립트
- [ ] `run.py` 작성
- [ ] 서버 실행 테스트
  ```bash
  python run.py
  # 또는
  uvicorn app.main:app --reload --port 8000
  ```

### 2.9 Backend 테스트
- [ ] http://localhost:8000 접속 확인
- [ ] http://localhost:8000/docs Swagger UI 확인
- [ ] /health 엔드포인트 테스트
- [ ] /api/translate 엔드포인트 테스트
  ```bash
  curl -X POST http://localhost:8000/api/translate \
    -H "Content-Type: application/json" \
    -d '{"text": "こんにちは"}'
  ```

---

## Phase 3: Frontend 구현 (Next.js)

### 3.1 Frontend 초기화
- [ ] frontend 디렉토리 이동
  ```bash
  cd ../frontend
  ```
- [ ] Next.js 프로젝트 생성
  ```bash
  npx create-next-app@latest . --typescript --tailwind --app --src-dir --import-alias "@/*"
  ```

### 3.2 의존성 설치
- [ ] 추가 패키지 설치
  ```bash
  npm install react-dropzone
  ```

### 3.3 환경 변수 설정
- [ ] `.env.local` 파일 생성
  ```bash
  echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
  ```

### 3.4 API 클라이언트 작성
- [ ] `src/lib/api-client.ts` 작성
  - [ ] processImage() 함수
  - [ ] translateText() 함수
  - [ ] getOutputUrl() 함수
  - [ ] TypeScript 인터페이스 정의

### 3.5 컴포넌트 구현
- [ ] `src/components/ImageUploader.tsx` 작성
  - [ ] react-dropzone 사용
  - [ ] 드래그 앤 드롭 지원
  - [ ] 파일 유효성 검사
- [ ] `src/components/ImagePreview.tsx` 작성
  - [ ] 이미지 표시
  - [ ] 라벨 표시
- [ ] `src/components/TranslationResult.tsx` 작성
  - [ ] 번역 텍스트 목록 표시
  - [ ] 원본/번역 비교
- [ ] `src/components/ProgressBar.tsx` 작성 (선택)
  - [ ] 처리 진행 상태 표시

### 3.6 메인 페이지 구현
- [ ] `src/app/page.tsx` 작성
  - [ ] 상태 관리 (useState)
  - [ ] 이미지 업로드 처리
  - [ ] API 호출 및 결과 표시
  - [ ] 에러 처리
  - [ ] 다운로드 기능

### 3.7 스타일링
- [ ] `src/app/globals.css` 수정
- [ ] Tailwind 클래스 적용

### 3.8 설정 파일 수정
- [ ] `next.config.js` 수정
  - [ ] 이미지 도메인 설정
  - [ ] 환경 변수 설정

### 3.9 Frontend 테스트
- [ ] 개발 서버 실행
  ```bash
  npm run dev
  ```
- [ ] http://localhost:3000 접속 확인
- [ ] 이미지 업로드 테스트
- [ ] Backend API 연동 테스트

---

## Phase 4: 통합 테스트

### 4.1 전체 플로우 테스트
- [ ] Backend 실행 (포트 8000)
- [ ] Frontend 실행 (포트 3000)
- [ ] 만화 이미지 업로드
- [ ] OCR 결과 확인
- [ ] 번역 결과 확인
- [ ] 결과 이미지 다운로드

### 4.2 에러 케이스 테스트
- [ ] 잘못된 파일 형식 업로드
- [ ] 너무 큰 파일 업로드
- [ ] Backend 중지 상태에서 요청
- [ ] Claude CLI 타임아웃

### 4.3 성능 테스트
- [ ] 이미지 처리 시간 측정
- [ ] 메모리 사용량 확인

---

## Phase 5: 배포 설정

### 5.1 한글 폰트 설정
- [ ] 나눔고딕 폰트 다운로드
- [ ] `backend/fonts/` 디렉토리에 복사
- [ ] config.py에서 경로 확인

### 5.2 프로덕션 빌드
- [ ] Frontend 빌드
  ```bash
  cd frontend
  npm run build
  ```
- [ ] Backend 프로덕션 설정
  ```bash
  # .env 수정
  DEBUG=false
  ```

### 5.3 Cloudflare Tunnel 설정 (외부 접속)
- [ ] cloudflared 설치
  ```bash
  # macOS
  brew install cloudflared

  # Linux
  curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
  chmod +x cloudflared
  ```
- [ ] 터널 실행
  ```bash
  # Frontend 터널
  cloudflared tunnel --url http://localhost:3000
  ```

### 5.4 프로세스 관리
- [ ] Backend 서비스화 (선택)
  ```bash
  # systemd 또는 PM2 사용
  ```
- [ ] Frontend 서비스화 (선택)

---

## Phase 6: 문서화 및 마무리

### 6.1 README 작성
- [ ] 프로젝트 설명
- [ ] 설치 방법
- [ ] 사용 방법
- [ ] 스크린샷

### 6.2 코드 정리
- [ ] 불필요한 코드 제거
- [ ] 주석 추가
- [ ] 타입 힌트 확인

### 6.3 Git 설정
- [ ] .gitignore 설정
  ```bash
  cat > .gitignore << 'EOF'
  # Python
  venv/
  __pycache__/
  *.pyc
  .env

  # Node
  node_modules/
  .next/
  .env.local

  # Uploads/Outputs
  uploads/
  outputs/

  # IDE
  .vscode/
  .idea/
  EOF
  ```
- [ ] 초기 커밋

---

## Quick Start 명령어 모음

### Backend 시작
```bash
cd backend
source venv/bin/activate
python run.py
```

### Frontend 시작
```bash
cd frontend
npm run dev
```

### 외부 접속 (Cloudflare Tunnel)
```bash
cloudflared tunnel --url http://localhost:3000
```

---

## 트러블슈팅

### manga-ocr 설치 실패
```bash
# PyTorch 먼저 설치
pip install torch torchvision
pip install manga-ocr
```

### Claude CLI 응답 없음
```bash
# 로그인 상태 확인
claude whoami

# 재로그인
claude logout && claude login
```

### CORS 에러
- Backend의 CORS 설정 확인
- Frontend URL이 allow_origins에 포함되어 있는지 확인

### 한글 폰트 렌더링 문제
- fonts/ 디렉토리에 폰트 파일 존재 확인
- config.py의 FONT_DIR 경로 확인

### 포트 충돌
```bash
# 포트 사용 확인
lsof -i :8000
lsof -i :3000

# 프로세스 종료
kill -9 <PID>
```
