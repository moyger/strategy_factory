#!/usr/bin/env python3
"""
Universal Strategy Runner

Run any strategy with simple commands:
    python run_strategy.py --strategy atr_trailing_stop
    python run_strategy.py --strategy ftmo_challenge --challenge-size 100k
    python run_strategy.py --strategy sma --fast 10 --slow 50
    python run_strategy.py --strategy rsi --period 14

Author: Strategy Factory
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

# Add project to path
sys.path.append(str(Path(__file__).parent))

from strategies.sma_crossover import SMAStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.breakout_strategy import BreakoutStrategy
from strategies.atr_trailing_stop_strategy import ATRTrailingStopStrategy
from strategies.ftmo_challenge_strategy import FTMOChallengeStrategy
from strategies.advanced_strategy_template import AdvancedStrategyTemplate


def load_data(data_file: str = 'data/crypto/BTCUSD_5m.csv') -> pd.DataFrame:
    """Load and prepare data"""
    print(f"📂 Loading data from {data_file}...")

    df = pd.read_csv(data_file)
    df.columns = df.columns.str.lower()

    if 'date' in df.columns:
        df = df.rename(columns={'date': 'timestamp'})

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')

    # Use recent data (last 50k bars for speed)
    df = df.tail(50000)

    print(f"✅ Loaded {len(df):,} bars")
    print(f"   Period: {df.index[0]} to {df.index[-1]}")

    return df


def run_sma_strategy(args):
    """Run SMA Crossover Strategy"""
    print("\n" + "="*80)
    print("SMA CROSSOVER STRATEGY")
    print("="*80)

    # Create strategy
    strategy = SMAStrategy(
        fast_period=args.fast,
        slow_period=args.slow
    )

    print(f"\n📊 Strategy: {strategy}")
    print(f"   Parameters: Fast={args.fast}, Slow={args.slow}")

    # Load data
    df = load_data(args.data)

    # Generate signals
    print(f"\n🔍 Generating signals...")
    df_signals = strategy.generate_signals(df)

    # Count signals
    buy_signals = (df_signals['signal'] == 'BUY').sum()
    sell_signals = (df_signals['signal'] == 'SELL').sum()

    print(f"   Buy signals: {buy_signals}")
    print(f"   Sell signals: {sell_signals}")

    # Run backtest
    import vectorbt as vbt

    print(f"\n📈 Running backtest...")

    entries = (df_signals['signal'] == 'BUY')
    exits = (df_signals['signal'] == 'SELL')

    portfolio = vbt.Portfolio.from_signals(
        close=df['close'].values,
        entries=entries,
        exits=exits,
        init_cash=10000,
        fees=0.001,
        slippage=0.0005
    )

    # Print results
    print_results(portfolio)


def run_rsi_strategy(args):
    """Run RSI Mean Reversion Strategy"""
    print("\n" + "="*80)
    print("RSI MEAN REVERSION STRATEGY")
    print("="*80)

    # Create strategy
    strategy = RSIStrategy(
        period=args.period,
        oversold=args.oversold,
        overbought=args.overbought
    )

    print(f"\n📊 Strategy: {strategy}")
    print(f"   Parameters: Period={args.period}, Oversold={args.oversold}, Overbought={args.overbought}")

    # Load data
    df = load_data(args.data)

    # Generate signals
    print(f"\n🔍 Generating signals...")
    df_signals = strategy.generate_signals(df)

    # Count signals
    buy_signals = (df_signals['signal'] == 'BUY').sum()
    sell_signals = (df_signals['signal'] == 'SELL').sum()

    print(f"   Buy signals: {buy_signals}")
    print(f"   Sell signals: {sell_signals}")

    # Run backtest
    import vectorbt as vbt

    print(f"\n📈 Running backtest...")

    entries = (df_signals['signal'] == 'BUY')
    exits = (df_signals['signal'] == 'SELL')

    portfolio = vbt.Portfolio.from_signals(
        close=df['close'].values,
        entries=entries,
        exits=exits,
        init_cash=10000,
        fees=0.001,
        slippage=0.0005
    )

    # Print results
    print_results(portfolio)


def run_breakout_strategy(args):
    """Run Breakout Strategy"""
    print("\n" + "="*80)
    print("BREAKOUT STRATEGY")
    print("="*80)

    # Create strategy
    strategy = BreakoutStrategy(
        lookback=args.lookback,
        breakout_pct=args.breakout_pct
    )

    print(f"\n📊 Strategy: {strategy}")
    print(f"   Parameters: Lookback={args.lookback}, Breakout%={args.breakout_pct}")

    # Load data
    df = load_data(args.data)

    # Generate signals
    print(f"\n🔍 Generating signals...")
    df_signals = strategy.generate_signals(df)

    # Count signals
    buy_signals = (df_signals['signal'] == 'BUY').sum()
    sell_signals = (df_signals['signal'] == 'SELL').sum()

    print(f"   Buy signals: {buy_signals}")
    print(f"   Sell signals: {sell_signals}")

    # Run backtest
    import vectorbt as vbt

    print(f"\n📈 Running backtest...")

    entries = (df_signals['signal'] == 'BUY')
    exits = (df_signals['signal'] == 'SELL')

    portfolio = vbt.Portfolio.from_signals(
        close=df['close'].values,
        entries=entries,
        exits=exits,
        init_cash=10000,
        fees=0.001,
        slippage=0.0005
    )

    # Print results
    print_results(portfolio)

    # Generate report if requested
    if args.report:
        from strategy_factory.analyzer import StrategyAnalyzer
        analyzer = StrategyAnalyzer()

        returns = portfolio.returns()
        report_path = analyzer.generate_full_report(
            returns,
            output_file=f'{strategy.name}_report.html',
            title=f'{strategy.name} Performance Report'
        )

        print(f"\n📊 Report generated: {report_path}")


def run_atr_trailing_stop_strategy(args):
    """Run ATR Trailing Stop Strategy"""
    print("\n" + "="*80)
    print("ATR TRAILING STOP STRATEGY")
    print("="*80)

    # Create strategy
    strategy = ATRTrailingStopStrategy(
        atr_period=args.atr_period,
        atr_sl_multiplier=args.atr_sl,
        atr_tp_multiplier=args.atr_tp,
        risk_percent=args.risk_percent
    )

    print(f"\n📊 Strategy: {strategy}")

    # Load data
    df = load_data(args.data)

    # Run backtest
    print(f"\n📈 Running backtest...")
    portfolio = strategy.backtest(df, initial_capital=args.capital)

    # Print results
    strategy.print_results(portfolio)

    # Generate report if requested
    if args.report:
        from strategy_factory.analyzer import StrategyAnalyzer
        analyzer = StrategyAnalyzer()

        returns = portfolio.returns()
        report_path = analyzer.generate_full_report(
            returns,
            output_file=f'{strategy.name}_report.html',
            title=f'{strategy.name} Performance Report'
        )

        print(f"\n📊 Report generated: {report_path}")


def run_ftmo_challenge_strategy(args):
    """Run FTMO Challenge Strategy"""
    print("\n" + "="*80)
    print(f"FTMO {args.challenge_size.upper()} CHALLENGE STRATEGY")
    print("="*80)

    # Create strategy
    strategy = FTMOChallengeStrategy(
        challenge_size=args.challenge_size,
        risk_per_trade=args.risk_percent,
        atr_period=args.atr_period,
        atr_sl_multiplier=args.atr_sl,
        atr_tp_multiplier=args.atr_tp,
        session_filter=not args.no_session_filter,
        require_trend=not args.no_trend_filter
    )

    print(f"\n📊 Strategy: {strategy}")
    print(f"   Challenge: ${strategy.specs['balance']:,} account")

    # Load data
    df = load_data(args.data)

    # Run backtest
    print(f"\n📈 Running backtest...")
    results = strategy.backtest(df)

    # Print results
    strategy.print_results(results)

    # Generate report if requested
    if args.report:
        from strategy_factory.analyzer import StrategyAnalyzer
        analyzer = StrategyAnalyzer()

        portfolio = results['portfolio']
        returns = portfolio.returns()
        report_path = analyzer.generate_full_report(
            returns,
            output_file=f'{strategy.name}_report.html',
            title=f'{strategy.name} Performance Report'
        )

        print(f"\n📊 Report generated: {report_path}")


def run_advanced_strategy(args):
    """Run Advanced Strategy Template"""
    print("\n" + "="*80)
    print("ADVANCED STRATEGY TEMPLATE")
    print("="*80)

    # Create strategy
    strategy = AdvancedStrategyTemplate(
        sizing_method=args.sizing_method,
        risk_per_trade=args.risk_percent,
        kelly_fraction=args.kelly_fraction,
        atr_period=args.atr_period,
        atr_sl_multiplier=args.atr_sl,
        atr_tp_multiplier=args.atr_tp,
        session_filter=not args.no_session_filter,
        require_high_volatility=args.require_high_volatility,
        check_ftmo_rules=args.check_ftmo,
        ftmo_challenge_size=args.challenge_size if args.check_ftmo else '50k'
    )

    print(f"\n📊 Strategy: {strategy}")

    # Load data
    df = load_data(args.data)

    # Run backtest
    print(f"\n📈 Running backtest...")
    results = strategy.backtest(df, initial_capital=args.capital)

    # Print results
    strategy.print_results(results)

    # Generate report if requested
    if args.report:
        from strategy_factory.analyzer import StrategyAnalyzer
        analyzer = StrategyAnalyzer()

        portfolio = results['portfolio']
        returns = portfolio.returns()
        report_path = analyzer.generate_full_report(
            returns,
            output_file=f'{strategy.name}_report.html',
            title=f'{strategy.name} Performance Report'
        )

        print(f"\n📊 Report generated: {report_path}")


def print_results(portfolio):
    """Print basic backtest results"""
    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)

    print(f"\n📈 Performance:")
    print(f"   Total Return: {portfolio.total_return() * 100:.2f}%")
    print(f"   Final Equity: ${portfolio.value().iloc[-1]:,.2f}")
    print(f"   Sharpe Ratio: {portfolio.sharpe_ratio(freq='5min'):.2f}")
    print(f"   Max Drawdown: {portfolio.max_drawdown() * 100:.2f}%")

    print(f"\n💼 Trades:")
    print(f"   Number of Trades: {portfolio.trades.count()}")

    if portfolio.trades.count() > 0:
        print(f"   Win Rate: {portfolio.trades.win_rate() * 100:.1f}%")
        print(f"   Avg Win: ${portfolio.trades.winning.pnl.mean():.2f}")
        print(f"   Avg Loss: ${portfolio.trades.losing.pnl.mean():.2f}")
        print(f"   Profit Factor: {portfolio.trades.profit_factor():.2f}")

    print("\n" + "="*80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Universal Strategy Runner - Run any trading strategy with simple commands',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Simple strategies
  python run_strategy.py --strategy sma --fast 10 --slow 50
  python run_strategy.py --strategy rsi --period 14 --oversold 30 --overbought 70
  python run_strategy.py --strategy breakout --lookback 20 --breakout-pct 2.0

  # Advanced strategies
  python run_strategy.py --strategy atr_trailing_stop --atr-period 14 --atr-sl 2.0 --atr-tp 4.0
  python run_strategy.py --strategy ftmo_challenge --challenge-size 50k --risk-percent 1.0
  python run_strategy.py --strategy advanced --sizing-method kelly --check-ftmo

  # With reports
  python run_strategy.py --strategy atr_trailing_stop --report
  python run_strategy.py --strategy ftmo_challenge --challenge-size 100k --report
        """
    )

    # Main arguments
    parser.add_argument('--strategy', required=True,
                       choices=['sma', 'rsi', 'breakout', 'atr_trailing_stop', 'ftmo_challenge', 'advanced'],
                       help='Strategy to run')
    parser.add_argument('--data', default='data/crypto/BTCUSD_5m.csv',
                       help='Data file to use (default: BTCUSD 5-min)')
    parser.add_argument('--capital', type=float, default=10000,
                       help='Initial capital (default: 10000)')
    parser.add_argument('--report', action='store_true',
                       help='Generate QuantStats HTML report')

    # SMA parameters
    parser.add_argument('--fast', type=int, default=10,
                       help='Fast SMA period (default: 10)')
    parser.add_argument('--slow', type=int, default=50,
                       help='Slow SMA period (default: 50)')

    # RSI parameters
    parser.add_argument('--period', type=int, default=14,
                       help='RSI period (default: 14)')
    parser.add_argument('--oversold', type=int, default=30,
                       help='RSI oversold level (default: 30)')
    parser.add_argument('--overbought', type=int, default=70,
                       help='RSI overbought level (default: 70)')

    # Breakout parameters
    parser.add_argument('--lookback', type=int, default=20,
                       help='Breakout lookback period (default: 20)')
    parser.add_argument('--breakout-pct', type=float, default=2.0,
                       help='Breakout percentage (default: 2.0)')

    # ATR parameters (used by multiple strategies)
    parser.add_argument('--atr-period', type=int, default=14,
                       help='ATR period (default: 14)')
    parser.add_argument('--atr-sl', type=float, default=2.0,
                       help='ATR stop loss multiplier (default: 2.0)')
    parser.add_argument('--atr-tp', type=float, default=4.0,
                       help='ATR take profit multiplier (default: 4.0)')

    # Risk management parameters
    parser.add_argument('--risk-percent', type=float, default=1.0,
                       help='Risk per trade as percentage (default: 1.0)')
    parser.add_argument('--sizing-method', choices=['fixed_percent', 'kelly', 'volatility'],
                       default='fixed_percent',
                       help='Position sizing method (default: fixed_percent)')
    parser.add_argument('--kelly-fraction', type=float, default=0.5,
                       help='Kelly fraction (default: 0.5)')

    # FTMO parameters
    parser.add_argument('--challenge-size', choices=['10k', '25k', '50k', '100k', '200k'],
                       default='50k',
                       help='FTMO challenge size (default: 50k)')
    parser.add_argument('--check-ftmo', action='store_true',
                       help='Check FTMO compliance rules')

    # Filters
    parser.add_argument('--no-session-filter', action='store_true',
                       help='Disable session filtering')
    parser.add_argument('--no-trend-filter', action='store_true',
                       help='Disable trend filtering')
    parser.add_argument('--require-high-volatility', action='store_true',
                       help='Require high volatility for trading')

    args = parser.parse_args()

    # Route to appropriate strategy
    if args.strategy == 'sma':
        run_sma_strategy(args)
    elif args.strategy == 'rsi':
        run_rsi_strategy(args)
    elif args.strategy == 'breakout':
        run_breakout_strategy(args)
    elif args.strategy == 'atr_trailing_stop':
        run_atr_trailing_stop_strategy(args)
    elif args.strategy == 'ftmo_challenge':
        run_ftmo_challenge_strategy(args)
    elif args.strategy == 'advanced':
        run_advanced_strategy(args)


if __name__ == "__main__":
    main()
