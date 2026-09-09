# SAJIM HOLDINGS — FOUNDER SHAREHOLDER & OPERATIONAL AGREEMENT
**Effective Date:** September 8, 2026  
**Jurisdiction:** Nairobi / Kapenguria, Republic of Kenya  
**Company:** Sajim Holdings (SAJIM Lab)

---

## 1. PURPOSE & VISION
Sajim Holdings is formed to operate quantitative algorithmic forex trading strategies, proprietary trading firm challenges, and automated signal delivery systems. This agreement binds the founding members to their agreed equity allocations, responsibilities, vesting schedules, and governance protocols.

---

## 2. CAPITALIZATION & SHARE ALLOCATION TABLE (100% TOTAL)

| Member | Title / Role | Equity Share | Voting Power | Initial Salary | Profit Share Allocation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Jimmy Mathu** | Founder, Chief Executive Officer & Chief Architect | **40%** | Final / Supermajority (51%+ override) | $0 until $500 payout | 40% of net company dividends |
| **Tete** | Co-Founder, Chief Technology Officer (CTO) | **20%** | Technical Execution | $0 for 90 days; KES 15k priority post-payout | 20% of net company dividends |
| **Sammy** | Head of Risk & Head of Beta Sales | **15%** | Risk Checklist (No Policy Power) | 20% commission on Beta student fees | 15% of net company dividends |
| **Arnold** | Operations & Capital Lead | **15%** | Operations | Performance-based | 15% of net company dividends (conditional) |
| **ESOP Pool** | Employee Stock Ownership Plan | **10%** | Non-voting (held in treasury) | N/A | Reserved for key hires & top beta performers |

---

## 3. ROLES, POWERS & BOUNDARIES

### 3.1 Jimmy Mathu — Founder / Architect / CEO (40%)
1. **Core Responsibility:** Sole owner and custodian of the BEEP Trading Protocol, formulas ($B(t)$, $M(t)$, $\Lambda$), and `beep_core.py`.
2. **Trading Policy:** Jimmy writes and maintains all quantitative policies, risk boundaries, and target pairs.
3. **Executive Authority:** Jimmy retains absolute and final override power on every trading decision, system configuration, and capital deployment.
4. **Personal Debt Repayment:** Jimmy commits to repaying prior personal loans owed to Sammy directly from Jimmy's 40% dividend distribution (not from company operating capital).

### 3.2 Tete — Chief Technology Officer (CTO) (20%)
1. **Core Responsibility:** Engineering the end-to-end operational pipeline: MetaTrader 5 (MT5) bridge, Python automation bots, WhatsApp signal broadcast infrastructure, and API client consumption.
2. **IP Boundary:** Tete consumes BEEP outputs strictly through the authenticated API (`api.py`). Tete does not require, request, or hold the raw mathematical formulas ($B(t)$, $M(t)$, $\Lambda$) or core algorithm source code.
3. **Policy Execution:** Tete's bots execute the policies defined by the CEO. Tete cannot unilaterally alter trading parameters or entry thresholds.

### 3.3 Sammy — Head of Risk & Head of Beta Sales (15%)
1. **Checklist Power Only (Risk Checker, NOT Risk Maker):** Sammy acts as the physical and operational gatekeeper. Sammy does **not** create trading policy, nor can Sammy reject trades based on emotional judgment, opinions, or market gossip.
2. **The "4-Check" Gatekeeper Protocol:** Before any trade is executed or broadcast, Sammy verifies:
   - [ ] **Check 1:** $M(t) > 40$ (Valid momentum deviation from BEEP API)
   - [ ] **Check 2:** Stop Loss ($SL$) is set strictly below $B(t)$ (for BUY) or above $B(t)$ (for SELL)
   - [ ] **Check 3:** Lot size is strictly **0.01** (preserving account capital)
   - [ ] **Check 4:** $\Lambda(t) > 10\%$ (Adequate market volatility/expansion)
   - **Rule:** If all 4 are YES $\rightarrow$ Sammy issues **"GO"**. If any 1 is NO $\rightarrow$ Sammy issues **"STOP"**.
   - **Override:** If Sammy blocks a trade that satisfies all 4 checks, or attempts to authorize a trade that fails, the Founder holds immediate unilateral override.
3. **Beta Program Sales:** Sammy leads the onboarding of university students into the 100 KES "BEEP Student Beta" lab program, earning 20% direct commission.

### 3.4 Arnold — Operations & Capital Lead (15%)
1. **Core Responsibility:** Operational logistics, VPS server uptime maintenance, broker account setup, M-Pesa account compliance, and investor pipeline generation.
2. **IP Boundary:** Arnold has zero access to BEEP core code, mathematical models, or server credentials for the API backend.
3. **Probationary Milestone:** Arnold's equity is contingent upon active contribution and facilitating operational capital ($100,000$ KES pipeline or institutional prop funding).

### 3.5 ESOP Pool (10%)
1. The 10% equity pool is held in treasury to attract talent, developers, and exceptional Beta participants.
2. **Standard Grant Criteria:** 3 months of proven, consistent work + delivery of verified production module + NDA signature = up to 2% equity grant with 6-month vesting.

---

## 4. VESTING, DEPARTURE & BUYBACK TERMS

1. **Vesting Schedule:** All founder shares vest over **twelve (12) months** on a linear monthly basis ($1/12$th per month) following a 30-day trial period.
2. **Early Departure / Bailout:** If any member leaves or is terminated before 12 months:
   - All unvested shares immediately revert to the Sajim Holdings Company Treasury.
   - For vested shares, the Company holds the unilateral first right of refusal to repurchase shares at a fixed buyback valuation of **KES 1,000 per 1% equity**.
3. **Loyalty Protection:** In the event of an early bailout by non-technical members, returned equity may be re-allocated by the Founder to loyal technical builders (e.g., Tete) as a retention bonus.

---

## 5. SEPARATION OF FAMILY AND MERIT
Sajim Holdings operates strictly as a commercial meritocracy. Family relations receive personal affection, love, and voluntary financial gifts funded solely from Jimmy's personal earnings. Company equity, administrative power, and technical keys are awarded strictly based on tangible deliverables and technical execution.

---

## 6. SIGNATURES & RATIFICATION

By signing below, the founding members irrevocably agree to all terms, roles, and equity allocations outlined herein:

**Jimmy Mathu (Founder / CEO):** _____________________________ **Date:** ______________

**Tete (Co-Founder / CTO):** _________________________________ **Date:** ______________

**Sammy (Head of Risk):** ___________________________________ **Date:** ______________

**Arnold (Head of Ops):** ____________________________________ **Date:** ______________
