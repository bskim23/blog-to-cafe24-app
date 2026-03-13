import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const url = String(body.url || "").trim();
    const boardNo = Number(body.boardNo || 8);

    if (!url) {
      return NextResponse.json(
        { success: false, message: "블로그 주소를 입력해 주세요." },
        { status: 400 }
      );
    }

    if (!Number.isInteger(boardNo) || boardNo < 1) {
      return NextResponse.json(
        { success: false, message: "게시판 번호가 올바르지 않습니다." },
        { status: 400 }
      );
    }

    const scriptPath = path.join(process.cwd(), "manual_upload.py");

    const result = await new Promise<{
      code: number | null;
      stdout: string;
      stderr: string;
    }>((resolve) => {
      const child = spawn("python3", [scriptPath, url, String(boardNo)], {
        cwd: process.cwd(),
        env: process.env,
      });

      let stdout = "";
      let stderr = "";

      child.stdout.on("data", (data) => {
        stdout += data.toString();
      });

      child.stderr.on("data", (data) => {
        stderr += data.toString();
      });

      child.on("close", (code) => {
        resolve({ code, stdout, stderr });
      });
    });

    const raw = (result.stdout || result.stderr || "").trim();

    try {
      const parsed = JSON.parse(raw);
      if (!parsed.success) {
        return NextResponse.json(parsed, { status: 500 });
      }
      return NextResponse.json(parsed);
    } catch {
      return NextResponse.json(
        {
          success: false,
          message: "Python 실행 결과를 해석하지 못했습니다.",
          raw,
        },
        { status: 500 }
      );
    }
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        message: error instanceof Error ? error.message : "알 수 없는 오류",
      },
      { status: 500 }
    );
  }
}
