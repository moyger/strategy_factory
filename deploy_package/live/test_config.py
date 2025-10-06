"""
Test configuration and validate settings on Mac
(No MT5 required)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from live.config_live import *

def test_configuration():
    """Test all configuration settings"""

    print("="*80)
    print("CONFIGURATION TEST (macOS Compatible)")
    print("="*80)

    print(f"\n📋 Account Settings:")
    print(f"   Account Type: {ACCOUNT_TYPE}")
    print(f"   Initial Balance: ${INITIAL_BALANCE:,}")
    print(f"   Risk Per Trade: {RISK_PER_TRADE}%")

    print(f"\n🛡️  FTMO Safety Limits:")
    print(f"   Max Total Loss: {FTMO_MAX_TOTAL_LOSS_PCT}%")
    print(f"   Max Daily Loss: {FTMO_MAX_DAILY_LOSS_PCT}%")
    print(f"   Safety Stop at DD: {SAFETY_STOP_AT_DD_PCT}%")
    print(f"   Safety Stop Daily: {SAFETY_STOP_AT_DAILY_LOSS_PCT}%")

    print(f"\n⚙️  Strategy Settings:")
    print(f"   Asia Breakout: {STRATEGY_PARAMS['enable_asia_breakout']}")
    print(f"   Triangle Breakout: {STRATEGY_PARAMS['enable_triangle_breakout']}")
    print(f"   Triangle Lookback: {STRATEGY_PARAMS['triangle_lookback']}")

    print(f"\n🧪 Mode:")
    print(f"   Paper Trade Mode: {PAPER_TRADE_MODE}")

    print(f"\n⏰ Trading Hours (GMT):")
    print(f"   London Session: {LONDON_SESSION_START}:00 - {LONDON_SESSION_END}:00")
    print(f"   Trading Days: {TRADING_DAYS} (0=Mon, 4=Fri)")

    # Validate
    print(f"\n🔍 Validating configuration...")
    is_valid = validate_config()

    if is_valid:
        print(f"\n✅ Configuration is valid and ready for deployment!")
        print(f"\n📝 Next Steps:")
        print(f"   1. Deploy to Windows VPS (MetaTrader5 requires Windows)")
        print(f"   2. Install MT5 on VPS")
        print(f"   3. Install dependencies: pip install MetaTrader5 pandas numpy")
        print(f"   4. Copy this project to VPS")
        print(f"   5. Run: python live/live_trader.py")
    else:
        print(f"\n❌ Configuration has errors. Please fix before deploying.")

    print(f"\n{'='*80}")

    # Calculate expected performance
    print(f"\nEXPECTED PERFORMANCE (Based on Backtest)")
    print(f"{'='*80}")

    risk_scenarios = {
        1.0: {'return': 50, 'dd': 5.66, 'daily': 1.53},
        1.25: {'return': 75, 'dd': 7.05, 'daily': 1.92},
        1.5: {'return': 110, 'dd': 8.42, 'daily': 2.30},
        1.75: {'return': 156, 'dd': 9.78, 'daily': 2.68},
    }

    if RISK_PER_TRADE in risk_scenarios:
        scenario = risk_scenarios[RISK_PER_TRADE]
        annual_pnl = INITIAL_BALANCE * scenario['return'] / 100
        monthly_pnl = annual_pnl / 12

        print(f"\nWith {RISK_PER_TRADE}% Risk Per Trade:")
        print(f"   Expected Annual Return: {scenario['return']}%")
        print(f"   Expected Annual P&L: ${annual_pnl:,.0f}")
        print(f"   Expected Monthly P&L: ${monthly_pnl:,.0f}")
        print(f"   Expected Max Drawdown: -{scenario['dd']}%")
        print(f"   Expected Worst Daily Loss: -{scenario['daily']}%")

        # FTMO compliance
        ftmo_compliant = scenario['dd'] < FTMO_MAX_TOTAL_LOSS_PCT and scenario['daily'] < FTMO_MAX_DAILY_LOSS_PCT
        print(f"\n   FTMO Compliant: {'✅ YES' if ftmo_compliant else '❌ NO'}")

        if scenario['dd'] > SAFETY_STOP_AT_DD_PCT:
            print(f"   ⚠️  WARNING: Max DD exceeds your safety stop!")

        if RISK_PER_TRADE >= 1.75:
            print(f"\n   ⚠️  WARNING: 1.75% risk is aggressive!")
            print(f"   Max DD will be -{scenario['dd']}% (only 0.22% from FTMO limit)")
    else:
        print(f"\n⚠️  Custom risk level: {RISK_PER_TRADE}%")
        print(f"   Performance metrics not available for this risk level")

    print(f"\n{'='*80}")
    print(f"REALISTIC EXPECTATIONS")
    print(f"{'='*80}")
    print(f"\n⚠️  Remember:")
    print(f"   - These are BACKTEST results, not guarantees")
    print(f"   - Live performance may differ significantly")
    print(f"   - PAPER TRADE for 3-6 months before going live")
    print(f"   - Expect losing months (July 2025: -$3,378 in backtest)")
    print(f"   - Can handle waking up at 3 AM GMT consistently?")
    print(f"\n{'='*80}\n")

if __name__ == '__main__':
    test_configuration()
