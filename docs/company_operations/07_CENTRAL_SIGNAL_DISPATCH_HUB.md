# SAJIM TRADERS — UNIFIED SIGNAL DISPATCH HUB
**Concept:** Converging Algo Signals & Manual Setups into ONE Unified Review Queue  
**Author:** Jimmy Mathu, Founder & CEO  
**Target Architecture:** Hybrid Intake Pipeline (Algo + Manual $\to$ Staging Queue $\to$ Approval $\to$ Broadcast & MT5)  
**Classification:** Core Operations Standard  

---

## 1. THE PROBLEM YOU ARE SOLVING

Right now, there is a risk of confusion:
- Automated algorithms on the Hostinger VPS generate signals.
- Alu and Jimmy find high-probability manual setups on charts.
- If these setups are scattered across WhatsApp chats, scratchpads, and server logs, trades will be missed, clients will get disorganized alerts, and risk will not be audited.

### The Solution: A Single Unified "Intake Deck"
Every trade opportunity—whether discovered by a Python bot or spotted manually by Alu—must land in **ONE standardized staging queue**. Nothing goes live to clients or into an FTMO account until it passes through this single hub.

---

## 2. THE UNIFIED ARCHITECTURE PIPELINE

```
  [SOURCE A: 24/7 VPS BOT]                  [SOURCE B: ALU MANUAL DESK]
(BEEP RARE Momentum Plume)               (M15 Mirage Liquidity Sweep)
             │                                        │
             └───────────────────┬────────────────────┘
                                 ▼
         ┌─────────────────────────────────────────────────┐
         │     THE CENTRAL STAGING INBOX (THE HUB)         │
         │  - Formats both into the exact same Card        │
         │  - Status: PENDING_APPROVAL                     │
         └───────────────────────┬─────────────────────────┘
                                 ▼
         ┌─────────────────────────────────────────────────┐
         │           SAMMY'S 4-CHECK GATEKEEPER            │
         │  - Momentum > 40? [x]                           │
         │  - Stop Loss safe? [x]                          │
         │  - Lot size strictly 0.01 / 0.50%? [x]          │
         │  - No high-impact news? [x]                     │
         └───────────────────────┬─────────────────────────┘
                                 │ (APPROVED)
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
[CLIENT DISTRIBUTION ENGINE]                [FTMO & LIVE EXECUTION ENGINE]
(VIP Telegram / WhatsApp Beta)              (MT5 Terminal Bridge opens order)
```

---

## 3. HOW TO IMPLEMENT THIS IMMEDIATELY (2 POWERFUL OPTIONS)

### OPTION 1: THE INTERNAL TELEGRAM STAGING ROOM (FASTEST & EASIEST)
Since the entire team (Jimmy, Sammy, Alu, Tete, Val) uses smartphones on the move, this can be active in 10 minutes without coding new websites:

1. **Create a Private Telegram Group:**
   - Group Name: `[INTERNAL] SAJIM STAGING DESK`.
   - Members: Jimmy, Sammy, Alu, Tete, Val, and our Telegram Bot (`@SajimBroadcasterBot`).

2. **Standardized Card Template (Used by Both Algo & Human):**
   Whenever the VPS bot or Alu finds a trade, it posts this exact card into the group:
   ```
   🔔 [PENDING STAGED SIGNAL]
   Symbol: XAUUSD (Gold)
   Direction: BUY
   Source: MANUAL (Alu Liquidity Sweep)  <-- Or ALGO (VPS Rare Plume)
   Entry: 2510.50
   Stop Loss: 2505.00
   Take Profit: 2525.00
   Target R:R: 1:3.0
   Calculated Lot: 0.01 (0.50% Risk)

   Sammy 4-Check:
   [ ] M > 40  [ ] SL Set  [ ] Lot Safe  [ ] No News
   ```

3. **1-Tap Approval:**
   - Sammy inspects the card. If it passes, Sammy replies: `✅ GO`.
   - The bot (or Val) takes that exact message and:
     - **Action 1:** Forwards it with 1 click to the **VIP Client Channel** for paying subscribers and beta students.
     - **Action 2:** Sends the order to the MT5 bridge to execute on our **FTMO challenge accounts**!

---

### OPTION 2: THE NEXT.JS WEB PORTAL STAGING QUEUE (ENTERPRISE GRADE)
We already have Supabase Auth and a typed database layer hooked into our Next.js frontend (`frontend/`):

1. **The Staging Database Table (`staged_signals`):**
   Both `core/beep_broadcast.py` (for automated bots) and a web form for Alu insert into the same table:
   ```sql
   CREATE TABLE staged_signals (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       source VARCHAR(20), -- 'ALGO_VPS' or 'MANUAL_ALU'
       symbol VARCHAR(20) NOT NULL,
       direction VARCHAR(10) NOT NULL, -- 'BUY' or 'SELL'
       entry_price NUMERIC NOT NULL,
       stop_loss NUMERIC NOT NULL,
       take_profit NUMERIC NOT NULL,
       status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'APPROVED', 'REJECTED'
       approved_by VARCHAR(50)
   );
   ```

2. **The Review Dashboard in the Web Cockpit:**
   In our Next.js dashboard, Jimmy and Sammy see a live card feed of all pending setups.
   - Clicking **`[APPROVE]`**:
     - Automatically updates status to `APPROVED`.
     - Triggers `core/telegram_broadcaster.py` to notify all client groups instantly.
     - Automatically fires `core/mt5_bridge.py` to place the trade on live/FTMO accounts.
   - Clicking **`[REJECT]`**:
     - Discards the trade with a reason logged (e.g. "Spread too wide").

---

## 4. EXECUTIVE RECOMMENDATION: DEPLOY OPTION 1 TODAY, SCALE TO OPTION 2

1. **Today:** Use **Option 1 (Internal Telegram Staging Group)**. It requires zero waiting, works on everyone's phone today, and allows Alu, Sammy, and the VPS bot to speak the exact same visual language.
2. **Next Week:** Have Tete wire **Option 2 (Web Portal Staging Table)** into Supabase so you have a complete institutional audit log of every trade approved, who approved it, and the final payout outcome.
