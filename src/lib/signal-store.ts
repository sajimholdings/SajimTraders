import { SignalSubmission } from "./signal-domain";

type SignalStore = { signals: SignalSubmission[] };

const globalStore = globalThis as typeof globalThis & { __sajimSignalStore?: SignalStore };
const store: SignalStore = globalStore.__sajimSignalStore || { signals: [] };
globalStore.__sajimSignalStore = store;

const supabaseUrl = process.env.SUPABASE_URL?.replace(/\/$/, "");
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const useSupabase = Boolean(supabaseUrl && supabaseServiceRoleKey);

type SupabaseSignalRow = {
  id: string;
  symbol: string;
  timeframe: string;
  action: SignalSubmission["action"];
  entry: number;
  stop_loss: number;
  take_profit: number;
  source: SignalSubmission["source"];
  strategy_version: string;
  screenshot_url?: string | null;
  rationale: string;
  submitted_by: string;
  status: SignalSubmission["status"];
  expires_at: string;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
};

function fromRow(row: SupabaseSignalRow): SignalSubmission {
  return {
    id: row.id,
    symbol: row.symbol,
    timeframe: row.timeframe,
    action: row.action,
    entry: Number(row.entry),
    stopLoss: Number(row.stop_loss),
    takeProfit: Number(row.take_profit),
    source: row.source,
    strategyVersion: row.strategy_version,
    screenshotUrl: row.screenshot_url || undefined,
    rationale: row.rationale,
    submittedBy: row.submitted_by,
    status: row.status,
    expiresAt: row.expires_at,
    rejectionReason: row.rejection_reason || undefined,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function toRow(signal: SignalSubmission) {
  return {
    id: signal.id,
    symbol: signal.symbol,
    timeframe: signal.timeframe,
    action: signal.action,
    entry: signal.entry,
    stop_loss: signal.stopLoss,
    take_profit: signal.takeProfit,
    source: signal.source,
    strategy_version: signal.strategyVersion,
    screenshot_url: signal.screenshotUrl || null,
    rationale: signal.rationale,
    submitted_by: signal.submittedBy,
    status: signal.status,
    expires_at: signal.expiresAt,
    rejection_reason: signal.rejectionReason || null,
    created_at: signal.createdAt,
    updated_at: signal.updatedAt,
  };
}

async function supabaseRequest(path: string, init?: RequestInit) {
  if (!supabaseUrl || !supabaseServiceRoleKey) throw new Error("Supabase server configuration is missing");
  return fetch(`${supabaseUrl}/rest/v1/${path}`, {
    ...init,
    headers: {
      apikey: supabaseServiceRoleKey,
      Authorization: `Bearer ${supabaseServiceRoleKey}`,
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
}

export async function listSignals(): Promise<SignalSubmission[]> {
  if (useSupabase) {
    const response = await supabaseRequest("signal_submissions?select=*&order=created_at.desc");
    if (!response.ok) throw new Error(`Supabase signal read failed (${response.status})`);
    return (await response.json() as SupabaseSignalRow[]).map(fromRow);
  }
  return [...store.signals].sort((a, b) => b.createdAt.localeCompare(a.createdAt));
}

export async function insertSignal(signal: SignalSubmission): Promise<SignalSubmission> {
  if (useSupabase) {
    const response = await supabaseRequest("signal_submissions", {
      method: "POST",
      headers: { Prefer: "return=representation" },
      body: JSON.stringify(toRow(signal)),
    });
    if (!response.ok) throw new Error(`Supabase signal insert failed (${response.status})`);
    const rows = await response.json() as SupabaseSignalRow[];
    return fromRow(rows[0]);
  }
  store.signals.push(signal);
  return signal;
}

export async function transitionSignal(id: string, status: SignalSubmission["status"], reason?: string) {
  if (useSupabase) {
    const response = await supabaseRequest(`signal_submissions?id=eq.${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { Prefer: "return=representation" },
      body: JSON.stringify({ status, rejection_reason: reason || null, updated_at: new Date().toISOString() }),
    });
    if (!response.ok) throw new Error(`Supabase signal transition failed (${response.status})`);
    const rows = await response.json() as SupabaseSignalRow[];
    return rows[0] ? fromRow(rows[0]) : null;
  }
  const signal = store.signals.find((candidate) => candidate.id === id);
  if (!signal) return null;
  signal.status = status;
  signal.updatedAt = new Date().toISOString();
  if (reason) signal.rejectionReason = reason;
  return signal;
}
