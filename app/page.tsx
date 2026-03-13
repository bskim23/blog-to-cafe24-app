"use client";

import { useState } from "react";

type UploadResult = {
  success: boolean;
  message?: string;
  raw?: string;
};

export default function Home() {
  const [url, setUrl] = useState("");
  const [boardNo, setBoardNo] = useState("8");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);

  const handleSubmit = async () => {
    setLoading(true);
    setResult(null);

    try {
      const apiUrl = new URL("/api/manual-upload", window.location.origin).toString();

      const res = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          boardNo: Number(boardNo),
        }),
      });

      const rawText = await res.text();

      let parsed: any = null;
      try {
        parsed = JSON.parse(rawText);
      } catch {
        parsed = null;
      }

      setResult({
        success: !!parsed?.ok || !!parsed?.success,
        message: parsed?.message || `HTTP ${res.status}`,
        raw: rawText,
      });
    } catch (error) {
      const err = error as Error;
      setResult({
        success: false,
        message: `${err.name}: ${err.message}`,
        raw: JSON.stringify(
          {
            origin: typeof window !== "undefined" ? window.location.origin : "",
            href: typeof window !== "undefined" ? window.location.href : "",
          },
          null,
          2
        ),
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-6 py-10 text-slate-900">
      <div className="mx-auto max-w-3xl">
        <div className="rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight">
              FEATURE TEST - 네이버 블로그 → 카페24 게시판 업로드
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              지금은 API 연결 상태를 먼저 확인하는 단계입니다.
            </p>
          </div>

          <div className="space-y-6">
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-700">
                네이버 블로그 글 주소
              </label>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://blog.naver.com/..."
                className="w-full rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-500"
              />
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-700">
                게시판 번호
              </label>
              <input
                type="number"
                value={boardNo}
                onChange={(e) => setBoardNo(e.target.value)}
                className="w-40 rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-500"
              />
            </div>

            <button
              onClick={handleSubmit}
              disabled={loading}
              className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "확인 중..." : "API 연결 확인"}
            </button>
          </div>

          <div className="mt-8">
            <h2 className="mb-3 text-sm font-semibold text-slate-700">처리 결과</h2>

            {!result && (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                아직 실행 결과가 없습니다.
              </div>
            )}

            {result && (
              <div
                className={`rounded-2xl px-4 py-5 text-sm leading-6 ${
                  result.success
                    ? "border border-emerald-200 bg-emerald-50 text-emerald-900"
                    : "border border-rose-200 bg-rose-50 text-rose-900"
                }`}
              >
                <div className="font-semibold">
                  {result.success ? "호출 성공" : "호출 실패"}
                </div>
                {result.message && <div className="mt-2">메시지: {result.message}</div>}
                {result.raw && (
                  <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-xl bg-white/70 p-3 text-xs">
                    {result.raw}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
