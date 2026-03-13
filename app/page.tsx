<h1 className="text-3xl font-bold tracking-tight">
  FEATURE TEST - 네이버 블로그 → 카페24 게시판 업로드
</h1>
"use client";

import { useState } from "react";

type UploadResult = {
  success: boolean;
  message?: string;
  title?: string;
  sourceUrl?: string;
  boardNo?: number;
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
      const res = await fetch("/api/manual-upload", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url,
          boardNo: Number(boardNo),
        }),
      });

      const data = (await res.json()) as UploadResult;
      setResult(data);
    } catch (error) {
      setResult({
        success: false,
        message: error instanceof Error ? error.message : "요청 중 오류가 발생했습니다.",
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
              네이버 블로그 → 카페24 게시판 업로드
            </h1>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              블로그 포스팅 주소를 입력하면 해당 글 1건을 카페24 게시판에 바로 업로드합니다.
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
                placeholder="https://blog.naver.com/... 또는 https://m.blog.naver.com/..."
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
              disabled={loading || !url.trim()}
              className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "업로드 중..." : "카페24 게시판에 업로드"}
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
                  {result.success ? "업로드 성공" : "업로드 실패"}
                </div>

                {result.title && <div className="mt-2">제목: {result.title}</div>}
                {result.boardNo && <div>게시판 번호: {result.boardNo}</div>}
                {result.sourceUrl && (
                  <div className="break-all">원문 주소: {result.sourceUrl}</div>
                )}
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
