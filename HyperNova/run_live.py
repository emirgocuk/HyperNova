import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import requests
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime
from termcolor import cprint
import traceback

# --- CORE MODULES ---
from core.paper_account import PaperAccount
from core.web_server import TradingDashboard
from core.data_logger import TradeDataLogger

# --- CONFIGURATION (FULL 4-FACTOR MICROSTRUCTURE QUANT SCALPER - 1000:1) ---
SYMBOLS = ["SOL", "HYPE", "BTC"]
TIMEFRAME = "1m"
LEVERAGE = 1000.0  # 1000:1 Leverage
MAX_POSITIONS = 3

# Fast Scalping Parameters ($0.80 Margin per $800 Notional):
LOT_SIZE_USD_NOTIONAL = 800.0    # $800 Notional per trade (Only $0.80 Margin at 1000:1!)
BASE_PROFIT_TRIGGER = 0.0004     # +0.04% Fiyat Hareketi = +$0.32 (+%40 ROE) -> İz Sürmeyi Başlat
FAST_SL_PCT = 0.0025             # -0.25% Sıkı Stop-Loss
STAGNANT_TIMEOUT_SECONDS = 150   # Sadece kâra GEÇEMEYEN (ölü) pozisyonlar 2.5 dk sonra kapatılır!

data_logger = TradeDataLogger()
paper_account = PaperAccount(start_balance=10000.0, leverage=LEVERAGE)
web_dashboard = TradingDashboard(paper_account, port=5000)
web_dashboard.start_background()

# Fast In-Memory Caches
candles_cache = {}
last_candle_fetch = {}
microstructure_cache = {}
last_micro_fetch = {}
meta_context_cache = {}
last_meta_fetch = 0


def fetch_live_1m_candles(coin: str, limit: int = 40) -> pd.DataFrame:
    """
    Fetches real-time 1-minute OHLCV candles from HyperLiquid.
    """
    now = time.time()
    if coin in candles_cache and (now - last_candle_fetch.get(coin, 0)) < 0.8:
        return candles_cache[coin]

    url = "https://api.hyperliquid.xyz/info"
    end_ms = int(now * 1000)
    start_ms = end_ms - (limit * 60 * 1000)

    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": "1m",
            "startTime": start_ms,
            "endTime": end_ms
        }
    }

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=1.8)
        data = resp.json()
        candles = data if isinstance(data, list) else data.get('candles', [])

        if candles:
            df = pd.DataFrame(candles)
            df['t'] = pd.to_datetime(df['t'], unit='ms')
            df.set_index('t', inplace=True)
            df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'}, inplace=True)
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = df[col].astype(float)
            df.sort_index(inplace=True)

            candles_cache[coin] = df.tail(limit)
            last_candle_fetch[coin] = now
            return candles_cache[coin]
    except Exception:
        pass

    return candles_cache.get(coin, pd.DataFrame())


def fetch_all_meta_contexts() -> dict:
    """
    Fetches global Funding Rates, Open Interest, 24h Volume, and Premium Basis for all coins.
    """
    global meta_context_cache, last_meta_fetch
    now = time.time()
    if meta_context_cache and (now - last_meta_fetch) < 2.0:
        return meta_context_cache

    url = "https://api.hyperliquid.xyz/info"
    try:
        resp = requests.post(url, json={"type": "metaAndAssetCtxs"}, headers={"Content-Type": "application/json"}, timeout=2.0)
        data = resp.json()
        universe = data[0].get('universe', [])
        ctxs = data[1] if len(data) > 1 else []

        res = {}
        for asset, ctx in zip(universe, ctxs):
            name = asset.get('name')
            if name in SYMBOLS:
                mark_px = float(ctx.get('markPx', 0) or 0)
                oracle_px = float(ctx.get('oraclePx', 0) or mark_px or 1.0)
                funding = float(ctx.get('funding', 0) or 0) * 100 * 365 * 24  # Annualized APR %
                oi_usd = float(ctx.get('openInterest', 0) or 0) * mark_px / 1e6 # $ Millions
                vol_usd = float(ctx.get('dayNtlVlm', 0) or 0) / 1e6             # $ Millions
                basis_pct = ((mark_px - oracle_px) / oracle_px) * 100 if oracle_px > 0 else 0.0

                res[name] = {
                    'funding_apr': round(funding, 2),
                    'oi_millions': round(oi_usd, 2),
                    'vol_millions': round(vol_usd, 2),
                    'basis_pct': round(basis_pct, 4)
                }
        meta_context_cache = res
        last_meta_fetch = now
        return res
    except Exception:
        return meta_context_cache


def fetch_full_microstructure(coin: str) -> dict:
    """
    Combines ALL 4 Free Data Feeds into a Composite Microstructure Alpha Score:
    1. L2 Orderbook Imbalance (OIR)
    2. Funding Rate (APR %)
    3. Open Interest & Volume Flow
    4. Basis Premium (Mark vs Oracle Delta)
    """
    now = time.time()
    if coin in microstructure_cache and (now - last_micro_fetch.get(coin, 0)) < 0.8:
        return microstructure_cache[coin]

    # 1. Fetch L2 Book
    url = "https://api.hyperliquid.xyz/info"
    oir = 0.0
    bid_vol = 0.0
    ask_vol = 0.0
    try:
        resp = requests.post(url, json={"type": "l2Book", "coin": coin}, headers={"Content-Type": "application/json"}, timeout=1.5)
        data = resp.json()
        levels = data.get('levels', [[], []])
        bid_vol = sum(float(b['sz']) for b in levels[0][:5]) if len(levels) > 0 and levels[0] else 0.0
        ask_vol = sum(float(a['sz']) for a in levels[1][:5]) if len(levels) > 1 and levels[1] else 0.0
        total_vol = bid_vol + ask_vol
        oir = (bid_vol - ask_vol) / total_vol if total_vol > 0 else 0.0
    except Exception:
        pass

    # 2. Fetch Meta Context (Funding, OI, Basis)
    meta = fetch_all_meta_contexts().get(coin, {
        'funding_apr': 0.0, 'oi_millions': 0.0, 'vol_millions': 0.0, 'basis_pct': 0.0
    })

    funding_apr = meta.get('funding_apr', 0.0)
    basis_pct = meta.get('basis_pct', 0.0)

    # 3. Calculate Composite Alpha Score [-100 (Strong Bear) to +100 (Strong Bull)]
    # OIR contributes 60 points, Basis contributes 25 points, Funding Bias contributes 15 points
    oir_score = oir * 60.0
    basis_score = np.clip(basis_pct * 1000.0, -25.0, 25.0)
    funding_bias = -np.clip(funding_apr / 2.0, -15.0, 15.0)  # Extreme positive funding means Longs overleveraged -> Short bias
    composite_alpha = oir_score + basis_score + funding_bias

    res = {
        'bid_vol': bid_vol,
        'ask_vol': ask_vol,
        'oir': round(oir, 3),
        'oir_pct': round(oir * 100, 1),
        'funding_apr': funding_apr,
        'oi_millions': meta.get('oi_millions', 0.0),
        'vol_millions': meta.get('vol_millions', 0.0),
        'basis_pct': basis_pct,
        'composite_alpha': round(composite_alpha, 1),
        'timestamp': now
    }
    microstructure_cache[coin] = res
    last_micro_fetch[coin] = now
    return res


def run_full_microstructure_quant_engine():
    margin_val = LOT_SIZE_USD_NOTIONAL / LEVERAGE
    cprint("="*70, "cyan")
    cprint("🌟 HYPERNOVA: 4 FAKTÖRLÜ KURUMSAL MİKROYAPI SCALPER ENGINE", "yellow", attrs=['bold'])
    cprint(f"🪙 Varlıklar: SOL, HYPE, BTC | Teminat: ${margin_val:.2f} (Hacim: ${LOT_SIZE_USD_NOTIONAL:.0f})", "green")
    cprint("📊 Beslenen 4 Canlı Veri Boyutu:", "cyan")
    cprint("   1️⃣ L2 Orderbook Derinliği & Dengesizliği (OIR)", "magenta")
    cprint("   2️⃣ Gerçek Zamanlı Fonlama Oranları (Funding APR %)", "magenta")
    cprint("   3️⃣ Açık Pozisyon Büyüklüğü (Open Interest $M) & Hacim Akışı", "magenta")
    cprint("   4️⃣ Vadeli/Spot Prim Farkı (Basis Premium Mark vs Oracle)", "magenta")
    cprint("="*70, "cyan")

    loop_count = 0

    while True:
        loop_count += 1
        current_prices = {}

        for coin in SYMBOLS:
            try:
                df = fetch_live_1m_candles(coin, limit=40)
                micro = fetch_full_microstructure(coin)
                web_dashboard.update_microstructure(coin, micro)

                if df.empty or len(df) < 15:
                    continue

                current_price = float(df['Close'].iloc[-1])
                current_prices[coin] = current_price

                # Fast 1m Oscillators
                bb = ta.bbands(df['Close'], length=12, std=1.8)
                stoch_rsi = ta.stochrsi(df['Close'], length=12, rsi_length=12, k=3, d=3)

                bbl = float(bb.iloc[-1, 0]) if bb is not None else current_price * 0.9985
                bbm = float(bb.iloc[-1, 1]) if bb is not None else current_price
                bbu = float(bb.iloc[-1, 2]) if bb is not None else current_price * 1.0015
                stoch_k = float(stoch_rsi.iloc[-1, 0]) if stoch_rsi is not None else 50.0

                alpha_score = micro.get('composite_alpha', 0.0)
                oir_pct = micro.get('oir_pct', 0.0)
                funding = micro.get('funding_apr', 0.0)
                basis_pct = micro.get('basis_pct', 0.0)

                # Log High-Frequency Market State for AI Training
                if loop_count % 3 == 0:
                    data_logger.log_market_state(
                        symbol=coin, price=current_price, bbl=bbl, bbm=bbm, bbu=bbu,
                        stoch_k=stoch_k, oir=oir_pct/100.0, funding_apr=funding,
                        basis_pct=basis_pct, composite_alpha=alpha_score
                    )

                # =========================================================
                # 4 FAKTÖRLÜ BİRLEŞİK SİNYAL ÜRETİMİ
                # =========================================================
                signal = None
                reason_str = ""

                # LONG: Dip/Aşırı Satım + Güçlü Alıcı Baskısı (Alpha > 0)
                if (current_price <= bbl or stoch_k < 26):
                    if alpha_score >= -10.0:  # Tahtada ve fonlamada ağır bir çöküş baskısı yoksa
                        signal = "LONG"
                        reason_str = f"Dip + Alpha:{alpha_score:+.0f} (OIR:{oir_pct:+.0f}% | Fund:{funding:.1f}%)"

                # SHORT: Tepe/Aşırı Alım + Satıcı Baskısı (Alpha < 0)
                elif (current_price >= bbu or stoch_k > 74):
                    if alpha_score <= 10.0:   # Tahtada aşırı bir alım duvarı yoksa
                        signal = "SHORT"
                        reason_str = f"Tepe + Alpha:{alpha_score:+.0f} (OIR:{oir_pct:+.0f}% | Fund:{funding:.1f}%)"

                # -----------------------------------------------------
                # 1. KESKİN TEPE KİLİTLEME & ÇIKIŞ YÖNETİMİ
                # -----------------------------------------------------
                open_positions = [p for p in paper_account.positions if p['symbol'] == coin]

                for pos in list(open_positions):
                    entry_price = pos['entry_price']
                    side = pos['side']
                    size_coin = pos['size_coin']

                    # PnL & ROE
                    if side == 'LONG':
                        pnl_pct = (current_price - entry_price) / entry_price
                        pnl_usd = (current_price - entry_price) * size_coin
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price
                        pnl_usd = (entry_price - current_price) * size_coin

                    req_margin = pos.get('required_margin', LOT_SIZE_USD_NOTIONAL / LEVERAGE)
                    roe_pct = (pnl_usd / max(req_margin, 0.01)) * 100.0

                    if 'peak_pnl_pct' not in pos:
                        pos['peak_pnl_pct'] = max(0.0, pnl_pct)
                    else:
                        pos['peak_pnl_pct'] = max(pos['peak_pnl_pct'], pnl_pct)

                    entry_time = datetime.fromisoformat(pos['time'])
                    dur_secs = (datetime.now() - entry_time).total_seconds()

                    should_close = False
                    exit_reason = ""

                    # A. TEPE TÜKENİŞ ÇIKIŞI (Exhaustion Pin Exit)
                    if roe_pct >= 40.0:
                        if side == 'LONG' and (current_price >= bbu * 0.9997 or stoch_k >= 85 or alpha_score < -30):
                            should_close = True
                            exit_reason = f"🎯 TEPE TÜKENİŞ KÂR KİLİT (+${pnl_usd:.2f} / +{roe_pct:.1f}% ROE | Alpha:{alpha_score:+.0f})"
                        elif side == 'SHORT' and (current_price <= bbl * 1.0003 or stoch_k <= 15 or alpha_score > 30):
                            should_close = True
                            exit_reason = f"🎯 DİP TÜKENİŞ KÂR KİLİT (+${pnl_usd:.2f} / +{roe_pct:.1f}% ROE | Alpha:{alpha_score:+.0f})"

                    # B. KADEMELİ SIKILAŞAN MİKRO-TRAILING
                    if not should_close and pos['peak_pnl_pct'] >= BASE_PROFIT_TRIGGER:
                        if pos['peak_pnl_pct'] >= 0.0008:
                            trailing_tolerance = 0.00005
                        elif pos['peak_pnl_pct'] >= 0.0005:
                            trailing_tolerance = 0.00009
                        else:
                            trailing_tolerance = 0.00015

                        if pnl_pct <= (pos['peak_pnl_pct'] - trailing_tolerance):
                            should_close = True
                            peak_roe = (pos['peak_pnl_pct'] * (entry_price * size_coin) / req_margin) * 100
                            exit_reason = f"🚀 SIKI İZ SÜREN TEPE KÂRI (+${pnl_usd:.2f} / +{roe_pct:.1f}% ROE | Zirve: +{peak_roe:.0f}%)"

                    # C. TERS SİNYAL DÖNÜŞÜ
                    elif not should_close and signal and signal != side:
                        should_close = True
                        exit_reason = f"🔄 TERS SİNYAL DÖNÜŞÜ ({side} -> {signal})"

                    # D. ÖLÜ POZİSYON ZAMAN AŞIMI
                    elif not should_close and dur_secs >= STAGNANT_TIMEOUT_SECONDS and pnl_pct < 0.0003:
                        should_close = True
                        exit_reason = f"⏱️ YATAY/ÖLÜ POZİSYON ÇIKIŞI ({pnl_pct*100:+.2f}%)"

                    # E. HARD STOP LOSS (-0.25%)
                    elif not should_close and pnl_pct <= -FAST_SL_PCT:
                        should_close = True
                        exit_reason = f"🛑 Sıkı Stop-Loss ({pnl_pct*100:.2f}%)"

                    if should_close:
                        cprint(f"\n💰 {coin} KAPATILDI: {exit_reason}", "green" if pnl_usd >= 0 else "yellow", attrs=['bold'])
                        web_dashboard.add_log(f"💰 {coin} {exit_reason}")
                        paper_account.execute_trade(coin, ('SHORT' if side == 'LONG' else 'LONG'), size_coin, current_price)
                        web_dashboard.notify_position_change('close', {'symbol': coin, 'pnl': exit_reason})

                        # Save Action-Reward Outcome to Machine Learning Database
                        data_logger.log_trade_experience({
                            'symbol': coin,
                            'side': side,
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'size_coin': size_coin,
                            'notional_usd': LOT_SIZE_USD_NOTIONAL,
                            'required_margin': req_margin,
                            'leverage': LEVERAGE,
                            'pnl_usd': pnl_usd,
                            'roe_pct': roe_pct,
                            'price_change_pct': pnl_pct * 100.0,
                            'duration_seconds': dur_secs,
                            'exit_reason': exit_reason,
                            'entry_stoch_k': pos.get('entry_stoch_k', 50.0),
                            'entry_oir': pos.get('entry_oir', 0.0),
                            'entry_alpha': pos.get('entry_alpha', 0.0),
                            'entry_time': pos.get('time', str(datetime.now()))
                        })

                # -----------------------------------------------------
                # 2. ANLIK YENİ GİRİŞLER (4-FAKTÖR TEYİTLİ)
                # -----------------------------------------------------
                has_pos = any(p['symbol'] == coin for p in paper_account.positions)

                if not has_pos and signal and len(paper_account.positions) < MAX_POSITIONS:
                    size_coin = round(LOT_SIZE_USD_NOTIONAL / current_price, 4)
                    sl_price = current_price * (1 - FAST_SL_PCT) if signal == "LONG" else current_price * (1 + FAST_SL_PCT)
                    tp_price = current_price * (1 + 0.0010) if signal == "LONG" else current_price * (1 - 0.0010)

                    cprint(f"\n⚡ {coin} 1000:1 {signal} GİRİŞ @ ${current_price:.4f} ({reason_str})", "yellow", attrs=['bold'])
                    cprint(f"   Hacim: ${LOT_SIZE_USD_NOTIONAL:.0f} | Teminat: ${LOT_SIZE_USD_NOTIONAL/LEVERAGE:.2f} | Alpha: {alpha_score:+.0f}", "cyan")

                    executed = paper_account.execute_trade(coin, signal, size_coin, current_price, sl_price=sl_price, tp_price=tp_price)
                    if executed:
                        # Attach ML metadata to new position
                        for p in paper_account.positions:
                            if p['symbol'] == coin:
                                p['entry_stoch_k'] = stoch_k
                                p['entry_oir'] = oir_pct / 100.0
                                p['entry_alpha'] = alpha_score

                        web_dashboard.add_log(f"⚡ {coin} {signal} ${LOT_SIZE_USD_NOTIONAL:.0f} (1000:1) | Alpha: {alpha_score:+.0f} @ {current_price:.4f}")
                        web_dashboard.notify_position_change('open', {'symbol': coin, 'side': signal, 'size': size_coin, 'price': current_price})

                # UI Update
                web_dashboard.update_price(coin, current_price)
                web_dashboard.update_status(f"{coin} ${current_price:.2f} | Alpha:{alpha_score:+.0f} | OIR:{oir_pct:+.0f}% | K:{stoch_k:.0f}")

            except Exception as e:
                pass

        # -----------------------------------------------------
        # 3. CANLI PORTFÖY & MARGİN DURUMU
        # -----------------------------------------------------
        if current_prices and loop_count % 3 == 0:
            stats = paper_account.get_portfolio_status(current_prices)
            pnl_color = "green" if stats['unrealized_pnl'] >= 0 else "red"
            equity_color = "green" if stats['equity'] >= paper_account.start_balance else "red"

            print(f"\r⚡ Bakiye: ${stats['balance']:.2f} | Varlık: ${stats['equity']:.2f} | Kâr: ${stats['unrealized_pnl']:+.2f} | Teminat: ${stats['used_margin']:.2f} | Poz: {stats['open_positions']}", end="", flush=True)

        time.sleep(0.7)


if __name__ == "__main__":
    try:
        run_full_microstructure_quant_engine()
    except KeyboardInterrupt:
        print("\nScalper durduruldu.")
    except Exception as e:
        traceback.print_exc()
        input("Cikis...")
