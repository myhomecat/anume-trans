import { ProcessResponse, TranslateResponse, TranslateRequest, OCRResponse, TranslateStyle, BatchResponse, JobStatus } from './types';

// same-origin: 브라우저는 자기 Next(BFF)만 호출, Next가 분석기로 중계
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

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

export async function checkHealth(): Promise<{ status: string; ocr_loaded: boolean }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}

export async function processBatch(
  files: File[],
  targetLanguage: string = '한국어',
  style: string = 'manga'
): Promise<BatchResponse> {
  const formData = new FormData();
  files.forEach((f) => formData.append('images', f));
  formData.append('target_language', targetLanguage);
  formData.append('style', style);

  const response = await fetch(`${API_BASE_URL}/api/process/batch`, {
    method: 'POST',
    body: formData,
  });

  return response.json();
}

export async function submitBatchAsync(
  files: File[],
  opts: { email?: string; targetLanguage?: string; style?: string } = {}
): Promise<{ job_id: string; status: string; total: number }> {
  const formData = new FormData();
  files.forEach((f) => formData.append('images', f));
  formData.append('target_language', opts.targetLanguage || '한국어');
  formData.append('style', opts.style || 'manga');
  formData.append('email', opts.email || '');

  const response = await fetch(`${API_BASE_URL}/api/process/batch/async`, {
    method: 'POST',
    body: formData,
  });
  return response.json();
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/job/${jobId}`);
  return response.json();
}

export async function getVapidKey(): Promise<string> {
  const r = await fetch(`${API_BASE_URL}/api/push/key`);
  const d = await r.json();
  return d.publicKey;
}

export async function subscribePush(jobId: string, subscription: PushSubscription): Promise<void> {
  await fetch(`${API_BASE_URL}/api/push/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, subscription }),
  });
}
