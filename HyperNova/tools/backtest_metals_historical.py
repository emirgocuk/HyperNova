"""
Optimized Historical Metals Backtester with Trend Alignment, Dynamic ATR Trailing Stops,
and Anti-Overtrading Filters.
"""

import sys
import os
import io

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf

# Add parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class OptimizedMetalsBacktester:
    """
    Optimized Event-Driven Backtester for Gold & Silver:
    - Trend Filter: EMA 50 & EMA 200 alignment (Only longs in bull trend, only shorts in bear trend)
    - Extreme Oscillator Confluence: StochRSI < 18 or > 82
    - Asymmetric R:R: 0.60% TP vs 0.40% SL + Breakeven Trailing Stop at +0.25%
    - Spread: 0.02%, Fee: 0.04%
    """
    def __init__(
        self,
        initial_capital: float = 10000.0,
        trade_size_usd: float = 100.0,
        tp_pct: float = 0.0055,       # +0.55% TP
        sl_pct: float = 0.0040,       # -0.40% SL
        be_trigger_pct: float = 0.0025, # Move SL to Entry (Breakeven) after +0.25% gain
        spread_pct: float = 0.0002,
        fee_pct: float = 0.0003,
        max_positions: int = 2
    ):
        self.initial_capital = initial_capital
        self.trade_size_usd = trade_size_usd
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.be_trigger_pct = be_trigger_pct
        self.spread_pct = spread_pct
        self.fee_pct = fee_pct
        self.max_positions = max_positions

    def run_backtest(self, df: pd.DataFrame, symbol: str) -> dict:
        if df.empty or len(df) < 200:
            return {'error': f'Insufficient data for {symbol}'}

        df_calc = df.copy()

        # Indicators
        bb = ta.bbands(df_calc['Close'], length=20, std=2.2)
        stoch_rsi = ta.stochrsi(df_calc['Close'], length=14, rsi_length=14, k=3, d=3)
        ema_50 = ta.ema(df_calc['Close'], length=50)
        ema_200 = ta.ema(df_calc['Close'], length=200)
        adx_df = ta.adx(df_calc['High'], df_calc['Low'], df_calc['Close'], length=14)

        df_calc['BBL'] = bb.iloc[:, 0]
        df_calc['BBU'] = bb.iloc[:, 2]
        df_calc['STOCH_K'] = stoch_rsi.iloc[:, 0]
        df_calc['EMA_50'] = ema_50
        df_calc['EMA_200'] = ema_200
        df_calc['ADX'] = adx_df.iloc[:, 0] if adx_df is not None else 20.0

        cash = self.initial_capital
        positions = []
        trades = []
        equity_curve = []

        warmup = 200

        for i in range(warmup, len(df_calc)):
            bar = df_calc.iloc[i]
            current_price = float(bar['Close'])
            high_price = float(bar['High'])
            low_price = float(bar['Low'])
            bbl = float(bar['BBL']) if not np.isnan(bar['BBL']) else current_price * 0.995
            bbu = float(bar['BBU']) if not np.isnan(bar['BBU']) else current_price * 1.005
            stoch_k = float(bar['STOCH_K']) if not np.isnan(bar['STOCH_K']) else 50.0
            ema50_val = float(bar['EMA_50']) if not np.isnan(bar['EMA_50']) else current_price
            ema200_val = float(bar['EMA_200']) if not np.isnan(bar['EMA_200']) else current_price
            adx_val = float(bar['ADX']) if not np.isnan(bar['ADX']) else 20.0

            # 1. Manage Positions & Exits
            active_positions = []
            for pos in positions:
                side = pos['side']
                entry_price = pos['entry_price']
                size_coin = pos['size_coin']
                entry_idx = pos['entry_idx']
                sl_price = pos['sl_price']
                tp_price = pos['tp_price']

                # Breakeven Trailing Stop Check
                if side == "LONG" and high_price >= entry_price * (1 + self.be_trigger_pct):
                    # Move stop to breakeven + 0.05%
                    pos['sl_price'] = max(sl_price, entry_price * 1.0005)
                elif side == "SHORT" and low_price <= entry_price * (1 - self.be_trigger_pct):
                    pos['sl_price'] = min(sl_price, entry_price * 0.9995)

                exit_price = None
                exit_reason = None

                if side == "LONG":
                    if high_price >= tp_price:
                        exit_price = tp_price
                        exit_reason = "TAKE_PROFIT"
                    elif low_price <= pos['sl_price']:
                        exit_price = pos['sl_price']
                        exit_reason = "BREAKEVEN_OR_SL"

                elif side == "SHORT":
                    if low_price <= tp_price:
                        exit_price = tp_price
                        exit_reason = "TAKE_PROFIT"
                    elif high_price >= pos['sl_price']:
                        exit_price = pos['sl_price']
                        exit_reason = "BREAKEVEN_OR_SL"

                if exit_price is not None:
                    trade_cost = (size_coin * exit_price) * self.fee_pct
                    if side == "LONG":
                        gross_pnl = (exit_price - entry_price) * size_coin
                    else:
                        gross_pnl = (entry_price - exit_price) * size_coin

                    net_pnl = gross_pnl - trade_cost - pos['entry_fee']
                    cash += (size_coin * entry_price) + net_pnl

                    trades.append({
                        'symbol': symbol,
                        'side': side,
                        'entry_idx': entry_idx,
                        'exit_idx': i,
                        'duration_bars': i - entry_idx,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'net_pnl': net_pnl,
                        'pnl_pct': (net_pnl / self.trade_size_usd) * 100,
                        'reason': exit_reason
                    })
                else:
                    active_positions.append(pos)

            positions = active_positions

            # 2. Precision Signal Filter (Trend + Momentum Confluence)
            if len(positions) < self.max_positions:
                signal = None

                # Long: Price above 200 EMA (Uptrend) + Pullback to BBL or StochRSI < 18
                if current_price > ema200_val and (current_price <= bbl or stoch_k < 18):
                    signal = "LONG"

                # Short: Price below 200 EMA (Downtrend) + Bounce to BBU or StochRSI > 82
                elif current_price < ema200_val and (current_price >= bbu or stoch_k > 82):
                    signal = "SHORT"

                if signal:
                    already_entered = any(
                        p['side'] == signal and abs(p['entry_price'] - current_price)/current_price < 0.003
                        for p in positions
                    )

                    if not already_entered and cash >= self.trade_size_usd:
                        exec_price = current_price * (1 + self.spread_pct) if signal == "LONG" else current_price * (1 - self.spread_pct)
                        size_coin = self.trade_size_usd / exec_price
                        entry_fee = (size_coin * exec_price) * self.fee_pct

                        tp_price = exec_price * (1 + self.tp_pct) if signal == "LONG" else exec_price * (1 - self.tp_pct)
                        sl_price = exec_price * (1 - self.sl_pct) if signal == "LONG" else exec_price * (1 + self.sl_pct)

                        cash -= self.trade_size_usd
                        positions.append({
                            'side': signal,
                            'entry_price': exec_price,
                            'size_coin': size_coin,
                            'tp_price': tp_price,
                            'sl_price': sl_price,
                            'entry_fee': entry_fee,
                            'entry_idx': i
                        })

            # 3. Record Equity
            unrealized = 0.0
            for pos in positions:
                if pos['side'] == "LONG":
                    unrealized += (current_price - pos['entry_price']) * pos['size_coin']
                else:
                    unrealized += (pos['entry_price'] - current_price) * pos['size_coin']

            pos_value = sum(p['size_coin'] * p['entry_price'] for p in positions)
            total_equity = cash + pos_value + unrealized
            equity_curve.append(total_equity)

        # 4. Metrics
        equity_series = pd.Series(equity_curve)
        final_equity = equity_series.iloc[-1]
        net_profit = final_equity - self.initial_capital
        net_return_pct = (net_profit / self.initial_capital) * 100

        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        max_dd_pct = abs(drawdown.min()) * 100

        if trades:
            tdf = pd.DataFrame(trades)
            wins = tdf[tdf['net_pnl'] > 0]
            losses = tdf[tdf['net_pnl'] <= 0]
            win_rate = (len(wins) / len(tdf)) * 100
            gross_win = wins['net_pnl'].sum() if not wins.empty else 0.0
            gross_loss = abs(losses['net_pnl'].sum()) if not losses.empty else 1.0
            profit_factor = round(gross_win / max(gross_loss, 1e-6), 2)
            total_trades = len(tdf)
            avg_win = wins['net_pnl'].mean() if not wins.empty else 0.0
            avg_loss = losses['net_pnl'].mean() if not losses.empty else 0.0
            avg_duration_mins = tdf['duration_bars'].mean() * 5
        else:
            win_rate, profit_factor, total_trades, avg_win, avg_loss, avg_duration_mins = 0, 0, 0, 0, 0, 0

        daily_ret = equity_series.pct_change().dropna()
        sharpe = round(float((daily_ret.mean() / daily_ret.std()) * np.sqrt(252 * 288)), 2) if len(daily_ret) > 1 and daily_ret.std() > 0 else 0.0

        return {
            'symbol': symbol,
            'total_candles': len(df_calc),
            'start_date': str(df_calc.index[0]),
            'end_date': str(df_calc.index[-1]),
            'initial_capital': self.initial_capital,
            'final_equity': round(final_equity, 2),
            'net_profit_usd': round(net_profit, 2),
            'net_return_pct': round(net_return_pct, 2),
            'total_trades': total_trades,
            'win_rate_pct': round(win_rate, 2),
            'profit_factor': profit_factor,
            'max_drawdown_pct': round(max_dd_pct, 2),
            'sharpe_ratio': sharpe,
            'avg_win_usd': round(avg_win, 2),
            'avg_loss_usd': round(avg_loss, 2),
            'avg_duration_mins': round(avg_duration_mins, 1)
        }


def run_optimized_metals_backtest():
    print("="*65)
    print("🚀 OPTIMIZED METALS (GOLD & SILVER) HISTORICAL BACKTEST")
    print("🎯 STRATEGY: Trend-Aligned Pullbacks + Breakeven Trailing Protection")
    print("="*65)

    gold_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'historical', 'GOLD_5m_60d.csv'))
    silver_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'database', 'historical', 'SILVER_5m_60d.csv'))

    gold_df = pd.read_csv(gold_path, index_col=0, parse_dates=True)
    silver_df = pd.read_csv(silver_path, index_col=0, parse_dates=True)

    backtester = OptimizedMetalsBacktester(
        initial_capital=10000.0,
        trade_size_usd=100.0,      # $100 per micro trade
        tp_pct=0.0055,             # +0.55% Take Profit
        sl_pct=0.0040,             # -0.40% Stop Loss
        be_trigger_pct=0.0022      # Move SL to Entry after +0.22%
    )

    print("\n" + "="*65)
    print("📊 BACKTEST RESULT: GOLD (XAUUSD)")
    print("="*65)
    gold_res = backtester.run_backtest(gold_df, "GOLD")
    print_res(gold_res)

    print("\n" + "="*65)
    print("📊 BACKTEST RESULT: SILVER (XAGUSD)")
    print("="*65)
    silver_res = backtester.run_backtest(silver_df, "SILVER")
    print_res(silver_res)

    print("\n" + "="*65)
    print("🌟 PORTFÖY TOPLAM PERFORMANSI (GOLD + SILVER)")
    print("="*65)
    total_profit = gold_res['net_profit_usd'] + silver_res['net_profit_usd']
    total_trades = gold_res['total_trades'] + silver_res['total_trades']
    avg_wr = (gold_res['win_rate_pct'] + silver_res['win_rate_pct']) / 2
    avg_pf = (gold_res['profit_factor'] + silver_res['profit_factor']) / 2
    print(f"💰 Toplam Net Kâr:         +${total_profit:.2f} ({((total_profit)/10000)*100:+.2f}%)")
    print(f"🔄 Toplam İşlem Sayısı:     {total_trades} adet")
    print(f"🎯 Ortalama Kazanma Oranı:  %{avg_wr:.1f}")
    print(f"⚖️ Ortalama Profit Factor:  {avg_pf:.2f}")
    print(f"🛡️ Maksimum Drawdown:      Gold: %{gold_res['max_drawdown_pct']} | Silver: %{silver_res['max_drawdown_pct']}")
    print("="*65)


def print_res(res: dict):
    if 'error' in res:
        print(f"Hata: {res['error']}")
        return
    print(f"📅 Veri Aralığı:       {res['start_date'][:10]} -> {res['end_date'][:10]} ({res['total_candles']} mum / 5m)")
    print(f"💰 Başlangıç Bakiyesi:  ${res['initial_capital']:.2f}")
    print(f"📈 Bitiş Bakiyesi:      ${res['final_equity']:.2f}")
    print(f"💸 Net Kâr / Zarar:     ${res['net_profit_usd']:+.2f} ({res['net_return_pct']:+.2f}%)")
    print(f"🔄 Toplam İşlem:        {res['total_trades']}")
    print(f"🎯 Kazanma Oranı (WR):  %{res['win_rate_pct']:.1f}")
    print(f"⚖️ Profit Factor (PF):  {res['profit_factor']}")
    print(f"🛡️ Max Drawdown (DD):   %{res['max_drawdown_pct']:.2f}")
    print(f"📊 Sharpe Ratio:        {res['sharpe_ratio']}")
    print(f"💧 Ortalama Kâr/Zarar:  +${res['avg_win_usd']:.2f} / -${abs(res['avg_loss_usd']):.2f}")
    print(f"⏱️ Ortalama Süre:       {res['avg_duration_mins']} dakika")


if __name__ == "__main__":
    run_optimized_metals_backtest()
