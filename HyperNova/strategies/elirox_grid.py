import pandas as pd
import numpy as np
from strategies.base_strategy import BaseStrategy

class EliroxGridStrategy(BaseStrategy):
    """
    Fixed-Range Compounding Grid Bot (Elirox Style).
    Places a fixed grid of 25 levels between a defined high and low.
    Trades the ranges and marginally increases lot sizes as PnL grows (compounding).
    """
    def __init__(self, high_price=70316, low_price=64597, levels=25, base_lot=0.2):
        super().__init__(
            name="Elirox_Fixed_Grid", 
            params={
                "high_price": high_price, 
                "low_price": low_price,
                "levels": levels,
                "base_lot": base_lot
            }
        )
        
        # Calculate grid spacing
        self.high = high_price
        self.low = low_price
        self.levels = levels
        self.grid_gap = (self.high - self.low) / self.levels
        
        # Build the grid lines
        self.grid_lines = [self.low + (i * self.grid_gap) for i in range(self.levels + 1)]
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Since this is a deeply stateful grid bot (it depends on open positions 
        at specific grid lines), traditional vector-based signal generation (1 or -1) 
        doesn't work well without tracking executions.
        
        For the backtester, we will output a specialized state dictionary per row.
        """
        # We need a custom backtesting loop for Grid bots in the engine,
        # but to keep it simple for the generic tester, we will emit signals
        # when price crosses a grid line.
        
        data = df.copy()
        data['signal'] = 0
        data['grid_level_crossed'] = -1
        
        # Vectorized way to find which grid cell the price is in
        bins = [-np.inf] + self.grid_lines + [np.inf]
        # Digitize returns the bin index (1-based)
        data['cell_index'] = np.digitize(data['close'], bins)
        
        # Detect cell changes (crossing a grid line)
        data['cell_change'] = data['cell_index'].diff()
        
        # If price dropped into a new cell (crossed a line downwards) -> BUY
        # Note: We only buy if we are INSIDE the active grid bounds
        buy_condition = (data['cell_change'] < 0) & (data['close'] >= self.low) & (data['close'] <= self.high)
        
        # If price rose into a new cell (crossed a line upwards) -> SELL
        sell_condition = (data['cell_change'] > 0) & (data['close'] >= self.low) & (data['close'] <= self.high)
        
        data.loc[buy_condition, 'signal'] = 1
        data.loc[sell_condition, 'signal'] = -1
        
        # Store the exact grid price that was crossed for perfect limit order simulation
        data.loc[data['signal'] != 0, 'limit_price'] = data['close'] # Approximation for now
        
        return data

    def calculate_lot_size(self, current_balance: float, initial_balance: float) -> float:
        """
        Compounding logic: For every 5% gain in balance, increase lot size by 5%.
        """
        base_lot = self.params['base_lot']
        profit_pct = (current_balance - initial_balance) / initial_balance
        
        if profit_pct > 0:
            # Increase lot size proportionally (conservative compounding)
            # E.g., 10% profit = 10% bigger lot
            multiplier = 1 + (profit_pct * 0.5) # Dampened compounding
            new_lot = base_lot * multiplier
            return round(new_lot, 2)
        
        return base_lot
