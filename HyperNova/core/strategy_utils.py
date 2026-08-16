
import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_market_cipher_signals(df: pd.DataFrame):
    """
    Consolidated Market Cipher Logic (WaveTrend + StochRSI + MFI + VWAP).
    Returns basic signals and support/resistance levels.
    """
    if df.empty:
        return None, None, None, None

    # --- INDICATORS ---
    
    # 1. WaveTrend
    n1, n2 = 9, 12
    ap = (df['High'] + df['Low'] + df['Close']) / 3
    esa = ta.ema(ap, length=n1)
    d = ta.ema((ap - esa).abs(), length=n1)
    # Avoid division by zero
    d = d.replace(0, 0.000001)
    ci = (ap - esa) / (0.015 * d)
    tci = ta.ema(ci, length=n2)
    wt1 = tci
    wt2 = ta.sma(wt1, length=3)
    
    # 2. StochRSI
    # Handle small DF size gracefully just in case, though caller should ensure size
    stoch_k = pd.Series(0, index=df.index)
    try:
        stoch_res = ta.stochrsi(df['Close'], length=14, rsi_length=14, k=3, d=3)
        if stoch_res is not None:
             stoch_k = stoch_res.iloc[:, 0]
    except: pass
    
    # 3. MFI / VWAP
    mfi = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14).fillna(50)
    vwap = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume']).fillna(df['Close'])
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=14).fillna(0)
    
    # 4. Volume Surge
    vol = df['Volume']
    vol_ma = vol.rolling(20).mean()
    vol_std = vol.rolling(20).std()
    # Handle zero std
    vol_z = (vol - vol_ma) / (vol_std.replace(0, 1))
    
    # --- SIGNAL GENERATION (Last Candle) ---
    curr_wt1 = wt1.iloc[-1]
    curr_wt2 = wt2.iloc[-1]
    prev_wt1 = wt1.iloc[-2]
    prev_wt2 = wt2.iloc[-2]
    
    curr_k = stoch_k.iloc[-1]
    curr_m = mfi.iloc[-1]
    curr_vw = vwap.iloc[-1]
    curr_price = df['Close'].iloc[-1]
    curr_atr = atr.iloc[-1]
    
    # Crossovers
    wt_cross_up = (prev_wt1 < prev_wt2) and (curr_wt1 > curr_wt2)
    wt_cross_down = (prev_wt1 > prev_wt2) and (curr_wt1 < curr_wt2)
    
    is_vol_surge = vol_z.iloc[-1] > 2
    
    # Scoring
    long_score = 0
    short_score = 0
    
    # Conditions
    if curr_wt1 < -50 and wt_cross_up: long_score += 2
    if curr_wt1 > 50 and wt_cross_down: short_score += 2
    
    if curr_k < 20: long_score += 1
    if curr_k > 80: short_score += 1
    
    if curr_m < 25: long_score += 1
    if curr_m > 75: short_score += 1
    
    if curr_price > curr_vw: long_score += 1
    else: short_score += 1
    
    ENTRY_THRESHOLD = 4
    signal = None
    sl = None
    tp = None
    
    atr_mult = 2.5 if is_vol_surge else 2.0
    
    if long_score >= ENTRY_THRESHOLD and (wt_cross_up or is_vol_surge):
        signal = "LONG"
        sl = curr_price - (curr_atr * atr_mult)
        tp = curr_price + (curr_price - sl) * 2.0
        
    elif short_score >= ENTRY_THRESHOLD and (wt_cross_down or is_vol_surge):
        signal = "SHORT"
        sl = curr_price + (curr_atr * atr_mult)
        tp = curr_price - (sl - curr_price) * 2.0
        
    return signal, curr_price, sl, tp
