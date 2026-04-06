# API Reference

Backend API (FastAPI) 엔드포인트 문서입니다.

**Base URL:** `http://localhost:8000`

**API 문서 (자동 생성):**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 인증

API 키가 설정된 경우 `X-API-Key` 헤더가 필요합니다:

```
X-API-Key: your-api-secret-key
```

> 환경변수 `API_SECRET_KEY`가 비어있으면 인증이 비활성화됩니다.

---

## Endpoints

### 헬스체크

#### GET /health

서버 상태 확인

**Response:**
```json
{
  "status": "healthy",
  "ocr_loaded": true
}
```

---

### 전체 처리 파이프라인

#### POST /api/process

만화 이미지를 업로드하고 OCR → 번역 → 이미지 처리 파이프라인을 실행합니다.

**Request:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `image` | File | 필수 | 만화 이미지 (PNG, JPG, WebP) |
| `target_language` | string | 선택 | 목표 언어 (기본값: "한국어") |
| `style` | string | 선택 | 번역 스타일: "formal", "casual", "manga" (기본값: "manga") |

**cURL 예시:**
```bash
curl -X POST http://localhost:8000/api/process \
  -F "image=@/path/to/manga.jpg" \
  -F "target_language=한국어" \
  -F "style=manga"
```

**Response (성공):**
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "texts": [
    {
      "original": "おはよう",
      "translated": "좋은 아침",
      "location": "상단 왼쪽 말풍선",
      "type": "dialogue"
    },
    {
      "original": "ドキドキ",
      "translated": "두근두근",
      "location": "중앙 효과음",
      "type": "sfx"
    }
  ],
  "output_url": "/outputs/550e8400-e29b-41d4-a716-446655440000/final.png"
}
```

**Response (실패):**
```json
{
  "success": false,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "texts": null,
  "output_url": null,
  "error": "Claude CLI timeout after 60s"
}
```

---

### 파일 다운로드

#### GET /api/download/{job_id}/{filename}

처리된 이미지를 다운로드합니다.

**Parameters:**

| 파라미터 | 설명 |
|----------|------|
| `job_id` | 작업 ID |
| `filename` | 파일명 (예: "final.png") |

**cURL 예시:**
```bash
curl -O http://localhost:8000/api/download/550e8400-e29b-41d4-a716-446655440000/final.png
```

**Response:**
- 성공: 이미지 파일 (Content-Type: image/png)
- 실패 (404): `{"detail": "File not found"}`

---

### 텍스트 번역

#### POST /api/translate

텍스트만 번역합니다 (이미지 처리 없음).

**Request Body:**
```json
{
  "text": "おはようございます",
  "source_language": "일본어",
  "target_language": "한국어",
  "style": "manga",
  "context": "학원물 만화, 여고생 캐릭터"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `text` | string | 필수 | 번역할 텍스트 |
| `source_language` | string | 선택 | 원본 언어 (기본값: "일본어") |
| `target_language` | string | 선택 | 목표 언어 (기본값: "한국어") |
| `style` | string | 선택 | 번역 스타일 (기본값: "manga") |
| `context` | string | 선택 | 추가 컨텍스트 정보 |

**cURL 예시:**
```bash
curl -X POST http://localhost:8000/api/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは", "target_language": "한국어"}'
```

**Response:**
```json
{
  "success": true,
  "translation": "안녕하세요"
}
```

---

#### POST /api/translate/batch

여러 텍스트를 한 번에 번역합니다.

**Request Body:**
```json
{
  "texts": [
    "おはよう",
    "こんにちは",
    "さようなら"
  ],
  "target_language": "한국어",
  "style": "manga"
}
```

**Response:**
```json
{
  "success": true,
  "translations": [
    "좋은 아침",
    "안녕",
    "안녕히 가"
  ]
}
```

---

### OCR

#### POST /api/ocr

이미지에서 텍스트만 추출합니다.

**Request:**

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `image` | File | 필수 | OCR할 이미지 |

**cURL 예시:**
```bash
curl -X POST http://localhost:8000/api/ocr \
  -F "image=@/path/to/image.jpg"
```

**Response:**
```json
{
  "success": true,
  "text": "抽出されたテキスト"
}
```

---

## 정적 파일

### GET /outputs/{job_id}/{filename}

처리된 결과 이미지에 직접 접근합니다.

**예시:**
```
http://localhost:8000/outputs/550e8400-e29b-41d4-a716-446655440000/final.png
```

---

## 데이터 타입

### TextType (Enum)

```python
class TextType(str, Enum):
    DIALOGUE = "dialogue"    # 대사
    SFX = "sfx"              # 효과음
    NARRATION = "narration"  # 나레이션
```

### TranslateStyle (Enum)

```python
class TranslateStyle(str, Enum):
    FORMAL = "formal"   # 존댓말, 격식체
    CASUAL = "casual"   # 반말, 비격식체
    MANGA = "manga"     # 만화 대사체
```

### Region

```python
class Region(BaseModel):
    x: int         # X 좌표
    y: int         # Y 좌표
    width: int     # 너비
    height: int    # 높이
```

### TextItem

```python
class TextItem(BaseModel):
    original: str           # 원본 텍스트
    translated: str         # 번역된 텍스트
    location: str           # 위치 설명
    type: TextType          # 텍스트 유형
    region: Optional[Region] # 좌표 (선택)
```

---

## 에러 코드

| HTTP Status | 설명 |
|-------------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 (파일 없음, 잘못된 형식) |
| 401 | 인증 실패 |
| 404 | 리소스를 찾을 수 없음 |
| 413 | 파일 크기 초과 |
| 500 | 서버 내부 에러 |

---

## Frontend에서 사용하기

### TypeScript 타입 정의

```typescript
// types/api.ts

export type TextType = 'dialogue' | 'sfx' | 'narration';
export type TranslateStyle = 'formal' | 'casual' | 'manga';

export interface Region {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface TextItem {
  original: string;
  translated: string;
  location: string;
  type: TextType;
  region?: Region;
}

export interface ProcessResponse {
  success: boolean;
  job_id: string;
  texts?: TextItem[];
  output_url?: string;
  error?: string;
}

export interface TranslateRequest {
  text: string;
  source_language?: string;
  target_language?: string;
  style?: TranslateStyle;
  context?: string;
}

export interface TranslateResponse {
  success: boolean;
  translation?: string;
  error?: string;
}

export interface OCRResponse {
  success: boolean;
  text?: string;
  error?: string;
}
```

### API 클라이언트 예시

```typescript
// lib/api-client.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function processImage(
  file: File,
  targetLanguage: string = '한국어',
  style: string = 'manga'
): Promise<ProcessResponse> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('target_language', targetLanguage);
  formData.append('style', style);

  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: 'POST',
    body: formData,
  });

  return response.json();
}

export async function translateText(
  text: string,
  options: Partial<TranslateRequest> = {}
): Promise<TranslateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      target_language: '한국어',
      style: 'manga',
      ...options,
    }),
  });

  return response.json();
}

export async function extractText(file: File): Promise<OCRResponse> {
  const formData = new FormData();
  formData.append('image', file);

  const response = await fetch(`${API_BASE_URL}/api/ocr`, {
    method: 'POST',
    body: formData,
  });

  return response.json();
}

export function getOutputUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}
```

### React 사용 예시

```tsx
import { useState } from 'react';
import { processImage, getOutputUrl } from '@/lib/api-client';

export default function TranslateForm() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!file) return;

    setLoading(true);
    try {
      const response = await processImage(file);

      if (response.success) {
        setResult({
          texts: response.texts,
          imageUrl: getOutputUrl(response.output_url),
        });
      } else {
        alert(response.error);
      }
    } catch (err) {
      alert('서버 연결 실패');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? '처리 중...' : '번역하기'}
      </button>

      {result && (
        <div>
          <img src={result.imageUrl} alt="Translated" />
          <ul>
            {result.texts.map((t, i) => (
              <li key={i}>
                {t.original} → {t.translated}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

---

## Rate Limiting (선택적)

프로덕션 환경에서 권장되는 Rate Limiting 설정:

```python
# app/dependencies.py

from fastapi import Request, HTTPException
from collections import defaultdict
import time

# 간단한 인메모리 Rate Limiter
request_counts = defaultdict(list)
RATE_LIMIT = 10  # 분당 최대 요청 수

async def rate_limiter(request: Request):
    client_ip = request.client.host
    current_time = time.time()

    # 1분 이내 요청만 유지
    request_counts[client_ip] = [
        t for t in request_counts[client_ip]
        if current_time - t < 60
    ]

    if len(request_counts[client_ip]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    request_counts[client_ip].append(current_time)
```

사용:
```python
from fastapi import Depends

@router.post("/api/process")
async def process_image(
    ...,
    _: None = Depends(rate_limiter)
):
    ...
```
