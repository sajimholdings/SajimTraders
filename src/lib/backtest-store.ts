import { BacktestJob, BacktestJobStatus } from "./backtest-domain";

type BacktestStore = { jobs: BacktestJob[] };
const globalStore = globalThis as typeof globalThis & { __sajimBacktestStore?: BacktestStore };
const store: BacktestStore = globalStore.__sajimBacktestStore || { jobs: [] };
globalStore.__sajimBacktestStore = store;

export function listBacktestJobs(): BacktestJob[] {
  return [...store.jobs].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export function insertBacktestJob(job: BacktestJob): BacktestJob {
  store.jobs.push(job);
  return job;
}

export function getBacktestJob(runId: string): BacktestJob | null {
  return store.jobs.find((job) => job.runId === runId) || null;
}

export function transitionBacktestJob(runId: string, status: BacktestJobStatus, error?: string): BacktestJob | null {
  const job = getBacktestJob(runId);
  if (!job) return null;
  job.status = status;
  job.updatedAt = new Date().toISOString();
  if (error) job.error = error;
  return job;
}
