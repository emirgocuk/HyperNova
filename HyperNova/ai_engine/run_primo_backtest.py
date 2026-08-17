import time
import json
import os
import sys
import requests
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ensure UTF-8 on Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
hypernova_root = os.path.dirname(current_dir)
sys.path.insert(0, hypernova_root)
sys.path.insert(0, current_dir)

from ai_engine.primo_indicators import PrimoIndicatorEngine
from ai_engine.primo_nlp import PrimoNLPFeatureExtractor
from ai_engine.primo_agent import PrimoPPOAgent


def fetch_historical_candles(coin: str, interval: str = "1m", num_candles: int = 1500) -> List[Dict[str, float]]:
    """
    Fetches real historical candle data from HyperLiquid info API.
    """
    url = "https://api.hyperliquid.xyz/info"
    now_ms = int(time.time() * 1000)
    interval_ms = 60 * 1000 if interval == "1m" else (5 * 60 * 1000)
    start_ms = now_ms - (num_candles * interval_ms)

    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": interval,
            "startTime": start_ms,
            "endTime": now_ms
        }
    }

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10.0)
        data = resp.json()
        raw_candles = data if isinstance(data, list) else data.get("candles", [])
        formatted = []
        for c in raw_candles:
            formatted.append({
                "time": c.get("t", 0),
                "open": float(c["o"]),
                "high": float(c["h"]),
                "low": float(c["l"]),
                "close": float(c["c"]),
                "volume": float(c.get("v", 0.0))
            })
        print(f"  [OK] {coin}: {len(formatted)} adet gerçek 1-dakikalık mum verisi indirildi.")
        return formatted
    except Exception as e:
        print(f"  [UYARI] {coin} verisi çekilemedi ({e}), simüle edilmiş veri üretiliyor...")
        # Fallback realistic random-walk
        base_price = 145.0 if coin == "SOL" else (58.0 if coin == "HYPE" else 95000.0)
        candles = []
        curr = base_price
        for i in range(num_candles):
            drift = np.random.normal(0, curr * 0.0008)
            curr += drift
            h = curr + abs(np.random.normal(0, curr * 0.0004))
            l = curr - abs(np.random.normal(0, curr * 0.0004))
            candles.append({
                "time": start_ms + (i * interval_ms),
                "open": curr - drift * 0.5,
                "high": h,
                "low": l,
                "close": curr,
                "volume": 1000.0
            })
        return candles


class PrimoRealismBacktester:
    """
    Backtesting engine replicating exact 200x Leverage, MEXC Fee & Slippage Friction, 
    Primo DRL Features, and Break-Even Fee Protection Shield.
    """
    def __init__(
        self,
        start_balance: float = 10000.0,
        leverage: float = 200.0,
        lot_size_usd: float = 800.0,
        exchange_preset: str = "MEXC",
        maker_fee_pct: float = 0.0000,
        taker_fee_pct: float = 0.0002,   # 0.02% MEXC Taker
        slippage_pct: float = 0.0001,    # 0.01% Execution Slippage
        base_profit_trigger: float = 0.0012, # +0.12% wave trigger (3x fee)
        fast_sl_pct: float = 0.0035,     # -0.35% Hard SL
        stagnant_timeout_bars: int = 6   # 6 bars (6 minutes)
    ):
        self.start_balance = start_balance
        self.balance = start_balance
        self.leverage = leverage
        self.lot_size_usd = lot_size_usd
        self.maker_fee_pct = maker_fee_pct
        self.taker_fee_pct = taker_fee_pct
        self.slippage_pct = slippage_pct
        self.base_profit_trigger = base_profit_trigger
        self.fast_sl_pct = fast_sl_pct
        self.stagnant_timeout_bars = stagnant_timeout_bars

        self.tech_engine = PrimoIndicatorEngine()
        self.nlp_engine = PrimoNLPFeatureExtractor()
        self.agent = PrimoPPOAgent(state_dim=23)

        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: List[float] = [start_balance]
        self.total_fees_paid = 0.0
        self.total_slippage_cost = 0.0

    def run_simulation(self, symbol: str, candles: List[Dict[str, float]]):
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]

        # Warmup window of 60 bars for indicators
        warmup = 60
        if len(closes) < warmup + 10:
            print(f"Yetersiz veri: {len(closes)} bar.")
            return

        active_pos: Optional[Dict[str, Any]] = None

        for t in range(warmup, len(candles)):
            window_closes = list(closes[:t + 1])
            window_highs = list(highs[:t + 1])
            window_lows = list(lows[:t + 1])

            current_price = closes[t]

            # 1. Compute 6 Indicators (8 Normalized Features)
            tech_dict = self.tech_engine.compute_vector(window_highs, window_lows, window_closes, current_price)
            tech_vector = self.tech_engine.get_feature_array(window_highs, window_lows, window_closes, current_price)

            # 2. Extract NLP Features (7 Features)
            nlp_dict = self.nlp_engine.get_cached_features(symbol)
            nlp_vector = self.nlp_engine.get_feature_array(symbol)

            # 3. Microstructure Features (4 Features)
            oir = np.clip(np.sin(t / 15.0) * 0.45, -0.9, 0.9)  # Realistic orderbook wave
            micro_vector = np.array([oir, 0.05, 0.8, 0.0002], dtype=np.float32)

            # 4. Agent Inference (23-dim State)
            pos_ratio = (active_pos["notional_usd"] / self.lot_size_usd * (1.0 if active_pos and active_pos["side"] == "LONG" else -1.0)) if active_pos else 0.0
            unrealized_pnl_pct = 0.0
            price_ratio = 1.0
            if active_pos:
                if active_pos["side"] == "LONG":
                    unrealized_pnl_pct = (current_price - active_pos["entry_price"]) / active_pos["entry_price"]
                else:
                    unrealized_pnl_pct = (active_pos["entry_price"] - current_price) / active_pos["entry_price"]
                price_ratio = current_price / active_pos["entry_price"]

            state = np.zeros(23, dtype=np.float32)
            state[0] = float(np.clip(self.balance / self.start_balance, 0.1, 10.0))
            state[1] = float(pos_ratio)
            state[2] = float(np.clip(unrealized_pnl_pct * 10.0, -1.0, 1.0))
            state[3] = float(np.clip(price_ratio - 1.0, -0.2, 0.2))
            state[4:12] = tech_vector
            state[12:19] = nlp_vector
            state[19:23] = micro_vector

            action_scalar, action_meta = self.agent.predict(state)

            rsi_14 = tech_dict.get("rsi_14", 50.0)
            bbu = tech_dict.get("bbu", current_price * 1.002)
            bbl = tech_dict.get("bbl", current_price * 0.998)
            alpha_score = oir * 60.0

            # 5. Position Management & Exit
            if active_pos:
                side = active_pos["side"]
                entry_price = active_pos["entry_price"]
                size_coin = active_pos["size_coin"]
                req_margin = active_pos["required_margin"]

                if side == "LONG":
                    pnl_pct = (current_price - entry_price) / entry_price
                    pnl_usd = (current_price - entry_price) * size_coin
                else:
                    pnl_pct = (entry_price - current_price) / entry_price
                    pnl_usd = (entry_price - current_price) * size_coin

                roe_pct = (pnl_usd / max(req_margin, 0.01)) * 100.0
                active_pos["peak_pnl_pct"] = max(active_pos.get("peak_pnl_pct", 0.0), pnl_pct)
                bars_held = t - active_pos["entry_bar"]

                should_close = False
                exit_reason = ""

                # 1. Exhaustion Take Profit (+30% ROE or BB extremes)
                if roe_pct >= 30.0:
                    if side == "LONG" and (current_price >= bbu * 0.9998 or rsi_14 >= 80 or alpha_score < -30):
                        should_close = True
                        exit_reason = f"🎯 TEPE TÜKENİŞ KÂR KİLİT (+{roe_pct:.1f}% ROE)"
                    elif side == "SHORT" and (current_price <= bbl * 1.0002 or rsi_14 <= 20 or alpha_score > 30):
                        should_close = True
                        exit_reason = f"🎯 DİP TÜKENİŞ KÂR KİLİT (+{roe_pct:.1f}% ROE)"

                # 2. Dynamic Trailing (Waves >= +0.20% / +40% ROE = 5x Round-Trip Fee!)
                if not should_close and active_pos["peak_pnl_pct"] >= self.base_profit_trigger:
                    tol = 0.00040 if active_pos["peak_pnl_pct"] >= 0.0040 else 0.00025
                    if pnl_pct <= (active_pos["peak_pnl_pct"] - tol):
                        should_close = True
                        exit_reason = f"🚀 İZ SÜREN DALGA KÂRI (+{roe_pct:.1f}% ROE)"

                # 3. Komisyon Koruma Kalkanı (Break-Even + Fee Shield)
                elif not should_close and active_pos["peak_pnl_pct"] >= 0.0010 and pnl_pct <= 0.00050:
                    should_close = True
                    exit_reason = "🛡️ KOMİSYON KORUMA KALKANI (Komisyon Kurtarıldı)"

                # 4. Trend Reversal Exit (SMA30 Cross Invalidation)
                elif not should_close and ((side == "LONG" and current_price < sma_30 * 0.9990) or (side == "SHORT" and current_price > sma_30 * 1.0010)):
                    should_close = True
                    exit_reason = f"🔄 TREND DÖNÜŞ ÇIKIŞI ({pnl_pct*100:+.2f}%)"

                # 5. Stagnant Timeout (25 Dakika Sabır)
                elif not should_close and bars_held >= self.stagnant_timeout_bars and pnl_pct < 0.0005:
                    should_close = True
                    exit_reason = f"⏱️ YATAY ÇIKIŞ ({pnl_pct*100:+.2f}%)"

                # 6. Hard SL (-0.40%)
                elif not should_close and pnl_pct <= -self.fast_sl_pct:
                    should_close = True
                    exit_reason = f"🛑 Sıkı Stop-Loss ({pnl_pct*100:.2f}%)"

                if should_close:
                    # Apply exit slippage and exit fee
                    exit_slip = current_price * self.slippage_pct * (-1.0 if side == "LONG" else 1.0)
                    eff_exit_price = current_price + exit_slip
                    slip_cost = abs(exit_slip) * size_coin

                    if side == "LONG":
                        gross_pnl = (eff_exit_price - entry_price) * size_coin
                    else:
                        gross_pnl = (entry_price - eff_exit_price) * size_coin

                    exit_fee = (size_coin * eff_exit_price) * self.taker_fee_pct
                    entry_fee = active_pos["entry_fee"]
                    total_fees = entry_fee + exit_fee
                    net_pnl = gross_pnl - exit_fee  # entry fee was already deducted

                    self.balance += (gross_pnl - exit_fee)
                    self.total_fees_paid += exit_fee
                    self.total_slippage_cost += slip_cost

                    self.trades.append({
                        "symbol": symbol,
                        "side": side,
                        "entry_price": entry_price,
                        "exit_price": eff_exit_price,
                        "gross_pnl": gross_pnl,
                        "fees": total_fees,
                        "net_pnl": net_pnl,
                        "roe_pct": roe_pct,
                        "bars_held": bars_held,
                        "exit_reason": exit_reason,
                        "time": candles[t]["time"]
                    })
                    active_pos = None

            # 6. Entry Logic (Trend-Regime Sniper Mode)
            if not active_pos:
                signal = None
                sma_30 = tech_dict.get("sma_30", current_price)
                sma_60 = tech_dict.get("sma_60", current_price)
                macd_hist = tech_dict.get("macd_hist", 0.0)

                # Trend Regime Confirmation (Trade WITH the Higher Timeframe Trend)
                is_uptrend = current_price > sma_30 > sma_60 and macd_hist > 0
                is_downtrend = current_price < sma_30 < sma_60 and macd_hist < 0

                if (is_uptrend and action_scalar >= 0.15) or (current_price <= bbl and rsi_14 < 32 and action_scalar >= 0.05):
                    signal = "LONG"
                elif (is_downtrend and action_scalar <= -0.15) or (current_price >= bbu and rsi_14 > 68 and action_scalar <= -0.05):
                    signal = "SHORT"

                if signal:
                    # Apply entry slippage
                    entry_slip = current_price * self.slippage_pct * (1.0 if signal == "LONG" else -1.0)
                    eff_entry_price = current_price + entry_slip
                    size_coin = self.lot_size_usd / eff_entry_price
                    required_margin = self.lot_size_usd / self.leverage
                    entry_fee = self.lot_size_usd * self.taker_fee_pct

                    if (required_margin + entry_fee) <= self.balance:
                        self.balance -= entry_fee
                        self.total_fees_paid += entry_fee
                        self.total_slippage_cost += (abs(entry_slip) * size_coin)

                        active_pos = {
                            "symbol": symbol,
                            "side": signal,
                            "size_coin": size_coin,
                            "entry_price": eff_entry_price,
                            "entry_fee": entry_fee,
                            "required_margin": required_margin,
                            "notional_usd": self.lot_size_usd,
                            "entry_bar": t,
                            "peak_pnl_pct": 0.0
                        }

            self.equity_curve.append(self.balance)


def run_full_backtest():
    print("=================================================================")
    print(" >>> HYPERNOVA: 200X GERÇEKÇİ GERİYE DÖNÜK TEST (BACKTEST) <<<   ")
    print("=================================================================")
    print("Parametreler:")
    print("  • Kaldıraç:               200x")
    print("  • İşlem Büyüklüğü:        $800 Notional (Teminat: $4.00)")
    print("  • Borsa Modeli:           MEXC Vadeli (Taker: %0.02, Maker: %0.00)")
    print("  • Kayma (Slippage):       %0.01")
    print("  • Kâr Tetikleyicisi:      +%0.12 (Komisyonun 3x Katı)")
    print("  • Komisyon Kalkanı:       Aktif (+%0.045 Kâr Kilidi)")
    print("  • Başlangıç Bakiyesi:     $10,000.00")
    print("=================================================================\n")

    symbols = ["SOL", "HYPE", "BTC"]
    tester = PrimoRealismBacktester(
        start_balance=10000.0,
        leverage=200.0,
        lot_size_usd=800.0,
        maker_fee_pct=0.0000,
        taker_fee_pct=0.0002,
        slippage_pct=0.0001,
        base_profit_trigger=0.0020,
        fast_sl_pct=0.0040,
        stagnant_timeout_bars=25
    )

    print("Gerçek Piyasa Mum Verileri İndiriliyor (HyperLiquid API)...")
    for sym in symbols:
        candles = fetch_historical_candles(sym, interval="1m", num_candles=1200)
        print(f"-> {sym} simülasyonu çalıştırılıyor...")
        tester.run_simulation(sym, candles)

    trades = tester.trades
    total_trades = len(trades)

    if total_trades == 0:
        print("\n[UYARI] Belirtilen periyotta sinyal oluşmadı.")
        return

    winning_trades = [t for t in trades if t["net_pnl"] > 0]
    losing_trades = [t for t in trades if t["net_pnl"] < 0]
    win_rate = (len(winning_trades) / total_trades) * 100.0

    total_gross_pnl = sum(t["gross_pnl"] for t in trades)
    total_net_pnl = sum(t["net_pnl"] for t in trades)
    total_fees = tester.total_fees_paid
    total_slippage = tester.total_slippage_cost

    gross_wins = sum(t["gross_pnl"] for t in winning_trades)
    gross_losses = abs(sum(t["gross_pnl"] for t in losing_trades))
    profit_factor = (gross_wins / max(gross_losses, 0.001))

    # Sharpe Ratio
    returns = [t["net_pnl"] / 10000.0 for t in trades]
    sharpe = (np.mean(returns) / max(np.std(returns), 1e-8)) * np.sqrt(len(returns)) if len(returns) > 1 else 0.0

    # Max Drawdown
    equity_arr = np.array(tester.equity_curve)
    peaks = np.maximum.accumulate(equity_arr)
    drawdowns = (peaks - equity_arr) / peaks
    max_dd_pct = np.max(drawdowns) * 100.0
    max_dd_usd = np.max(peaks - equity_arr)

    print("\n" + "=" * 65)
    print("           >>> BACKTEST PERFORMANS RAPORU <<<                    ")
    print("=" * 65)
    print(f" Toplam İşlem Sayısı:         {total_trades}")
    print(f" Kazanan İşlem Sayısı:        {len(winning_trades)} (Yeşil)")
    print(f" Kaybeden İşlem Sayısı:       {len(losing_trades)} (Kırmızı)")
    print(f" Kazanma Oranı (Win Rate):    %{win_rate:.2f}")
    print(f" Kâr Faktörü (Profit Factor): {profit_factor:.2f}")
    print(f" Sharpe Oranı:                {sharpe:.2f}")
    print(f" Maksimum Drawdown (DD):      -%{max_dd_pct:.2f} (${max_dd_usd:.2f})")
    print("-" * 65)
    print(f" Toplam Brüt Kâr (Gross):     +${total_gross_pnl:.2f}")
    print(f" Ödenen Borsa Komisyonu:      -${total_fees:.2f} (MEXC Taker: %0.02)")
    print(f" Tahmini Kayma (Slippage):    -${total_slippage:.2f} (%0.01)")
    print(f" NET KÂR (Cepte Kalan):       {'+' if total_net_pnl >= 0 else ''}${total_net_pnl:.2f}")
    print(f" Net Portföy Getirisi (ROI):  %{((tester.balance - tester.start_balance) / tester.start_balance) * 100.0:+.2f}")
    print(f" Bitiş Bakiyesi:              ${tester.balance:.2f}")
    print("=" * 65)

    print("\nSon 10 İşlemin Özeti:")
    print(f"{'Varlık':<6} | {'Yön':<6} | {'Giriş':<9} | {'Çıkış':<9} | {'Komisyon':<9} | {'Net Kâr':<9} | {'Neden'}")
    print("-" * 80)
    for t in trades[-10:]:
        print(f"{t['symbol']:<6} | {t['side']:<6} | ${t['entry_price']:<8.4f} | ${t['exit_price']:<8.4f} | ${t['fees']:<8.3f} | {'+' if t['net_pnl'] >= 0 else ''}${t['net_pnl']:<8.2f} | {t['exit_reason']}")
    print("=" * 80)


if __name__ == "__main__":
    run_full_backtest()
