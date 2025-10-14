@echo off
REM Windows Setup Script for Crypto Trading Bot
REM Run this once to set up everything on Windows VPS

echo ================================================================================
echo CRYPTO TRADING BOT - WINDOWS VPS SETUP
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python 3.8 or higher:
    echo 1. Go to https://www.python.org/downloads/
    echo 2. Download Python 3.11 or 3.12
    echo 3. During installation, check "Add Python to PATH"
    echo 4. Restart this script after installation
    echo.
    pause
    exit /b 1
)

echo Step 1: Python found
python --version
echo.

echo Step 2: Upgrading pip...
python -m pip install --upgrade pip
echo.

echo Step 3: Choose Bybit connection method...
echo.
echo Which Bybit adapter do you want to use?
echo.
echo 1. Official Bybit SDK (pybit) - RECOMMENDED
echo    - Official from Bybit
echo    - Always up-to-date
echo    - Best performance
echo    - Lighter weight
echo.
echo 2. CCXT (Multi-exchange)
echo    - Works with 100+ exchanges
echo    - Easy to switch brokers
echo    - Unified API
echo.
set /p adapter_choice="Enter choice (1 or 2): "

echo.
echo Step 4: Installing required packages...

if "%adapter_choice%"=="1" (
    echo Installing pybit (Official Bybit SDK)...
    pip install pybit
    echo.
    echo NOTE: Set "broker_adapter": "official" in your config file
) else (
    echo Installing ccxt (Multi-exchange)...
    pip install ccxt
    echo.
    echo NOTE: Set "broker_adapter": "ccxt" in your config file
)

echo.
echo Installing pandas (data analysis)...
pip install pandas

echo Installing numpy (numerical computing)...
pip install numpy

echo Installing yfinance (historical data)...
pip install yfinance

echo Installing vectorbt (backtesting)...
pip install vectorbt

echo Installing requests (API calls)...
pip install requests

echo.
echo ================================================================================
echo SETUP COMPLETE!
echo ================================================================================
echo.
echo Next steps:
echo 1. Edit config_crypto_bybit.json and add your Bybit API keys
echo 2. Run: run_crypto_bot_windows.bat
echo.
echo Important:
echo - Always start with testnet: true
echo - Always start with dry_run: true
echo - Test for 1-2 weeks before going live
echo.
pause
