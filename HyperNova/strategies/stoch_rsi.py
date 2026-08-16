import pandas as pd
import pandas_ta as ta
import numpy as np
from backtesting import Strategy
from backtesting.lib import crossover

class StochRSIStrategy(Strategy):
    # Strategy parameters
    rsi_period = 14
    stoch_period = 14
    smooth_k = 3
    smooth_d = 3
    oversold = 20
    overbought = 80
    take_profit = 0.025
    stop_loss = 0.015
    
    def init(self):
        # Calculate StochRSI using pandas_ta
        # StochRSI returns two columns: STOCHRSI_k, STOCHRSI_d by default usually or we calculate manually
        # method 1: self.data.df.ta.stochrsi(...)
        
        # Accessing the full dataframe from backtesting.py's self.data
        # Backtesting.py converts data to internal arrays, but we can access .df usually or pass series
        # However, it's safer to use 'I' with a wrapper function that returns numpy arrays.
        
        def get_stoch_rsi_k(close, rsi_len, stoch_len, k, d):
            # Calculate full StochRSI DataFrame
            df = pd.DataFrame({'close': close})
            # ta.stochrsi returns a DF with k and d columns
            stoch = ta.stochrsi(df['close'], length=rsi_len, rsi_length=stoch_len, k=k, d=d)
            if stoch is None: return np.zeros_like(close)
            return stoch.iloc[:, 0].to_numpy() # First column is usually K

        def get_stoch_rsi_d(close, rsi_len, stoch_len, k, d):
            df = pd.DataFrame({'close': close})
            stoch = ta.stochrsi(df['close'], length=rsi_len, rsi_length=stoch_len, k=k, d=d)
            if stoch is None: return np.zeros_like(close)
            return stoch.iloc[:, 1].to_numpy() # Second column is usually D
            
        def get_ema(close, length):
            return ta.ema(pd.Series(close), length=length).to_numpy()

        # We wrap them in self.I to ensure they are calculated one step at a time if needed or all at once
        # backtesting.py's self.I handles numpy array returns well.
        
        self.stoch_k = self.I(get_stoch_rsi_k, self.data.Close, self.rsi_period, self.stoch_period, self.smooth_k, self.smooth_d)
        self.stoch_d = self.I(get_stoch_rsi_d, self.data.Close, self.rsi_period, self.stoch_period, self.smooth_k, self.smooth_d)
        
        self.ema_fast = self.I(get_ema, self.data.Close, 20)
        self.ema_slow = self.I(get_ema, self.data.Close, 50)
    
    def next(self):
        # Skip if not enough data
        if len(self.data) < 50:
            return
            
        current_price = self.data.Close[-1]
        current_k = self.stoch_k[-1]
        prev_k = self.stoch_k[-2] if len(self.stoch_k) > 1 else current_k
        
        # Trend Filter
        is_uptrend = self.ema_fast[-1] > self.ema_slow[-1]
        is_downtrend = self.ema_fast[-1] < self.ema_slow[-1]
        
        # Crossover logic
        # pandas_ta values might be 0-100 or 0-1? Usually 0-100.
        
        cross_up = self.stoch_k[-1] > self.stoch_d[-1] and self.stoch_k[-2] <= self.stoch_d[-2]
        cross_down = self.stoch_k[-1] < self.stoch_d[-1] and self.stoch_k[-2] >= self.stoch_d[-2]
        
        # Long
        if (not self.position and 
            current_k < self.oversold and
            cross_up and
            is_uptrend):
            
            self.buy(
                sl=current_price * (1 - self.stop_loss),
                tp=current_price * (1 + self.take_profit)
            )
        
        # Short
        elif (not self.position and 
              current_k > self.overbought and
              cross_down and
              is_downtrend):
            
            self.sell(
                sl=current_price * (1 + self.stop_loss),
                tp=current_price * (1 - self.take_profit)
            )
