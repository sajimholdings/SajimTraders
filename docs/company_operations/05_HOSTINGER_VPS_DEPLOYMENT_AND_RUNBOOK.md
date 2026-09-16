# SAJIM TRADERS — HOSTINGER VPS DEPLOYMENT & 24/7 RUNBOOK
**Document ID:** SOP-VPS-002  
**Target Operators:** Arnold (Procurement & Billing) & Tete (Technical Deployment)  
**Authority:** Jimmy Mathu, CEO  
**Effective Date:** September 12, 2026  

---

## 1. WHY HOSTINGER VPS IS MANDATORY TODAY

Running trading bots on a personal laptop or home desktop introduces fatal risks:
1. **Power & Battery Drops:** Sudden power outages in Kenya can cut off open orders without trailing protection.
2. **Wi-Fi & Data Latency:** Cellular Wi-Fi spikes introduce execution slippage on high-speed Gold moves.
3. **Hardware Sleep/Hibernate:** Windows automatically suspends background Python daemons if untouched.

A **Hostinger Cloud KVM VPS** provides:
- **99.9% Guaranteed Uptime:** Hosted in Tier-3 enterprise data centers.
- **Ultra-Low Latency (< 10ms):** Direct fiber cross-connects to European broker trading servers.
- **Continuous 24/7 Execution:** Automated bots run while the entire team sleeps.

---

## 2. PROCUREMENT SPECIFICATIONS (FOR ARNOLD)

Arnold is responsible for purchasing the server using the team's operating cashflow (\$43 liquid capital):

| Specification | Recommended Configuration | Budget Range |
| :--- | :--- | :--- |
| **Provider** | **Hostinger** ([hostinger.com/vps-hosting](https://www.hostinger.com/vps-hosting)) | ~$6.00 – $12.00 / month |
| **Plan Tier** | **KVM 2** (or KVM 1 minimum) | 2 vCPU, 8 GB RAM, 100 GB NVMe Storage |
| **Operating System** | **Windows Server 2022 (Datacenter)** *(Preferred for Native MT5)*<br>or **Ubuntu 24.04 LTS** *(if using Linux + Wine)* | Included in plan |
| **Server Location** | **United Kingdom (London)** or **Germany (Frankfurt)** | Closest proximity to Headway / JustMarkets / FTMO servers |
| **Payment Method** | M-Pesa Global / Virtual Visa / PayPal | Funded from team operational pool |

---

## 3. TECHNICAL SETUP INSTRUCTIONS (FOR TETE)

Once Arnold provides the server IP, Administrator username, and password:

### Step 1: Remote Desktop Connection (RDP)
1. On your Windows PC, open **Remote Desktop Connection** (`mstsc.exe`).
2. Enter the Hostinger VPS IP Address: `xxx.xxx.xxx.xxx`.
3. Username: `Administrator`.
4. Password: `(Hostinger VPS Password)`.

### Step 2: Install Base Software & Environment
Open PowerShell as Administrator on the VPS and run:
```powershell
# 1. Install Chocolatey (Package Manager)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 2. Install Python 3.12 & Git
choco install python --version=3.12.4 -y
choco install git -y
refreshenv
```

### Step 3: Install MetaTrader 5 & Configure Broker
1. Download the MetaTrader 5 installer directly inside the VPS browser:
   - For Headway: `https://hw.site/download/mt5`
   - For FTMO: `https://ftmo.com/en/metatrader-5/`
2. Install MT5 to default directory: `C:\Program Files\MetaTrader 5\terminal64.exe`.
3. Launch MT5, log in to our master trading account:
   - Login: `[REDACTED_ACCOUNT]`
   - Server: `Headway-Real` (or FTMO Challenge server)
   - Save password in terminal and enable **"Allow automated trading"** in *Tools -> Options -> Expert Advisors*.

### Step 4: Clone Codebase & Install Python Dependencies
```powershell
# Clone repository
cd C:\
git clone https://github.com/SajimTraders/SAJIM-HOLDINGS.git "C:\SAJIM HOLDINGS"
cd "C:\SAJIM HOLDINGS"

# Install Python requirements
pip install -r requirements-windows.txt
pip install -r requirements.txt
```

### Step 5: Configure `.env` Credentials
Ensure `.env` on the VPS contains the encrypted credentials:
```ini
MT5_LOGIN=[REDACTED_ACCOUNT]
MT5_PASSWORD=YOUR_ENCRYPTED_PASSWORD
MT5_SERVER=Headway-Real
MT5_PATH="C:\Program Files\MetaTrader 5\terminal64.exe"
BEEP_API_SECRET=your_production_secret
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

---

## 4. 24/7 AUTO-RESTART DAEMON (CRITICAL)

To guarantee the bot restarts automatically if the VPS ever reboots for Windows updates:

### Automated Startup Script (`scripts/run_vps_daemon.bat`)
Create a shortcut of this file in the Windows Startup folder (`shell:startup`):
```bat
@echo off
title SAJIM 24/7 TRADING DAEMON
cd "C:\SAJIM HOLDINGS"
:loop
echo [%date% %time%] Starting Sajim 24/7 Server Daemon...
python run.py server
echo [%date% %time%] Daemon crashed or exited. Restarting in 10 seconds...
timeout /t 10 /nobreak
goto loop
```

---

## 5. MONITORING & VERIFICATION PROTOCOL (TETE & VAL)

1. **Heartbeat Check:** Verify that `overnight_status.json` is updating every 15 seconds.
2. **Remote Telemetry:** The VPS automatically pushes active signals to Supabase and broadcasts to our VIP Telegram channel.
3. **Morning Report (09:00 EAT):** Val checks the live dashboard and confirms VPS status to Jimmy and the team.
