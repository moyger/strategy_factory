"""
Strategy Analyzer - Analyze strategy performance using QuantStats

Replaces QuantAnalyzer with free open-source alternative.
Generates comprehensive HTML reports, tear sheets, and metrics.
"""

import pandas as pd
import numpy as np
import quantstats as qs
import vectorbt as vbt
from typing import Dict, List, Optional
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Extend pandas with quantstats
qs.extend_pandas()


class StrategyAnalyzer:
    """
    Analyze trading strategy performance using QuantStats

    Example:
        analyzer = StrategyAnalyzer()
        analyzer.generate_full_report(returns, output_file='report.html')
        metrics = analyzer.get_key_metrics(returns)
    """

    def __init__(self, output_dir: str = 'results/analysis_reports'):
        """
        Initialize analyzer

        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_full_report(self,
                            returns: pd.Series,
                            benchmark: Optional[pd.Series] = None,
                            output_file: str = 'strategy_report.html',
                            title: str = 'Strategy Performance Report') -> str:
        """
        Generate comprehensive HTML report

        Args:
            returns: Series of strategy returns
            benchmark: Optional benchmark returns for comparison
            output_file: Output filename
            title: Report title

        Returns:
            Path to generated report
        """
        output_path = self.output_dir / output_file

        print(f"📊 Generating full report...")

        # Generate report
        qs.reports.html(
            returns,
            benchmark=benchmark,
            output=str(output_path),
            title=title,
            download_filename=output_file
        )

        print(f"✅ Report saved: {output_path}")
        return str(output_path)

    def generate_tearsheet(self,
                          returns: pd.Series,
                          benchmark: Optional[pd.Series] = None,
                          mode: str = 'full') -> None:
        """
        Generate tear sheet (printed to console or notebook)

        Args:
            returns: Series of strategy returns
            benchmark: Optional benchmark returns
            mode: 'full', 'basic', or 'metrics'
        """
        print(f"\n{'='*80}")
        print(f"STRATEGY TEAR SHEET - {mode.upper()}")
        print(f"{'='*80}\n")

        if mode == 'full':
            qs.reports.full(returns, benchmark=benchmark)
        elif mode == 'basic':
            qs.reports.basic(returns, benchmark=benchmark)
        elif mode == 'metrics':
            qs.reports.metrics(returns, benchmark=benchmark, mode='full')
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def get_key_metrics(self, returns: pd.Series, benchmark: Optional[pd.Series] = None) -> Dict:
        """
        Get key performance metrics

        Args:
            returns: Series of strategy returns
            benchmark: Optional benchmark returns

        Returns:
            Dictionary of metrics
        """
        metrics = {
            # Returns
            'total_return': qs.stats.comp(returns) * 100,
            'cagr': qs.stats.cagr(returns) * 100,
            'daily_mean': returns.mean() * 100,
            'daily_std': returns.std() * 100,

            # Risk-adjusted
            'sharpe': qs.stats.sharpe(returns),
            'sortino': qs.stats.sortino(returns),
            'calmar': qs.stats.calmar(returns),
            'omega': qs.stats.omega(returns),

            # Drawdown
            'max_drawdown': qs.stats.max_drawdown(returns) * 100,
            'avg_drawdown': qs.stats.avg_drawdown(returns) * 100,
            'avg_drawdown_days': qs.stats.avg_drawdown_days(returns),

            # Win rate
            'win_rate': qs.stats.win_rate(returns) * 100,
            'avg_win': qs.stats.avg_win(returns) * 100,
            'avg_loss': qs.stats.avg_loss(returns) * 100,
            'win_loss_ratio': qs.stats.win_loss_ratio(returns),

            # Risk
            'volatility': qs.stats.volatility(returns) * 100,
            'var_95': qs.stats.var(returns) * 100,
            'cvar_95': qs.stats.cvar(returns) * 100,

            # Consistency
            'best_day': qs.stats.best(returns) * 100,
            'worst_day': qs.stats.worst(returns) * 100,
            'consecutive_wins': qs.stats.consecutive_wins(returns),
            'consecutive_losses': qs.stats.consecutive_losses(returns),
        }

        # Add benchmark comparison if provided
        if benchmark is not None:
            metrics['alpha'] = qs.stats.alpha(returns, benchmark) * 100
            metrics['beta'] = qs.stats.beta(returns, benchmark)
            metrics['information_ratio'] = qs.stats.information_ratio(returns, benchmark)

        return metrics

    def print_metrics(self, metrics: Dict) -> None:
        """Print metrics in formatted table"""
        print(f"\n{'='*80}")
        print(f"PERFORMANCE METRICS")
        print(f"{'='*80}\n")

        # Group metrics
        groups = {
            'Returns': ['total_return', 'cagr', 'daily_mean'],
            'Risk-Adjusted': ['sharpe', 'sortino', 'calmar', 'omega'],
            'Drawdown': ['max_drawdown', 'avg_drawdown', 'avg_drawdown_days'],
            'Win/Loss': ['win_rate', 'avg_win', 'avg_loss', 'win_loss_ratio'],
            'Risk': ['volatility', 'var_95', 'cvar_95'],
            'Extremes': ['best_day', 'worst_day', 'consecutive_wins', 'consecutive_losses']
        }

        for group_name, metric_keys in groups.items():
            print(f"\n{group_name}:")
            print("-" * 60)
            for key in metric_keys:
                if key in metrics:
                    value = metrics[key]
                    if isinstance(value, float):
                        if 'ratio' in key or 'beta' in key:
                            print(f"  {key:.<40} {value:.2f}")
                        else:
                            print(f"  {key:.<40} {value:.2f}%")
                    else:
                        print(f"  {key:.<40} {value}")

    def compare_strategies(self,
                          strategies: Dict[str, pd.Series],
                          output_file: str = 'strategy_comparison.html') -> pd.DataFrame:
        """
        Compare multiple strategies

        Args:
            strategies: Dict of {strategy_name: returns_series}
            output_file: Output filename for report

        Returns:
            DataFrame with comparison metrics
        """
        print(f"📊 Comparing {len(strategies)} strategies...")

        comparison_data = []

        for name, returns in strategies.items():
            metrics = self.get_key_metrics(returns)
            metrics['strategy'] = name
            comparison_data.append(metrics)

        df = pd.DataFrame(comparison_data)
        df = df.set_index('strategy')

        # Sort by Sharpe ratio
        df = df.sort_values('sharpe', ascending=False)

        # Save to CSV
        csv_path = self.output_dir / output_file.replace('.html', '.csv')
        df.to_csv(csv_path)
        print(f"✅ Comparison saved: {csv_path}")

        return df

    def analyze_portfolio(self,
                         portfolio: vbt.Portfolio,
                         output_file: str = 'portfolio_analysis.html') -> Dict:
        """
        Analyze portfolio from vectorbt

        Args:
            portfolio: vectorbt Portfolio object
            output_file: Output filename

        Returns:
            Dictionary of metrics
        """
        print(f"📊 Analyzing portfolio...")

        # Get returns
        returns = portfolio.returns()

        # Generate full report
        self.generate_full_report(returns, output_file=output_file)

        # Get metrics
        metrics = self.get_key_metrics(returns)

        # Add portfolio-specific metrics
        metrics.update({
            'num_trades': portfolio.trades.count(),
            'profit_factor': portfolio.trades.profit_factor() if portfolio.trades.count() > 0 else 0,
            'expectancy': portfolio.trades.expectancy() if portfolio.trades.count() > 0 else 0,
            'avg_trade_duration': portfolio.trades.duration.mean() if portfolio.trades.count() > 0 else 0,
        })

        return metrics

    def monte_carlo_report(self,
                          returns: pd.Series,
                          n_simulations: int = 1000,
                          output_file: str = 'monte_carlo.html') -> Dict:
        """
        Run Monte Carlo simulation and generate report

        Args:
            returns: Series of returns
            n_simulations: Number of simulations
            output_file: Output filename

        Returns:
            Dictionary with simulation statistics
        """
        print(f"🎲 Running Monte Carlo simulation ({n_simulations} runs)...")

        # Run simulations
        simulated_returns = []

        for _ in range(n_simulations):
            # Bootstrap sampling
            sampled = np.random.choice(returns.values, size=len(returns), replace=True)
            sim_cumulative = (1 + pd.Series(sampled)).cumprod()
            simulated_returns.append(sim_cumulative.iloc[-1] - 1)

        simulated_returns = np.array(simulated_returns)

        # Calculate statistics
        results = {
            'mean_return': np.mean(simulated_returns) * 100,
            'median_return': np.median(simulated_returns) * 100,
            'std_return': np.std(simulated_returns) * 100,
            'percentile_5': np.percentile(simulated_returns, 5) * 100,
            'percentile_25': np.percentile(simulated_returns, 25) * 100,
            'percentile_75': np.percentile(simulated_returns, 75) * 100,
            'percentile_95': np.percentile(simulated_returns, 95) * 100,
            'probability_positive': (simulated_returns > 0).sum() / n_simulations * 100,
            'worst_case': simulated_returns.min() * 100,
            'best_case': simulated_returns.max() * 100
        }

        print(f"\n✅ Monte Carlo Results:")
        print(f"   Mean return: {results['mean_return']:.2f}%")
        print(f"   95% CI: [{results['percentile_5']:.2f}%, {results['percentile_95']:.2f}%]")
        print(f"   Probability of profit: {results['probability_positive']:.1f}%")

        return results

    def rolling_metrics(self,
                       returns: pd.Series,
                       window: int = 252,
                       output_file: str = 'rolling_metrics.csv') -> pd.DataFrame:
        """
        Calculate rolling performance metrics

        Args:
            returns: Series of returns
            window: Rolling window size (default 252 = 1 year)
            output_file: Output filename

        Returns:
            DataFrame with rolling metrics
        """
        print(f"📊 Calculating rolling metrics (window={window})...")

        rolling_data = {
            'rolling_return': returns.rolling(window).apply(lambda x: (1 + x).prod() - 1) * 100,
            'rolling_volatility': returns.rolling(window).std() * np.sqrt(252) * 100,
            'rolling_sharpe': returns.rolling(window).apply(lambda x: qs.stats.sharpe(x)),
            'rolling_sortino': returns.rolling(window).apply(lambda x: qs.stats.sortino(x)),
            'rolling_max_dd': returns.rolling(window).apply(lambda x: qs.stats.max_drawdown(x)) * 100,
        }

        df = pd.DataFrame(rolling_data)

        # Save to CSV
        csv_path = self.output_dir / output_file
        df.to_csv(csv_path)
        print(f"✅ Rolling metrics saved: {csv_path}")

        return df

    def drawdown_analysis(self, returns: pd.Series) -> pd.DataFrame:
        """
        Analyze drawdown periods

        Args:
            returns: Series of returns

        Returns:
            DataFrame with drawdown periods
        """
        print(f"📉 Analyzing drawdown periods...")

        # Calculate cumulative returns
        cumulative = (1 + returns).cumprod()

        # Calculate running maximum
        running_max = cumulative.cummax()

        # Calculate drawdown
        drawdown = (cumulative - running_max) / running_max * 100

        # Find drawdown periods
        in_drawdown = drawdown < 0
        drawdown_periods = []

        start_idx = None
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and start_idx is None:
                start_idx = i
            elif not is_dd and start_idx is not None:
                end_idx = i - 1
                period_dd = drawdown.iloc[start_idx:end_idx+1]

                drawdown_periods.append({
                    'start': returns.index[start_idx] if hasattr(returns, 'index') else start_idx,
                    'end': returns.index[end_idx] if hasattr(returns, 'index') else end_idx,
                    'duration': end_idx - start_idx + 1,
                    'max_drawdown': period_dd.min(),
                    'recovery': cumulative.iloc[i] >= cumulative.iloc[start_idx-1] if start_idx > 0 else True
                })
                start_idx = None

        df = pd.DataFrame(drawdown_periods)

        if len(df) > 0:
            df = df.sort_values('max_drawdown')

            print(f"\n✅ Found {len(df)} drawdown periods")
            print(f"   Worst drawdown: {df['max_drawdown'].min():.2f}%")
            print(f"   Avg duration: {df['duration'].mean():.0f} days")
            print(f"   Recovery rate: {df['recovery'].sum() / len(df) * 100:.0f}%")

        return df

    def export_trades(self, portfolio: vbt.Portfolio, output_file: str = 'trades.csv') -> pd.DataFrame:
        """
        Export trade history to CSV

        Args:
            portfolio: vectorbt Portfolio object
            output_file: Output filename

        Returns:
            DataFrame with trades
        """
        trades = portfolio.trades.records_readable

        if len(trades) > 0:
            csv_path = self.output_dir / output_file
            trades.to_csv(csv_path, index=False)
            print(f"✅ Exported {len(trades)} trades to {csv_path}")

        return trades
