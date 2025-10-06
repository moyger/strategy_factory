"""
Professional Backtest Reporting with Quantstats

Generates comprehensive tearsheet reports for strategy performance analysis.
"""
import pandas as pd
import numpy as np
import quantstats as qs
import matplotlib.pyplot as plt
from pathlib import Path

# Extend pandas functionality for quantstats
qs.extend_pandas()

class BacktestReporter:
    def __init__(self, trades_df, equity_curve_df, initial_equity=100000):
        """
        Initialize reporter with backtest results

        Args:
        - trades_df: DataFrame with trade history
        - equity_curve_df: DataFrame with timestamp and equity columns
        - initial_equity: Starting capital
        """
        self.trades_df = trades_df
        self.equity_curve_df = equity_curve_df
        self.initial_equity = initial_equity

        # Prepare returns series
        self.returns = self._prepare_returns()

    def _prepare_returns(self):
        """Convert equity curve to returns series"""
        if len(self.equity_curve_df) == 0:
            return pd.Series(dtype=float)

        equity_series = pd.Series(
            self.equity_curve_df['equity'].values,
            index=pd.to_datetime(self.equity_curve_df['timestamp'])
        )

        # Calculate percentage returns
        returns = equity_series.pct_change().fillna(0)
        return returns

    def generate_html_report(self, output_path='output/london_breakout/tearsheet.html',
                            benchmark=None, title='London Breakout Strategy'):
        """
        Generate full HTML tearsheet report

        Args:
        - output_path: Path to save HTML report
        - benchmark: Optional benchmark returns series (e.g., SPY)
        - title: Report title
        """
        print(f"Generating HTML tearsheet: {output_path}")

        # Create output directory
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Generate report
        qs.reports.html(
            self.returns,
            benchmark=benchmark,
            output=output_path,
            title=title
        )

        print(f"✅ HTML report saved to {output_path}")
        return output_path

    def generate_metrics_report(self):
        """Generate text-based metrics report"""
        print("\n" + "=" * 80)
        print("QUANTSTATS PERFORMANCE METRICS")
        print("=" * 80)

        # Basic metrics
        print("\n📊 Returns Metrics:")
        print(f"  Total Return: {qs.stats.comp(self.returns)*100:.2f}%")
        print(f"  CAGR: {qs.stats.cagr(self.returns)*100:.2f}%")
        print(f"  Sharpe Ratio: {qs.stats.sharpe(self.returns):.2f}")
        print(f"  Sortino Ratio: {qs.stats.sortino(self.returns):.2f}")
        print(f"  Calmar Ratio: {qs.stats.calmar(self.returns):.2f}")

        # Risk metrics
        print("\n📉 Risk Metrics:")
        print(f"  Max Drawdown: {qs.stats.max_drawdown(self.returns)*100:.2f}%")
        print(f"  Volatility (Annual): {qs.stats.volatility(self.returns)*100:.2f}%")
        print(f"  Value at Risk (95%): {qs.stats.value_at_risk(self.returns)*100:.2f}%")
        print(f"  Conditional VaR (95%): {qs.stats.conditional_value_at_risk(self.returns)*100:.2f}%")

        # Win rate metrics (from trades)
        if len(self.trades_df) > 0:
            print("\n🎯 Trade Statistics:")
            wins = self.trades_df[self.trades_df['pnl_dollars'] > 0]
            losses = self.trades_df[self.trades_df['pnl_dollars'] <= 0]

            win_rate = len(wins) / len(self.trades_df) * 100
            avg_win = wins['pnl_dollars'].mean() if len(wins) > 0 else 0
            avg_loss = losses['pnl_dollars'].mean() if len(losses) > 0 else 0
            profit_factor = abs(wins['pnl_dollars'].sum() / losses['pnl_dollars'].sum()) if len(losses) > 0 and losses['pnl_dollars'].sum() != 0 else float('inf')

            print(f"  Total Trades: {len(self.trades_df)}")
            print(f"  Win Rate: {win_rate:.2f}%")
            print(f"  Avg Win: ${avg_win:.2f}")
            print(f"  Avg Loss: ${avg_loss:.2f}")
            print(f"  Profit Factor: {profit_factor:.2f}")
            print(f"  Expectancy: ${self.trades_df['pnl_dollars'].mean():.2f}")

        # Distribution metrics
        print("\n📈 Distribution:")
        print(f"  Best Day: {qs.stats.best(self.returns)*100:.2f}%")
        print(f"  Worst Day: {qs.stats.worst(self.returns)*100:.2f}%")
        print(f"  Skew: {qs.stats.skew(self.returns):.2f}")
        print(f"  Kurtosis: {qs.stats.kurtosis(self.returns):.2f}")

        # Consistency
        print("\n🎲 Consistency:")
        print(f"  Win Days: {qs.stats.win_rate(self.returns)*100:.2f}%")
        print(f"  Average Up Day: {qs.stats.avg_win(self.returns)*100:.2f}%")
        print(f"  Average Down Day: {qs.stats.avg_loss(self.returns)*100:.2f}%")

        print("\n" + "=" * 80)

    def plot_equity_curve(self, output_path='output/london_breakout/equity_curve.png'):
        """Generate equity curve with drawdown plot"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

        # Equity curve
        equity = (1 + self.returns).cumprod() * self.initial_equity
        equity.plot(ax=ax1, linewidth=2, color='#2E86AB')
        ax1.set_title('Equity Curve', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Equity ($)', fontsize=12)
        ax1.grid(alpha=0.3)
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Drawdown
        drawdown = qs.stats.to_drawdown_series(self.returns) * 100
        drawdown.plot(ax=ax2, kind='area', color='#A23B72', alpha=0.5)
        ax2.set_title('Drawdown', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Drawdown (%)', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.grid(alpha=0.3)

        plt.tight_layout()

        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✅ Equity curve saved to {output_path}")
        plt.close()

    def plot_monthly_returns(self, output_path='output/london_breakout/monthly_returns.png'):
        """Generate monthly returns heatmap"""
        fig = plt.figure(figsize=(12, 6))
        qs.plots.monthly_heatmap(self.returns, show=False)

        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✅ Monthly returns heatmap saved to {output_path}")
        plt.close()

    def plot_rolling_metrics(self, output_path='output/london_breakout/rolling_metrics.png', window=30):
        """Generate rolling Sharpe and volatility"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

        # Rolling Sharpe
        rolling_sharpe = qs.stats.rolling_sharpe(self.returns, window)
        rolling_sharpe.plot(ax=ax1, linewidth=2, color='#2E86AB')
        ax1.set_title(f'{window}-Day Rolling Sharpe Ratio', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Sharpe Ratio', fontsize=12)
        ax1.axhline(y=0, color='red', linestyle='--', alpha=0.3)
        ax1.grid(alpha=0.3)

        # Rolling Volatility
        rolling_vol = qs.stats.rolling_volatility(self.returns, window) * 100
        rolling_vol.plot(ax=ax2, linewidth=2, color='#A23B72')
        ax2.set_title(f'{window}-Day Rolling Volatility', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Volatility (%)', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.grid(alpha=0.3)

        plt.tight_layout()

        # Save
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✅ Rolling metrics saved to {output_path}")
        plt.close()

    def generate_full_report(self):
        """Generate complete report with all visualizations"""
        print("\n" + "=" * 80)
        print("GENERATING COMPREHENSIVE BACKTEST REPORT")
        print("=" * 80)

        # Metrics
        self.generate_metrics_report()

        # Visualizations
        self.plot_equity_curve()
        self.plot_monthly_returns()
        self.plot_rolling_metrics()

        # HTML tearsheet
        self.generate_html_report()

        print("\n" + "=" * 80)
        print("✅ REPORT GENERATION COMPLETE")
        print("=" * 80)
        print("\nGenerated files:")
        print("  - output/london_breakout/tearsheet.html (Full interactive report)")
        print("  - output/london_breakout/equity_curve.png")
        print("  - output/london_breakout/monthly_returns.png")
        print("  - output/london_breakout/rolling_metrics.png")


if __name__ == '__main__':
    # Test with London Breakout results
    print("Loading London Breakout backtest results...")

    # Run the backtest first if results don't exist
    from strategy_breakout_v3 import LondonBreakoutV3
    from data_loader import ForexDataLoader

    loader = ForexDataLoader()
    h1_df = loader.load('EURUSD', 'H1')
    h4_df = loader.load('EURUSD', 'H4')

    h1_df = h1_df[h1_df.index >= '2020-01-01']  # Full 5-year period
    h4_df = h4_df[h4_df.index >= '2020-01-01']

    print("Running backtest...")
    strategy = LondonBreakoutV3(pair='EURUSD')
    trades = strategy.backtest(h1_df, h4_df)

    # Create equity curve from trades
    equity_curve = []
    equity = 100000

    for idx, trade in trades.iterrows():
        equity += trade['pnl_dollars']
        equity_curve.append({
            'timestamp': trade['exit_time'],
            'equity': equity
        })

    equity_df = pd.DataFrame(equity_curve)

    # Generate report
    reporter = BacktestReporter(
        trades_df=trades,
        equity_curve_df=equity_df,
        initial_equity=100000
    )

    reporter.generate_full_report()
