"""
Massive Historical Data Downloader for AI Training
Downloads M1, M5, and H1 data for EURUSD, BTCUSD, GOLD from MT5.
Target: ~1GB of training data.
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger("MassiveDownloader")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')

OUTPUT_DIR = "database/training_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SYMBOLS = ["EURUSD", "BTCUSD", "GOLD"]

TIMEFRAMES = {
    "M1":  (mt5.TIMEFRAME_M1,  730),   # 2 years of 1-min data (~750k candles per symbol)
    "M5":  (mt5.TIMEFRAME_M5,  730),   # 2 years of 5-min data (~150k candles per symbol)
    "H1":  (mt5.TIMEFRAME_H1, 1825),   # 5 years of hourly data (~30k candles per symbol)
}


def download_symbol_timeframe(symbol: str, tf_name: str, tf_const: int, days: int) -> pd.DataFrame:
    """Downloads historical candle data for a symbol/timeframe combo."""
    logger.info(f"📥 Downloading {symbol} {tf_name} — {days} days...")
    
    if not mt5.symbol_select(symbol, True):
        logger.error(f"❌ Cannot select {symbol} in Market Watch. Skipping.")
        return pd.DataFrame()
    
    # Estimate number of bars based on timeframe
    bars_per_day = {"M1": 1440, "M5": 288, "H1": 24}
    max_bars = days * bars_per_day.get(tf_name, 24)
    max_bars = min(max_bars, 500000)  # MT5 limit
    
    # Use copy_rates_pos (counts back from latest bar) — works even on weekends
    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, max_bars)
    
    if rates is None or len(rates) == 0:
        logger.error(f"❌ No data for {symbol} {tf_name}. Error: {mt5.last_error()}")
        return pd.DataFrame()
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'time': 'timestamp', 'real_volume': 'volume'}, inplace=True)
    df.drop(columns=['tick_volume', 'spread'], inplace=True, errors='ignore')
    
    # Add symbol column for multi-symbol training
    df['symbol'] = symbol
    
    logger.info(f"✅ {symbol} {tf_name}: {len(df):,} candles downloaded ({df['timestamp'].min()} → {df['timestamp'].max()})")
    return df


def add_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds 25+ technical indicators for AI training."""
    if df.empty:
        return df
    
    c = df['close']
    h = df['high']
    l = df['low']
    v = df['volume']
    
    # ---- Momentum Indicators ----
    # RSI(14)
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # RSI(7) — faster
    avg_gain7 = gain.rolling(7).mean()
    avg_loss7 = -delta.clip(upper=0).rolling(7).mean()
    rs7 = avg_gain7 / (avg_loss7 + 1e-10)
    df['rsi_7'] = 100 - (100 / (1 + rs7))
    
    # MACD(12, 26, 9)
    ema12 = c.ewm(span=12).mean()
    ema26 = c.ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # Stochastic RSI
    rsi = df['rsi_14']
    rsi_min = rsi.rolling(14).min()
    rsi_max = rsi.rolling(14).max()
    df['stoch_rsi'] = (rsi - rsi_min) / (rsi_max - rsi_min + 1e-10)
    
    # ---- Trend Indicators ----
    df['ema_9'] = c.ewm(span=9).mean()
    df['ema_21'] = c.ewm(span=21).mean()
    df['ema_50'] = c.ewm(span=50).mean()
    df['sma_200'] = c.rolling(200).mean()
    
    # EMA cross signals (normalized distance)
    df['ema_cross_9_21'] = (df['ema_9'] - df['ema_21']) / (c + 1e-10)
    df['ema_cross_21_50'] = (df['ema_21'] - df['ema_50']) / (c + 1e-10)
    df['price_vs_sma200'] = (c - df['sma_200']) / (c + 1e-10)
    
    # ADX(14) — Average Directional Index
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    plus_dm = ((h - h.shift()).clip(lower=0)).where((h - h.shift()) > (l.shift() - l), 0)
    minus_dm = ((l.shift() - l).clip(lower=0)).where((l.shift() - l) > (h - h.shift()), 0)
    atr14 = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / (atr14 + 1e-10))
    minus_di = 100 * (minus_dm.rolling(14).mean() / (atr14 + 1e-10))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
    df['adx_14'] = dx.rolling(14).mean()
    
    # ---- Volatility Indicators ----
    df['atr_14'] = atr14
    df['atr_7'] = tr.rolling(7).mean()
    
    # Bollinger Bands
    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    df['bb_upper'] = sma20 + 2 * std20
    df['bb_lower'] = sma20 - 2 * std20
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (sma20 + 1e-10)
    df['bb_position'] = (c - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-10)
    
    # ---- Volume Indicators ----
    df['log_return'] = np.log(c / c.shift(1))
    df['vol_sma_ratio'] = v / (v.rolling(20).mean() + 1e-10)
    
    # OBV (On Balance Volume)
    obv = (np.sign(delta) * v).cumsum()
    df['obv_norm'] = (obv - obv.rolling(50).mean()) / (obv.rolling(50).std() + 1e-10)
    
    # ---- Price Action ----
    df['candle_body'] = (c - df['open']) / (h - l + 1e-10)
    df['upper_wick'] = (h - pd.concat([c, df['open']], axis=1).max(axis=1)) / (h - l + 1e-10)
    df['lower_wick'] = (pd.concat([c, df['open']], axis=1).min(axis=1) - l) / (h - l + 1e-10)
    
    # Drop the intermediate EMA/SMA columns (we keep the normalized versions)
    df.drop(columns=['ema_9', 'ema_21', 'ema_50', 'sma_200', 'bb_upper', 'bb_lower'], inplace=True, errors='ignore')
    
    return df


def run_massive_download():
    """Main entry point for the massive data collection."""
    if not mt5.initialize():
        logger.error(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return
    
    logger.info(f"✅ MT5 Connected: {mt5.version()}")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Timeframes: {list(TIMEFRAMES.keys())}")
    logger.info("=" * 60)
    
    total_candles = 0
    total_files = 0
    
    for symbol in SYMBOLS:
        for tf_name, (tf_const, days) in TIMEFRAMES.items():
            df = download_symbol_timeframe(symbol, tf_name, tf_const, days)
            
            if df.empty:
                continue
            
            # Apply feature engineering
            logger.info(f"🔧 Engineering 25+ features for {symbol} {tf_name}...")
            df = add_advanced_features(df)
            
            # Drop NaN rows from windowed calculations
            before = len(df)
            df.dropna(inplace=True)
            logger.info(f"   Dropped {before - len(df)} NaN rows → {len(df):,} clean rows")
            
            # Save
            filename = f"{symbol}_{tf_name}_engineered.csv"
            filepath = os.path.join(OUTPUT_DIR, filename)
            df.to_csv(filepath, index=False)
            
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            logger.info(f"💾 Saved: {filepath} ({size_mb:.1f} MB, {len(df):,} rows)")
            
            total_candles += len(df)
            total_files += 1
    
    mt5.shutdown()
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"📊 DOWNLOAD COMPLETE")
    logger.info(f"   Total files: {total_files}")
    logger.info(f"   Total candles: {total_candles:,}")
    
    # Calculate total size
    total_bytes = sum(
        os.path.getsize(os.path.join(OUTPUT_DIR, f))
        for f in os.listdir(OUTPUT_DIR)
        if f.endswith('.csv')
    )
    logger.info(f"   Total disk size: {total_bytes / (1024*1024):.1f} MB")


if __name__ == "__main__":
    run_massive_download()
