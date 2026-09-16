# SAJIM TRADERS & HOLDINGS — TEAM OPERATIONAL CHARTER & DAILY HANDOFFS
**Classification:** Executive Organizational Standard  
**Authority:** Jimmy Mathu, Founder & CEO  
**Effective Date:** September 12, 2026  

---

## 1. THE FOUNDATIONAL PRINCIPLE: CLEAN SEPARATION OF POWERS

To run our systems smoothly without friction, conflict, or chaos, **every single team member must have an exact, non-overlapping boundary**. No one steps on another person's toes:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 EXECUTIVE LEADERSHIP                                   │
│  - Jimmy Mathu (CEO): Strategy, BEEP IP Custodian, FTMO Allocation, Final Override    │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
       ┌───────────────────────────────────┼───────────────────────────────────┐
       ▼                                   ▼                                   ▼
┌──────────────┐                   ┌──────────────┐                    ┌──────────────┐
│  TECHNOLOGY  │                   │  RISK & DESK │                    │  OPERATIONS  │
│  CTO: Tete   │                   │ Head: Sammy  │                    │ Head: Arnold │
└──────┬───────┘                   └──────┬───────┘                    └──────┬───────┘
       │                                  │                                   │
       ▼                                  ▼                                   ▼
[Hostinger VPS & Bots]             [Trader: ALU]                       [Comms: VAL]
(24/7 Python & Bridge)             (Manual FTMO Desk)                  (Team & Community)
```

---

## 2. EXACT ROLE DEFINITIONS & NON-NEGOTIABLE BOUNDARIES

### 2.1 Jimmy Mathu — Founder & CEO (100% Holdings | 30% Traders)
* **Primary Mandate:** The General & Chief Architect. Sets corporate strategy, holds 100% ownership of BEEP IP, closes outside investors for the 10% pool, and decides when to scale FTMO challenges.
* **Daily Focus:** Macro market analysis, algorithm R&D, reviewing daily PnL, closing capital deals.
* **Non-Negotiable Boundary:** Holds **final unilateral override** on any operational or trading dispute.

---

### 2.2 Tete — Chief Technology Officer (18.5% Traders)
* **Primary Mandate:** The Systems Architect. Responsible for the technical uptime of the Hostinger VPS, MT5 terminal bridge, Python bot daemons, FastAPI backend, and Next.js client portal.
* **Daily Focus:**
  - Verify Hostinger VPS CPU/RAM usage and restart daemons if memory leaks occur.
  - Ensure the MT5 terminal is actively connected and logged in to broker servers.
  - Maintain the low-latency WebSocket and JSONL signal pipelines.
* **Non-Negotiable Boundary:** Tete executes the CEO's quantitative policies; he **cannot unilaterally alter BEEP trading parameters or entry thresholds**. Core mathematical equations remain confidential.

---

### 2.3 Sammy — Head of Risk & Beta Sales (18.5% Traders)
* **Primary Mandate:** The Gatekeeper & Account Guardian. Enforces risk discipline across both automated bots and manual trading. Leads the BEEP Student Beta program.
* **Daily Focus:**
  - Physically inspects the **4-Check Gatekeeper Card** before Alu opens any manual trade.
  - Monitors open drawdown on live accounts and FTMO challenges.
  - Enforces the **3.5% daily drawdown circuit breaker** with zero hesitation.
  - Coordinates recruitment of university students for the 100 KES Beta program.
* **Non-Negotiable Boundary:** **Sammy is the Risk Checker, NOT the Risk Maker.** He enforces rules written by the CEO. He cannot block a valid trade based on emotional feelings or invent new rules.

---

### 2.4 Arnold — Head of Operations & Capital Lead (10.0% Traders)
* **Primary Mandate:** The Logistics Engine & Investor Liaison. Ensures the team has the physical and financial tools required to work every single day without interruption.
* **Daily Focus:**
  - Procures and maintains the **Hostinger VPS billing** so the server never expires.
  - Manages the M-Pesa operational float (daily team lunch, airtime/credits, transport).
  - Coordinates introductory pitch meetings with prospective 10% pool investors.
  - Secures secondary backup power and internet at the command station.
* **Non-Negotiable Boundary:** Arnold has **zero access to BEEP source code or server root secrets**. His equity is conditional upon facilitating operational capital.

---

### 2.5 Alu — Quantitative Execution Trader (Manual Desk)
* **Primary Mandate:** The Sharpshooter. Executes disciplined manual trades on live broker accounts and FTMO challenge accounts during active market sessions.
* **Daily Focus:**
  - Monitors Gold (`XAUUSD`) and Yen crosses during London Open (10:00 EAT) and NY Open (15:30 EAT).
  - Identifies Mirage Liquidity Sweeps with confirmed CHoCH candle closes.
  - Submits every trade setup to Sammy for 4-Check verification before pulling the trigger.
  - Maintains the Trade Flight Recorder (logs entry, exit, SL, TP, and R-multiple).
* **Non-Negotiable Boundary:** Alu **never takes a trade without Sammy's 4-Check approval**. No revenge trading, no oversize lot guessing. Lot size is strictly 0.01 on accounts under \$100 USD.

---

### 2.6 Val — Communications & Team Operations Manager
* **Primary Mandate:** The Operational Coordinator. Keeps the entire team connected, organizes daily cadences, documents company history, and manages beta student communities.
* **Daily Focus:**
  - Facilitates the **09:30 EAT Daily Morning Standup** and records action items.
  - Welcomes new 100 KES Beta students on WhatsApp, verifies their demo MT5 IDs, and shares morning educational recaps.
  - Coordinates daily team logistics with Arnold (lunch stipends, airtime credits).
  - Logs daily financial milestones, trade wins, and team deliverables in the company archive.
* **Non-Negotiable Boundary:** Val ensures professional, scam-free communications. She never promises guaranteed trading profits to beta students.

---

## 3. THE 24-HOUR OPERATIONAL HANDOFF CADENCE (EAT / NAIROBI)

```
========================================================================================
TIME (EAT)      PHASE & ACTIVITY                            LEAD OPERATOR
========================================================================================
09:00 - 09:30   Server & Telemetry Audit                    Tete (CTO)
                - Verify Hostinger VPS bot ran overnight.
                - Confirm overnight_status.json is green.

09:30 - 10:00   Daily Morning Standup                       Val (Comms Manager)
                - Team sync: Jimmy, Tete, Sammy, Arnold, Alu.
                - Confirm day's capital targets & FTMO status.

10:00 - 13:00   London Session Execution                    Alu (Trader) + Sammy (Risk)
                - Alu scans M15 sweeps on Gold.
                - Sammy enforces 4-Check Gatekeeper Card.
                - VPS bot runs automated H1 RARE momentum.

13:00 - 14:00   Team Lunch & Logistics Break                Arnold (Ops) + Val (Comms)
                - Arnold dispenses team lunch float & credits.
                - Val shares morning educational recap to Beta.

15:00 - 18:30   New York Session Overlap                    Alu + VPS Algo + Jimmy
                - High-volatility session (US data/news).
                - Partial profit locking (+1.5R to +2.0R).
                - Stops trailed to break-even.

18:30 - 19:30   Daily Session Close & PnL Reconciliation     Sammy (Risk) + Val (Comms)
                - Alu logs all completed trades.
                - Sammy audits daily drawdown.
                - Val records day's net earnings in archive.

20:00 - 08:00   24/7 Overnight Autonomous Extraction         Hostinger VPS (Automated)
                - Automated daemon takes over Asian session.
                - Trailing stops protect capital while team sleeps.
========================================================================================
```

---

## 4. CODE OF CONDUCT & COMPANY MERITOCRACY

1. **Family = Love & Personal Support. Company = Strict Execution & Merit.**
2. **We Don't Guess, We Calculate:** No trade is opened based on a "feeling". BEEP math and Mirage structure govern everything.
3. **Protect the Capital First, Profit Second:** If an account hits our 3.5% daily drawdown ceiling, the desk shuts down for 24 hours without argument.
4. **Loyalty is Rewarded:** Outstanding performance by Alu and Val earns equity grants from the 10% ESOP pool. Ideas pitched by the team are incubated and funded by Sajim Holdings.
