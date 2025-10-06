"""
Live Trading Configuration
FTMO-Compliant Settings for London Breakout v4.1

IMPORTANT: Review all settings before going live!
"""

# ==============================================================================
# ACCOUNT SETTINGS
# ==============================================================================

ACCOUNT_TYPE = 'FTMO'  # Options: 'FTMO', 'PROP_FIRM', 'PERSONAL'
INITIAL_BALANCE = 100000  # Your account starting balance
BROKER = 'MT5'  # MetaTrader 5

# ==============================================================================
# RISK MANAGEMENT (FTMO COMPLIANT)
# ==============================================================================

# Risk per trade (% of current equity)
RISK_PER_TRADE = 0.75  # Recommended: 1.5% for optimal return/risk
                       # Conservative: 1.0%
                       # Aggressive: 1.75% (close to FTMO limits!)
                       # MAX: 1.75% (do NOT exceed for FTMO)

# FTMO Compliance Limits
FTMO_MAX_TOTAL_LOSS_PCT = 10.0  # Account terminated if exceeded
FTMO_MAX_DAILY_LOSS_PCT = 5.0   # Account terminated if exceeded
FTMO_PROFIT_TARGET_PCT = 10.0   # Challenge requirement

# Safety margins (buffer before hitting FTMO limits)
SAFETY_STOP_AT_DD_PCT = 8.5     # Stop trading at -8.5% DD (before -10%)
SAFETY_STOP_AT_DAILY_LOSS_PCT = 4.0  # Stop trading at -4% daily loss (before -5%)

# Emergency stops
MAX_CONSECUTIVE_LOSSES = 5       # Stop trading after X losses in a row
MAX_DAILY_TRADES = 3            # Maximum trades per day (prevent overtrading)

# ==============================================================================
# STRATEGY PARAMETERS (OPTIMIZED - DO NOT CHANGE)
# ==============================================================================

# These parameters were optimized through proper OOS validation
# Changing them may result in overfitting or poor performance

STRATEGY_PARAMS = {
    # Asia Breakout Settings
    'enable_asia_breakout': True,
    'min_asia_range_pips': 15,
    'max_asia_range_pips': 60,
    'breakout_buffer_pips': 1.5,
    'min_first_hour_move_pips': 18,

    # Triangle Pattern Settings
    'enable_triangle_breakout': True,  # Set False for Asia-only (simpler, 97% of profits)
    'triangle_lookback': 60,  # DO NOT CHANGE - optimized parameter
    'triangle_r2_min': 0.5,
    'triangle_slope_tolerance': 0.0003,
    'triangle_buffer_pct': 0.0015,
    'triangle_time_start': 3,  # 3 AM
    'triangle_time_end': 9,    # 9 AM

    # Risk/Reward
    'risk_reward_ratio': 1.3,
    'min_tp_pips': 25,
    'use_trailing_stop': True,
}

# ==============================================================================
# TRADING HOURS & SESSIONS
# ==============================================================================

TRADING_ENABLED = True  # Master switch - set False to stop all trading

# Trading sessions (GMT/UTC)
ASIA_SESSION_START = 0   # 00:00 GMT
ASIA_SESSION_END = 3     # 03:00 GMT

LONDON_SESSION_START = 3  # 03:00 GMT
LONDON_SESSION_END = 11   # 11:00 GMT

# Days to trade (0=Monday, 6=Sunday)
TRADING_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday only

# Avoid trading during high-impact news (optional)
AVOID_NEWS = True
HIGH_IMPACT_NEWS_BUFFER_MINUTES = 30  # Don't trade 30min before/after news

# ==============================================================================
# INSTRUMENT SETTINGS
# ==============================================================================

SYMBOL = 'EURUSD'
TIMEFRAME_EXECUTION = 'H1'  # 1-hour for trade execution
TIMEFRAME_TREND = 'H4'      # 4-hour for trend filter

# Broker-specific settings
SYMBOL_SUFFIX = ''  # e.g., '.raw' or 'pro' depending on broker
SLIPPAGE_PIPS = 1.0  # Expected slippage (conservative estimate)

# ==============================================================================
# LOGGING & MONITORING
# ==============================================================================

# Log settings
LOG_LEVEL = 'INFO'  # Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
LOG_TO_FILE = True
LOG_FILE_PATH = 'live/logs/trading.log'
LOG_ROTATION = 'daily'  # Rotate logs daily

# Notifications (optional - requires setup)
TELEGRAM_ENABLED = False
TELEGRAM_BOT_TOKEN = ''  # Your Telegram bot token
TELEGRAM_CHAT_ID = ''    # Your Telegram chat ID

EMAIL_ENABLED = False
EMAIL_ADDRESS = ''
EMAIL_SMTP_SERVER = ''
EMAIL_SMTP_PORT = 587

# Alert thresholds
ALERT_ON_TRADE_ENTRY = True
ALERT_ON_TRADE_EXIT = True
ALERT_ON_DAILY_LOSS_PCT = 3.0  # Alert if daily loss exceeds -3%
ALERT_ON_DRAWDOWN_PCT = 6.0    # Alert if drawdown exceeds -6%

# ==============================================================================
# PAPER TRADING MODE
# ==============================================================================

PAPER_TRADE_MODE = False  # IMPORTANT: Set True for paper trading, False for live!

# Paper trading settings
PAPER_INITIAL_BALANCE = 100000
PAPER_LOG_FILE = 'live/logs/paper_trades.csv'

# ==============================================================================
# DATABASE & PERSISTENCE
# ==============================================================================

# Track trades and performance
DATABASE_ENABLED = True
DATABASE_PATH = 'live/data/trading_history.db'

# Save state for recovery after restart
SAVE_STATE = True
STATE_FILE = 'live/data/trading_state.json'

# ==============================================================================
# PERFORMANCE TRACKING
# ==============================================================================

# Track these metrics
TRACK_DAILY_PNL = True
TRACK_DRAWDOWN = True
TRACK_WIN_RATE = True
TRACK_RISK_METRICS = True

# Report frequency
DAILY_REPORT_TIME = '18:00'  # Send daily summary at 6 PM GMT
WEEKLY_REPORT_DAY = 5        # Friday (0=Monday)

# ==============================================================================
# SAFETY CHECKS (AUTO-ENFORCEMENT)
# ==============================================================================

# These are automatically enforced by the trading system
ENFORCE_FTMO_LIMITS = True      # Automatically stop if FTMO limits violated
ENFORCE_DAILY_TRADE_LIMIT = True
ENFORCE_CONSECUTIVE_LOSS_LIMIT = True
ENFORCE_TRADING_HOURS = True

# Restart behavior after stop
AUTO_RESUME_NEXT_DAY = True  # Resume trading next day after daily loss limit hit
AUTO_RESUME_AFTER_LOSS_STREAK = False  # Require manual restart after loss streak

# ==============================================================================
# ADVANCED SETTINGS (EXPERTS ONLY)
# ==============================================================================

# Order execution
ORDER_MAGIC_NUMBER = 20251006  # Unique identifier for this EA
ORDER_COMMENT = 'LondonBreakout_v4.1'
MAX_RETRIES = 3
RETRY_DELAY_MS = 500

# Connection monitoring
CHECK_CONNECTION_INTERVAL = 60  # Check MT5 connection every 60 seconds
RECONNECT_ATTEMPTS = 5

# Data validation
VALIDATE_DATA_QUALITY = True
MIN_BARS_REQUIRED = 100  # Minimum bars needed before trading

# ==============================================================================
# RECOMMENDED SETTINGS BY ACCOUNT TYPE
# ==============================================================================

"""
FTMO CHALLENGE (Most Conservative):
    RISK_PER_TRADE = 1.0
    SAFETY_STOP_AT_DD_PCT = 7.0
    SAFETY_STOP_AT_DAILY_LOSS_PCT = 3.5
    MAX_CONSECUTIVE_LOSSES = 4
    enable_triangle_breakout = False  # Asia only for simplicity

FTMO VERIFICATION (Balanced):
    RISK_PER_TRADE = 1.25
    SAFETY_STOP_AT_DD_PCT = 8.0
    SAFETY_STOP_AT_DAILY_LOSS_PCT = 4.0
    MAX_CONSECUTIVE_LOSSES = 5
    enable_triangle_breakout = True

FTMO FUNDED (Optimal):
    RISK_PER_TRADE = 1.5
    SAFETY_STOP_AT_DD_PCT = 8.5
    SAFETY_STOP_AT_DAILY_LOSS_PCT = 4.0
    MAX_CONSECUTIVE_LOSSES = 5
    enable_triangle_breakout = True

PERSONAL ACCOUNT (Aggressive - if you can handle it):
    RISK_PER_TRADE = 1.75
    SAFETY_STOP_AT_DD_PCT = 9.0
    SAFETY_STOP_AT_DAILY_LOSS_PCT = 4.5
    MAX_CONSECUTIVE_LOSSES = 6
    enable_triangle_breakout = True
"""

# ==============================================================================
# VALIDATION
# ==============================================================================

def validate_config():
    """Validate configuration before going live"""
    errors = []
    warnings = []

    # Critical checks
    if RISK_PER_TRADE > 1.75:
        errors.append(f"RISK_PER_TRADE ({RISK_PER_TRADE}%) exceeds safe maximum (1.75%)")

    if RISK_PER_TRADE > 1.5:
        warnings.append(f"RISK_PER_TRADE ({RISK_PER_TRADE}%) is aggressive. Max DD will be close to -10%")

    if not PAPER_TRADE_MODE and ACCOUNT_TYPE == 'FTMO':
        warnings.append("PAPER_TRADE_MODE is OFF and ACCOUNT_TYPE is FTMO. Ensure you've tested thoroughly!")

    if SAFETY_STOP_AT_DD_PCT >= FTMO_MAX_TOTAL_LOSS_PCT:
        errors.append(f"SAFETY_STOP_AT_DD_PCT ({SAFETY_STOP_AT_DD_PCT}%) must be < FTMO limit ({FTMO_MAX_TOTAL_LOSS_PCT}%)")

    if SAFETY_STOP_AT_DAILY_LOSS_PCT >= FTMO_MAX_DAILY_LOSS_PCT:
        errors.append(f"SAFETY_STOP_AT_DAILY_LOSS_PCT ({SAFETY_STOP_AT_DAILY_LOSS_PCT}%) must be < FTMO limit ({FTMO_MAX_DAILY_LOSS_PCT}%)")

    if not TRADING_ENABLED:
        warnings.append("TRADING_ENABLED is False - no trades will be taken")

    if TELEGRAM_ENABLED and not TELEGRAM_BOT_TOKEN:
        warnings.append("TELEGRAM_ENABLED but no bot token provided")

    # Print results
    if errors:
        print("❌ CONFIGURATION ERRORS:")
        for err in errors:
            print(f"   - {err}")
        return False

    if warnings:
        print("⚠️  CONFIGURATION WARNINGS:")
        for warn in warnings:
            print(f"   - {warn}")

    if not errors and not warnings:
        print("✅ Configuration validated successfully")

    return True

if __name__ == '__main__':
    print("="*80)
    print("LIVE TRADING CONFIGURATION VALIDATION")
    print("="*80)
    print(f"\nAccount Type: {ACCOUNT_TYPE}")
    print(f"Risk Per Trade: {RISK_PER_TRADE}%")
    print(f"Paper Trade Mode: {PAPER_TRADE_MODE}")
    print(f"Asia Breakout: {STRATEGY_PARAMS['enable_asia_breakout']}")
    print(f"Triangle Patterns: {STRATEGY_PARAMS['enable_triangle_breakout']}")
    print("\nValidating...")
    validate_config()
