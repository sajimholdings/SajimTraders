import { NextResponse } from "next/server";
import { createSignal, validateSignalInput } from "@/lib/signal-domain";
import { insertSignal, listSignals } from "@/lib/signal-store";

export async function GET() {
  try {
    const signals = await listSignals();
    return NextResponse.json({ count: signals.length, signals });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error instanceof Error ? error.message : "signal read failed" }, { status: 503 });
  }
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const validation = validateSignalInput(body);
  if (!validation.ok) {
    return NextResponse.json({ ok: false, errors: validation.errors }, { status: 400 });
  }

  try {
    const signal = await insertSignal(createSignal(body));
    return NextResponse.json({ ok: true, signal, riskReward: validation.riskReward }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ ok: false, error: error instanceof Error ? error.message : "signal insert failed" }, { status: 503 });
  }
}
