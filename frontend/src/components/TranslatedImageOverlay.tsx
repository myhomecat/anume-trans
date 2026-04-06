'use client';

import { useRef, forwardRef, useImperativeHandle } from 'react';
import { TextItem } from '@/lib/types';

interface TranslatedImageOverlayProps {
  originalUrl: string;
  outputUrl?: string;  // 인페인팅된 이미지 URL
  imageWidth: number;
  imageHeight: number;
  texts: TextItem[];
}

export interface TranslatedImageOverlayRef {
  getElement: () => HTMLDivElement | null;
}

const TranslatedImageOverlay = forwardRef<TranslatedImageOverlayRef, TranslatedImageOverlayProps>(
  ({ originalUrl, outputUrl, imageWidth, imageHeight, texts }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);

    useImperativeHandle(ref, () => ({
      getElement: () => containerRef.current,
    }));

    // 컨테이너 크기 계산 (최대 800px 너비)
    const maxWidth = 800;
    const scale = Math.min(1, maxWidth / imageWidth);
    const displayWidth = imageWidth * scale;
    const displayHeight = imageHeight * scale;

    // 인페인팅된 이미지가 있으면 그것을 표시
    const displayUrl = outputUrl || originalUrl;
    const useInpaintedImage = !!outputUrl;

    return (
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">번역된 이미지</h3>

        <div
          ref={containerRef}
          className="relative mx-auto overflow-hidden"
          style={{
            width: displayWidth,
            height: displayHeight,
          }}
        >
          {/* 이미지 (인페인팅된 이미지 또는 원본) */}
          <img
            src={displayUrl}
            alt="Translated"
            className="absolute top-0 left-0 w-full h-full object-contain"
            crossOrigin="anonymous"
          />

          {/* 인페인팅된 이미지가 없을 때만 텍스트 오버레이 표시 */}
          {!useInpaintedImage && texts.map((item, index) => {
            if (!item.region) return null;

            const { x, y, width, height } = item.region;

            // 스케일 적용
            const scaledX = x * scale;
            const scaledY = y * scale;
            const scaledW = width * scale;
            const scaledH = height * scale;

            // 폰트 크기 계산 (영역 크기에 맞춤)
            const isVertical = height > width * 1.5;
            const fontSize = isVertical
              ? Math.max(8, Math.min(14, scaledW * 0.7))
              : Math.max(8, Math.min(14, scaledH * 0.25));

            return (
              <div
                key={index}
                className="absolute flex items-center justify-center bg-white text-black overflow-hidden"
                style={{
                  left: scaledX,
                  top: scaledY,
                  width: scaledW,
                  height: scaledH,
                  fontSize: `${fontSize}px`,
                  lineHeight: 1.2,
                  padding: '2px',
                  boxSizing: 'border-box',
                  writingMode: isVertical ? 'vertical-rl' : 'horizontal-tb',
                  textOrientation: isVertical ? 'upright' : 'mixed',
                  wordBreak: 'break-all',
                  textAlign: 'center',
                }}
              >
                {item.translated}
              </div>
            );
          })}
        </div>

        <p className="text-xs text-gray-500 mt-2 text-center">
          {useInpaintedImage
            ? '* 인페인팅 기술로 원본 말풍선 형태가 유지됩니다'
            : '* 텍스트 위치를 조정하려면 말풍선 위로 마우스를 올려보세요'
          }
        </p>
      </div>
    );
  }
);

TranslatedImageOverlay.displayName = 'TranslatedImageOverlay';

export default TranslatedImageOverlay;
