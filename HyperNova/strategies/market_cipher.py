import pandas as pd
import pandas_ta as ta
import numpy as np
from backtesting import Strategy
from backtesting.lib import crossover

class MarketCipherStrategy(Strategy):
    # Wave Trend parameters
    wt_channel_len = 9
    wt_average_len = 12
    wt_ma_len = 3
    
    # StochRSI parameters
    rsi_period = 14
    stoch_period = 14
    smooth_k = 3
    smooth_d = 3
    
    # MFI parameters
    mfi_period = 14
    
    # Thresholds
    wt_oversold = -50     # Slightly adjusted for typical WT scale
    wt_overbought = 50
    stoch_oversold = 20
    stoch_overbought = 80
    mfi_oversold = 25
    mfi_overbought = 75
    
    # Risk management
    take_profit = 0.035
    stop_loss = 0.02
    
    # Divergence detection
    divergence_lookback = 10
    
    def init(self):
        # 1. Wave Trend Oscillator
        def get_wavetrend(high, low, close, n1, n2, n3):
            # Convert inputs to series
            h = pd.Series(high)
            l = pd.Series(low)
            c = pd.Series(close)
            ap = (h + l + c) / 3
            
            esa = ta.ema(ap, length=n1)
            d = ta.ema((ap - esa).abs(), length=n1)
            ci = (ap - esa) / (0.015 * d)
            tci = ta.ema(ci, length=n2)
            
            wt1 = tci
            wt2 = ta.sma(wt1, length=n3)
            
            # Return as tuple of numpy arrays
            return wt1.to_numpy(), wt2.to_numpy()

        self.wt1, self.wt2 = self.I(get_wavetrend, self.data.High, self.data.Low, self.data.Close, 
                                    self.wt_channel_len, self.wt_average_len, self.wt_ma_len)
        
        # 2. Stoch RSI
        def get_stoch_rsi(close, rsi_len, stoch_len, k, d):
            # pandas-ta stochrsi returns DataFrame with K and D columns
            srsi = ta.stochrsi(pd.Series(close), length=rsi_len, rsi_length=stoch_len, k=k, d=d)
            if srsi is None: return np.zeros_like(close), np.zeros_like(close)
            return srsi.iloc[:, 0].to_numpy(), srsi.iloc[:, 1].to_numpy() # K, D

        self.stoch_k, self.stoch_d = self.I(get_stoch_rsi, self.data.Close, 
                                            self.rsi_period, self.stoch_period, self.smooth_k, self.smooth_d)
        
        # 3. MFI
        def get_mfi(high, low, close, volume, length):
            m = ta.mfi(pd.Series(high), pd.Series(low), pd.Series(close), pd.Series(volume), length=length)
            return m.fillna(50).to_numpy() # Handle NaNs
        
        self.mfi = self.I(get_mfi, self.data.High, self.data.Low, self.data.Close, self.data.Volume, self.mfi_period)
        
        # 4. VWAP
        def get_vwap(high, low, close, volume):
            # Convert to pandas series for calculation
            h_s = pd.Series(high)
            l_s = pd.Series(low)
            c_s = pd.Series(close)
            v_s = pd.Series(volume)
            
            typical_price = (h_s + l_s + c_s) / 3
            volume_price = typical_price * v_s
            
            # Rolling window of 20
            window = 20
            rolling_vp = volume_price.rolling(window).sum()
            rolling_v = v_s.rolling(window).sum()
            
            vwap = rolling_vp / rolling_v
            # Fill NaNs with Close price
            return vwap.fillna(c_s).to_numpy()

        self.vwap = self.I(get_vwap, self.data.High, self.data.Low, self.data.Close, self.data.Volume)
        
        # 5. ATR for Dynamic SL
        def get_atr(high, low, close, length):
            return ta.atr(pd.Series(high), pd.Series(low), pd.Series(close), length=length).fillna(0).to_numpy()
            
        self.atr = self.I(get_atr, self.data.High, self.data.Low, self.data.Close, 14)
        
        # 6. Volume Stats
        def get_vol_stats(volume):
            v = pd.Series(volume)
            ma = ta.sma(v, length=20)
            std = v.rolling(20).std()
            return ma.fillna(0).to_numpy(), std.fillna(1).to_numpy()
            
        self.volume_ma, self.volume_std = self.I(get_vol_stats, self.data.Volume)

        # 7. Macro TEMA (1H)
        def get_macro_tema():
            # Create Series with correct index
            s = pd.Series(self.data.Close, index=self.data.index)
            # Resample to 1H
            s_1h = s.resample('1h').last()
            # Calculate TEMA on 1H
            tema_1h = ta.tema(s_1h, length=50)
            # Fill NaNs in 1H for safety
            tema_1h = tema_1h.fillna(method='bfill').fillna(method='ffill')
            # Reindex back to 5m (ffill to propagate last 1H value)
            tema_5m = tema_1h.reindex(s.index).ffill()
            return tema_5m.fillna(method='bfill').to_numpy()
            
        self.tema = self.I(get_macro_tema) # TEMA(50) on 1H

        # 8. ADX (Trend Strength)
        def get_adx(high, low, close, length):
            adx_df = ta.adx(pd.Series(high), pd.Series(low), pd.Series(close), length=length)
            if adx_df is None: return np.zeros_like(close)
            return adx_df[f'ADX_{length}'].fillna(0).to_numpy()
            
        self.adx = self.I(get_adx, self.data.High, self.data.Low, self.data.Close, 14)
        
        # 9. Bollinger Bands (Grid Boundaries)
        def get_bb(close, length, std):
            bb = ta.bbands(pd.Series(close), length=length, std=std)
            if bb is None: return np.zeros_like(close), np.zeros_like(close), np.zeros_like(close)
            # Returns lower, mid, upper columns usually
            # Use iloc to be safe: 0=Lower, 1=Mid, 2=Upper
            l = bb.iloc[:, 0].fillna(method='bfill')
            m = bb.iloc[:, 1].fillna(method='bfill')
            u = bb.iloc[:, 2].fillna(method='bfill')
            return l.to_numpy(), m.to_numpy(), u.to_numpy()
            
        self.bb_lower, self.bb_mid, self.bb_upper = self.I(get_bb, self.data.Close, 20, 2.0)

    def detect_divergence(self, price_data, indicator_data, lookback):
        # Helper to detect divergence on the last 'lookback' bars
        # This runs inside next(), so we look at data[-lookback:]
        if len(price_data) < lookback * 2:
            return False, False
        
        # Slices
        p_recent = price_data[-lookback:]
        i_recent = indicator_data[-lookback:]
        
        p_prev = price_data[-lookback*2:-lookback]
        i_prev = indicator_data[-lookback*2:-lookback]
        
        # Bullish: Price lower low, Indicator higher low
        bullish = (np.min(p_recent) < np.min(p_prev)) and (np.min(i_recent) > np.min(i_prev))
        
        # Bearish: Price higher high, Indicator lower high
        bearish = (np.max(p_recent) > np.max(p_prev)) and (np.max(i_recent) < np.max(i_prev))
        
        return bullish, bearish

    def next(self):
        # Skip warm-up
        if len(self.data) < 60: return
        
        # Current values
        price = self.data.Close[-1]
        
        # --- HYBRID LOGIC SWITCH ---
        current_adx = self.adx[-1]
        is_grid_mode = current_adx < 25
        
        ENTRY_THRESHOLD = 4
        
        if is_grid_mode:
            # === GRID MODE (Mean Reversion) ===
            # Logic: Buy near Lower BB, Sell near Upper BB
            lower = self.bb_lower[-1]
            upper = self.bb_upper[-1]
            mid = self.bb_mid[-1]
            
            # Distance check (within 0.2%)
            near_threshold = 0.002
            dist_to_lower = (price - lower) / lower
            dist_to_upper = (upper - price) / upper
            
            bandwidth = upper - lower
            
            if not self.position:
                if dist_to_lower < near_threshold: # Buy Zone
                    try:
                        sl = lower - (bandwidth * 0.2)
                        tp = upper - (bandwidth * 0.1)
                        if sl > 0 and tp > 0 and sl < price and tp > price:
                             self.buy(sl=sl, tp=tp)
                    except Exception as e:
                        print(f"Grid Long Error: {e} | Price: {price}, SL: {sl}, TP: {tp}")
                    
                elif dist_to_upper < near_threshold: # Sell Zone
                    try:
                        sl = upper + (bandwidth * 0.2)
                        tp = lower + (bandwidth * 0.1)
                        if sl > 0 and tp > 0 and sl > price and tp < price:
                             self.sell(sl=sl, tp=tp)
                    except Exception as e:
                        print(f"Grid Short Error: {e} | Price: {price}, SL: {sl}, TP: {tp}")
                    
        else:
            # === TREND MODE (Market Cipher) ===
            wt1 = self.wt1[-1]
            wt2 = self.wt2[-1]
            k = self.stoch_k[-1]
            m = self.mfi[-1]
            vw = self.vwap[-1]
            vol = self.data.Volume[-1]
            atr = self.atr[-1]
            
            # Volume Surge
            vol_ma = self.volume_ma[-1]
            vol_std = self.volume_std[-1]
            vol_z = (vol - vol_ma) / (vol_std + 1e-9)
            is_vol_surge = vol_z > 2
            
            # Divergence on WaveTrend
            div_lookback = self.divergence_lookback
            bullish_div, bearish_div = self.detect_divergence(self.data.Close, self.wt1, div_lookback)
            
            # 0. Macro Trend Filter (Freqtrade Style)
            tema_curr = self.tema[-1]
            tema_prev = self.tema[-2]
            slope_up = tema_curr > tema_prev
            slope_down = tema_curr < tema_prev
            
            # Strict Trend: Price must be on correct side of TEMA AND TEMA must be sloping that way
            is_uptrend = (price > tema_curr) and slope_up
            is_downtrend = (price < tema_curr) and slope_down

            # Confluence Signals
            long_score = 0
            short_score = 0
            
            # 1. WT Signals (Context Aware)
            wt_cross_up = crossover(self.wt1, self.wt2)
            wt_cross_down = crossover(self.wt2, self.wt1)
            
            # Standard Reversal (Counter-Trend or Early Trend)
            if self.wt1[-1] < self.wt_oversold and wt_cross_up:
                long_score += 2
            if self.wt1[-1] > self.wt_overbought and wt_cross_down:
                short_score += 2
                
            # 2. Stoch Signals
            if k < self.stoch_oversold: long_score += 1
            if k > self.stoch_overbought: short_score += 1
            
            # 3. MFI Signals
            if m < self.mfi_oversold: long_score += 1
            if m > self.mfi_overbought: short_score += 1
            
            # 4. VWAP Context
            if price > vw: long_score += 1
            else: short_score += 1
            
            # 5. Divergence Boost
            if bullish_div: long_score += 3
            if bearish_div: short_score += 3
            
            # Dynamic Risk
            atr_mult = 2.5 if is_vol_surge else 2.0
            
            # Execution
            if not self.position:
                # ENTRY LOGIC
            
                # Long Entry
                if is_uptrend: # ONLY Long in Uptrend
                    if long_score >= ENTRY_THRESHOLD and (is_vol_surge or bullish_div or wt_cross_up):
                        sl = price - (atr * atr_mult)
                        # Dynamic TP/SL is set, but we also use Time-Based ROI later
                        tp = price + (price - sl) * 2.0 # Higher TP, rely on ROI to close early
                        self.buy(sl=sl, tp=tp)
                
                # Short Entry
                elif is_downtrend: # ONLY Short in Downtrend
                    if short_score >= ENTRY_THRESHOLD and (is_vol_surge or bearish_div or wt_cross_down):
                        sl = price + (atr * atr_mult)
                        tp = price - (sl - price) * 2.0
                        self.sell(sl=sl, tp=tp)
                        
        # Global Exit Logic (Time-Based ROI applies to ALL positions)
        if self.position:
            # EXIT LOGIC (Time-Based ROI)
            if len(self.trades) > 0:
                duration_bars = (len(self.data) - 1) - self.trades[-1].entry_bar
                current_profit = self.position.pl_pct # This is aggregate, but good enough for single position
                
                # ROI Table (for 5m candles)
                should_close = False
                
                if duration_bars > 6 and current_profit > 0.04:
                    should_close = True
                elif duration_bars > 12 and current_profit > 0.02:
                    should_close = True
                elif duration_bars > 24 and current_profit > 0.01:
                    should_close = True
                    
                if should_close:
                    self.position.close()

# =========================================
# LIVE TRADING WRAPPER (The Fix)
# =========================================
def analyze_market_cipher(df):
    """
    Wrapper to use the Strategy logic on a DataFrame for Live/Paper trading.
    Returns: 'LONG', 'SHORT', or None
    """
    # 1. Instantiate Strategy to calculate indicators
    # We can't easily perform a backtest.run() on 1 candle.
    # Instead, we should extract the indicator logic or use a helper.
    # PRO TIP: For live execution, it's often better to re-implement the entry logic 
    # functionally or use the class logic if designed for it.
    
    # Since our logic is embedded in init() and next(), let's replicate the MAIN signals here.
    # This is "Double Maintenance" but standard for Backtesting.py users.
    
    # CALCULATIONS
    # WaveTrend
    n1, n2 = 9, 12
    ap = (df['High'] + df['Low'] + df['Close']) / 3
    esa = ta.ema(ap, length=n1)
    d = ta.ema((ap - esa).abs(), length=n1)
    ci = (ap - esa) / (0.015 * d)
    tci = ta.ema(ci, length=n2)
    wt1 = tci
    wt2 = ta.sma(wt1, length=3)
    
    # StochRSI
    rsi = ta.rsi(df['Close'], length=14)
    stoch_k = ta.stochrsi(df['Close'], length=14, rsi_length=14, k=3, d=3).iloc[:, 0]
    
    # MFI
    mfi = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14).fillna(50)
    
    # VWAP
    vwap = ta.vwap(df['High'], df['Low'], df['Close'], df['Volume']).fillna(df['Close'])
    
    # ATR
    atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    
    # Volume Surge
    vol = df['Volume']
    vol_ma = vol.rolling(20).mean()
    vol_std = vol.rolling(20).std()
    vol_z = (vol - vol_ma) / (vol_std + 1e-9)
    is_vol_surge = vol_z.iloc[-1] > 2
    
    # Current Values
    curr_wt1 = wt1.iloc[-1]
    curr_wt2 = wt2.iloc[-1]
    prev_wt1 = wt1.iloc[-2]
    prev_wt2 = wt2.iloc[-2]
    
    curr_k = stoch_k.iloc[-1]
    curr_m = mfi.iloc[-1]
    curr_vw = vwap.iloc[-1]
    curr_price = df['Close'].iloc[-1]
    curr_atr = atr.iloc[-1]
    
    # Macro Trend (TEMA) - We do this in run_live but let's double check here? 
    # No, run_live handles the filter. This checks entry setup.
    
    # SCORING (Safe Mode)
    long_score = 0
    short_score = 0
    
    wt_cross_up = (prev_wt1 < prev_wt2) and (curr_wt1 > curr_wt2)
    wt_cross_down = (prev_wt1 > prev_wt2) and (curr_wt1 < curr_wt2)
    
    # 1. WT Signals
    if curr_wt1 < -50 and wt_cross_up: long_score += 2
    if curr_wt1 > 50 and wt_cross_down: short_score += 2
    
    # 2. Stoch Signals
    if curr_k < 20: long_score += 1
    if curr_k > 80: short_score += 1
    
    # 3. MFI Signals
    if curr_m < 25: long_score += 1
    if curr_m > 75: short_score += 1
    
    # 4. VWAP Context
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
