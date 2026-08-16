"""
Nautilus-Style Event-Driven Backtesting and Simulation Engine.
Simulates realistic order execution with Bid/Ask spread, maker/taker fees,
latency slippage, and dynamic ATR risk controls.
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
from typing import Dict, Any, List, Optional
from core.portfolio_allocator import PortfolioAllocator
from core.regime_classifier import RegimeClassifier
from ai_engine.kronos_engine import KronosEngine
from agents.vibe_agent import VibeAgent


class EventDrivenBacktester:
    """
    Production-grade event-driven backtesting engine modeled after NautilusTrader.
    Iterates through historical bars, updating account state, orders, fills, and equity.
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        maker_fee: float = 0.0002,   # 0.02% Maker fee
        taker_fee: float = 0.0005,   # 0.05% Taker fee
        spread_pct: float = 0.0003,  # 0.03% Bid/Ask spread
        slippage_pct: float = 0.0002 # 0.02% Average market order slippage
    ):
        self.initial_capital = initial_capital
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.spread_pct = spread_pct
        self.slippage_pct = slippage_pct

        # Initialize Sub-engines
        self.allocator = PortfolioAllocator(default_risk_per_trade_pct=0.015)
        self.regime_classifier = RegimeClassifier()
        self.kronos = KronosEngine()
        self.vibe_agent = VibeAgent()

    def run(self, df: pd.DataFrame, symbol: str = "BTC") -> Dict[str, Any]:
        """
        Executes event-driven backtest over historical OHLCV data.
        """
        if df.empty or len(df) < 60:
            return {'error': 'Insufficient data for backtest'}

        df_calc = df.copy()
        df_calc['ATR'] = ta.atr(df_calc['High'], df_calc['Low'], df_calc['Close'], length=14)
        df_calc['RSI'] = ta.rsi(df_calc['Close'], length=14)

        cash = self.initial_capital
        position = None
        trades_history = []
        equity_curve = []

        warmup_period = 50

        for i in range(warmup_period, len(df_calc)):
            bar = df_calc.iloc[i]
            history_window = df_calc.iloc[:i+1]
            current_price = bar['Close']
            high_price = bar['High']
            low_price = bar['Low']
            current_atr = bar['ATR'] if not np.isnan(bar['ATR']) else current_price * 0.01
            current_rsi = bar['RSI'] if not np.isnan(bar['RSI']) else 50.0

            # 1. POSITION & RISK MANAGEMENT (Check SL / TP on current bar)
            if position is not None:
                side = position['side']
                entry_price = position['entry_price']
                size_coin = position['size_coin']
                sl = position['sl_price']
                tp = position['tp_price']
                exit_price = None
                exit_reason = None

                # Check Stop-Loss
                if side == "LONG" and low_price <= sl:
                    exit_price = sl * (1 - self.slippage_pct)
                    exit_reason = "STOP_LOSS"
                elif side == "SHORT" and high_price >= sl:
                    exit_price = sl * (1 + self.slippage_pct)
                    exit_reason = "STOP_LOSS"
                # Check Take-Profit
                elif side == "LONG" and high_price >= tp:
                    exit_price = tp * (1 - self.slippage_pct)
                    exit_reason = "TAKE_PROFIT"
                elif side == "SHORT" and low_price <= tp:
                    exit_price = tp * (1 + self.slippage_pct)
                    exit_reason = "TAKE_PROFIT"

                if exit_price is not None:
                    fee = (size_coin * exit_price) * self.taker_fee
                    if side == "LONG":
                        gross_pnl = (exit_price - entry_price) * size_coin
                    else:
                        gross_pnl = (entry_price - exit_price) * size_coin
                    net_pnl = gross_pnl - fee - position['entry_fee']
                    cash += (size_coin * entry_price) + net_pnl

                    trades_history.append({
                        'entry_idx': position['entry_idx'],
                        'exit_idx': i,
                        'symbol': symbol,
                        'side': side,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'net_pnl': net_pnl,
                        'return_pct': (net_pnl / (size_coin * entry_price)) * 100,
                        'reason': exit_reason
                    })
                    position = None

            # 2. SIGNAL GENERATION (Only if no active position)
            if position is None:
                ai_out = self.kronos.predict(history_window)
                raw_signal = ai_out['signal']
                regime_out = self.regime_classifier.classify(history_window)
                regime = regime_out['regime']

                # If Kronos is Neutral, use Regime + Momentum signal
                if raw_signal == "NEUTRAL":
                    if regime == "TRENDING_BULL" and current_rsi > 52:
                        raw_signal = "LONG"
                    elif regime == "TRENDING_BEAR" and current_rsi < 48:
                        raw_signal = "SHORT"
                    elif regime == "RANGING_CHOP":
                        if current_rsi < 32:
                            raw_signal = "LONG"
                        elif current_rsi > 68:
                            raw_signal = "SHORT"

                if raw_signal in ["LONG", "SHORT"]:
                    vibe_decision = self.vibe_agent.conduct_vibe_debate(
                        symbol=symbol,
                        signal=raw_signal,
                        price=current_price,
                        regime_info=regime_out,
                        ai_forecast=ai_out,
                        funding_rate=0.01
                    )

                    if vibe_decision.approved:
                        size_calc = self.allocator.calculate_atr_position_size(
                            equity=cash,
                            price=current_price,
                            atr=current_atr,
                            risk_pct=0.015,
                            atr_multiplier=2.0
                        )

                        size_coin = size_calc['size_coin']
                        size_usd = size_calc['size_usd']

                        if size_usd > 10.0 and size_usd <= cash:
                            exec_price = current_price * (1 + self.spread_pct + self.slippage_pct) if raw_signal == "LONG" else current_price * (1 - self.spread_pct - self.slippage_pct)
                            entry_fee = (size_coin * exec_price) * self.taker_fee

                            if raw_signal == "LONG":
                                sl_price = exec_price - (current_atr * 2.0)
                                tp_price = exec_price + (current_atr * 3.5)
                            else:
                                sl_price = exec_price + (current_atr * 2.0)
                                tp_price = exec_price - (current_atr * 3.5)

                            cash -= size_usd
                            position = {
                                'side': raw_signal,
                                'size_coin': size_coin,
                                'entry_price': exec_price,
                                'sl_price': sl_price,
                                'tp_price': tp_price,
                                'entry_fee': entry_fee,
                                'entry_idx': i
                            }

            # 3. RECORD EQUITY
            unrealized_pnl = 0.0
            if position is not None:
                if position['side'] == "LONG":
                    unrealized_pnl = (current_price - position['entry_price']) * position['size_coin']
                else:
                    unrealized_pnl = (position['entry_price'] - current_price) * position['size_coin']
                total_equity = cash + (position['size_coin'] * position['entry_price']) + unrealized_pnl
            else:
                total_equity = cash

            equity_curve.append(total_equity)

        # 4. CALCULATE INSTITUTIONAL PERFORMANCE METRICS
        equity_series = pd.Series(equity_curve)
        net_profit = equity_series.iloc[-1] - self.initial_capital
        net_return_pct = (net_profit / self.initial_capital) * 100

        peak = equity_series.cummax()
        drawdowns = (equity_series - peak) / peak
        max_drawdown_pct = abs(drawdowns.min()) * 100

        if trades_history:
            trades_df = pd.DataFrame(trades_history)
            wins = trades_df[trades_df['net_pnl'] > 0]
            losses = trades_df[trades_df['net_pnl'] <= 0]
            win_rate = (len(wins) / len(trades_df)) * 100
            gross_win = wins['net_pnl'].sum() if not wins.empty else 0.0
            gross_loss = abs(losses['net_pnl'].sum()) if not losses.empty else 1.0
            profit_factor = round(gross_win / max(gross_loss, 1e-6), 2)
            total_trades = len(trades_df)
        else:
            win_rate = 0.0
            profit_factor = 0.0
            total_trades = 0

        periodic_returns = equity_series.pct_change().dropna()
        if len(periodic_returns) > 1 and periodic_returns.std() > 0:
            sharpe_ratio = round(float((periodic_returns.mean() / periodic_returns.std()) * np.sqrt(252 * 24)), 2)
        else:
            sharpe_ratio = 0.0

        return {
            'initial_capital': self.initial_capital,
            'final_equity': round(float(equity_series.iloc[-1]), 2),
            'net_profit_usd': round(float(net_profit), 2),
            'net_return_pct': round(float(net_return_pct), 2),
            'max_drawdown_pct': round(float(max_drawdown_pct), 2),
            'win_rate_pct': round(float(win_rate), 2),
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': total_trades,
            'trades': trades_history
        }
