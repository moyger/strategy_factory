"""
Strategy Optimizer - Optimize strategy parameters using genetic algorithms

Uses DEAP (Distributed Evolutionary Algorithms in Python) for optimization.
Implements walk-forward analysis for robustness validation.
"""

import pandas as pd
import numpy as np
import vectorbt as vbt
from typing import Dict, List, Tuple, Callable, Any
from dataclasses import dataclass
import random
from deap import base, creator, tools, algorithms
import warnings
warnings.filterwarnings('ignore')


@dataclass
class OptimizationResult:
    """Results from parameter optimization"""
    best_params: Dict
    best_fitness: float
    all_generations: List
    convergence_history: List
    final_metrics: Dict


class StrategyOptimizer:
    """
    Optimize strategy parameters using genetic algorithms

    Example:
        optimizer = StrategyOptimizer()
        result = optimizer.optimize_sma(df, generations=50, population=100)
        print(f"Best params: {result.best_params}")
    """

    def __init__(self, initial_capital: float = 10000, commission: float = 0.001):
        """
        Initialize optimizer

        Args:
            initial_capital: Starting capital
            commission: Commission per trade
        """
        self.initial_capital = initial_capital
        self.commission = commission

    def optimize_sma(self,
                     df: pd.DataFrame,
                     fast_range: Tuple[int, int] = (5, 30),
                     slow_range: Tuple[int, int] = (40, 200),
                     generations: int = 50,
                     population: int = 100,
                     verbose: bool = True) -> OptimizationResult:
        """
        Optimize SMA crossover parameters using genetic algorithm

        Args:
            df: DataFrame with OHLCV data
            fast_range: (min, max) for fast SMA period
            slow_range: (min, max) for slow SMA period
            generations: Number of generations to evolve
            population: Population size
            verbose: Print progress

        Returns:
            OptimizationResult with best parameters
        """
        if verbose:
            print(f"🧬 Optimizing SMA strategy...")
            print(f"   Generations: {generations}, Population: {population}")

        # Define evaluation function
        def evaluate(individual):
            fast, slow = individual
            if fast >= slow:
                return (0,)  # Invalid

            close = df['close'].values
            fast_sma = pd.Series(close).rolling(int(fast)).mean()
            slow_sma = pd.Series(close).rolling(int(slow)).mean()

            entries = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
            exits = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))

            portfolio = vbt.Portfolio.from_signals(
                close=close,
                entries=entries,
                exits=exits,
                init_cash=self.initial_capital,
                fees=self.commission
            )

            # Fitness = Sharpe ratio
            sharpe = portfolio.sharpe_ratio() if portfolio.sharpe_ratio() is not None else 0
            return (sharpe,)

        # Run optimization
        result = self._run_genetic_optimization(
            evaluate_func=evaluate,
            param_ranges=[fast_range, slow_range],
            param_types=['int', 'int'],
            generations=generations,
            population=population,
            verbose=verbose
        )

        # Format results
        best_params = {'type': 'SMA', 'fast': int(result['best_individual'][0]), 'slow': int(result['best_individual'][1])}

        if verbose:
            print(f"✅ Optimization complete!")
            print(f"   Best params: {best_params}")
            print(f"   Best Sharpe: {result['best_fitness']:.2f}")

        return OptimizationResult(
            best_params=best_params,
            best_fitness=result['best_fitness'],
            all_generations=result['log'],
            convergence_history=result['convergence'],
            final_metrics={}
        )

    def optimize_rsi(self,
                     df: pd.DataFrame,
                     period_range: Tuple[int, int] = (5, 30),
                     oversold_range: Tuple[int, int] = (15, 40),
                     overbought_range: Tuple[int, int] = (60, 85),
                     generations: int = 50,
                     population: int = 100,
                     verbose: bool = True) -> OptimizationResult:
        """Optimize RSI parameters"""
        if verbose:
            print(f"🧬 Optimizing RSI strategy...")

        def evaluate(individual):
            period, oversold, overbought = individual
            if oversold >= overbought:
                return (0,)

            close = df['close'].values
            rsi = self._calculate_rsi(close, int(period))

            entries = rsi < oversold
            exits = rsi > overbought

            portfolio = vbt.Portfolio.from_signals(
                close=close,
                entries=entries,
                exits=exits,
                init_cash=self.initial_capital,
                fees=self.commission
            )

            sharpe = portfolio.sharpe_ratio() if portfolio.sharpe_ratio() is not None else 0
            return (sharpe,)

        result = self._run_genetic_optimization(
            evaluate_func=evaluate,
            param_ranges=[period_range, oversold_range, overbought_range],
            param_types=['int', 'int', 'int'],
            generations=generations,
            population=population,
            verbose=verbose
        )

        best_params = {
            'type': 'RSI',
            'period': int(result['best_individual'][0]),
            'oversold': int(result['best_individual'][1]),
            'overbought': int(result['best_individual'][2])
        }

        if verbose:
            print(f"✅ Best params: {best_params}")
            print(f"   Best Sharpe: {result['best_fitness']:.2f}")

        return OptimizationResult(
            best_params=best_params,
            best_fitness=result['best_fitness'],
            all_generations=result['log'],
            convergence_history=result['convergence'],
            final_metrics={}
        )

    def walk_forward_analysis(self,
                              df: pd.DataFrame,
                              strategy_params: Dict,
                              train_window: int = 252,  # 1 year
                              test_window: int = 63,    # 3 months
                              step_size: int = 21,      # 1 month
                              verbose: bool = True) -> pd.DataFrame:
        """
        Perform walk-forward analysis on strategy

        Args:
            df: DataFrame with OHLCV data
            strategy_params: Strategy parameters to test
            train_window: Training window size (bars)
            test_window: Testing window size (bars)
            step_size: Step size for rolling window
            verbose: Print progress

        Returns:
            DataFrame with walk-forward results
        """
        if verbose:
            print(f"🚶 Walk-forward analysis...")
            print(f"   Train: {train_window} bars, Test: {test_window} bars, Step: {step_size}")

        results = []
        total_steps = (len(df) - train_window - test_window) // step_size

        for i in range(0, len(df) - train_window - test_window, step_size):
            # Split data
            train_data = df.iloc[i:i + train_window]
            test_data = df.iloc[i + train_window:i + train_window + test_window]

            # Optimize on train
            if strategy_params['type'] == 'SMA':
                train_result = self.optimize_sma(train_data, verbose=False, generations=20, population=50)
                optimized_params = train_result.best_params
            elif strategy_params['type'] == 'RSI':
                train_result = self.optimize_rsi(train_data, verbose=False, generations=20, population=50)
                optimized_params = train_result.best_params
            else:
                continue

            # Test on out-of-sample
            test_metrics = self._backtest_strategy(test_data, optimized_params)

            results.append({
                'fold': len(results) + 1,
                'train_start': train_data.index[0] if hasattr(train_data, 'index') else 0,
                'train_end': train_data.index[-1] if hasattr(train_data, 'index') else 0,
                'test_start': test_data.index[0] if hasattr(test_data, 'index') else 0,
                'test_end': test_data.index[-1] if hasattr(test_data, 'index') else 0,
                'optimized_params': str(optimized_params),
                'test_return': test_metrics['total_return'],
                'test_sharpe': test_metrics['sharpe_ratio'],
                'test_drawdown': test_metrics['max_drawdown'],
                'test_trades': test_metrics['num_trades']
            })

            if verbose and len(results) % 5 == 0:
                print(f"   Completed {len(results)}/{total_steps} folds")

        df_results = pd.DataFrame(results)

        if verbose:
            print(f"\n✅ Walk-forward complete!")
            print(f"   Avg test return: {df_results['test_return'].mean():.2f}%")
            print(f"   Avg test Sharpe: {df_results['test_sharpe'].mean():.2f}")
            print(f"   Consistency: {(df_results['test_return'] > 0).sum() / len(df_results) * 100:.0f}% positive")

        return df_results

    def monte_carlo_simulation(self,
                              df: pd.DataFrame,
                              strategy_params: Dict,
                              n_simulations: int = 1000,
                              confidence_level: float = 0.95,
                              verbose: bool = True) -> Dict:
        """
        Run Monte Carlo simulation on strategy

        Args:
            df: DataFrame with OHLCV data
            strategy_params: Strategy parameters
            n_simulations: Number of simulations
            confidence_level: Confidence level for intervals
            verbose: Print progress

        Returns:
            Dict with simulation results
        """
        if verbose:
            print(f"🎲 Monte Carlo simulation ({n_simulations} runs)...")

        # Run base backtest
        portfolio = self._backtest_strategy(df, strategy_params, return_portfolio=True)
        trades = portfolio.trades.records_readable

        if len(trades) == 0:
            print("❌ No trades generated")
            return {}

        # Get trade returns
        trade_returns = trades['PnL'].values

        # Run simulations
        simulation_results = []

        for i in range(n_simulations):
            # Randomly sample trades with replacement
            sampled_returns = np.random.choice(trade_returns, size=len(trade_returns), replace=True)

            # Calculate cumulative return
            cumulative = np.cumprod(1 + sampled_returns / self.initial_capital)
            total_return = (cumulative[-1] - 1) * 100

            simulation_results.append(total_return)

        simulation_results = np.array(simulation_results)

        # Calculate statistics
        lower_percentile = (1 - confidence_level) / 2
        upper_percentile = 1 - lower_percentile

        results = {
            'mean_return': simulation_results.mean(),
            'median_return': np.median(simulation_results),
            'std_return': simulation_results.std(),
            f'lower_{int(confidence_level*100)}': np.percentile(simulation_results, lower_percentile * 100),
            f'upper_{int(confidence_level*100)}': np.percentile(simulation_results, upper_percentile * 100),
            'probability_positive': (simulation_results > 0).sum() / n_simulations * 100,
            'worst_case': simulation_results.min(),
            'best_case': simulation_results.max()
        }

        if verbose:
            print(f"\n✅ Monte Carlo complete!")
            print(f"   Mean return: {results['mean_return']:.2f}%")
            print(f"   {int(confidence_level*100)}% CI: [{results[f'lower_{int(confidence_level*100)}']:.2f}%, {results[f'upper_{int(confidence_level*100)}']:.2f}%]")
            print(f"   Probability of profit: {results['probability_positive']:.1f}%")

        return results

    def _run_genetic_optimization(self,
                                   evaluate_func: Callable,
                                   param_ranges: List[Tuple],
                                   param_types: List[str],
                                   generations: int,
                                   population: int,
                                   verbose: bool) -> Dict:
        """Run genetic algorithm optimization"""
        # Setup DEAP
        if hasattr(creator, "FitnessMax"):
            del creator.FitnessMax
        if hasattr(creator, "Individual"):
            del creator.Individual

        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()

        # Register parameters
        for i, (param_range, param_type) in enumerate(zip(param_ranges, param_types)):
            if param_type == 'int':
                toolbox.register(f"attr_{i}", random.randint, param_range[0], param_range[1])
            else:
                toolbox.register(f"attr_{i}", random.uniform, param_range[0], param_range[1])

        # Register individual and population
        toolbox.register("individual", tools.initCycle, creator.Individual,
                        [getattr(toolbox, f"attr_{i}") for i in range(len(param_ranges))],
                        n=1)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        # Register genetic operators
        toolbox.register("evaluate", evaluate_func)
        toolbox.register("mate", tools.cxTwoPoint)
        toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=1, indpb=0.2)
        toolbox.register("select", tools.selTournament, tournsize=3)

        # Create initial population
        pop = toolbox.population(n=population)
        hof = tools.HallOfFame(1)
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("max", np.max)

        # Run evolution
        pop, log = algorithms.eaSimple(pop, toolbox,
                                       cxpb=0.7, mutpb=0.2,
                                       ngen=generations,
                                       stats=stats,
                                       halloffame=hof,
                                       verbose=verbose)

        return {
            'best_individual': hof[0],
            'best_fitness': hof[0].fitness.values[0],
            'log': log,
            'convergence': [record['max'] for record in log]
        }

    def _backtest_strategy(self, df: pd.DataFrame, params: Dict, return_portfolio: bool = False):
        """Backtest strategy with given parameters"""
        close = df['close'].values

        if params['type'] == 'SMA':
            fast_sma = pd.Series(close).rolling(params['fast']).mean()
            slow_sma = pd.Series(close).rolling(params['slow']).mean()
            entries = (fast_sma > slow_sma) & (fast_sma.shift(1) <= slow_sma.shift(1))
            exits = (fast_sma < slow_sma) & (fast_sma.shift(1) >= slow_sma.shift(1))

        elif params['type'] == 'RSI':
            rsi = self._calculate_rsi(close, params['period'])
            entries = rsi < params['oversold']
            exits = rsi > params['overbought']

        else:
            raise ValueError(f"Unknown strategy type: {params['type']}")

        portfolio = vbt.Portfolio.from_signals(
            close=close,
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=self.commission
        )

        if return_portfolio:
            return portfolio

        return {
            'total_return': portfolio.total_return() * 100,
            'sharpe_ratio': portfolio.sharpe_ratio() if portfolio.sharpe_ratio() is not None else 0,
            'max_drawdown': portfolio.max_drawdown() * 100,
            'num_trades': portfolio.trades.count()
        }

    def _calculate_rsi(self, close: np.ndarray, period: int) -> pd.Series:
        """Calculate RSI indicator"""
        close_series = pd.Series(close)
        delta = close_series.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi
