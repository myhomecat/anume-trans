'use client';

import { useState } from 'react';
import ImageUploader from '@/components/ImageUploader';
import ProgressBar from '@/components/ProgressBar';
import { processBatch, getOutputUrl } from '@/lib/api-client';
import { BatchResponse } from '@/lib/types';

interface Picked {
  file: File;
  url: string;
}

export default function Home() {
  const [picked, setPicked] = useState<Picked[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [batch, setBatch] = useState<BatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFilesSelect = (files: File[]) => {
    setPicked((prev) => {
      const seen = new Set(prev.map((p) => `${p.file.name}:${p.file.size}`));
      const added = files
        .filter((f) => !seen.has(`${f.name}:${f.size}`))
        .map((f) => ({ file: f, url: URL.createObjectURL(f) }));
      return [...prev, ...added];
    });
    setBatch(null);
    setError(null);
    setProgress(0);
  };

  const removeAt = (idx: number) => {
    setPicked((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleProcess = async () => {
    if (picked.length === 0) return;
    setIsProcessing(true);
    setError(null);
    setBatch(null);
    setProgress(20);
    setCurrentStep(`${picked.length}장 처리 중 (감지·OCR·번역·렌더링)...`);
    try {
      const res = await processBatch(picked.map((p) => p.file));
      setProgress(100);
      setCurrentStep('완료!');
      if (res.success) {
        setBatch(res);
      } else {
        setError('처리 중 오류가 발생했습니다.');
      }
    } catch {
      setError('서버 연결에 실패했습니다. 분석기 서버가 실행 중인지 확인해주세요.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setPicked([]);
    setBatch(null);
    setError(null);
    setProgress(0);
    setCurrentStep('');
  };

  const successResults = batch?.results.filter((r) => r.success && r.output_url) ?? [];

  return (
    <main className="min-h-screen p-4 md:p-8 bg-gray-100">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Anime/Manga Translator</h1>
          <p className="text-gray-600">
            만화 이미지를 여러 장 업로드하면 자동 감지·번역 후 파일로 내려받습니다 (여러 장은 ZIP)
          </p>
        </div>

        {/* 업로드 영역 */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">원본 이미지 업로드</h2>
          <ImageUploader onFilesSelect={handleFilesSelect} />

          {picked.length > 0 && (
            <div className="mt-4">
              <p className="text-sm text-gray-600 mb-2">{picked.length}장 선택됨</p>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
                {picked.map((p, i) => (
                  <div key={`${p.file.name}-${i}`} className="relative group">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={p.url} alt={p.file.name} className="w-full h-24 object-cover rounded border" />
                    <button
                      onClick={() => removeAt(i)}
                      className="absolute top-1 right-1 bg-black/60 text-white rounded-full w-5 h-5 text-xs leading-5 opacity-0 group-hover:opacity-100 transition-opacity"
                      aria-label="remove"
                    >
                      ×
                    </button>
                    <p className="text-[10px] text-gray-500 truncate mt-1">{p.file.name}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {isProcessing && (
            <div className="mt-4">
              <ProgressBar progress={progress} currentStep={currentStep} />
            </div>
          )}

          <div className="flex gap-2 mt-4">
            <button
              onClick={handleProcess}
              disabled={picked.length === 0 || isProcessing}
              className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                picked.length === 0 || isProcessing
                  ? 'bg-gray-300 cursor-not-allowed text-gray-500'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {isProcessing ? '처리 중...' : `번역 시작${picked.length ? ` (${picked.length}장)` : ''}`}
            </button>
            {(picked.length > 0 || batch) && (
              <button
                onClick={handleReset}
                className="py-3 px-4 rounded-lg font-medium bg-gray-200 hover:bg-gray-300 text-gray-700 transition-colors"
              >
                초기화
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-100 border border-red-200 text-red-700 rounded-lg mb-6">
            <p className="font-medium">오류 발생</p>
            <p className="text-sm mt-1">{error}</p>
          </div>
        )}

        {/* 결과 영역 */}
        {batch && (
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800">
                번역 결과 ({successResults.length}/{batch.count} 성공)
              </h2>
              {batch.zip_url && successResults.length >= 2 && (
                <a
                  href={getOutputUrl(batch.zip_url)}
                  download
                  className="py-2 px-4 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                >
                  전체 다운로드 (ZIP)
                </a>
              )}
              {successResults.length === 1 && successResults[0].output_url && (
                <a
                  href={getOutputUrl(successResults[0].output_url)}
                  download
                  className="py-2 px-4 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                >
                  이미지 다운로드
                </a>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {batch.results.map((r, i) => (
                <div key={`${r.filename}-${i}`} className="border rounded-lg overflow-hidden">
                  {r.success && r.output_url ? (
                    <>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={getOutputUrl(r.output_url)}
                        alt={r.filename}
                        className="w-full object-contain bg-gray-50"
                      />
                      <div className="p-2">
                        <p className="text-xs font-medium text-gray-700 truncate">{r.filename}</p>
                        <p className="text-[11px] text-gray-500">번역 {r.texts?.length ?? 0}개</p>
                      </div>
                    </>
                  ) : (
                    <div className="p-4 text-sm text-red-600">
                      <p className="font-medium truncate">{r.filename}</p>
                      <p className="text-xs mt-1">{r.error || '처리 실패'}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>Powered by manga-ocr &amp; Claude AI</p>
        </footer>
      </div>
    </main>
  );
}
