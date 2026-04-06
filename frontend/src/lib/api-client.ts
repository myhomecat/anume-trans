import { ProcessResponse, TranslateResponse, TranslateRequest, OCRResponse, TranslateStyle } from './types';

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

export async function checkHealth(): Promise<{ status: string; ocr_loaded: boolean }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
}
