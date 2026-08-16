from backtesting import Strategy
from backtesting.lib import crossover
import pandas_ta as ta
import pandas as pd
from core.strategy_utils import calculate_market_cipher_signals

class ProfitEngineStrategy(Strategy):
    """
    Backtesting Strategy that mimics the HyperNova V2 Profit Engine.
    Includes:
    1. Market Cipher (Trend) - via calculate_market_cipher_signals
    2. Smart Grid (Accumulation) - Simplified for backtest (no AI latency, just logic)
    """
    
    # Grid Parameters
    bb_length = 20
    bb_std = 2.0
    adx_threshold = 25
    
    def init(self):
        # Pre-calculate Indicators to speed up
        self.df = pd.DataFrame({
            'Open': self.data.Open,
            'High': self.data.High,
            'Low': self.data.Low,
            'Close': self.data.Close,
            'Volume': self.data.Volume
        })
        
        # We will calculate signals inside next() to mimic live feed frame-by-frame
        # But for speed in backtesting, vectorization is preferred. 
        # However, our utility is designed for DF.
        pass

    def next(self):
        # Slice data up to current candle to mimic live feed
        # Note: self.data is effectively the full array, but we should inspect current index
        # This is slow for backtesting. A better way for Backtesting lib is to use vectorized wrapper.
        # But we want to verify the SHARED utility. So we will pay the performance cost.
        
        # Optimization: Pass a window of last 300 candles (Better Warmup)
        idx = len(self.data.Close)
        if idx < 300: return
        
        # Construct small DF for the utility
        lookback = 300
        current_index = self.data.index[idx-lookback:idx]
        
        window = pd.DataFrame({
            'Open': self.data.Open[idx-lookback:idx],
            'High': self.data.High[idx-lookback:idx],
            'Low': self.data.Low[idx-lookback:idx],
            'Close': self.data.Close[idx-lookback:idx],
            'Volume': self.data.Volume[idx-lookback:idx]
        })
        
        # KEY FIX: Pandas TA VWAP requires a proper DatetimeIndex
        window.index = pd.to_datetime(current_index)
        
        # 1. Market Cipher Signal (Hunter)
        signal, price, sl, tp = calculate_market_cipher_signals(window)
        
        # DEBUG: Print first signal to confirm it works
        if signal and not self.position:
             print(f"DEBUGGER: Signal Found in Backtest: {signal} at {window.index[-1]}")
        
        # 2. Grid Logic (Farmer)
        # Re-implement basic grid logic here since GridAgent is a class
        # Ideally we refactor GridAgent to have a static/util method too.
        # For now, inline the logic:
        
        adx_val = ta.adx(window['High'], window['Low'], window['Close'], length=14)['ADX_14'].iloc[-1]
        
        # EXECUTION LOGIC
        
        # A. TREND MDOE
        if signal and adx_val > 20: # Cipher logic often works best in trends
             if signal == 'LONG' and not self.position:
                 self.buy(sl=sl, tp=tp)
             elif signal == 'SHORT' and not self.position:
                 self.sell(sl=sl, tp=tp)
                 
        # B. GRID MODE (Sideways)
        elif adx_val < self.adx_threshold and not self.position:
            # BB Calculation
            bb = ta.bbands(window['Close'], length=self.bb_length, std=self.bb_std)
            upper = bb.iloc[-1, 2] # Index 2 is Upper
            lower = bb.iloc[-1, 0] # Index 0 is Lower
            curr_price = window['Close'].iloc[-1]
            
            # Simple Mean Reversion
            if curr_price <= lower:
                # Buy at lower band, Target Mid band
                mid = bb.iloc[-1, 1]
                self.buy(tp=mid, sl=curr_price*0.99) # Tight SL
            elif curr_price >= upper:
                mid = bb.iloc[-1, 1]
                self.sell(tp=mid, sl=curr_price*1.01)

