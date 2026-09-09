# BEEP ARCHITECTURE & ACCESS PROTECTION GUIDE
**Author:** Jimmy Mathu (Founder & Chief Architect)  
**Company:** Sajim Holdings (SAJIM Lab)  
**Scope:** Core IP Protection, API Isolation & Team Operational Boundaries

---

## 1. THE 3-TIER ISOLATION ARCHITECTURE

To ensure Jimmy's 4 years of quantitative IP ($B(t)$, $M(t)$, $\Lambda(t)$ formulas and weight matrices) are never compromised, Sajim Holdings uses a strict 3-tier boundary:

```
+-------------------------------------------------------------+
| TIER 1: THE SACRED CORE (Jimmy Only)                        |
| File: beep_core.py                                          |
| Contains: Raw math, deviation formulas, weights, B(t) bands |
| Access: 100% Jimmy Mathu. Never committed to shared Git.    |
+------------------------------+------------------------------+
                               | (Local Import Only)
                               v
+-------------------------------------------------------------+
| TIER 2: THE SECURE GATEWAY (Jimmy's VPS / Host)              |
| File: api.py                                                |
| Function: Authenticates requests via X-BEEP-API-KEY.         |
| Outputs: Sanitized JSON (Direction, SL/TP, M(t), 4-Check).  |
| Access: Tete and Sammy have API keys, but NO source access. |
+------------------------------+------------------------------+
                               | (HTTPS / Encrypted REST)
                               v
+-------------------------------------------------------------+
| TIER 3: THE CONSUMER CLIENT (Sajim Holdings Team)           |
| File: app.py (MT5 Bridge, Sammy Dashboard, WhatsApp Bot)    |
| Developers: Tete (CTO) & Sammy (Risk)                       |
| Access: Queries api.py remotely. Never sees beep_core.py.   |
+-------------------------------------------------------------+
```

---

## 2. API ENDPOINTS & TEAM WORKFLOW

### Endpoint 1: Signal Generation (`POST /v1/signal`)
* **Consumer:** Tete's MT5 bridge / Python trading bot.
* **Input:** `{"symbol": "XAUUSD", "prices": [2310.5, 2311.2, ...]}`
* **Output:** Direction (`BUY`/`SELL`), suggested Entry, $B(t)$ support floor, Stop Loss, Take Profit, and $M(t)$ momentum.
* **IP Protection:** Exact deviation ratios, internal z-score calculations, and mathematical constants are omitted.

### Endpoint 2: Sammy's 4-Check Gatekeeper (`POST /v1/sammy-4check`)
* **Consumer:** Sammy's risk dashboard / verification terminal.
* **Input:** Proposed trade metrics.
* **Output:** `GO` or `STOP` decision based on the 4 canonical conditions:
  1. $M(t) > 40$
  2. $SL$ below $B(t)$ (for BUY) or above $B(t)$ (for SELL)
  3. Lot size == $0.01$
  4. $\Lambda > 10\%$

### Endpoint 3: Executive Override (`POST /v1/override`)
* **Consumer:** Jimmy Mathu only.
* **Input:** Trade ID + Override Master Secret.
* **Function:** Bypasses any false-positive block if the founder verifies market conditions manually.

---

## 3. HOW TO DEPLOY & PROTECT BEEP ON A VPS (KES 1,500/MO SERVER)

1. **Keep `beep_core.py` and `api.py` on your private server:**
   - Host `api.py` on a lightweight VPS (or local PC with Cloudflare Tunnel/ngrok).
2. **Issue Separate API Keys:**
   - Tete gets: `sajim-tete-live-key-9921`
   - Sammy gets: `sajim-sammy-risk-key-4412`
   - Jimmy holds: `jimmy-founder-master-secret-7700`
3. **Hardening Options (Optional Next Step):**
   - **PyArmor Obfuscation:** Run `pyarmor gen beep_core.py` to convert the core into an encrypted binary so even if someone copies the file, it cannot be read or decompiled.
   - **Compiled C Extension (.pyd):** Compile `beep_core.py` using Cython into a compiled Windows binary.

---

## 4. HOW TO RUN

### Step 1: Start the Secure API Gateway
```bash
python api.py
```
*(Runs on port 8080 by default)*

### Step 2: Run the Sajim Holdings Client
```bash
python app.py
```
*(Connects via API, tests connection, evaluates signal, and formats the WhatsApp broadcast alert)*
