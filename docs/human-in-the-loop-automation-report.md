# Human-in-the-Loop Automation Report

## Executive Summary

The proposed system makes sense because it automates the part that currently creates the most operational risk: how ideas become approved actions.

The current workflow depends heavily on a trader watching charts, finding a setup, posting it in WhatsApp, and then trying to manage it manually. That creates several predictable problems:

- Overtrading
- Inconsistent setup quality
- Unclear accountability
- Edited or deleted messages with no reliable history
- Different traders applying different risk rules
- No clean dataset for measuring which strategy actually works
- Difficult handover between shifts
- Slow response when a setup changes or becomes invalid

The first automation step should therefore not be full autonomous execution. It should be a controlled human-in-the-loop workflow:

```text
Human submission -> System validation -> Authorized review -> Verified publication -> Outcome tracking
```

This approach gives the team immediate operational control while creating the evidence required before trusting any strategy with more automation.

## Why This Model Makes Sense

The firm currently has multiple possible signal sources:

- BEEP
- Pine Script
- EMA-based rules
- Price-action setups
- Python algorithms
- Manual chart analysis

At this stage, none of these should automatically be treated as a proven edge. The platform must allow them to compete under the same measurement rules instead of relying on reputation, excitement, or a short sequence of profitable trades.

Every proposed setup should be treated as a versioned signal with a source, timestamp, evidence, reviewer, risk profile, and final outcome.

This changes the operation from:

```text
Trader opinion -> WhatsApp message -> Subscriber reaction
```

to:

```text
Strategy evidence -> Verification gates -> Authorized signal -> Subscriber delivery -> Measured result
```

That is the correct bridge between manual trading operations and future automation.

## First Automation Milestone

The first production milestone is a Signal Operations Platform, not an autonomous trading bot.

A trader submits:

- Chart screenshot
- Symbol
- Timeframe
- Direction
- Proposed entry
- Stop loss
- Take profit
- Strategy source
- Strategy version
- Short rationale
- Optional supporting data

The system then validates the submission before a reviewer sees it.

Automated checks should include:

- Is the symbol approved?
- Is the timeframe approved for the source strategy?
- Are entry, stop loss, and take profit present?
- Is the direction valid?
- Is the R:R acceptable?
- Is the signal expired or too old?
- Is spread/friction acceptable?
- Is there already a duplicate or conflicting setup?
- Has the submitting trader exceeded the shift limit?
- Has the strategy source been suspended because of poor recent performance?

The system should never publish a signal merely because a trader uploaded a screenshot.

## Signal Lifecycle

Every signal should follow a controlled state machine:

```text
DRAFT
  -> SUBMITTED
  -> REVIEWING
  -> VERIFIED
  -> PUBLISHED
  -> EXPIRED
```

Other valid outcomes are:

```text
REJECTED
CANCELLED
RETRACTED
```

Once a signal reaches `VERIFIED`, the critical fields must be immutable. If entry, direction, SL, TP, or timeframe changes, the system should create a new version rather than silently editing history.

Every transition should record:

- Actor
- Timestamp
- Previous state
- New state
- Reason
- Evidence reference

WhatsApp, Telegram, or email should be delivery channels only. They should not be the source of truth.

## Trader Governance

The platform should support traders while preventing abusive behavior.

Recommended controls:

- Maximum submissions per shift
- Cooldown between submissions
- Required evidence before submission
- Duplicate setup detection
- Pair and timeframe whitelist
- Minimum R:R requirement
- Mandatory stop loss and take profit
- No direct publishing rights for ordinary traders
- Automatic escalation for unusual risk
- Daily rejected-signal monitoring
- Repeated violation alerts
- Temporary submission freeze after defined violations
- Full audit history

These controls do not remove human judgment. They make human judgment visible, consistent, and reviewable.

## Review and Publishing Rules

A normal setup can require one authorized reviewer. High-risk or exceptional setups should require two-person approval.

For example:

- Trader submits the signal.
- System performs mechanical validation.
- Risk reviewer checks capital and gate conditions.
- Authorized publisher releases the verified signal.
- System sends the same immutable payload to eligible subscribers.

The person who submits a signal should not be able to silently approve and publish it without oversight.

A verified signal should also have an expiry time. If the setup does not trigger within that window, subscribers should see it as expired rather than continuing to treat it as active.

A retract action should be available when market conditions change. Retraction must create a visible cancellation event and audit record.

## Risk and Subscriber Profiles

A `3/8` result can be profitable under a 1:3 risk/reward model before trading friction:

$$
EV = 0.375(3R) - 0.625(1R) = +0.5R
$$

That does not mean every group of 8 trades will be profitable. It means the theoretical expectancy is positive if the assumptions are real and execution costs do not consume the edge.

The platform should track more than win rate:

- Expectancy
- Profit factor
- Maximum drawdown
- Maximum losing streak
- Average R per trade
- Spread and slippage
- Commission
- Results by symbol
- Results by timeframe
- Results by session
- Results by market regime
- Out-of-sample performance
- Forward-test performance
- Sample size and confidence limits

Initially, subscriber delivery should use controlled risk profiles rather than collecting and acting on client balances:

- Conservative
- Standard
- Aggressive

Balance-linked sizing should remain a later legal and regulatory decision. The first system can deliver a verified setup and clearly defined risk instructions without becoming a client-account management platform.

## Strategy Source Comparison

Every source should have its own identity and version:

```text
source: BEEP
strategy_version: beep-v1.4
signal_id: UUID
backtest_evidence_id: backtest-2026-09-14-001
```

The system should keep BEEP, Pine Script, EMA, price action, and Python results separate. Combining all sources into one headline win rate would hide important differences.

A strategy should only be promoted after it has evidence across:

- In-sample testing
- Out-of-sample testing
- Forward testing
- Realistic spread
- Slippage
- Commission
- Different regimes
- Different sessions
- Different symbols and timeframes

A short profitable run is useful evidence, but it is not proof of a durable edge.

## Data and Audit Value

This workflow creates a clean internal dataset that WhatsApp cannot provide.

For each signal, the firm can later answer:

- Who found it?
- Which source generated it?
- What did the screenshot show?
- Which gates passed or failed?
- Who approved it?
- When was it published?
- Which subscribers received it?
- Did it trigger?
- What was the final R outcome?
- Was it changed, cancelled, or retracted?
- Did the result match the original risk assumptions?

This data becomes the foundation for a future strategy research and automation layer.

## Recommended Build Order

1. Signal submission form and screenshot storage.
2. Signal validation service.
3. Internal review queue.
4. Role-based approval and publishing.
5. Subscriber delivery adapters.
6. Expiry and retraction workflow.
7. Outcome and performance tracking.
8. Trader governance dashboard.
9. Strategy comparison dashboard.
10. Forward-test evidence registry.
11. Only then consider automated bridge execution for strategies that pass evidence requirements.

## What This Solves Immediately

This first milestone gives the team:

- One controlled source of truth
- Less dependence on scattered WhatsApp messages
- Reduced overtrading
- Clear trader accountability
- Consistent risk checks
- Verifiable subscriber communication
- Better shift handoffs
- A reusable audit trail
- A real dataset for future research
- A safer path toward automation

## Final Recommendation

Build the Signal Operations Platform first.

Do not begin by promising fully autonomous trading or by declaring that BEEP, Pine Script, EMA rules, or Python algorithms have already found a durable edge. Let every source submit evidence through the same controlled process.

The winning architecture is:

```text
Multiple strategy sources
        ->
Controlled signal intake
        ->
Automated gates
        ->
Human risk verification
        ->
Authorized subscriber delivery
        ->
Outcome measurement
        ->
Evidence-based automation
```

This is useful beyond trading as well. The same model applies anywhere people generate recommendations that need validation before they reach customers: financial research, compliance approvals, operational incidents, healthcare workflows, security alerts, and quality-control systems.

The central principle is simple:

> Humans can generate and review decisions, but the system must control the workflow, preserve the evidence, enforce the rules, and record the outcome.
