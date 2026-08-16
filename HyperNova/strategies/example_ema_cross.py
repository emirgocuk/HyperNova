import pandas as pd
import numpy as np
from strategies.base_strategy import BaseStrategy

class EMACrossStrategy(BaseStrategy):
    """
    A simple example strategy:
    Buy when fast EMA crosses above slow EMA.
    Sell when fast EMA crosses below slow EMA.
    """
    def __init__(self):
        super().__init__(
            name="EMA_Cross_Simple", 
            params={"fast_period": 9, "slow_period": 21}
        )

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        # Create a copy so we don't modify the original
        data = df.copy()
        
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        
        # Calculate EMAs
        data[f'ema_{fast}'] = data['close'].ewm(span=fast, adjust=False).mean()
        data[f'ema_{slow}'] = data['close'].ewm(span=slow, adjust=False).mean()
        
        # Default hold
        data['signal'] = 0
        
        # Determine cross logic
        # Buy: Fast > Slow AND previous Fast <= previous Slow
        buy_condition = (data[f'ema_{fast}'] > data[f'ema_{slow}']) & \
                        (data[f'ema_{fast}'].shift(1) <= data[f'ema_{slow}'].shift(1))
                        
        # Sell: Fast < Slow AND previous Fast >= previous Slow
        sell_condition = (data[f'ema_{fast}'] < data[f'ema_{slow}']) & \
                         (data[f'ema_{fast}'].shift(1) >= data[f'ema_{slow}'].shift(1))
                         
        data.loc[buy_condition, 'signal'] = 1
        data.loc[sell_condition, 'signal'] = -1
        
        return data
