import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({
    service: "sajim-ops",
    status: "ok",
    timestamp: new Date().toISOString(),
    mode: "foundation",
  });
}
