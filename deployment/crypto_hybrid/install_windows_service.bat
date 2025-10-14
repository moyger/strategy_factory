@echo off
REM Install Crypto Trading Bot as Windows Service
REM This allows the bot to run 24/7 in the background and auto-start on reboot

echo ================================================================================
echo INSTALL CRYPTO BOT AS WINDOWS SERVICE
echo ================================================================================
echo.
echo This will install the bot as a Windows service that:
echo - Runs 24/7 in the background
echo - Starts automatically on Windows reboot
echo - Can be managed via Services.msc
echo.
echo WARNING: This requires Administrator privileges!
echo Right-click this file and select "Run as Administrator"
echo.
pause

REM Check for admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: You need to run this as Administrator!
    echo Right-click and select "Run as Administrator"
    pause
    exit /b 1
)

echo Administrator privileges confirmed.
echo.

REM Install NSSM (Non-Sucking Service Manager) if not present
if not exist "nssm.exe" (
    echo NSSM not found. Please download it:
    echo 1. Go to: https://nssm.cc/download
    echo 2. Download nssm-2.24.zip
    echo 3. Extract nssm.exe to this folder
    echo 4. Run this script again
    echo.
    pause
    exit /b 1
)

echo NSSM found.
echo.

REM Get current directory
set CURRENT_DIR=%cd%

echo Installing service...
nssm install CryptoTradingBot "%CURRENT_DIR%\run_crypto_bot_windows.bat"

REM Configure service
nssm set CryptoTradingBot AppDirectory "%CURRENT_DIR%"
nssm set CryptoTradingBot DisplayName "Crypto Trading Bot (Nick Radge)"
nssm set CryptoTradingBot Description "Automated crypto trading bot using Nick Radge Hybrid strategy on Bybit"
nssm set CryptoTradingBot Start SERVICE_AUTO_START
nssm set CryptoTradingBot AppStdout "%CURRENT_DIR%\logs\service_stdout.log"
nssm set CryptoTradingBot AppStderr "%CURRENT_DIR%\logs\service_stderr.log"
nssm set CryptoTradingBot AppRotateFiles 1
nssm set CryptoTradingBot AppRotateBytes 1048576

echo.
echo ================================================================================
echo SERVICE INSTALLED!
echo ================================================================================
echo.
echo Service Name: CryptoTradingBot
echo Display Name: Crypto Trading Bot (Nick Radge)
echo Status: Not started yet
echo.
echo To manage the service:
echo - Start:   sc start CryptoTradingBot
echo - Stop:    sc stop CryptoTradingBot
echo - Status:  sc query CryptoTradingBot
echo - Remove:  sc delete CryptoTradingBot
echo.
echo Or use Services Manager:
echo - Press Win+R
echo - Type: services.msc
echo - Find: Crypto Trading Bot
echo.
echo IMPORTANT: Test the bot manually first before starting the service!
echo           Run: run_crypto_bot_windows.bat
echo.
pause
