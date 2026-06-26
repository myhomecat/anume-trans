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
  original_url?: string;   // 원본 이미지 URL
  output_url?: string;     // 렌더링된 이미지 URL (선택적)
  image_width?: number;    // 이미지 너비
  image_height?: number;   // 이미지 높이
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

export interface BatchItemResult {
  filename: string;
  success: boolean;
  output_url?: string;
  texts?: TextItem[];
  image_width?: number;
  image_height?: number;
  error?: string;
}

export interface BatchResponse {
  success: boolean;
  batch_id: string;
  count: number;
  results: BatchItemResult[];
  zip_url?: string | null;
}

export interface JobResultItem {
  filename: string;
  success: boolean;
  output_url?: string;
  n_texts?: number;
  error?: string;
}

export interface JobStatus {
  job_id: string;
  status: 'queued' | 'processing' | 'done' | 'error';
  phase?: string;
  total: number;
  done: number;
  zip_url?: string | null;
  error?: string | null;
  results?: JobResultItem[];
}
