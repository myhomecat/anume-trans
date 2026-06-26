'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import ImageUploader from '@/components/ImageUploader';
import { submitBatchAsync, getJob, getOutputUrl } from '@/lib/api-client';
import { JobStatus } from '@/lib/types';

interface Picked {
  file: File;
  url: string;
}

// localStorage에 저장하는 작업 메타 (job_id 목록 = "내 작업")
interface SavedJob {
  job_id: string;
  total: number;
  label: string;
  created: number;
}

const LS_KEY = 'anume_jobs';

function loadSaved(): SavedJob[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '[]');
  } catch {
    return [];
  }
}
function saveSaved(jobs: SavedJob[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(jobs));
}

const PHASE_LABEL: Record<string, string> = {
  queued: '대기 중', detect: '감지·OCR', translate: '번역', render: '렌더링',
};

export default function Home() {
  const [picked, setPicked] = useState<Picked[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [saved, setSaved] = useState<SavedJob[]>([]);
  const [statuses, setStatuses] = useState<Record<string, JobStatus>>({});
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 마운트 시 localStorage에서 "내 작업" 복원
  useEffect(() => {
    setSaved(loadSaved());
  }, []);

  const refresh = useCallback(async (jobs: SavedJob[]) => {
    const entries = await Promise.all(
      jobs.map(async (j) => {
        try {
          return [j.job_id, await getJob(j.job_id)] as const;
        } catch {
          return [j.job_id, null] as const;
        }
      })
    );
    setStatuses((prev) => {
      const next = { ...prev };
      for (const [id, st] of entries) if (st) next[id] = st;
      return next;
    });
  }, []);

  // 진행 중 작업이 있으면 2초마다 폴링 (브라우저 닫았다 와도 복원되어 이어 폴링)
  useEffect(() => {
    if (saved.length === 0) return;
    refresh(saved);
    timerRef.current = setInterval(() => {
      const active = saved.filter((j) => {
        const st = statuses[j.job_id];
        return !st || (st.status !== 'done' && st.status !== 'error');
      });
      if (active.length === 0) {
        if (timerRef.current) clearInterval(timerRef.current);
        return;
      }
      refresh(active);
    }, 2000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saved]);

  const handleFilesSelect = (files: File[]) => {
    setPicked((prev) => {
      const seen = new Set(prev.map((p) => `${p.file.name}:${p.file.size}`));
      const added = files
        .filter((f) => !seen.has(`${f.name}:${f.size}`))
        .map((f) => ({ file: f, url: URL.createObjectURL(f) }));
      return [...prev, ...added];
    });
    setError(null);
  };

  const removeAt = (idx: number) => setPicked((prev) => prev.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    if (picked.length === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitBatchAsync(picked.map((p) => p.file));
      const label =
        picked.length === 1 ? picked[0].file.name : `${picked.length}장 (${picked[0].file.name} 외)`;
      const job: SavedJob = { job_id: res.job_id, total: res.total, label, created: Date.now() };
      const next = [job, ...loadSaved()];
      saveSaved(next);
      setSaved(next);
      setPicked([]); // 제출 후 선택 초기화 — 브라우저 닫아도 "내 작업"에서 추적됨
    } catch {
      setError('제출 실패. 분석기 서버 상태를 확인해주세요.');
    } finally {
      setSubmitting(false);
    }
  };

  const removeJob = (jobId: string) => {
    const next = loadSaved().filter((j) => j.job_id !== jobId);
    saveSaved(next);
    setSaved(next);
  };

  return (
    <main className="min-h-screen p-4 md:p-8 bg-gray-100">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Anime/Manga Translator</h1>
          <p className="text-gray-600">
            여러 장 업로드 → 백그라운드 번역 → 완료 후 다운로드 (브라우저 닫아도 진행, 다시 와서 받기)
          </p>
        </div>

        {/* 업로드 */}
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
                      className="absolute top-1 right-1 bg-black/60 text-white rounded-full w-5 h-5 text-xs leading-5 opacity-0 group-hover:opacity-100"
                      aria-label="remove"
                    >×</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <button
            onClick={handleSubmit}
            disabled={picked.length === 0 || submitting}
            className={`w-full mt-4 py-3 px-4 rounded-lg font-medium transition-colors ${
              picked.length === 0 || submitting
                ? 'bg-gray-300 cursor-not-allowed text-gray-500'
                : 'bg-blue-500 hover:bg-blue-600 text-white'
            }`}
          >
            {submitting ? '제출 중...' : `번역 시작${picked.length ? ` (${picked.length}장)` : ''}`}
          </button>
          {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        </div>

        {/* 내 작업 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">내 작업</h2>
          {saved.length === 0 && (
            <p className="text-sm text-gray-500">아직 작업이 없습니다. 이미지를 업로드하고 번역을 시작하세요.</p>
          )}
          <div className="space-y-4">
            {saved.map((j) => {
              const st = statuses[j.job_id];
              const done = st?.status === 'done';
              const err = st?.status === 'error';
              const ok = (st?.results || []).filter((r) => r.success && r.output_url);
              const pct = st && st.total ? Math.round((st.done / st.total) * 100) : 0;
              return (
                <div key={j.job_id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <div className="min-w-0">
                      <p className="font-medium text-gray-800 truncate">{j.label}</p>
                      <p className="text-xs text-gray-500">
                        {!st && '상태 조회 중...'}
                        {st && !done && !err &&
                          `${PHASE_LABEL[st.phase || st.status] || st.status} · ${st.done}/${st.total} (${pct}%)`}
                        {done && `완료 · ${ok.length}/${st?.total} 성공`}
                        {err && `오류: ${st?.error}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {done && st?.zip_url && ok.length >= 2 && (
                        <a href={getOutputUrl(st.zip_url)} download
                          className="py-2 px-3 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium">
                          ZIP 다운로드
                        </a>
                      )}
                      {done && ok.length === 1 && ok[0].output_url && (
                        <a href={getOutputUrl(ok[0].output_url)} download
                          className="py-2 px-3 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm font-medium">
                          이미지 다운로드
                        </a>
                      )}
                      <button onClick={() => removeJob(j.job_id)}
                        className="py-2 px-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm">
                        삭제
                      </button>
                    </div>
                  </div>

                  {/* 진행 바 */}
                  {st && !done && !err && (
                    <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                      <div className="bg-blue-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  )}

                  {/* 결과 썸네일 */}
                  {done && ok.length > 0 && (
                    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2 mt-2">
                      {ok.map((r, i) => (
                        <div key={`${r.filename}-${i}`}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={getOutputUrl(r.output_url!)} alt={r.filename}
                            className="w-full h-28 object-cover rounded border bg-gray-50" />
                          <p className="text-[10px] text-gray-500 truncate">{r.filename} · {r.n_texts ?? 0}개</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>Powered by manga-ocr &amp; Claude AI</p>
        </footer>
      </div>
    </main>
  );
}
