import { NextResponse } from "next/server";
import { getBacktestJob } from "@/lib/backtest-store";

export async function GET(_request: Request, context: { params: Promise<{ runId: string }> }) {
  const { runId } = await context.params;
  const job = getBacktestJob(runId);
  if (!job) return NextResponse.json({ ok: false, error: "backtest run not found" }, { status: 404 });
  return NextResponse.json({ ok: true, job, execution: "queued-only" });
}
