@echo off
REM Windows Batch File to Run Crypto Trading Bot on Windows VPS
REM Nick Radge Crypto Hybrid Strategy - Bybit Deployment

echo ================================================================================
echo CRYPTO TRADING BOT - WINDOWS VPS
echo ================================================================================
echo.
echo Strategy: Nick Radge Crypto Hybrid
echo Broker: Bybit
echo Position Stops: 40%% (Optimal from backtest)
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found! Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check if config exists
if not exist "config_crypto_bybit.json" (
    echo ERROR: config_crypto_bybit.json not found!
    echo Please create configuration file first.
    pause
    exit /b 1
)

echo Configuration file found: config_crypto_bybit.json
echo.

REM Check if required packages are installed
echo Checking dependencies...
python -c "import ccxt" >nul 2>&1
if errorlevel 1 (
    echo Installing ccxt...
    pip install ccxt
)

python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo Installing pandas...
    pip install pandas
)

python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo Installing numpy...
    pip install numpy
)

python -c "import yfinance" >nul 2>&1
if errorlevel 1 (
    echo Installing yfinance...
    pip install yfinance
)

echo.
echo ================================================================================
echo STARTING CRYPTO TRADING BOT
echo ================================================================================
echo.
echo Press Ctrl+C to stop the bot
echo Logs will be saved to: deployment\logs\crypto_bybit_live.log
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Run the bot
python live_crypto_bybit.py --config config_crypto_bybit.json

if errorlevel 1 (
    echo.
    echo ERROR: Bot crashed or stopped unexpectedly
    echo Check logs\crypto_bybit_live.log for details
    pause
)

echo.
echo Bot stopped.
pause
