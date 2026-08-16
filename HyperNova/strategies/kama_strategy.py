import pandas as pd
import numpy as np
from backtesting import Strategy
import warnings

# Suppress pandas rank usage warning if any
warnings.filterwarnings('ignore')

def kama(close, fast=2, slow=15):
    """
    Kaufman Adaptive Moving Average calculation.
    """
    close = pd.Series(close)
    length = slow
    er_values = np.zeros(len(close))
    kama_values = np.zeros(len(close))

    # Efficiency Ratio (ER)
    # ER = Change / Volatility
    for i in range(length, len(close)):
        change = abs(close[i] - close[i - length])
        volatility = sum(abs(close[j+1] - close[j]) for j in range(i-length, i))
        er = change / volatility if volatility != 0 else 0.0
        er_values[i] = er

    # Initial KAMA is standard close (or SMA)
    kama_values[:length] = close[:length]
    
    # KAMA Calculation
    for i in range(length, len(close)):
        er = er_values[i]
        fastSC = 2 / (fast + 1)
        slowSC = 2 / (slow + 1)
        # SC = [ER * (fastSC - slowSC) + slowSC]^2
        sc = (er * (fastSC - slowSC) + slowSC) ** 2
        kama_values[i] = kama_values[i - 1] + sc * (close[i] - kama_values[i - 1])

    kama_series = pd.Series(kama_values, index=close.index)
    er_series = pd.Series(er_values, index=close.index)
    return kama_series.to_numpy(), er_series.to_numpy()

def linear_regression_channel(close, length=40, mult=1.5):
    """
    Calculates Linear Regression Channel: Mid, Upper, Lower, and Slope.
    """
    close = pd.Series(close)
    n = len(close)

    mid_array = np.full(n, np.nan)
    upper_array = np.full(n, np.nan)
    lower_array = np.full(n, np.nan)
    slope_array = np.full(n, np.nan)

    # Note: Rolling window loop can be slow in Python backtesting.
    # ideally we use vectorized ops, but for custom regression loop is precise.
    for i in range(length, n):
        y = close[i-length:i].values
        x = np.arange(length)
        if len(y) == length:
            slope, intercept = np.polyfit(x, y, 1)
            # fitted = intercept + slope * x
            
            # Mid line is at the END of the regression line (current point projection)
            mid_line = intercept + slope * (length - 1)
            
            # Calculate Standard Deviation of residuals
            # fast calculation: sum((y - fitted)**2)
            fitted_y = intercept + slope * x
            std_res = np.std(y - fitted_y)

            upper_line = mid_line + mult * std_res
            lower_line = mid_line - mult * std_res

            mid_array[i] = mid_line
            upper_array[i] = upper_line
            lower_array[i] = lower_line
            slope_array[i] = slope

    return mid_array, upper_array, lower_array, slope_array

class KAMAStrategy(Strategy):
    fast_period = 2
    slow_period = 15
    er_threshold = 0.3
    stop_loss = 0.015
    take_profit = 0.07
    reg_length = 40
    reg_mult = 1.5

    def init(self):
        # 1. KAMA & ER
        self.kama, self.er = self.I(kama, self.data.Close, self.fast_period, self.slow_period)
        
        # 2. Linear Regression Channel
        self.mid_line, self.upper_line, self.lower_line, self.slope = self.I(
            linear_regression_channel,
            self.data.Close,
            self.reg_length,
            self.reg_mult
        )

    def next(self):
        # Wait for enough data
        if len(self.data.Close) < max(self.slow_period, self.reg_length):
            return

        price = self.data.Close[-1]
        prev_price = self.data.Close[-2]

        current_kama = self.kama[-1]
        prev_kama = self.kama[-2]
        current_er = self.er[-1]

        # Trend Direction
        kama_up = current_kama > prev_kama
        kama_down = current_kama < prev_kama

        # Crossovers
        cross_above = (price > current_kama and prev_price <= prev_kama)
        cross_below = (price < current_kama and prev_price >= prev_kama)

        current_slope = self.slope[-1]

        # --- Entry Logic ---
        if not self.position:
            # Long Entry: 
            # 1. KAMA Trending Up
            # 2. Price Crossed Above KAMA
            # 3. Efficiency Ratio is high enough (Not choppy)
            # 4. Regression Slope is Positive (Confirming trend)
            if kama_up and cross_above and current_er >= self.er_threshold:
                if current_slope > 0:
                    sl = price * (1 - self.stop_loss)
                    tp = price * (1 + self.take_profit)
                    self.buy(sl=sl, tp=tp)

            # Short Entry:
            # 1. KAMA Trending Down
            # 2. Price Crossed Below KAMA
            # 3. Efficiency Ratio high
            # 4. Regression Slope Negative
            if kama_down and cross_below and current_er >= self.er_threshold:
                if current_slope < 0:
                    sl = price * (1 + self.stop_loss)
                    tp = price * (1 - self.take_profit)
                    self.sell(sl=sl, tp=tp)

        # --- Exit Logic ---
        # Exit if trend reverses or market becomes too choppy/weak
        # "current_er < self.er_threshold * 0.5" means market lost direction strength
        elif self.position:
            if self.position.is_long and (kama_down or current_er < self.er_threshold * 0.5):
                self.position.close()
            if self.position.is_short and (kama_up or current_er < self.er_threshold * 0.5):
                self.position.close()
