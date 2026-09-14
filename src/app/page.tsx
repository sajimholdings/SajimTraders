"use client";

import { FormEvent, useEffect, useState } from "react";
import { SIGNAL_SOURCES, SignalSubmission } from "@/lib/signal-domain";

const initialForm = {
  symbol: "XAUUSD",
  timeframe: "M15",
  action: "BUY",
  entry: "",
  stopLoss: "",
  takeProfit: "",
  source: "BEEP",
  strategyVersion: "beep-unverified-v1",
  rationale: "",
  submittedBy: "operator",
  expiresAt: "",
};

export default function Home() {
  const [form, setForm] = useState(initialForm);
  const [signals, setSignals] = useState<SignalSubmission[]>([]);
  const [message, setMessage] = useState("API foundation ready");

  async function loadSignals() {
    const response = await fetch("/api/signals");
    const data = await response.json();
    setSignals(data.signals || []);
  }

  useEffect(() => {
    void loadSignals();
  }, []);

  async function submitSignal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("Validating signal...");
    const response = await fetch("/api/signals", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, entry: Number(form.entry), stopLoss: Number(form.stopLoss), takeProfit: Number(form.takeProfit) }),
    });
    const data = await response.json();
    if (!response.ok) {
      setMessage(data.errors?.join(" | ") || "Signal rejected");
      return;
    }
    setMessage(`Signal ${data.signal.id.slice(0, 8)} submitted for review`);
    setForm(initialForm);
    await loadSignals();
  }

  async function transitionSignal(id: string, status: string) {
    const response = await fetch(`/api/signals/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (response.ok) {
      setMessage(`Signal moved to ${status}`);
      await loadSignals();
    }
  }

  function updateField(field: keyof typeof initialForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">SAJIM HOLDINGS / FUNCTIONAL FOUNDATION</p>
          <h1>Signal operations</h1>
        </div>
        <span className="status">{message}</span>
      </header>

      <section className="grid">
        <form className="panel" onSubmit={submitSignal}>
          <div className="panel-heading">
            <div><p className="eyebrow">01 / INTAKE</p><h2>Submit setup</h2></div>
            <span className="badge">HUMAN REVIEW</span>
          </div>
          <div className="form-grid">
            <label>Symbol<input value={form.symbol} onChange={(event) => updateField("symbol", event.target.value)} /></label>
            <label>Timeframe<input value={form.timeframe} onChange={(event) => updateField("timeframe", event.target.value)} /></label>
            <label>Action<select value={form.action} onChange={(event) => updateField("action", event.target.value)}><option>BUY</option><option>SELL</option></select></label>
            <label>Source<select value={form.source} onChange={(event) => updateField("source", event.target.value)}>{SIGNAL_SOURCES.map((source) => <option key={source}>{source}</option>)}</select></label>
            <label>Entry<input required type="number" step="any" value={form.entry} onChange={(event) => updateField("entry", event.target.value)} /></label>
            <label>Stop loss<input required type="number" step="any" value={form.stopLoss} onChange={(event) => updateField("stopLoss", event.target.value)} /></label>
            <label>Take profit<input required type="number" step="any" value={form.takeProfit} onChange={(event) => updateField("takeProfit", event.target.value)} /></label>
            <label>Expires at<input required type="datetime-local" value={form.expiresAt} onChange={(event) => updateField("expiresAt", new Date(event.target.value).toISOString())} /></label>
          </div>
          <label>Strategy version<input value={form.strategyVersion} onChange={(event) => updateField("strategyVersion", event.target.value)} /></label>
          <label>Rationale<textarea required value={form.rationale} onChange={(event) => updateField("rationale", event.target.value)} placeholder="Why should this setup be reviewed?" /></label>
          <button className="primary" type="submit">Submit for review</button>
        </form>

        <section className="panel">
          <div className="panel-heading"><div><p className="eyebrow">02 / QUEUE</p><h2>Verification queue</h2></div><span className="count">{signals.length}</span></div>
          {signals.length === 0 ? <p className="empty">No submissions yet. The queue will show immutable signal records here.</p> : <div className="signal-list">{signals.map((signal) => <article className="signal" key={signal.id}><div className="signal-top"><strong>{signal.symbol} / {signal.timeframe}</strong><span className={`state state-${signal.status.toLowerCase()}`}>{signal.status}</span></div><p>{signal.action} · {signal.source} · {signal.strategyVersion}</p><p className="mono">Entry {signal.entry} · SL {signal.stopLoss} · TP {signal.takeProfit}</p><div className="actions">{signal.status === "SUBMITTED" && <button onClick={() => transitionSignal(signal.id, "REVIEWING")}>Review</button>}{signal.status === "REVIEWING" && <><button onClick={() => transitionSignal(signal.id, "VERIFIED")}>Verify</button><button onClick={() => transitionSignal(signal.id, "REJECTED")}>Reject</button></>} {signal.status === "VERIFIED" && <button className="primary" onClick={() => transitionSignal(signal.id, "PUBLISHED")}>Publish</button>}</div></article>)}</div>}
        </section>
      </section>
    </main>
  );
}
