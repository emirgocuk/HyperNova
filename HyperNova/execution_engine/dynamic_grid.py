import logging
import numpy as np

logger = logging.getLogger("DynamicGrid")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')

class DynamicGrid:
    """
    The Adaptive Skeleton: A non-linear, self-rebalancing grid system.
    Philosophy: The grid is not static. It widens like a stretching spring as 
    price moves away from the center (Fibonacci spacing), accommodating high tension.
    """
    def __init__(self, current_price: float, atr: float, num_grids: int = 5, side: str = "LONG", base_gap_pct: float = None):
        self.center_price = current_price
        self.atr = atr
        self.num_grids = num_grids
        self.side = side.upper()
        
        # Base gap defines the distance between the center and the first grid level.
        # If not provided, it dynamically uses 50% of the current ATR as a starting point.
        self.base_gap = base_gap_pct * current_price if base_gap_pct else (self.atr * 0.5)
        
        self.grid_levels = []
        self._calculate_fibonacci_levels()

    def _calculate_fibonacci_levels(self):
        """
        Calculates grid placement using slightly modified Fibonacci sequence:
        1, 1, 2, 3, 5 -> cumulative gaps from center: 1x, 2x, 4x, 7x, 12x
        This allows the bot to 'give way' and not fight a strong trend rigidly.
        """
        if self.side not in ["LONG", "SHORT"]:
            logger.error(f"Invalid side {self.side}")
            return
            
        fib_sequence = [1, 1, 2, 3, 5, 8, 13, 21]
        cumulative_gap = 0
        
        self.grid_levels = []
        
        for i in range(self.num_grids):
            # Fetch Fibonacci multiplier
            multiplier = fib_sequence[i] if i < len(fib_sequence) else fib_sequence[-1]
            cumulative_gap += multiplier
            
            # The gap gets wider the further we go down the grid
            price_distance = cumulative_gap * self.base_gap
            
            if self.side == "LONG":
                # For Longs, we lay limit BUY orders below the current price
                level_price = self.center_price - price_distance
            else:
                # For Shorts, we lay limit SELL orders above the current price
                level_price = self.center_price + price_distance
                
            # Volume sizing: Martingale-lite (increase size slightly as price drops)
            # Size increases linearly while distance increases exponentially (safer)
            level_size_weight = 1 + (i * 0.5) 
            
            self.grid_levels.append({
                "level": i + 1,
                "price": round(level_price, 5),
                "distance_from_center": round(price_distance, 5),
                "size_weight": level_size_weight,
                "status": "PENDING"
            })
            
        logger.info(f"Generated {self.side} Grid. Center: {self.center_price:.4f} | ATR: {self.atr:.4f}")
        for lvl in self.grid_levels:
            logger.debug(f"Level {lvl['level']}: Price={lvl['price']} | Weight={lvl['size_weight']}")

    def rebalance_grid(self, new_price: float, confidence_score: float):
        """
        Dynamic Rebalancing (The "Yielding" Mechanism)
        If the price drops significantly and the AI confidence in a reversal drops,
        we drag the center price down and recalculate to prevent liquidation.
        """
        price_drop_pct = abs(new_price - self.center_price) / self.center_price
        
        # If price moved more than 2% away from center AND confidence is low (< 0.4)
        if price_drop_pct > 0.02 and confidence_score < 0.4:
            logger.info(f"🚨 TENSION TOO HIGH! Rebalancing Grid Center from {self.center_price:.4f} to {new_price:.4f}")
            self.center_price = new_price
            self._calculate_fibonacci_levels()
            return True # Indicates rebalance occurred
        return False

def test_dynamic_grid():
    # Simulate current market state
    mock_price = 100.0
    mock_atr = 0.50 # Moderate volatility
    
    # 1. Initialize Adaptive Skeleton
    logger.info("--- Testing Normal Long Grid ---")
    grid = DynamicGrid(current_price=mock_price, atr=mock_atr, num_grids=5, side="LONG")
    
    for lvl in grid.grid_levels:
        print(lvl)
        
    print("\n--- Testing High Tension Rebalance ---")
    # 2. Simulate a sudden crash to 97.0 (3% drop) with bad AI confidence (0.3)
    crashed_price = 97.0
    ai_confidence = 0.3
    
    did_rebalance = grid.rebalance_grid(new_price=crashed_price, confidence_score=ai_confidence)
    if did_rebalance:
        for lvl in grid.grid_levels:
            print(lvl)

if __name__ == "__main__":
    test_dynamic_grid()
