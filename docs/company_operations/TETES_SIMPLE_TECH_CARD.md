# TETE'S SIMPLE TECH CHECKLIST
**Chief Technology Officer:** Tete  
**Rule:** Tete does not need to get overwhelmed with complex algorithmic formulas or 400-line math derivations. Jimmy will directly assign what needs to be coded. Tete's job is to keep the servers online, the MT5 connection green, and the bots running smoothly.

---

## 💻 TETE'S 3 DAILY NON-TECHNICAL CHECKS

### 1. Is the Hostinger VPS Online? (Daily Morning Check)
- Every morning at 9:00 AM, open **Remote Desktop** on your computer and connect to the Hostinger VPS.
- Check the MetaTrader 5 terminal in the bottom right corner:
  - **Green / Blue bars:** Connected and live!
  - **Red bars / "No Connection":** Go to *File -> Login to Trade Account*, re-enter the password, and click OK.

### 2. Start the 24/7 Automated Bot (1-Click Run)
On the VPS desktop, double-click:
```cmd
C:\SAJIM HOLDINGS\scripts\hostinger_vps_setup.bat
```
Or type this single command in terminal:
```bash
python run.py server
```
- Confirm the terminal window is open and showing rolling timestamp logs every few seconds.

### 3. Error Check & Escalation
- If you see **RED ERRORS** or the terminal crashes:
  1. Take a screenshot immediately.
  2. Send it to Jimmy on WhatsApp: *"Bro, MT5 disconnected here, check this screenshot."*
  3. **Important:** Do NOT change any algorithm math files on your own. Wait for Jimmy's instruction.
