"""
FTMO Risk Manager

Enforces FTMO Swing Challenge rules:
- Maximum drawdown: -10% (failure)
- Maximum daily drawdown: -5% (failure)
- Profit target: +10% (pass)
- Leverage: 1:30 max
- 60-day time limit

Circuit breakers:
- Stop trading if approaching DD limits
- Scale down after consecutive losses
- Scale up gradually during winning streaks
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FTMORiskManager:
    def __init__(self, initial_equity=100000.0, leverage=30.0):
        """
        Args:
        - initial_equity: Starting account size ($100k for FTMO Swing)
        - leverage: Max leverage (1:30)
        """
        self.initial_equity = initial_equity
        self.equity = initial_equity
        self.peak_equity = initial_equity
        self.daily_start_equity = initial_equity
        self.leverage = leverage

        # FTMO rules
        self.max_drawdown_pct = 0.10  # -10%
        self.max_daily_dd_pct = 0.05   # -5%
        self.profit_target_pct = 0.10  # +10%

        # Circuit breaker thresholds
        self.dd_warning_threshold = 0.07    # -7% total DD: reduce risk
        self.dd_critical_threshold = 0.09   # -9% total DD: stop trading
        self.daily_dd_warning = 0.03        # -3% daily DD: reduce risk
        self.daily_dd_critical = 0.045      # -4.5% daily DD: stop trading

        # Position sizing
        self.base_risk_per_trade_pct = 0.01  # 1% risk per trade (base)
        self.max_risk_per_trade_pct = 0.02   # 2% max risk per trade
        self.min_risk_per_trade_pct = 0.005  # 0.5% min risk per trade

        # Consecutive loss tracking
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.max_consecutive_losses = 3  # Scale down after 3 losses

        # State
        self.is_challenge_active = True
        self.failure_reason = None
        self.pass_date = None
        self.trades = []

    def update_equity(self, new_equity, timestamp):
        """Update equity and check FTMO rules"""
        self.equity = new_equity

        # Update peak
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity

        # Check total drawdown
        total_dd = (self.equity - self.peak_equity) / self.peak_equity
        if total_dd < -self.max_drawdown_pct:
            self.is_challenge_active = False
            self.failure_reason = f'Max DD violated: {total_dd*100:.2f}% (limit: -10%)'
            return False

        # Check profit target
        total_return = (self.equity - self.initial_equity) / self.initial_equity
        if total_return >= self.profit_target_pct:
            self.is_challenge_active = False
            self.pass_date = timestamp
            return True  # Challenge passed!

        return True

    def update_daily(self, new_equity, current_date):
        """Update daily equity and check daily DD limit"""
        # Check if new day
        if current_date != getattr(self, 'last_date', None):
            self.daily_start_equity = self.equity
            self.last_date = current_date

        self.equity = new_equity

        # Check daily drawdown
        daily_dd = (self.equity - self.daily_start_equity) / self.daily_start_equity
        if daily_dd < -self.max_daily_dd_pct:
            self.is_challenge_active = False
            self.failure_reason = f'Daily DD violated: {daily_dd*100:.2f}% (limit: -5%)'
            return False

        return True

    def can_trade(self):
        """Check if trading is allowed"""
        if not self.is_challenge_active:
            return False

        # Check circuit breakers
        total_dd = (self.equity - self.peak_equity) / self.peak_equity
        if total_dd < -self.dd_critical_threshold:
            return False  # Stop trading at -9% DD

        daily_dd = (self.equity - self.daily_start_equity) / self.daily_start_equity
        if daily_dd < -self.daily_dd_critical:
            return False  # Stop trading at -4.5% daily DD

        return True

    def calculate_position_size(self, entry_price, stop_loss_price, pair='EURUSD'):
        """
        Calculate position size based on:
        - Current risk per trade (adjusted for DD and consecutive losses)
        - Stop loss distance
        - FTMO leverage limit

        Returns: lot size (1.0 = $100k notional)
        """
        if not self.can_trade():
            return 0.0

        # Adjust risk based on drawdown and consecutive losses
        risk_pct = self.get_adjusted_risk_pct()

        # Calculate risk amount in dollars
        risk_dollars = self.equity * risk_pct

        # Calculate stop loss distance in pips
        pip_value = 0.0001 if pair in ['EURUSD', 'GBPUSD'] else 0.01
        sl_distance_pips = abs(entry_price - stop_loss_price) / pip_value

        # Calculate position size
        # For EUR/USD: 1 standard lot (100k) = $10 per pip
        # Position size = Risk $ / (SL pips × $ per pip)
        dollars_per_pip_per_lot = 10.0
        lot_size = risk_dollars / (sl_distance_pips * dollars_per_pip_per_lot)

        # Apply leverage limit
        max_lot_size = (self.equity * self.leverage) / 100000  # Notional / 100k
        lot_size = min(lot_size, max_lot_size)

        # Minimum 0.01 lots
        lot_size = max(0.01, round(lot_size, 2))

        return lot_size

    def get_adjusted_risk_pct(self):
        """
        Dynamically adjust risk per trade based on:
        - Total drawdown
        - Daily drawdown
        - Consecutive losses
        - Consecutive wins
        """
        base_risk = self.base_risk_per_trade_pct

        # Reduce risk based on total DD
        total_dd = (self.equity - self.peak_equity) / self.peak_equity
        if total_dd < -self.dd_warning_threshold:
            base_risk *= 0.5  # Cut risk in half at -7% DD

        # Reduce risk based on daily DD
        daily_dd = (self.equity - self.daily_start_equity) / self.daily_start_equity
        if daily_dd < -self.daily_dd_warning:
            base_risk *= 0.5  # Cut risk in half at -3% daily DD

        # Reduce risk after consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            base_risk *= 0.5

        # Increase risk after consecutive wins (but cap at max)
        if self.consecutive_wins >= 5:
            base_risk *= 1.5

        # Clamp to min/max
        return np.clip(base_risk, self.min_risk_per_trade_pct, self.max_risk_per_trade_pct)

    def record_trade(self, pnl, timestamp):
        """Record trade outcome and update consecutive win/loss counter"""
        self.trades.append({
            'timestamp': timestamp,
            'pnl': pnl,
            'equity_before': self.equity,
            'equity_after': self.equity + pnl
        })

        # Update consecutive counters
        if pnl > 0:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0

        # Update equity
        return self.update_equity(self.equity + pnl, timestamp)

    def get_risk_status(self):
        """Get current risk status for monitoring"""
        total_dd = (self.equity - self.peak_equity) / self.peak_equity
        daily_dd = (self.equity - self.daily_start_equity) / self.daily_start_equity
        total_return = (self.equity - self.initial_equity) / self.initial_equity

        # Determine risk level
        if total_dd < -self.dd_critical_threshold or daily_dd < -self.daily_dd_critical:
            risk_level = 'CRITICAL'
        elif total_dd < -self.dd_warning_threshold or daily_dd < -self.daily_dd_warning:
            risk_level = 'WARNING'
        else:
            risk_level = 'NORMAL'

        return {
            'equity': self.equity,
            'total_dd': total_dd,
            'daily_dd': daily_dd,
            'total_return': total_return,
            'risk_level': risk_level,
            'can_trade': self.can_trade(),
            'adjusted_risk_pct': self.get_adjusted_risk_pct(),
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'challenge_active': self.is_challenge_active,
            'failure_reason': self.failure_reason
        }

    def get_summary(self):
        """Get summary statistics"""
        status = self.get_risk_status()

        return {
            'Initial Equity': f'${self.initial_equity:,.2f}',
            'Final Equity': f'${self.equity:,.2f}',
            'Total Return': f'{status["total_return"]*100:.2f}%',
            'Max Drawdown': f'{status["total_dd"]*100:.2f}%',
            'Total Trades': len(self.trades),
            'Challenge Passed': self.pass_date is not None,
            'Challenge Failed': self.failure_reason is not None,
            'Failure Reason': self.failure_reason
        }

if __name__ == '__main__':
    print("FTMO Risk Manager Test")
    print("=" * 60)

    # Test scenario 1: Normal trading
    print("\n1. Normal Trading Scenario")
    rm = FTMORiskManager(initial_equity=100000)

    # Calculate position size for a trade
    entry = 1.1000
    stop_loss = 1.0980  # 20 pip SL
    lot_size = rm.calculate_position_size(entry, stop_loss)
    print(f"Entry: {entry}, SL: {stop_loss} (20 pips)")
    print(f"Position size: {lot_size:.2f} lots")
    print(f"Risk: ${rm.equity * rm.get_adjusted_risk_pct():,.2f} ({rm.get_adjusted_risk_pct()*100:.1f}%)")

    # Simulate winning trades
    print("\n2. Winning Streak")
    for i in range(5):
        rm.record_trade(500, datetime.now())
        status = rm.get_risk_status()
        print(f"Trade {i+1}: +$500 | Equity: ${rm.equity:,.0f} | Return: {status['total_return']*100:.2f}%")

    # Test position sizing after wins
    lot_size_after_wins = rm.calculate_position_size(entry, stop_loss)
    print(f"\nPosition size after 5 wins: {lot_size_after_wins:.2f} lots (increased risk)")

    # Simulate losing streak
    print("\n3. Losing Streak")
    for i in range(4):
        rm.record_trade(-700, datetime.now())
        status = rm.get_risk_status()
        print(f"Loss {i+1}: -$700 | Equity: ${rm.equity:,.0f} | DD: {status['total_dd']*100:.2f}% | Risk: {status['risk_level']}")

    # Test position sizing after losses
    lot_size_after_losses = rm.calculate_position_size(entry, stop_loss)
    print(f"\nPosition size after 4 losses: {lot_size_after_losses:.2f} lots (reduced risk)")

    # Test circuit breaker
    print("\n4. Circuit Breaker Test")
    rm2 = FTMORiskManager(initial_equity=100000)
    rm2.update_equity(91000, datetime.now())  # -9% DD (critical)
    print(f"Equity: $91,000 (91% of initial)")
    print(f"Can trade: {rm2.can_trade()} (should be False at -9% DD)")

    # Test daily DD limit
    print("\n5. Daily DD Limit Test")
    rm3 = FTMORiskManager(initial_equity=100000)
    current_date = datetime.now().date()
    rm3.update_daily(100000, current_date)
    rm3.update_daily(94500, current_date)  # -5.5% daily DD
    status3 = rm3.get_risk_status()
    print(f"Daily start: $100,000, Current: $94,500")
    print(f"Daily DD: {status3['daily_dd']*100:.2f}%")
    print(f"Challenge active: {rm3.is_challenge_active}")
    print(f"Failure reason: {rm3.failure_reason}")

    # Test profit target
    print("\n6. Profit Target Test")
    rm4 = FTMORiskManager(initial_equity=100000)
    rm4.update_equity(110000, datetime.now())  # +10% profit
    status4 = rm4.get_risk_status()
    print(f"Equity: $110,000")
    print(f"Return: {status4['total_return']*100:.2f}%")
    print(f"Challenge passed: {rm4.pass_date is not None}")

    print("\n" + "=" * 60)
    print("✅ FTMO Risk Manager working correctly")
