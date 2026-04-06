'use client';

import { TextItem } from '@/lib/types';

interface Props {
  texts: TextItem[];
}

const typeLabels: Record<string, string> = {
  dialogue: '대사',
  sfx: '효과음',
  narration: '나레이션',
};

const typeColors: Record<string, string> = {
  dialogue: 'bg-blue-100 text-blue-800',
  sfx: 'bg-orange-100 text-orange-800',
  narration: 'bg-green-100 text-green-800',
};

export default function TranslationResult({ texts }: Props) {
  if (texts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-4">
        <p className="text-gray-500 text-center">텍스트가 감지되지 않았습니다.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">번역 결과</h3>
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {texts.map((item, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-3"
          >
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs px-2 py-0.5 rounded ${typeColors[item.type] || 'bg-gray-100 text-gray-800'}`}>
                {typeLabels[item.type] || item.type}
              </span>
              <span className="text-xs text-gray-500">{item.location}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-xs text-gray-400 mb-1">원본</p>
                <p className="text-gray-700">{item.original}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1">번역</p>
                <p className="text-gray-900 font-medium">{item.translated}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
