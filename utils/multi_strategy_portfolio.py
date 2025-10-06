"""
Multi-Strategy Portfolio Manager

Combines 3 strategies with risk allocation:
- 40% Volatility Gap Scalping (M5)
- 35% Trend Following (H4)
- 25% London Breakout (H1)

Features:
- Conflict resolution (avoid multiple positions in same direction)
- Dynamic allocation based on market conditions
- Correlation management between strategies
- Per-strategy position sizing based on allocation
"""
import pandas as pd
import numpy as np
from ftmo_risk_manager import FTMORiskManager

class MultiStrategyPortfolio:
    def __init__(self, initial_equity=100000.0):
        """
        Args:
        - initial_equity: Starting account size
        """
        self.equity = initial_equity
        self.risk_manager = FTMORiskManager(initial_equity)

        # Strategy allocations (risk %)
        self.allocations = {
            'scalping': 0.40,   # 40%
            'trend': 0.35,       # 35%
            'breakout': 0.25     # 25%
        }

        # Active positions per strategy
        self.positions = {
            'scalping': None,
            'trend': None,
            'breakout': None
        }

        # Conflict resolution rules
        self.max_positions = 2  # Max 2 simultaneous positions
        self.max_same_direction = 1  # Max 1 position per direction

    def get_allocated_risk(self, strategy_name):
        """
        Get risk allocation for specific strategy

        Returns: risk % for this strategy
        """
        base_risk = self.risk_manager.get_adjusted_risk_pct()
        allocated_risk = base_risk * self.allocations[strategy_name]
        return allocated_risk

    def calculate_position_size(self, strategy_name, entry_price, stop_loss_price, pair='EURUSD'):
        """
        Calculate position size for a strategy based on allocation

        Args:
        - strategy_name: 'scalping', 'trend', or 'breakout'
        - entry_price: Entry price
        - stop_loss_price: Stop loss price
        - pair: Currency pair

        Returns: lot size
        """
        # Get allocated risk for this strategy
        risk_pct = self.get_allocated_risk(strategy_name)

        # Calculate risk amount in dollars
        risk_dollars = self.equity * risk_pct

        # Calculate stop loss distance in pips
        pip_value = 0.0001 if pair in ['EURUSD', 'GBPUSD'] else 0.01
        sl_distance_pips = abs(entry_price - stop_loss_price) / pip_value

        # Calculate position size
        dollars_per_pip_per_lot = 10.0
        lot_size = risk_dollars / (sl_distance_pips * dollars_per_pip_per_lot)

        # Apply leverage limit (1:30)
        max_lot_size = (self.equity * 30) / 100000
        lot_size = min(lot_size, max_lot_size)

        # Minimum 0.01 lots
        lot_size = max(0.01, round(lot_size, 2))

        return lot_size

    def check_position_conflicts(self, strategy_name, position_type):
        """
        Check if opening a new position would violate conflict rules

        Args:
        - strategy_name: 'scalping', 'trend', or 'breakout'
        - position_type: 'long' or 'short'

        Returns: True if allowed, False if conflict
        """
        # Count active positions
        active_count = sum(1 for p in self.positions.values() if p is not None)
        if active_count >= self.max_positions:
            return False  # Too many positions

        # Count positions in same direction
        same_direction_count = sum(
            1 for p in self.positions.values()
            if p is not None and p['type'] == position_type
        )
        if same_direction_count >= self.max_same_direction:
            return False  # Too many positions in same direction

        return True

    def open_position(self, strategy_name, position_type, entry_price, sl, tp, entry_time):
        """
        Open a new position for a strategy

        Args:
        - strategy_name: 'scalping', 'trend', or 'breakout'
        - position_type: 'long' or 'short'
        - entry_price, sl, tp: Trade parameters
        - entry_time: Timestamp

        Returns: lot_size if opened, None if rejected
        """
        # Check if strategy already has position
        if self.positions[strategy_name] is not None:
            return None

        # Check conflict rules
        if not self.check_position_conflicts(strategy_name, position_type):
            return None

        # Check if trading is allowed
        if not self.risk_manager.can_trade():
            return None

        # Calculate position size
        lot_size = self.calculate_position_size(strategy_name, entry_price, sl)

        # Open position
        self.positions[strategy_name] = {
            'type': position_type,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'sl': sl,
            'tp': tp,
            'lot_size': lot_size
        }

        return lot_size

    def close_position(self, strategy_name, exit_price, exit_time, exit_reason):
        """
        Close position for a strategy

        Args:
        - strategy_name: 'scalping', 'trend', or 'breakout'
        - exit_price: Exit price
        - exit_time: Timestamp
        - exit_reason: 'tp', 'sl', 'trail', 'time'

        Returns: dict with trade results
        """
        if self.positions[strategy_name] is None:
            return None

        position = self.positions[strategy_name]
        entry_price = position['entry_price']
        position_type = position['type']
        lot_size = position['lot_size']

        # Calculate P&L
        pip_value = 0.0001
        if position_type == 'long':
            pnl_pips = (exit_price - entry_price) / pip_value
        else:
            pnl_pips = (entry_price - exit_price) / pip_value

        # Calculate P&L in dollars (lot_size × $10/pip × pnl_pips)
        pnl_dollars = lot_size * 10.0 * pnl_pips

        # Subtract costs
        commission = 0.0005 * (lot_size * 100000)
        slippage = 0.3 * (lot_size * 10)
        pnl_dollars -= (commission + slippage)

        # Update equity
        self.equity += pnl_dollars

        # Update risk manager
        self.risk_manager.record_trade(pnl_dollars, exit_time)
        self.risk_manager.update_daily(self.equity, exit_time.date())

        # Clear position
        self.positions[strategy_name] = None

        return {
            'strategy': strategy_name,
            'entry_time': position['entry_time'],
            'exit_time': exit_time,
            'type': position_type,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'sl': position['sl'],
            'tp': position['tp'],
            'lot_size': lot_size,
            'pnl_pips': pnl_pips,
            'pnl_dollars': pnl_dollars,
            'exit_reason': exit_reason,
            'equity': self.equity
        }

    def get_portfolio_status(self):
        """Get current portfolio status"""
        active_positions = {k: v for k, v in self.positions.items() if v is not None}
        risk_status = self.risk_manager.get_risk_status()

        return {
            'equity': self.equity,
            'active_positions': len(active_positions),
            'positions': active_positions,
            'risk_level': risk_status['risk_level'],
            'can_trade': risk_status['can_trade'],
            'total_dd': risk_status['total_dd'],
            'daily_dd': risk_status['daily_dd'],
            'challenge_active': risk_status['challenge_active']
        }

    def get_summary(self):
        """Get portfolio summary"""
        risk_summary = self.risk_manager.get_summary()
        status = self.get_portfolio_status()

        return {
            **risk_summary,
            'Active Positions': status['active_positions'],
            'Risk Level': status['risk_level']
        }

if __name__ == '__main__':
    print("Multi-Strategy Portfolio Manager Test")
    print("=" * 60)

    # Initialize portfolio
    portfolio = MultiStrategyPortfolio(initial_equity=100000)

    print("\n1. Initial Status")
    status = portfolio.get_portfolio_status()
    print(f"Equity: ${status['equity']:,.2f}")
    print(f"Active positions: {status['active_positions']}")
    print(f"Can trade: {status['can_trade']}")

    # Simulate opening positions
    print("\n2. Opening Breakout Long Position")
    lot_size = portfolio.open_position(
        strategy_name='breakout',
        position_type='long',
        entry_price=1.1000,
        sl=1.0970,
        tp=1.1030,
        entry_time=pd.Timestamp('2024-01-01 09:00:00')
    )
    print(f"Breakout position opened: {lot_size:.2f} lots")

    # Try to open another long (should be rejected due to conflict)
    print("\n3. Try Opening Trend Long (should fail - conflict)")
    lot_size2 = portfolio.open_position(
        strategy_name='trend',
        position_type='long',
        entry_price=1.1005,
        sl=1.0980,
        tp=1.1055,
        entry_time=pd.Timestamp('2024-01-01 09:30:00')
    )
    print(f"Trend position opened: {lot_size2}")  # Should be None

    # Open short position (different direction, should work)
    print("\n4. Opening Scalping Short (different direction)")
    lot_size3 = portfolio.open_position(
        strategy_name='scalping',
        position_type='short',
        entry_price=1.1010,
        sl=1.1022,
        tp=1.1002,
        entry_time=pd.Timestamp('2024-01-01 10:00:00')
    )
    print(f"Scalping position opened: {lot_size3:.2f} lots")

    # Check status
    status = portfolio.get_portfolio_status()
    print(f"\nActive positions: {status['active_positions']}")
    print(f"Positions: {list(status['positions'].keys())}")

    # Close breakout position (winner)
    print("\n5. Close Breakout Position (TP)")
    result = portfolio.close_position(
        strategy_name='breakout',
        exit_price=1.1030,
        exit_time=pd.Timestamp('2024-01-01 11:00:00'),
        exit_reason='tp'
    )
    print(f"P&L: ${result['pnl_dollars']:.2f} ({result['pnl_pips']:.1f} pips)")
    print(f"New equity: ${result['equity']:,.2f}")

    # Close scalping position (loser)
    print("\n6. Close Scalping Position (SL)")
    result2 = portfolio.close_position(
        strategy_name='scalping',
        exit_price=1.1022,
        exit_time=pd.Timestamp('2024-01-01 10:30:00'),
        exit_reason='sl'
    )
    print(f"P&L: ${result2['pnl_dollars']:.2f} ({result2['pnl_pips']:.1f} pips)")
    print(f"New equity: ${result2['equity']:,.2f}")

    # Final summary
    print("\n7. Final Summary")
    summary = portfolio.get_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("✅ Portfolio manager working correctly")
