import { NextResponse } from "next/server";
import { transitionSignal } from "@/lib/signal-store";

const allowedTransitions = new Set(["REVIEWING", "VERIFIED", "PUBLISHED", "REJECTED", "EXPIRED", "CANCELLED", "RETRACTED"]);

export async function POST(request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params;
  const body = await request.json().catch(() => ({}));
  const status = typeof body.status === "string" ? body.status.toUpperCase() : "";
  if (!allowedTransitions.has(status)) {
    return NextResponse.json({ ok: false, error: "unsupported signal transition" }, { status: 400 });
  }

  try {
    const signal = await transitionSignal(id, status as Parameters<typeof transitionSignal>[1], body.reason);
    if (!signal) return NextResponse.json({ ok: false, error: "signal not found" }, { status: 404 });
    return NextResponse.json({ ok: true, signal });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error instanceof Error ? error.message : "signal transition failed" }, { status: 503 });
  }
}
