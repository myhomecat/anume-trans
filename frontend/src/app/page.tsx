'use client';

import { useState, useRef } from 'react';
import html2canvas from 'html2canvas';
import ImageUploader from '@/components/ImageUploader';
import ImagePreview from '@/components/ImagePreview';
import TranslationResult from '@/components/TranslationResult';
import TranslatedImageOverlay, { TranslatedImageOverlayRef } from '@/components/TranslatedImageOverlay';
import ProgressBar from '@/components/ProgressBar';
import { processImage, getOutputUrl } from '@/lib/api-client';
import { TextItem } from '@/lib/types';

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [result, setResult] = useState<{
    texts: TextItem[];
    originalUrl: string;
    outputUrl?: string;
    imageWidth: number;
    imageHeight: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const overlayRef = useRef<TranslatedImageOverlayRef>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
    setProgress(0);
  };

  const handleProcess = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError(null);
    setProgress(10);
    setCurrentStep('이미지 업로드 중...');

    try {
      setProgress(30);
      setCurrentStep('텍스트 분석 및 번역 중...');

      const response = await processImage(selectedFile);

      setProgress(90);
      setCurrentStep('결과 처리 중...');

      if (response.success && response.original_url) {
        setResult({
          texts: response.texts || [],
          originalUrl: getOutputUrl(response.original_url),
          outputUrl: response.output_url ? getOutputUrl(response.output_url) : undefined,
          imageWidth: response.image_width || 800,
          imageHeight: response.image_height || 600,
        });
        setProgress(100);
        setCurrentStep('완료!');
      } else {
        setError(response.error || '처리 중 오류가 발생했습니다.');
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다. 백엔드 서버가 실행 중인지 확인해주세요.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setProgress(0);
    setCurrentStep('');
  };

  const handleDownload = async () => {
    const element = overlayRef.current?.getElement();
    if (!element) return;

    try {
      // html2canvas로 캡처
      const canvas = await html2canvas(element, {
        useCORS: true,
        allowTaint: true,
        scale: 2, // 고해상도
        backgroundColor: '#ffffff',
      });

      // 다운로드
      const link = document.createElement('a');
      link.download = 'translated.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (err) {
      console.error('Download failed:', err);
      alert('이미지 다운로드에 실패했습니다.');
    }
  };

  return (
    <main className="min-h-screen p-4 md:p-8 bg-gray-100">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Anime/Manga Translator
          </h1>
          <p className="text-gray-600">
            만화 이미지를 업로드하면 텍스트를 자동으로 감지하고 번역합니다
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 왼쪽: 업로드 및 원본 */}
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">원본 이미지</h2>
              <ImageUploader onFileSelect={handleFileSelect} />
            </div>

            {previewUrl && (
              <ImagePreview
                src={previewUrl}
                alt="Original"
                label="업로드된 이미지"
              />
            )}

            {isProcessing && (
              <div className="bg-white rounded-lg shadow p-4">
                <ProgressBar progress={progress} currentStep={currentStep} />
              </div>
            )}

            <div className="flex gap-2">
              <button
                onClick={handleProcess}
                disabled={!selectedFile || isProcessing}
                className={`flex-1 py-3 px-4 rounded-lg font-medium transition-colors ${
                  !selectedFile || isProcessing
                    ? 'bg-gray-300 cursor-not-allowed text-gray-500'
                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                }`}
              >
                {isProcessing ? '처리 중...' : '번역 시작'}
              </button>
              {(selectedFile || result) && (
                <button
                  onClick={handleReset}
                  className="py-3 px-4 rounded-lg font-medium bg-gray-200 hover:bg-gray-300 text-gray-700 transition-colors"
                >
                  초기화
                </button>
              )}
            </div>
          </div>

          {/* 오른쪽: 결과 */}
          <div className="space-y-4">
            {error && (
              <div className="p-4 bg-red-100 border border-red-200 text-red-700 rounded-lg">
                <p className="font-medium">오류 발생</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            )}

            {result && (
              <>
                {/* 번역된 이미지 표시 (인페인팅된 이미지 또는 오버레이) */}
                <TranslatedImageOverlay
                  ref={overlayRef}
                  originalUrl={result.originalUrl}
                  outputUrl={result.outputUrl}
                  imageWidth={result.imageWidth}
                  imageHeight={result.imageHeight}
                  texts={result.texts}
                />

                <TranslationResult texts={result.texts} />

                <button
                  onClick={handleDownload}
                  className="block w-full py-3 px-4 bg-green-500 hover:bg-green-600 text-white text-center rounded-lg font-medium transition-colors"
                >
                  이미지 다운로드
                </button>
              </>
            )}

            {!result && !error && (
              <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400 mb-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <p>이미지를 업로드하고 번역을 시작하면<br />결과가 여기에 표시됩니다</p>
              </div>
            )}
          </div>
        </div>

        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>Powered by manga-ocr & Claude AI</p>
        </footer>
      </div>
    </main>
  );
}
