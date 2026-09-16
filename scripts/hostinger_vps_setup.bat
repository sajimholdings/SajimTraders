@echo off
rem ============================================================================
rem                 SAJIM TRADERS — HOSTINGER VPS BOOTSTRAPPER
rem ============================================================================
echo [*] Initializing Sajim Hostinger VPS Environment...

rem 1. Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python is not installed. Please install Python 3.12 from python.org or via winget/choco.
    pause
    exit /b 1
)

echo [*] Python found. Upgrading pip and installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements-windows.txt
pip install -r requirements.txt

rem 2. Verify MT5 Terminal connection
echo [*] Verifying MT5 installation and project configuration...
python -c "import MetaTrader5; print('[+] MetaTrader5 package loaded successfully.')"

rem 3. Launch the 24/7 Supervisor Loop
echo [*] Starting Sajim 24/7 Bridge Supervisor Daemon...
:loop
echo [%date% %time%] Launching server daemon...
python run.py server
echo [!] Server process exited. Restarting in 10 seconds...
timeout /t 10 /nobreak
goto loop
