import { NextResponse } from "next/server";
import { createBacktestJob, validateBacktestJobInput } from "@/lib/backtest-domain";
import { insertBacktestJob, listBacktestJobs } from "@/lib/backtest-store";

export async function GET() {
  return NextResponse.json({ count: listBacktestJobs().length, jobs: listBacktestJobs() });
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const validation = validateBacktestJobInput(body);
  if (!validation.ok) return NextResponse.json({ ok: false, errors: validation.errors }, { status: 400 });

  const job = insertBacktestJob(createBacktestJob(body));
  return NextResponse.json({ ok: true, job, execution: "queued-only" }, { status: 202 });
}
