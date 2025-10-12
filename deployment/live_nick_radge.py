#!/usr/bin/env python3
"""
Live Trading - Nick Radge Momentum Strategy

This script runs the Nick Radge momentum strategy live with:
- Daily data updates
- Quarterly rebalancing
- Regime recovery (re-enter on BEAR -> BULL)
- Position sizing with momentum weighting
- Multi-broker support (IBKR, Bybit, MT5)

Author: Strategy Factory
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Optional
import logging

# Import broker infrastructure
from deployment.broker_interface import Order, OrderSide, OrderType
from deployment.strategy_deployer import StrategyDeployer

# Import allocation calculation (we'll create standalone version)
# from strategies.nick_radge_momentum_strategy import NickRadgeMomentumStrategy
import numpy as np


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/live_nick_radge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LiveNickRadgeTrader:
    """
    Live trader for Nick Radge Momentum Strategy

    Features:
    - Downloads fresh daily stock data
    - Calculates momentum rankings
    - Rebalances quarterly (or on regime recovery)
    - Executes orders through broker
    - Risk management and position sizing
    """

    def __init__(self,
                 broker_name: str = 'ibkr',
                 config_path: str = 'deployment/config_live.json'):
        """
        Initialize live trader

        Args:
            broker_name: Broker to use ('ibkr', 'bybit', 'mt5')
            config_path: Path to live trading config

        Note:
            Capital is automatically retrieved from broker - no need to specify!
        """
        self.broker_name = broker_name
        self.config_path = config_path

        # Load config
        self.config = self._load_config()

        # Initialize broker connection
        self.deployer = StrategyDeployer('deployment/config.json')
        self.broker = None

        # Strategy parameters
        self.portfolio_size = self.config.get('portfolio_size', 7)
        self.roc_period = self.config.get('roc_period', 100)
        self.ma_period = self.config.get('ma_period', 100)
        self.strong_bull_positions = self.config.get('strong_bull_positions', 7)
        self.weak_bull_positions = self.config.get('weak_bull_positions', 3)
        self.bear_positions = 0
        self.bear_market_asset = self.config.get('bear_market_asset', None)  # e.g., 'SQQQ'
        self.bear_allocation = self.config.get('bear_allocation', 1.0)  # 100% by default
        self.regime_ma_long = 200  # For regime detection
        self.regime_ma_short = 50

        # State tracking
        self.last_rebalance_date = None
        self.last_regime = None
        self.current_positions = {}

    def _load_config(self) -> Dict:
        """Load live trading configuration"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            logger.info(f"Config not found, creating template: {self.config_path}")
            self._create_template_config()

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def _create_template_config(self) -> None:
        """Create template configuration"""
        template = {
            "strategy_name": "Nick Radge Momentum",
            "portfolio_size": 7,
            "roc_period": 100,
            "ma_period": 100,
            "strong_bull_positions": 7,
            "weak_bull_positions": 3,
            "bear_positions": 0,
            "bear_market_asset": None,  # Set to 'SQQQ', 'SPXU', or 'SH' to trade during BEAR
            "bear_allocation": 1.0,  # 1.0 = 100% allocation to bear asset
            "stock_universe": [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO",
                "ORCL", "ADBE", "CRM", "AMD", "INTC", "CSCO", "QCOM", "INTU",
                "NOW", "AMAT", "MU", "PLTR", "JPM", "BAC", "WFC", "GS", "MS",
                "BLK", "C", "SCHW", "AXP", "SPGI", "UNH", "JNJ", "LLY", "ABBV",
                "MRK", "TMO", "ABT", "PFE", "DHR", "AMGN", "WMT", "HD", "MCD",
                "NKE", "COST", "SBUX", "TGT", "LOW", "DIS", "CMCSA"
            ],
            "lookback_days": 200,  # For indicator calculation
            "max_position_size": 0.2,  # Max 20% per position
            "rebalance_time": "09:35",  # After market open
            "check_interval_minutes": 60,  # Check every hour
            "dry_run": True  # Set to False for real trading
        }

        Path(self.config_path).parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(template, f, indent=2)

        logger.info(f"✅ Template config created: {self.config_path}")

    def connect(self) -> bool:
        """Connect to broker"""
        logger.info(f"Connecting to {self.broker_name}...")

        self.deployer.connect_all()

        if not self.deployer.is_connected(self.broker_name):
            logger.error(f"Failed to connect to {self.broker_name}")
            return False

        self.broker = self.deployer.get_broker(self.broker_name)
        logger.info(f"✅ Connected to {self.broker_name}")

        return True

    def disconnect(self) -> None:
        """Disconnect from broker"""
        logger.info("Disconnecting...")
        self.deployer.disconnect_all()

    def download_market_data(self) -> tuple:
        """
        Download fresh market data for stock universe and SPY

        Returns:
            (prices DataFrame, spy_prices Series)
        """
        logger.info("📥 Downloading market data...")

        tickers = self.config['stock_universe'].copy()

        # Add bear market asset to universe if specified
        if self.bear_market_asset:
            if self.bear_market_asset not in tickers:
                tickers.append(self.bear_market_asset)
                logger.info(f"   Adding bear market asset: {self.bear_market_asset}")

        lookback_days = self.config.get('lookback_days', 200)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

        # Download stock data
        logger.info(f"   Downloading {len(tickers)} stocks...")
        data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)

        # Extract close prices
        if len(tickers) == 1:
            prices = data['Close'].to_frame()
            prices.columns = tickers
        else:
            prices = data['Close']

        # Remove stocks with insufficient data
        prices = prices.dropna(axis=1, thresh=len(prices) * 0.8)

        logger.info(f"   ✅ Downloaded {len(prices.columns)} stocks")

        # Download SPY for regime filter
        logger.info(f"   Downloading SPY (benchmark)...")
        spy_data = yf.download('SPY', start=start_date - timedelta(days=100), end=end_date,
                              auto_adjust=True, progress=False)
        spy_prices = spy_data['Close']

        logger.info(f"✅ Market data ready: {len(prices)} days")

        return prices, spy_prices

    def calculate_regime(self, spy_prices: pd.Series) -> str:
        """Calculate current market regime"""
        ma_long = spy_prices.rolling(window=self.regime_ma_long).mean()
        ma_short = spy_prices.rolling(window=self.regime_ma_short).mean()

        current_price = spy_prices.iloc[-1]
        current_ma_long = ma_long.iloc[-1]
        current_ma_short = ma_short.iloc[-1]

        if pd.isna(current_ma_long) or pd.isna(current_ma_short):
            return 'UNKNOWN'

        if current_price > current_ma_long:
            return 'STRONG_BULL'
        elif current_price > current_ma_short:
            return 'WEAK_BULL'
        else:
            return 'BEAR'

    def rank_stocks_by_momentum(self, prices: pd.DataFrame, spy_prices: pd.Series) -> pd.DataFrame:
        """
        Rank stocks by momentum (ROC)

        Returns:
            DataFrame with columns: ticker, roc, above_ma
        """
        # Calculate ROC for each stock
        roc = prices.pct_change(self.roc_period) * 100
        latest_roc = roc.iloc[-1]

        # Calculate MA for each stock
        ma = prices.rolling(window=self.ma_period).mean()
        latest_ma = ma.iloc[-1]
        latest_prices = prices.iloc[-1]

        # Calculate SPY ROC for relative strength
        spy_roc = spy_prices.pct_change(self.roc_period).iloc[-1] * 100

        # Build rankings
        rankings = []
        for ticker in prices.columns:
            # Skip bear market asset - it's not ranked with stocks
            if self.bear_market_asset and ticker == self.bear_market_asset:
                continue

            ticker_roc = latest_roc[ticker]
            ticker_ma = latest_ma[ticker]
            ticker_price = latest_prices[ticker]

            # Skip if NaN or not above MA
            if pd.isna(ticker_roc) or pd.isna(ticker_ma):
                continue

            if ticker_price <= ticker_ma:
                continue

            # Relative strength filter: only stocks outperforming SPY
            if ticker_roc <= spy_roc:
                continue

            rankings.append({
                'ticker': ticker,
                'roc': ticker_roc,
                'price': ticker_price,
                'ma': ticker_ma
            })

        # Sort by ROC descending
        rankings_df = pd.DataFrame(rankings)
        if len(rankings_df) > 0:
            rankings_df = rankings_df.sort_values('roc', ascending=False)

        return rankings_df

    def calculate_target_allocations(self, prices: pd.DataFrame, spy_prices: pd.Series) -> Dict[str, float]:
        """
        Calculate target portfolio allocations using strategy

        Args:
            prices: Stock prices DataFrame
            spy_prices: SPY prices Series

        Returns:
            Dictionary of {ticker: allocation_pct}
        """
        logger.info("📊 Calculating target allocations...")

        # Determine regime
        current_regime = self.calculate_regime(spy_prices)
        logger.info(f"   Current regime: {current_regime}")

        # Determine portfolio size based on regime
        if current_regime == 'STRONG_BULL':
            portfolio_size = self.strong_bull_positions
        elif current_regime == 'WEAK_BULL':
            portfolio_size = self.weak_bull_positions
        else:  # BEAR or UNKNOWN
            portfolio_size = self.bear_positions

        logger.info(f"   Portfolio size: {portfolio_size} positions")

        # If bear market, check for bear market asset or go to cash
        if portfolio_size == 0:
            if self.bear_market_asset:
                logger.info(f"   🐻 Bear market detected - allocating to {self.bear_market_asset}")
                return {self.bear_market_asset: self.bear_allocation}
            else:
                logger.info("   🐻 Bear market detected - going to cash")
                return {}

        # Rank stocks by momentum
        ranked = self.rank_stocks_by_momentum(prices, spy_prices)

        if len(ranked) == 0:
            logger.warning("   ⚠️  No stocks passed filters")
            return {}

        # Select top N stocks
        top_stocks = ranked.head(portfolio_size)

        logger.info(f"   Ranked {len(ranked)} stocks, selected top {len(top_stocks)}")

        # Calculate momentum-weighted allocations
        positive_roc = top_stocks['roc'].clip(lower=0)
        total_roc = positive_roc.sum()

        target_positions = {}

        if total_roc > 0:
            # Momentum weighting
            for idx, row in top_stocks.iterrows():
                ticker = row['ticker']
                weight = row['roc'] / total_roc
                target_positions[ticker] = weight
        else:
            # Equal weight fallback
            equal_weight = 1.0 / len(top_stocks)
            for idx, row in top_stocks.iterrows():
                target_positions[row['ticker']] = equal_weight

        logger.info(f"   Target positions: {len(target_positions)}")
        for ticker, weight in sorted(target_positions.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"      {ticker}: {weight*100:.2f}%")

        return target_positions

    def get_current_positions(self) -> Dict[str, float]:
        """
        Get current positions from broker

        Returns:
            Dictionary of {ticker: quantity}
        """
        positions = self.broker.get_positions()
        return {symbol: pos.quantity for symbol, pos in positions.items()}

    def calculate_rebalance_orders(self, target_allocations: Dict[str, float]) -> List[Order]:
        """
        Calculate orders needed to rebalance to target allocations

        Args:
            target_allocations: Target allocation weights

        Returns:
            List of Order objects
        """
        logger.info("🔄 Calculating rebalance orders...")

        # Get account balance
        balance = self.broker.get_balance()
        logger.info(f"   Account balance: ${balance:,.2f}")

        # Get current positions
        current_positions = self.get_current_positions()
        logger.info(f"   Current positions: {len(current_positions)}")

        # Calculate target quantities
        orders = []

        # First, close positions not in target
        for ticker in current_positions:
            if ticker not in target_allocations:
                # Close this position
                current_qty = current_positions[ticker]
                if current_qty > 0:
                    orders.append(Order(
                        symbol=ticker,
                        side=OrderSide.SELL,
                        quantity=abs(current_qty),
                        order_type=OrderType.MARKET
                    ))
                    logger.info(f"   📉 CLOSE {ticker}: {current_qty} shares")

        # Then, adjust positions to target allocations
        for ticker, target_weight in target_allocations.items():
            # Get current price
            try:
                current_price = self.broker.get_current_price(ticker)
            except:
                logger.warning(f"   ⚠️  Could not get price for {ticker}, skipping")
                continue

            # Calculate target dollar amount
            target_value = balance * target_weight

            # Calculate target quantity
            target_qty = int(target_value / current_price)

            # Get current quantity
            current_qty = current_positions.get(ticker, 0)

            # Calculate difference
            qty_diff = target_qty - current_qty

            # Apply max position size limit
            max_position_value = balance * self.config.get('max_position_size', 0.2)
            max_qty = int(max_position_value / current_price)

            if target_qty > max_qty:
                logger.info(f"   ⚠️  {ticker}: Target {target_qty} exceeds max {max_qty}, capping")
                target_qty = max_qty
                qty_diff = target_qty - current_qty

            # Create order if significant change
            if abs(qty_diff) > 0:
                side = OrderSide.BUY if qty_diff > 0 else OrderSide.SELL

                orders.append(Order(
                    symbol=ticker,
                    side=side,
                    quantity=abs(qty_diff),
                    order_type=OrderType.MARKET
                ))

                logger.info(f"   {'📈 BUY' if qty_diff > 0 else '📉 SELL'} {ticker}: "
                          f"{abs(qty_diff)} shares (${abs(qty_diff * current_price):,.2f})")

        logger.info(f"   Total orders: {len(orders)}")
        return orders

    def execute_orders(self, orders: List[Order]) -> None:
        """
        Execute rebalance orders

        Args:
            orders: List of orders to execute
        """
        if len(orders) == 0:
            logger.info("   No orders to execute")
            return

        logger.info(f"📤 Executing {len(orders)} orders...")

        if self.config.get('dry_run', True):
            logger.info("   ⚠️  DRY RUN MODE - Orders not sent to broker")
            for order in orders:
                logger.info(f"   [DRY RUN] {order}")
            return

        # Execute orders
        for order in orders:
            try:
                order_id = self.broker.place_order(order)
                logger.info(f"   ✅ {order} - Order ID: {order_id}")
                time.sleep(1)  # Rate limiting
            except Exception as e:
                logger.error(f"   ❌ Failed to place order {order}: {e}")

    def should_rebalance(self, current_regime: str) -> tuple:
        """
        Check if we should rebalance

        Returns:
            (should_rebalance: bool, reason: str)
        """
        today = pd.Timestamp(datetime.now().date())

        # Check if it's a quarterly rebalance date
        is_quarter_start = today.month in [1, 4, 7, 10] and today.day <= 5

        # Check for regime recovery (BEAR -> BULL)
        is_regime_recovery = (self.last_regime == 'BEAR' and
                             current_regime in ['STRONG_BULL', 'WEAK_BULL'])

        if is_quarter_start:
            return True, "Quarterly rebalance"
        elif is_regime_recovery:
            return True, "Regime recovery (BEAR -> BULL)"
        else:
            return False, "No rebalance needed"

    def run_daily_check(self) -> None:
        """Run daily check and rebalancing logic"""
        logger.info("="*60)
        logger.info(f"DAILY CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)

        try:
            # Download market data
            prices, spy_prices = self.download_market_data()

            # Calculate current regime
            current_regime = self.calculate_regime(spy_prices)
            logger.info(f"📊 Current Market Regime: {current_regime}")

            # Check if we should rebalance
            should_rebalance, reason = self.should_rebalance(current_regime)

            if should_rebalance:
                logger.info(f"🔄 Rebalancing: {reason}")

                # Calculate target allocations
                target_allocations = self.calculate_target_allocations(prices, spy_prices)

                # Calculate orders
                orders = self.calculate_rebalance_orders(target_allocations)

                # Execute orders
                self.execute_orders(orders)

                # Update state
                self.last_rebalance_date = datetime.now()

            else:
                logger.info(f"✅ No rebalance needed: {reason}")

            # Update regime tracking
            self.last_regime = current_regime

            # Print account summary
            self.deployer.print_account_summary()

        except Exception as e:
            logger.error(f"❌ Error during daily check: {e}", exc_info=True)

    def run_live(self) -> None:
        """
        Run live trading loop

        Checks market conditions every hour during trading hours
        """
        logger.info("="*60)
        logger.info("NICK RADGE MOMENTUM STRATEGY - LIVE TRADING")
        logger.info("="*60)

        if not self.connect():
            logger.error("Failed to connect to broker. Exiting.")
            return

        # Get current account balance
        try:
            balance = self.broker.get_balance()
            logger.info(f"\n💰 Account Balance: ${balance:,.2f}")
        except:
            logger.warning(f"   Could not retrieve balance")
            balance = 0

        logger.info(f"\n⚙️  Configuration:")
        logger.info(f"   Broker: {self.broker_name}")
        logger.info(f"   Portfolio Size: {self.config['portfolio_size']} positions")
        logger.info(f"   Stock Universe: {len(self.config['stock_universe'])} stocks")
        logger.info(f"   Dry Run: {self.config.get('dry_run', True)}")
        logger.info(f"\n   NOTE: Capital is automatically retrieved from broker balance")
        logger.info(f"         Current balance will be used for position sizing")

        try:
            while True:
                # Check if market hours (9:30 AM - 4:00 PM ET)
                now = datetime.now()
                current_time = now.time()

                # Market hours check (simplified - adjust for your timezone)
                if current_time.hour >= 9 and current_time.hour < 16:
                    self.run_daily_check()

                    # Sleep for check interval
                    sleep_minutes = self.config.get('check_interval_minutes', 60)
                    logger.info(f"\n💤 Next check in {sleep_minutes} minutes...")
                    time.sleep(sleep_minutes * 60)
                else:
                    logger.info("Outside market hours, sleeping until 9:30 AM...")
                    time.sleep(60 * 30)  # Check every 30 minutes

        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            self.disconnect()
            logger.info("✅ Live trading stopped")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Nick Radge Momentum Strategy - Live Trading')
    parser.add_argument('--broker', type=str, default='ibkr',
                       help='Broker to use (ibkr, bybit, mt5)')
    parser.add_argument('--config', type=str, default='deployment/config_live.json',
                       help='Path to live trading config')
    parser.add_argument('--check-once', action='store_true',
                       help='Run one check and exit (for testing)')

    args = parser.parse_args()

    # Create logs directory
    Path('logs').mkdir(exist_ok=True)

    # Initialize trader (capital is auto-detected from broker)
    trader = LiveNickRadgeTrader(
        broker_name=args.broker,
        config_path=args.config
    )

    if args.check_once:
        # Single check mode (for testing)
        logger.info("Running single check...")
        if trader.connect():
            trader.run_daily_check()
            trader.disconnect()
    else:
        # Continuous live trading
        trader.run_live()


if __name__ == "__main__":
    main()
