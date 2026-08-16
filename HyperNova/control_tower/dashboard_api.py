from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import asyncio
import threading
from datetime import datetime
import MetaTrader5 as mt5
import os
import logging

import sys
from pathlib import Path

# Add the parent directory (HyperNova) to sys.path so modules like execution_engine can be found
hypernova_dir = str(Path(__file__).resolve().parent.parent)
if hypernova_dir not in sys.path:
    sys.path.insert(0, hypernova_dir)

# Configure logging
logger = logging.getLogger("DashboardAPI")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Initialize FastAPI application
app = FastAPI(
    title="The Transparent Strategist API",
    description="Full Control Tower for AI Trading Engine",
    version="2.0.0"
)

# Apply CORS for Next.js Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================= GLOBAL STATE =======================
# Risk Profiles
RISK_PROFILES = {
    "aggressive": {
        "name": "Aggressive",
        "lot_size": 0.10,
        "max_drawdown_pct": 0.05,
        "grid_levels": 7,
        "sl_pct": 0.4,   # 0.4% stop loss
        "tp_pct": 0.8,   # 0.8% take profit
        "description": "Higher risk, wide SL/TP."
    },
    "balanced": {
        "name": "Balanced",
        "lot_size": 0.05,
        "max_drawdown_pct": 0.03,
        "grid_levels": 5,
        "sl_pct": 0.2,   # 0.2% stop loss
        "tp_pct": 0.4,   # 0.4% take profit
        "description": "Moderate risk. Standard SL/TP."
    },
    "safe": {
        "name": "Safe",
        "lot_size": 0.01,
        "max_drawdown_pct": 0.015,
        "grid_levels": 3,
        "sl_pct": 0.1,   # 0.1% stop loss
        "tp_pct": 0.2,   # 0.2% take profit
        "description": "Minimal risk, tight SL/TP."
    }
}

# Engine Configuration (persisted in memory, updated via UI)
ENGINE_CONFIG = {
    "active_profile": "balanced",
    "lot_size": 0.05,
    "max_drawdown_pct": 0.03,
    "grid_levels": 5,
    "sl_pct": 0.2,
    "tp_pct": 0.4,
    "data_fetch_days": 180,
    "training_epochs": 10,
    "symbol": "EURUSD",
    "timeframe": "M5"
}

# XAI Log Buffer (in-memory ring buffer)
XAI_LOGS = []
MAX_LOGS = 100

IS_TRAINING = False
IS_FETCHING_DATA = False

# MT5 Connection
MT5_CONNECTED = False
try:
    MT5_CONNECTED = mt5.initialize()
    if MT5_CONNECTED:
        logger.info(f"✅ MT5 Connected at startup: {mt5.version()}")
    else:
        logger.warning(f"MT5 not available at startup: {mt5.last_error()}")
except Exception as e:
    logger.warning(f"MT5 initialization error: {e}")

# ======================= HELPERS =======================
def add_xai_log(action: str, reason: str, confidence: float = 0.0, symbol: str = "EURUSD"):
    """Adds a log entry to the XAI log buffer."""
    global XAI_LOGS
    log_entry = {
        "id": int(time.time() * 1000),
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "action": action,
        "confidence": confidence,
        "xai_reason": reason
    }
    XAI_LOGS.insert(0, log_entry)
    XAI_LOGS = XAI_LOGS[:MAX_LOGS]

def get_mt5_account_info():
    """Fetches real account info from the running MT5 terminal."""
    global MT5_CONNECTED
    if not MT5_CONNECTED:
        MT5_CONNECTED = mt5.initialize()
        if not MT5_CONNECTED:
            return None
    account_info = mt5.account_info()
    if account_info is None:
        MT5_CONNECTED = False
        return None
    return account_info._asdict()

def run_training_in_background():
    """Triggers the trainer in a background thread."""
    global IS_TRAINING
    IS_TRAINING = True
    add_xai_log("TRAINING_START", f"CNN-LSTM training started. Epochs: {ENGINE_CONFIG['training_epochs']}, Data: {ENGINE_CONFIG['data_fetch_days']}d, Profile: {ENGINE_CONFIG['active_profile']}")
    try:
        from ai_engine.trainer import run_training_session
        csv_path = "database/historical/xm_eurusd_m5_180days_ready.csv"
        run_training_session(csv_path)
        add_xai_log("TRAINING_COMPLETE", "Model weights updated successfully. New regime detection patterns learned.", confidence=1.0)
    except Exception as e:
        add_xai_log("TRAINING_ERROR", f"Training failed: {str(e)}")
        logger.error(f"Training error: {e}")
    finally:
        IS_TRAINING = False

def run_data_fetch_in_background(days: int):
    """Fetches fresh data from MT5 and re-processes it."""
    global IS_FETCHING_DATA
    IS_FETCHING_DATA = True
    add_xai_log("DATA_FETCH", f"Downloading {days} days of {ENGINE_CONFIG['symbol']} {ENGINE_CONFIG['timeframe']} data from XM...")
    try:
        from data_layer.mt5_ingestor import MT5Ingestor
        import MetaTrader5 as mt5_lib
        
        ingestor = MT5Ingestor()
        df = ingestor.fetch_historical_data(
            symbol=ENGINE_CONFIG['symbol'],
            timeframe=mt5_lib.TIMEFRAME_M5,
            days=days
        )
        if not df.empty:
            filename = f"xm_{ENGINE_CONFIG['symbol'].lower()}_m5_{days}days.csv"
            ingestor.save_to_csv(df, filename)
            
            # Now process it
            from data_layer.historical_pipeline import process_historical_csv_for_training
            process_historical_csv_for_training(f"database/historical/{filename}")
            
            add_xai_log("DATA_READY", f"✅ {len(df)} candles processed. AI-ready dataset generated.", confidence=1.0)
        else:
            add_xai_log("DATA_ERROR", "No data returned from MT5. Is the terminal open?")
        
        ingestor.shutdown()
    except Exception as e:
        add_xai_log("DATA_ERROR", f"Data fetch failed: {str(e)}")
        logger.error(f"Data fetch error: {e}")
    finally:
        IS_FETCHING_DATA = False

# Add startup log
add_xai_log("SYSTEM_BOOT", f"Control Tower API v2.0 initialized. MT5: {'Connected' if MT5_CONNECTED else 'Offline'}. Profile: {ENGINE_CONFIG['active_profile'].title()}")

# ======================= PYDANTIC MODELS =======================
class ProfileUpdate(BaseModel):
    profile: str  # "aggressive" | "balanced" | "safe"

class ConfigUpdate(BaseModel):
    lot_size: float | None = None
    training_epochs: int | None = None
    grid_levels: int | None = None
    symbol: str | None = None

class DataFetchRequest(BaseModel):
    days: int = 180

# ======================= API ENDPOINTS =======================

@app.get("/")
async def root():
    return {"message": "The Transparent Strategist Control Tower API v2.0"}

@app.get("/api/v1/health")
async def get_health():
    """Returns the real-time status of the MT5 account and engine."""
    acc = get_mt5_account_info()
    
    from ai_engine.trainer import TRAINING_STATUS
    
    health_data = {
        "status": "ONLINE" if acc else "OFFLINE",
        "circuit_breaker_active": False,
        "daily_drawdown_pct": 0,
        "max_allowed_drawdown_pct": ENGINE_CONFIG["max_drawdown_pct"],
        "is_training": TRAINING_STATUS["is_active"],
        "is_fetching_data": IS_FETCHING_DATA,
        "is_bot_active": BOT_ENGINE.is_active if 'BOT_ENGINE' in globals() else False,
        "training_stats": TRAINING_STATUS if TRAINING_STATUS["is_active"] else None
    }
    
    if acc:
        drawdown = 1.0 - (acc['equity'] / acc['balance']) if acc['balance'] > 0 else 0
        health_data.update({
            "circuit_breaker_active": drawdown > ENGINE_CONFIG["max_drawdown_pct"],
            "daily_drawdown_pct": round(drawdown, 4),
            "equity": acc['equity'],
            "balance": acc['balance'],
            "currency": acc['currency'],
            "profit": acc.get('profit', 0)
        })
        
    return health_data

@app.get("/api/v1/config")
async def get_config():
    """Returns the current engine configuration."""
    return {
        "config": ENGINE_CONFIG,
        "profiles": RISK_PROFILES,
        "active_profile_details": RISK_PROFILES[ENGINE_CONFIG["active_profile"]]
    }

@app.post("/api/v1/config/profile")
async def set_profile(update: ProfileUpdate):
    """Switches the active risk profile."""
    profile_key = update.profile.lower()
    if profile_key not in RISK_PROFILES:
        raise HTTPException(status_code=400, detail=f"Invalid profile: {profile_key}")
    
    profile = RISK_PROFILES[profile_key]
    ENGINE_CONFIG["active_profile"] = profile_key
    ENGINE_CONFIG["lot_size"] = profile["lot_size"]
    ENGINE_CONFIG["max_drawdown_pct"] = profile["max_drawdown_pct"]
    ENGINE_CONFIG["grid_levels"] = profile["grid_levels"]
    ENGINE_CONFIG["sl_pct"] = profile["sl_pct"]
    ENGINE_CONFIG["tp_pct"] = profile["tp_pct"]
    
    add_xai_log("CONFIG_CHANGE", f"Risk profile → {profile['name']}. Lot: {profile['lot_size']}, SL: {profile['sl_pct']}%, TP: {profile['tp_pct']}%, Grid: {profile['grid_levels']}")
    
    return {"status": "success", "config": ENGINE_CONFIG}

@app.post("/api/v1/config/update")
async def update_config(update: ConfigUpdate):
    """Updates specific engine config values."""
    if update.symbol is not None and update.symbol != ENGINE_CONFIG["symbol"]:
        if BOT_ENGINE.is_active:
            raise HTTPException(status_code=400, detail="Cannot change symbol while bot is active. Please turn it off first.")
        ENGINE_CONFIG["symbol"] = update.symbol
        BOT_ENGINE.set_symbol(update.symbol)

    if update.lot_size is not None:
        ENGINE_CONFIG["lot_size"] = update.lot_size
    if update.training_epochs is not None:
        ENGINE_CONFIG["training_epochs"] = update.training_epochs
    if update.grid_levels is not None:
        ENGINE_CONFIG["grid_levels"] = update.grid_levels
    
    add_xai_log("CONFIG_UPDATE", f"Engine settings updated: {update.model_dump(exclude_none=True)}")
    return {"status": "success", "config": ENGINE_CONFIG}

@app.post("/api/v1/train/start")
async def start_training(background_tasks: BackgroundTasks):
    """Triggers the real CNN-LSTM training loop."""
    if IS_TRAINING:
        return {"status": "error", "message": "Training is already in progress"}
    
    background_tasks.add_task(run_training_in_background)
    return {"status": "success", "message": "Training started in background"}

@app.post("/api/v1/data/fetch")
async def fetch_data(req: DataFetchRequest, background_tasks: BackgroundTasks):
    """Triggers a fresh data fetch from MT5."""
    if IS_FETCHING_DATA:
        return {"status": "error", "message": "Data fetch already in progress"}
    if not MT5_CONNECTED:
        return {"status": "error", "message": "MT5 terminal not connected"}
    
    ENGINE_CONFIG["data_fetch_days"] = req.days
    background_tasks.add_task(run_data_fetch_in_background, req.days)
    return {"status": "success", "message": f"Fetching {req.days} days of data in background"}

@app.get("/api/v1/xai/logs")
async def get_xai_logs(limit: int = 50):
    """Returns XAI reasoning logs from the in-memory ring buffer."""
    return {"logs": XAI_LOGS[:limit]}

# ======================= BOT EXECUTION ENDPOINTS =======================

from execution_engine.mt5_executor import MT5Executor
from ai_engine.live_inference import get_inference_engine
BOT_ENGINE = MT5Executor(symbol=ENGINE_CONFIG["symbol"])
ACTIVE_TRADING_TASK = None
AI_ENGINE = None  # Lazy-loaded inference engine

CONFIDENCE_THRESHOLD = 0.35  # Minimum confidence to execute a trade

async def live_trading_loop():
    """Runs continuously while BOT_ENGINE is active. AI monitors market, Grid executes trades."""
    global AI_ENGINE
    if AI_ENGINE is None:
        AI_ENGINE = get_inference_engine()
    
    add_xai_log("ENGINE_SYNC", "🧠 AI-Protected Hybrid Grid Loop Started.", confidence=0.85)
    last_error = None
    last_signal = None
    last_grid_evaluation = 0
    
    MAX_CONCURRENT_POSITIONS = 10
    GRID_EVAL_COOLDOWN = 60  # Wait minimum 60 seconds before assessing grid status again
    
    while BOT_ENGINE.is_active:
        try:
            positions = BOT_ENGINE.get_open_positions()
            current_time = time.time()
            
            # 1. Run Real AI Inference (The Overseer)
            ai_result = AI_ENGINE.get_signal(ENGINE_CONFIG['symbol'])
            signal = ai_result['signal']
            confidence = ai_result['confidence']
            probs = ai_result.get('probabilities', {})
            
            prob_str = f"S={probs.get('SIDEWAYS',0):.0%} U={probs.get('UPTREND',0):.0%} D={probs.get('DOWNTREND',0):.0%}"
            
            # --- THE CIRCUIT BREAKER (AI Protection) ---
            if signal in ("UPTREND", "DOWNTREND") and confidence > 0.60:
                if last_signal != signal + "_DANGER":
                    add_xai_log("AI_SHIELD", f"🚨 DANGER: Strong {signal} detected! ({confidence:.1%}). Pausing Grid. Checking for casualties.", confidence=confidence)
                    last_signal = signal + "_DANGER"
                    
                # Execute emergency exit if holding dangerous positions
                if positions:
                    BOT_ENGINE.emergency_close_positions(signal)
            
            # --- THE YIELDING GRID (Money Printer) ---
            # If AI is confident it's Sideways, OR trend confidence is weak
            elif signal == "SIDEWAYS" or confidence <= 0.40:
                
                if current_time - last_grid_evaluation > GRID_EVAL_COOLDOWN:
                    last_grid_evaluation = current_time
                    open_trades_count = len(positions)
                    
                    if open_trades_count < MAX_CONCURRENT_POSITIONS:
                        if last_signal != "GRID_ACTIVE":
                            add_xai_log("GRID_ACTIVE", f"🟢 Market is stable. Deploying Fixed-Range Grid Traps. {prob_str}", confidence=probs.get('SIDEWAYS',0))
                            last_signal = "GRID_ACTIVE"
                        
                        # We need the current price to set the center of our grid limits
                        tick = mt5.symbol_info_tick(BOT_ENGINE.real_symbol)
                        if tick:
                            current_price = (tick.ask + tick.bid) / 2
                            BOT_ENGINE.execute_grid_logic(current_price, ENGINE_CONFIG)
                    
                    else:
                        total_pnl = sum(p['unrealized_pnl'] for p in positions)
                        add_xai_log("GRID_WARM", f"⏸️ Grid is full ({open_trades_count}/{MAX_CONCURRENT_POSITIONS}). Waiting for TP hits. PNL: ${total_pnl:.2f}", confidence=0.5)
            
            else:
                # Moderate trend, not dangerous enough to trigger breaker, not sideways enough for grid
                if last_signal != signal + "_MODERATE":
                    add_xai_log("AI_HOLD", f"🟡 Moderate {signal} ({confidence:.1%}). Waiting for clearer regime. {prob_str}", confidence=confidence)
                    last_signal = signal + "_MODERATE"

            await asyncio.sleep(5) # Tick rate
            
        except Exception as e:
            logger.error(f"Live trading loop error: {e}")
            add_xai_log("SYSTEM_ERROR", f"Loop exception: {str(e)}")
            await asyncio.sleep(10)

@app.post("/api/v1/bot/toggle")
async def toggle_bot():
    """Starts or stops the live execution engine."""
    global ACTIVE_TRADING_TASK
    if BOT_ENGINE.is_active:
        BOT_ENGINE.deactivate_bot()
        if ACTIVE_TRADING_TASK:
            ACTIVE_TRADING_TASK.cancel()
            ACTIVE_TRADING_TASK = None
        add_xai_log("BOT_STOPPED", "Live Execution Engine disarmed. Systems safely halted.", confidence=1.0)
    else:
        # Update symbol before starting
        BOT_ENGINE.symbol = ENGINE_CONFIG["symbol"]
        BOT_ENGINE.activate_bot()
        add_xai_log("BOT_STARTED", f"Live Execution Engine armed for {ENGINE_CONFIG['symbol']} on {ENGINE_CONFIG['active_profile']} profile.", confidence=1.0)
        
        # Start the trading loop
        ACTIVE_TRADING_TASK = asyncio.create_task(live_trading_loop())
    
    return {"status": "success", "is_active": BOT_ENGINE.is_active}

@app.get("/api/v1/bot/positions")
async def get_positions():
    """Returns all active open positions."""
    if not BOT_ENGINE.connected:
        return {"status": "error", "message": "MT5 Not Connected", "positions": []}
        
    positions = BOT_ENGINE.get_open_positions()
    return {"status": "success", "positions": positions}

@app.get("/api/v1/bot/pnl")
async def get_pnl():
    """Returns realized PNL for today and unrealized PNL for open trades."""
    if not BOT_ENGINE.connected:
        return {"status": "error", "message": "MT5 Not Connected"}
        
    realized_pnl = BOT_ENGINE.get_realized_pnl(days=1)
    
    positions = BOT_ENGINE.get_open_positions()
    unrealized_pnl = round(sum(p['unrealized_pnl'] for p in positions), 2)
    
    return {
        "status": "success", 
        "realized_pnl": realized_pnl, 
        "unrealized_pnl": unrealized_pnl
    }

# Update health endpoint internally inside the file replacement block to add bot status
health_function_override = """
@app.get("/api/v1/health")
async def get_health():
    acc = get_mt5_account_info()
    from ai_engine.trainer import TRAINING_STATUS
    health_data = {
        "status": "ONLINE" if acc else "OFFLINE",
        "circuit_breaker_active": False,
        "daily_drawdown_pct": 0,
        "max_allowed_drawdown_pct": ENGINE_CONFIG["max_drawdown_pct"],
        "is_training": TRAINING_STATUS["is_active"],
        "is_fetching_data": IS_FETCHING_DATA,
        "is_bot_active": BOT_ENGINE.is_active,
        "training_stats": TRAINING_STATUS if TRAINING_STATUS["is_active"] else None
    }
    if acc:
        drawdown = 1.0 - (acc['equity'] / acc['balance']) if acc['balance'] > 0 else 0
        health_data.update({
            "circuit_breaker_active": drawdown > ENGINE_CONFIG["max_drawdown_pct"],
            "daily_drawdown_pct": round(drawdown, 4),
            "equity": acc['equity'],
            "balance": acc['balance'],
            "currency": acc['currency'],
            "profit": acc.get('profit', 0)
        })
    return health_data
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
