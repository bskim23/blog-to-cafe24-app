import { NextResponse } from "next/server";

export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json({
    ok: true,
    method: "GET",
    message: "DEBUG GET OK",
  });
}

export async function POST() {
  return NextResponse.json({
    ok: true,
    method: "POST",
    message: "DEBUG POST OK",
  });
}
