import { NextResponse } from "next/server";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  return NextResponse.json({
    ok: true,
    code: searchParams.get("code"),
    state: searchParams.get("state"),
    error: searchParams.get("error"),
    error_description: searchParams.get("error_description"),
  });
}
