# SAJIM TRADERS & HOLDINGS — COMPANY OPERATIONS MANUAL (SOP)
**Document ID:** SOP-OPS-002  
**Classification:** Internal Operational Standard  
**Target Audience:** CEO, Trading Desk, Engineering, Operations, Communications  
**Author:** Jimmy Mathu, Founder & CEO  
**Effective Date:** September 12, 2026  

---

## 1. DUAL EXECUTION MODEL: AUTOMATED + MANUAL DESK

Sajim Traders executes capital operations across two coordinated channels:
1. **Automated Algorithmic Daemon:** Runs 24/7 on the Hostinger VPS server via MetaTrader 5 IPC bridge (`bots/sajim_server_overnight.py` / `bots/live_quant_cent_executor.py`).
2. **Disciplined Manual Trading Desk:** Operated by **Alu (Trader)** under the strict gatekeeping of **Sammy (Head of Risk)**, executing high-conviction discretionary confirmations of BEEP setups.

---

## 2. RECENT FINANCIAL PERFORMANCE & LIVE DESK LEDGER

During the initial launch phase, the manual trading desk established the following verified financial benchmark:
- **Funded Capital:** **\$35.00 USD**
- **Gross Returns Generated:** Approximately **\$53.00 USD** (**+51.4% Gross ROI**)
- **Operational Team Expenses:** **\$10.00 USD** (allocated for team lunch and mobile internet/airtime credits)
- **Net Operating Capital:** Scaled and retained for funding the **Hostinger VPS server**.

> [!NOTE]
> This lean, disciplined financial trajectory demonstrates immediate capital extraction while keeping overhead strictly under control.

---

## 3. HOSTINGER VPS PROCUREMENT & DEPLOYMENT SOP

To run our automated BEEP quant algorithms and MT5 terminal bridge 24/7 without dependency on local home power or personal PC battery, the firm is purchasing a **Hostinger VPS**:

### SOP-VPS-01: Server Provisioning (Arnold & Tete)
1. **Target Specification:** Hostinger KVM VPS (2 vCPU, 4GB–8GB RAM, NVMe Storage, Windows Server or Ubuntu Linux with Wine MT5).
2. **Procurement:** Arnold facilitates the payment from the team operational pool.
3. **Setup Sequence (Tete):**
   - Install MetaTrader 5 Terminal connected to our broker (`Headway` / `JustMarkets`).
   - Clone the repository: `git clone <repo_url> "C:\SAJIM HOLDINGS"`.
   - Setup Python 3.12 virtual environment and install requirements:
     ```bash
     pip install -r requirements-windows.txt
     ```
   - Configure `.env` with encrypted broker credentials (`MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`).
   - Launch the supervisor daemon:
     ```bash
     python run.py server
     ```
4. **Health Heartbeat:** Verify that `overnight_status.json` streams live telemetry to the cloud backend every 15 seconds.

---

## 4. MANUAL TRADING DESK SOP (ALU & SAMMY)

Manual trading is NOT guessing or gambling; it is human execution of pure BEEP mathematics.

```
[MARKET SETUP ARISES]
         │
         ▼
[SAMMY'S 4-CHECK GATEKEEPER]
  1. Is M(t) > 40? (Green)
  2. Is SL anchored behind B(t) or wick extreme? (Green)
  3. Is lot size calculated strictly (0.01 on current account)? (Green)
  4. Is spread <= 15% ATR? (Green)
         │
    (ALL 4 YES)
         ▼
[ALU EXECUTES TRADE ORDER]
  - Enter market or limit order.
  - Set exact SL and TP (Target R:R >= 1:2.5).
  - Move SL to Break-Even at +1.0R.
  - Close 50% partial at +2.0R.
         │
         ▼
[LOG IN TRADE FLIGHT RECORDER]
```

### Mandatory Manual Rules for Alu:
1. **Zero Unchecked Entries:** Alu never enters a trade without Sammy verifying the 4-Check Gatekeeper Card.
2. **No Revenge Trading:** If a stop-loss is hit, Alu must step away from the charts for a minimum of 45 minutes.
3. **Position Sizing:** On accounts under \$100 USD, lot size is strictly **0.01 lot**. No exceptions.
4. **Daily Profit Lock:** Once daily profit reaches $+10\%$ to $+15\%$, trading for that session ceases to bank the gains.

---

## 5. COMMUNICATIONS & COMMUNITY WORKFLOW (VAL)

Managed by **Val (Communications Manager)** to ensure flawless coordination between leadership, technical builders, traders, and clients:

### 5.1 Internal Team Cadence
- **Morning Standup (09:30 EAT):** Val checks in with Jimmy, Tete, Sammy, Arnold, and Alu to confirm the day's priorities.
- **Expense & Logistics Tracking:** Val logs daily operational requirements (airtime credits, lunch stipends, meeting coordination) with Arnold.
- **Milestone Logging:** Val maintains a daily company logbook summarizing trades executed, revenue generated, and system updates.

### 5.2 External Beta Community Management
- **Welcome Message:** Val greets incoming 100 KES Beta students, sends them the demo setup guide, and confirms their MT5 demo IDs.
- **Announcement Dispatch:** Val shares morning market outlooks prepared by Jimmy and signal recaps verified by Sammy.
- **Client Support:** Val answers common user questions regarding the web portal and forwards technical bugs to Tete.

---

## 6. EMERGENCY KILLSWITCH & INCIDENT RUNBOOK

> [!CAUTION]
> **CODE RED PROTOCOL:**
> In case of unexpected market volatility, broker disconnect, or cumulative daily loss reaching **5% of balance**:
> 1. Alu and Sammy immediately close all open manual positions.
> 2. Tete issues the automated bot shutdown: `python run.py --stop-all`.
> 3. No new trades may be opened for 24 hours without the explicit written approval of CEO Jimmy Mathu.
