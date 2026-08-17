import sys
import os
import math
import time
import json
import glob
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import requests
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to sys.path
hypernova_dir = str(Path(__file__).resolve().parent.parent)
if hypernova_dir not in sys.path:
    sys.path.insert(0, hypernova_dir)

from core.paper_account import PaperAccount
from core.data_logger import TradeDataLogger, CENTRAL_LAKE_DIR
from tools.train_from_phone_data import train_central_federated_model, WEIGHTS_DIR
from ai_engine.primo_indicators import PrimoIndicatorEngine
from ai_engine.primo_nlp import PrimoNLPFeatureExtractor
from ai_engine.primo_agent import PrimoPPOAgent

# Initialize Primo Academic AI Engines (Botunac et al. 2025)
primo_engine = PrimoIndicatorEngine()
primo_nlp = PrimoNLPFeatureExtractor()
primo_agent = PrimoPPOAgent(state_dim=23)
primo_telemetry_cache: Dict[str, Any] = {}

# Setup Logging
logger = logging.getLogger("HyperNovaUnified")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


# Modern FastAPI Lifespan Handler (Replaces deprecated @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(scalper_worker_loop())
    yield
    worker_task.cancel()


# FastAPI App
app = FastAPI(
    title="HyperNova 1000:1 Unified Engine API",
    description="High-Frequency Microstructure Scalper, AI Training Hub & Mobile Telemetry Gateway",
    version="3.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# ENGINE CONFIGURATION & GLOBAL STATE
# =====================================================================
class EngineSettings(BaseModel):
    symbols: List[str] = ["SOL", "HYPE", "BTC"]
    leverage: float = 200.0          # Max 200x Leverage (Institutional / MEXC standard)
    max_positions: int = 3
    lot_size_usd_notional: float = 800.0  # $800 Notional uses $4.00 Margin at 200x
    base_profit_trigger: float = 0.0012   # +0.12% Fiyat Hareketi = +$0.96 (3x Round-Trip Komisyon Eşiği!)
    fast_sl_pct: float = 0.0035           # -0.35% Stop-Loss (Gürültüye takılmaz)
    stagnant_timeout_seconds: int = 360   # 6 Dakika sabır (Erken komisyon yakmayı engeller)
    exchange_preset: str = "MEXC"         # MEXC, HYPERLIQUID, BINANCE, ZERO_FEE
    maker_fee_pct: float = 0.0000         # 0.00% MEXC Maker
    taker_fee_pct: float = 0.0002         # 0.02% MEXC Taker ($0.16 per $800 order)
    slippage_pct: float = 0.0001          # 0.01% Realistic Execution Slippage
    is_live_trading: bool = False         # False = Paper, True = Live CEX/Hyperliquid

config = EngineSettings()

data_logger = TradeDataLogger()
paper_account = PaperAccount(
    start_balance=10000.0,
    leverage=config.leverage,
    exchange_preset=config.exchange_preset,
    maker_fee_pct=config.maker_fee_pct,
    taker_fee_pct=config.taker_fee_pct,
    slippage_pct=config.slippage_pct
)

# Fast Caches
candles_cache: Dict[str, list] = {}
last_candle_fetch: Dict[str, float] = {}
microstructure_cache: Dict[str, dict] = {}
last_micro_fetch: Dict[str, float] = {}
meta_context_cache: Dict[str, dict] = {}
last_meta_fetch: float = 0.0
current_prices: Dict[str, float] = {}

# Engine Run State
is_engine_running = True
is_training_active = False
recent_logs: List[Dict[str, Any]] = []
MAX_LOG_HISTORY = 100

def add_log(message: str, log_type: str = "INFO"):
    global recent_logs
    entry = {
        "id": int(time.time() * 1000),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "message": message,
        "type": log_type
    }
    recent_logs.insert(0, entry)
    recent_logs = recent_logs[:MAX_LOG_HISTORY]
    logger.info(f"[{log_type}] {message}")

add_log("🚀 HyperNova Unified Backend Başlatıldı.", "SYSTEM")


# =====================================================================
# WEBSOCKET CONNECTION MANAGER
# =====================================================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

ws_manager = ConnectionManager()


# =====================================================================
# PURE PYTHON QUANT INDICATORS & MICROSTRUCTURE FEEDS
# =====================================================================
def calc_bollinger_bands(prices: list, length: int = 12, std_mult: float = 1.8):
    if len(prices) < length:
        p = prices[-1] if prices else 100.0
        return p * 0.9985, p, p * 1.0015
    subset = prices[-length:]
    mean = sum(subset) / length
    variance = sum((x - mean) ** 2 for x in subset) / length
    std = math.sqrt(variance)
    return mean - (std_mult * std), mean, mean + (std_mult * std)


def calc_stoch_rsi(prices: list, length: int = 12, rsi_length: int = 12) -> float:
    if len(prices) < (length + rsi_length):
        return 50.0

    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))

    rsis = []
    for i in range(rsi_length, len(gains) + 1):
        avg_gain = sum(gains[i - rsi_length:i]) / rsi_length
        avg_loss = sum(losses[i - rsi_length:i]) / rsi_length
        if avg_loss == 0:
            rsis.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsis.append(100.0 - (100.0 / (1.0 + rs)))

    if len(rsis) < length:
        return 50.0

    sub_rsis = rsis[-length:]
    min_r, max_r = min(sub_rsis), max(sub_rsis)
    if max_r == min_r:
        return 50.0

    return ((rsis[-1] - min_r) / (max_r - min_r)) * 100.0


def fetch_live_1m_candles(coin: str, limit: int = 40) -> list:
    now = time.time()
    if coin in candles_cache and (now - last_candle_fetch.get(coin, 0)) < 0.8:
        return candles_cache[coin]

    url = "https://api.hyperliquid.xyz/info"
    end_ms = int(now * 1000)
    start_ms = end_ms - (limit * 60 * 1000)
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": coin, "interval": "1m", "startTime": start_ms, "endTime": end_ms}
    }

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=1.8)
        data = resp.json()
        candles = data if isinstance(data, list) else data.get('candles', [])
        if candles:
            close_prices = [float(c['c']) for c in candles]
            candles_cache[coin] = close_prices[-limit:]
            last_candle_fetch[coin] = now
            return candles_cache[coin]
    except Exception:
        pass

    return candles_cache.get(coin, [])


def fetch_all_meta_contexts() -> dict:
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
            if name in config.symbols:
                mark_px = float(ctx.get('markPx', 0) or 0)
                oracle_px = float(ctx.get('oraclePx', 0) or mark_px or 1.0)
                funding = float(ctx.get('funding', 0) or 0) * 100 * 365 * 24
                oi_usd = float(ctx.get('openInterest', 0) or 0) * mark_px / 1e6
                vol_usd = float(ctx.get('dayNtlVlm', 0) or 0) / 1e6
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
    now = time.time()
    if coin in microstructure_cache and (now - last_micro_fetch.get(coin, 0)) < 0.8:
        return microstructure_cache[coin]

    url = "https://api.hyperliquid.xyz/info"
    oir, bid_vol, ask_vol = 0.0, 0.0, 0.0
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

    meta = fetch_all_meta_contexts().get(coin, {
        'funding_apr': 0.0, 'oi_millions': 0.0, 'vol_millions': 0.0, 'basis_pct': 0.0
    })

    funding_apr = meta.get('funding_apr', 0.0)
    basis_pct = meta.get('basis_pct', 0.0)

    oir_score = oir * 60.0
    basis_score = max(-25.0, min(25.0, basis_pct * 1000.0))
    funding_bias = -max(-15.0, min(15.0, funding_apr / 2.0))
    composite_alpha = oir_score + basis_score + funding_bias

    res = {
        'bid_vol': round(bid_vol, 2),
        'ask_vol': round(ask_vol, 2),
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


# =====================================================================
# ASYNC SCALPER ENGINE WORKER
# =====================================================================
async def scalper_worker_loop():
    global is_engine_running, current_prices
    loop_count = 0

    while True:
        try:
            if is_engine_running:
                loop_count += 1
                for coin in config.symbols:
                    prices = fetch_live_1m_candles(coin, limit=40)
                    micro = fetch_full_microstructure(coin)

                    if not prices or len(prices) < 15:
                        continue

                    current_price = float(prices[-1])
                    current_prices[coin] = current_price

                    # --- Primo Academic 6 Indicators ---
                    primo_tech_dict = primo_engine.compute_vector(prices, prices, prices, current_price)
                    primo_tech_vec = primo_engine.get_feature_array(prices, prices, prices, current_price)

                    # --- PrimoGPT 7 NLP Features (Fast In-Memory Cache) ---
                    primo_nlp_dict = primo_nlp.get_cached_features(coin)
                    primo_nlp_vec = primo_nlp.get_feature_array(coin)

                    bbl, bbm, bbu = primo_tech_dict['bb_lower'], primo_tech_dict['bb_middle'], primo_tech_dict['bb_upper']
                    rsi_14 = primo_tech_dict['rsi_14']
                    macd_hist = primo_tech_dict['macd_hist']
                    cci_20 = primo_tech_dict['cci_20']
                    dx_14 = primo_tech_dict['dx_14']

                    alpha_score = micro.get('composite_alpha', 0.0)
                    oir_pct = micro.get('oir_pct', 0.0)
                    funding = micro.get('funding_apr', 0.0)
                    basis_pct = micro.get('basis_pct', 0.0)

                    # --- Primo State Vector Construction (23-dim) ---
                    open_pos_coin = next((p for p in paper_account.positions if p['symbol'] == coin), None)
                    start_bal = getattr(paper_account, 'start_balance', 10000.0)
                    norm_bal = paper_account.balance / max(start_bal, 1.0)
                    norm_pos = ((open_pos_coin['size_coin'] * current_price / config.lot_size_usd_notional) * (1.0 if open_pos_coin['side'] == 'LONG' else -1.0)) if open_pos_coin else 0.0
                    unrealized_pnl_pct = 0.0
                    price_ratio = 0.0
                    if open_pos_coin and open_pos_coin['entry_price'] > 0:
                        ep = open_pos_coin['entry_price']
                        unrealized_pnl_pct = ((current_price - ep) / ep) * (1.0 if open_pos_coin['side'] == 'LONG' else -1.0)
                        price_ratio = (current_price / ep) - 1.0

                    base_vec = np.array([norm_bal, norm_pos, unrealized_pnl_pct, price_ratio], dtype=np.float32)
                    micro_vec = np.array([oir_pct / 100.0, funding / 100.0, micro.get('oi_millions', 0.0) / 100.0, basis_pct], dtype=np.float32)
                    state_vec_23 = np.concatenate([base_vec, primo_tech_vec, primo_nlp_vec, micro_vec])

                    # --- Primo PPO Decision Engine (Continuous Action [-1.0, 1.0]) ---
                    action_scalar, action_meta = primo_agent.predict(state_vec_23)

                    primo_telemetry_cache[coin] = {
                        "action_scalar": round(action_scalar, 3),
                        "action_label": action_meta.get("action_label", "HOLD_FLAT"),
                        "confidence": round(action_meta.get("confidence", 0.5), 2),
                        "indicators": {
                            "sma_30": round(primo_tech_dict['sma_30'], 2),
                            "sma_60": round(primo_tech_dict['sma_60'], 2),
                            "macd_hist": round(macd_hist, 4),
                            "rsi_14": round(rsi_14, 1),
                            "cci_20": round(cci_20, 1),
                            "dx_14": round(dx_14, 1),
                            "bb_lower": round(bbl, 2),
                            "bb_upper": round(bbu, 2)
                        },
                        "nlp": {
                            "sentiment": primo_nlp_dict.get("sentiment", 0),
                            "trend_direction": primo_nlp_dict.get("trend_direction", 0),
                            "price_impact": primo_nlp_dict.get("price_impact", 0),
                            "investor_confidence": primo_nlp_dict.get("investor_confidence", 0),
                            "risk_profile_change": primo_nlp_dict.get("risk_profile_change", 0)
                        },
                        "latency_ms": action_meta.get("latency_ms", 0.5)
                    }

                    # Telemetry logging
                    if loop_count % 3 == 0:
                        data_logger.log_market_state(
                            symbol=coin, price=current_price, bbl=bbl, bbm=bbm, bbu=bbu,
                            stoch_k=rsi_14, oir=oir_pct/100.0, funding_apr=funding,
                            basis_pct=basis_pct, composite_alpha=alpha_score
                        )

                    # Signal generation (Sniper Mode: High Conviction PPO + L2 Micro Alpha Gate)
                    signal = None
                    reason_str = ""
                    if (action_scalar >= 0.40 or (current_price <= bbl and rsi_14 < 30)) and alpha_score >= 12.0:
                        signal = "LONG"
                        reason_str = f"PPO {action_meta['action_label']} ({action_scalar:+.2f}) + Alpha:{alpha_score:+.0f} (RSI:{rsi_14:.0f} | OIR:{oir_pct:+.0f}%)"
                    elif (action_scalar <= -0.40 or (current_price >= bbu and rsi_14 > 70)) and alpha_score <= -12.0:
                        signal = "SHORT"
                        reason_str = f"PPO {action_meta['action_label']} ({action_scalar:+.2f}) + Alpha:{alpha_score:+.0f} (RSI:{rsi_14:.0f} | OIR:{oir_pct:+.0f}%)"

                    # 1. Exit & Trailing Management (Commission-Killer & Wave Rider)
                    open_positions = [p for p in paper_account.positions if p['symbol'] == coin]
                    for pos in list(open_positions):
                        entry_price = pos['entry_price']
                        side = pos['side']
                        size_coin = pos['size_coin']

                        if side == 'LONG':
                            pnl_pct = (current_price - entry_price) / entry_price
                            pnl_usd = (current_price - entry_price) * size_coin
                        else:
                            pnl_pct = (entry_price - current_price) / entry_price
                            pnl_usd = (entry_price - current_price) * size_coin

                        req_margin = pos.get('required_margin', config.lot_size_usd_notional / config.leverage)
                        roe_pct = (pnl_usd / max(req_margin, 0.01)) * 100.0

                        if 'peak_pnl_pct' not in pos:
                            pos['peak_pnl_pct'] = max(0.0, pnl_pct)
                        else:
                            pos['peak_pnl_pct'] = max(pos['peak_pnl_pct'], pnl_pct)

                        entry_time = datetime.fromisoformat(pos['time'])
                        dur_secs = (datetime.now() - entry_time).total_seconds()

                        should_close = False
                        exit_reason = ""

                        # 1. Exhaustion Take Profit (+60% ROE or indicator extremes)
                        if roe_pct >= 30.0:
                            if side == 'LONG' and (current_price >= bbu * 0.9997 or rsi_14 >= 82 or alpha_score < -35):
                                should_close = True
                                exit_reason = f"🎯 TEPE TÜKENİŞ KÂR KİLİT (+${pnl_usd:.2f} / +{roe_pct:.1f}% ROE | Alpha:{alpha_score:+.0f})"
                            elif side == 'SHORT' and (current_price <= bbl * 1.0003 or rsi_14 <= 18 or alpha_score > 35):
                                should_close = True
                                exit_reason = f"🎯 DİP TÜKENİŞ KÂR KİLİT (+${pnl_usd:.2f} / +{roe_pct:.1f}% ROE | Alpha:{alpha_score:+.0f})"

                        # 2. Dynamic Trailing (Waves >= +0.12% / +24% ROE)
                        if not should_close and pos['peak_pnl_pct'] >= config.base_profit_trigger:
                            tol = 0.00030 if pos['peak_pnl_pct'] >= 0.0030 else (0.00020 if pos['peak_pnl_pct'] >= 0.0018 else 0.00015)
                            if pnl_pct <= (pos['peak_pnl_pct'] - tol):
                                should_close = True
                                exit_reason = f"🚀 SIKI İZ SÜREN DALGA KÂRI (+${pnl_usd:.2f} / +{roe_pct:.1f}% ROE)"

                        # 3. Komisyon Koruma Kalkanı (Break-Even + Fees: +0.08% ulaşıldıktan sonra asla zarara düşmez)
                        elif not should_close and pos['peak_pnl_pct'] >= 0.0008 and pnl_pct <= 0.00045:
                            should_close = True
                            exit_reason = f"🛡️ KOMİSYON KORUMA KALKANI (+${pnl_usd:.2f} / Komisyon Kurtarıldı)"

                        # 4. Signal Flip (Only on strong opposite signal)
                        elif not should_close and signal and signal != side:
                            should_close = True
                            exit_reason = f"🔄 TERS SİNYAL DÖNÜŞÜ ({side} -> {signal})"

                        # 5. Stagnant Exit (6 Dakika sonra hâlâ ölü ise)
                        elif not should_close and dur_secs >= config.stagnant_timeout_seconds and pnl_pct < 0.0004:
                            should_close = True
                            exit_reason = f"⏱️ YATAY/ÖLÜ POZİSYON ÇIKIŞI ({pnl_pct*100:+.2f}%)"

                        # 6. Hard Stop Loss
                        elif not should_close and pnl_pct <= -config.fast_sl_pct:
                            should_close = True
                            exit_reason = f"🛑 Sıkı Stop-Loss ({pnl_pct*100:.2f}%)"

                        if should_close:
                            add_log(f"💰 {coin} KAPATILDI: {exit_reason}", "PROFIT" if pnl_usd >= 0 else "LOSS")
                            paper_account.execute_trade(coin, ('SHORT' if side == 'LONG' else 'LONG'), size_coin, current_price)

                            data_logger.log_trade_experience({
                                'symbol': coin,
                                'side': side,
                                'entry_price': entry_price,
                                'exit_price': current_price,
                                'size_coin': size_coin,
                                'notional_usd': config.lot_size_usd_notional,
                                'required_margin': req_margin,
                                'leverage': config.leverage,
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

                    # 2. Entries
                    has_pos = any(p['symbol'] == coin for p in paper_account.positions)
                    if not has_pos and signal and len(paper_account.positions) < config.max_positions:
                        size_coin = round(config.lot_size_usd_notional / current_price, 4)
                        sl_px = current_price * (1 - config.fast_sl_pct) if signal == "LONG" else current_price * (1 + config.fast_sl_pct)
                        tp_px = current_price * (1 + 0.0010) if signal == "LONG" else current_price * (1 - 0.0010)

                        executed = paper_account.execute_trade(coin, signal, size_coin, current_price, sl_price=sl_px, tp_price=tp_px)
                        if executed:
                            for p in paper_account.positions:
                                if p['symbol'] == coin:
                                    p['entry_stoch_k'] = rsi_14
                                    p['entry_oir'] = oir_pct / 100.0
                                    p['entry_alpha'] = alpha_score

                            add_log(f"⚡ {coin} 1000:1 {signal} @ ${current_price:.4f} ({reason_str})", "ORDER")

                # Broadcast live state via WebSocket
                if ws_manager.active_connections:
                    stats = paper_account.get_portfolio_status(current_prices)
                    ws_payload = {
                        "type": "TICK",
                        "timestamp": datetime.now().isoformat(),
                        "prices": current_prices,
                        "microstructure": microstructure_cache,
                        "primo": primo_telemetry_cache,
                        "stats": stats,
                        "is_running": is_engine_running,
                        "open_positions_count": len(paper_account.positions),
                        "logs": recent_logs[:10]
                    }
                    await ws_manager.broadcast(ws_payload)

        except Exception as e:
            logger.error(f"Engine Loop Error: {e}")

        await asyncio.sleep(0.8)


# =====================================================================
# WEBSOCKET ENDPOINTS
# =====================================================================
@app.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Initial snapshot
        stats = paper_account.get_portfolio_status(current_prices)
        await websocket.send_json({
            "type": "INIT",
            "stats": stats,
            "prices": current_prices,
            "microstructure": microstructure_cache,
            "primo": primo_telemetry_cache,
            "is_running": is_engine_running,
            "logs": recent_logs
        })
        while True:
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# =====================================================================
# REST API ENDPOINTS
# =====================================================================
@app.get("/api/v1/health")
@app.get("/api/v1/status")
def get_system_status():
    stats = paper_account.get_portfolio_status(current_prices)
    total_realized_pnl = sum(t.get('net_pnl', t.get('pnl', 0)) for t in paper_account.trade_history)

    return {
        "status": "ONLINE" if is_engine_running else "PAUSED",
        "is_bot_active": is_engine_running,
        "is_training": is_training_active,
        "balance": stats['balance'],
        "equity": stats['equity'],
        "unrealized_pnl": stats['unrealized_pnl'],
        "unrealized_gross_pnl": stats.get('unrealized_gross_pnl', stats['unrealized_pnl']),
        "realized_pnl": round(total_realized_pnl, 2),
        "total_fees_paid": stats.get('total_fees_paid', 0.0),
        "total_slippage_cost": stats.get('total_slippage_cost', 0.0),
        "exchange_preset": stats.get('exchange_preset', 'MEXC'),
        "maker_fee_pct": stats.get('maker_fee_pct', 0.0),
        "taker_fee_pct": stats.get('taker_fee_pct', 0.02),
        "slippage_pct": stats.get('slippage_pct', 0.01),
        "used_margin": stats.get('used_margin', 0.0),
        "free_margin": stats.get('free_margin', stats['equity']),
        "margin_level_pct": stats.get('margin_level_pct', 9999.0),
        "leverage": config.leverage,
        "open_positions": stats['open_positions'],
        "prices": current_prices,
        "microstructure": microstructure_cache,
        "primo": primo_telemetry_cache,
        "device_id": data_logger.device_id,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/primo")
def get_primo_telemetry():
    """
    Returns Primo Academic Engine real-time telemetry (6 Tech Indicators, 7 NLP Features, PPO Actions).
    """
    return {
        "status": "active",
        "model": "PrimoRL PPO + PrimoGPT (Botunac et al., 2025)",
        "telemetry": primo_telemetry_cache,
        "timestamp": datetime.now().isoformat()
    }


class NewsInput(BaseModel):
    symbol: str
    headlines: List[str]


@app.post("/api/v1/primo/news")
def submit_primo_news(news: NewsInput):
    """
    Endpoint for submitting live crypto headlines to PrimoGPT NLP feature extractor.
    """
    feats = primo_nlp.extract_features_from_text(news.symbol, news.headlines)
    return {
        "symbol": news.symbol.upper(),
        "extracted_features": feats,
        "status": "updated"
    }


@app.get("/api/v1/positions")
def get_positions():
    positions = []
    for pos in paper_account.positions:
        sym = pos['symbol']
        entry_px = float(pos['entry_price'])
        cur_px = float(current_prices.get(sym, entry_px))
        size_coin = float(pos['size_coin'])
        notional_usd = size_coin * cur_px
        req_margin = float(pos.get('required_margin', notional_usd / config.leverage))

        if pos['side'] == 'LONG':
            price_change_pct = (cur_px - entry_px) / entry_px if entry_px > 0 else 0.0
            pnl_usd = (cur_px - entry_px) * size_coin
        else:
            price_change_pct = (entry_px - cur_px) / entry_px if entry_px > 0 else 0.0
            pnl_usd = (entry_px - cur_px) * size_coin

        roe_pct = (pnl_usd / max(req_margin, 0.01)) * 100.0

        try:
            entry_time = datetime.fromisoformat(pos['time'])
            dur_secs = int((datetime.now() - entry_time).total_seconds())
            mins, secs = dur_secs // 60, dur_secs % 60
            dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        except Exception:
            dur_str = "0m"

        positions.append({
            'symbol': sym,
            'side': pos['side'],
            'size_coin': size_coin,
            'notional_usd': round(notional_usd, 2),
            'required_margin': round(req_margin, 2),
            'leverage': int(config.leverage),
            'entry_price': entry_px,
            'current_price': cur_px,
            'price_change_pct': round(price_change_pct * 100, 2),
            'pnl_usd': round(pnl_usd, 2),
            'roe_pct': round(roe_pct, 1),
            'sl_price': pos.get('sl_price'),
            'tp_price': pos.get('tp_price'),
            'duration_str': dur_str,
            'entry_time': pos['time']
        })
    return positions


@app.get("/api/v1/history")
def get_history():
    history = paper_account.trade_history[-50:]
    history.reverse()
    return history


@app.get("/api/v1/stats")
def get_stats():
    history = paper_account.trade_history
    if not history:
        return {
            'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
            'win_rate': 0, 'total_pnl': 0, 'avg_trade_pnl': 0, 'best_trade': 0, 'worst_trade': 0
        }
    total_trades = len(history)
    winning_trades = sum(1 for t in history if t.get('pnl', 0) > 0)
    losing_trades = sum(1 for t in history if t.get('pnl', 0) < 0)
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    pnls = [t.get('pnl', 0) for t in history]
    total_pnl = sum(pnls)

    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 2),
        'total_pnl': round(total_pnl, 2),
        'avg_trade_pnl': round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
        'best_trade': round(max(pnls), 2) if pnls else 0,
        'worst_trade': round(min(pnls), 2) if pnls else 0
    }


# =====================================================================
# ENGINE CONTROL COMMANDS (Start, Stop, Panic)
# =====================================================================
@app.post("/api/v1/control/start")
def start_engine():
    global is_engine_running
    is_engine_running = True
    add_log("🟢 Motor Başlatıldı. 1000:1 Al-Sat Aktif.", "CONTROL")
    return {"status": "success", "is_bot_active": True}


@app.post("/api/v1/control/stop")
def stop_engine():
    global is_engine_running
    is_engine_running = False
    add_log("⏸️ Motor Duraklatıldı.", "CONTROL")
    return {"status": "success", "is_bot_active": False}


@app.post("/api/v1/control/panic")
def panic_close_all():
    global is_engine_running
    is_engine_running = False
    closed_count = 0

    for pos in list(paper_account.positions):
        sym = pos['symbol']
        cur_px = current_prices.get(sym, pos['entry_price'])
        paper_account.execute_trade(sym, ('SHORT' if pos['side'] == 'LONG' else 'LONG'), pos['size_coin'], cur_px)
        closed_count += 1

    add_log(f"🚨 ACİL DURUM (PANIC): {closed_count} açık pozisyon anında piyasa fiyatından kapatıldı ve bot durduruldu.", "PANIC")
    return {"status": "success", "closed_positions": closed_count, "is_bot_active": False}


@app.get("/api/v1/config")
def get_config():
    return config.model_dump() if hasattr(config, "model_dump") else config.dict()


@app.post("/api/v1/config")
def update_config(new_cfg: EngineSettings):
    global config
    config = new_cfg
    paper_account.leverage = config.leverage
    if config.exchange_preset:
        paper_account.set_exchange_preset(config.exchange_preset)
    paper_account.maker_fee_pct = config.maker_fee_pct
    paper_account.taker_fee_pct = config.taker_fee_pct
    paper_account.slippage_pct = config.slippage_pct
    add_log(f"⚙️ Borsa & Konfigürasyon Güncellendi: Borsa={config.exchange_preset}, Kaldıraç={config.leverage}x, Taker Fee=%{config.taker_fee_pct*100:.3f}", "CONFIG")
    cfg_data = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    return {"status": "success", "config": cfg_data}


@app.get("/api/v1/logs")
def get_logs():
    return recent_logs


# =====================================================================
# MOBILE TELEMETRY & AI TRAINING HUB ENDPOINTS
# =====================================================================
@app.get("/api/v1/telemetry/export")
def export_telemetry():
    return data_logger.export_telemetry_payload()


@app.post("/api/v1/telemetry/upload")
def upload_telemetry(payload: Dict[str, Any]):
    try:
        res = TradeDataLogger.save_incoming_telemetry(payload)
        trades_cnt = payload.get('trades_count', len(payload.get('trades', [])))
        dev_id = payload.get('device_id', 'Unknown')
        add_log(f"📥 Telemetri Alındı: {dev_id} ({trades_cnt} işlem)", "TELEMETRY")
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/training/status")
def get_training_status():
    json_files = glob.glob(os.path.join(CENTRAL_LAKE_DIR, "*.json"))
    nodes_info = {}
    total_crowdsourced_trades = 0

    for jf in json_files:
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                payload = json.load(f)
                dev_id = payload.get('device_id', 'Unknown')
                cnt = payload.get('trades_count', len(payload.get('trades', [])))
                total_crowdsourced_trades += cnt
                nodes_info[dev_id] = {
                    'device_id': dev_id,
                    'trades_count': nodes_info.get(dev_id, {}).get('trades_count', 0) + cnt,
                    'last_sync': payload.get('exported_at', str(datetime.now()))
                }
        except Exception:
            pass

    local_stats = data_logger.get_summary_stats()

    rules_file = os.path.join(WEIGHTS_DIR, "edge_learned_rules.json")
    current_rules = None
    if os.path.exists(rules_file):
        try:
            with open(rules_file, 'r') as f:
                current_rules = json.load(f)
        except Exception:
            pass

    return {
        'total_nodes_connected': max(1, len(nodes_info)),
        'nodes_list': list(nodes_info.values()),
        'total_crowdsourced_trades': total_crowdsourced_trades + local_stats.get('total_trades_logged', 0),
        'local_node_stats': local_stats,
        'current_rules': current_rules,
        'data_lake_files_count': len(json_files),
        'is_training': is_training_active
    }


@app.post("/api/v1/training/start")
def trigger_training(background_tasks: BackgroundTasks):
    global is_training_active
    if is_training_active:
        return {"status": "warning", "message": "Eğitim zaten devam ediyor."}

    def train_task():
        global is_training_active
        is_training_active = True
        try:
            add_log("🧠 Federe Yapay Zeka Eğitimi Başlatıldı...", "TRAINING")
            res = train_central_federated_model()
            sample_count = res.get('rules', {}).get('total_training_samples', 0)
            add_log(f"✅ AI Eğitimi Tamamlandı! ({sample_count} tecrübe analiz edildi)", "TRAINING")
        except Exception as e:
            add_log(f"❌ AI Eğitimi Hatası: {e}", "ERROR")
        finally:
            is_training_active = False

    background_tasks.add_task(train_task)
    return {"status": "started", "message": "Model eğitimi arka planda başlatıldı."}


@app.get("/api/v1/ai/rules")
def get_ai_rules():
    rules_file = os.path.join(WEIGHTS_DIR, "edge_learned_rules.json")
    if os.path.exists(rules_file):
        try:
            with open(rules_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {
        "status": "empty",
        "message": "Henüz eğitilmiş kural bulunamadı. Lütfen önce AI eğitimini başlatın."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
