import logging
import asyncio
from datetime import datetime

logger = logging.getLogger("CircuitBreaker")

class CircuitBreaker:
    """
    The Safety Valve: Hard-coded engineering safety margins.
    Prevents catastrophic loss regardless of AI confidence.
    """
    def __init__(self, max_daily_drawdown_pct: float = 0.03):
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.start_of_day_equity = 0.0
        self.current_equity = 0.0
        self.is_tripped = False
        self.trip_time = None
        self.current_day = datetime.now().date()

    def update_equity(self, new_equity: float):
        """Update the daily equity and check against drawdown limits."""
        today = datetime.now().date()
        
        # Reset tracker on a new day
        if today > self.current_day:
            self._reset_daily(new_equity)
            return

        # Initialize start of day equity if not set
        if self.start_of_day_equity == 0.0:
            self.start_of_day_equity = new_equity
            
        self.current_equity = new_equity
        self._check_limits()

    def _reset_daily(self, new_equity: float):
        logger.info(f"🌅 New Day. Resetting Equity tracker. Starting balance: ${new_equity:.2f}")
        self.current_day = datetime.now().date()
        self.start_of_day_equity = new_equity
        self.current_equity = new_equity
        self.is_tripped = False
        self.trip_time = None

    def _check_limits(self):
        if self.is_tripped:
            return # Already tripped for the day
            
        drawdown_amount = self.start_of_day_equity - self.current_equity
        drawdown_pct = drawdown_amount / self.start_of_day_equity if self.start_of_day_equity > 0 else 0
        
        if drawdown_pct >= self.max_daily_drawdown_pct:
            self.is_tripped = True
            self.trip_time = datetime.now()
            logger.error(f"🚨 CIRCUIT BREAKER TRIPPED! 🚨")
            logger.error(f"Equity dropped by {drawdown_pct*100:.2f}% (Limit: {self.max_daily_drawdown_pct*100:.2f}%)")
            logger.error(f"Start: ${self.start_of_day_equity:.2f} | Current: ${self.current_equity:.2f}")
            logger.error("SYSTEM LOCKED UNTIL TOMORROW.")

class SlippageTracker:
    """Tracks the gap between AI signal price and actual broker fill price."""
    def __init__(self):
        self.trades = []
        
    def log_trade(self, symbol: str, action: str, expected_price: float, actual_price: float):
        slippage = abs(expected_price - actual_price)
        slippage_pct = (slippage / expected_price) * 100
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "action": action,
            "expected_price": expected_price,
            "actual_price": actual_price,
            "slippage_amount": slippage,
            "slippage_pct": slippage_pct
        }
        self.trades.append(log_entry)
        
        if slippage_pct > 0.05: # Warn if slip is > 0.05%
            logger.warning(f"⚠️ High Slippage on {action} {symbol}: Expected {expected_price}, Got {actual_price} (Slip: {slippage_pct:.3f}%)")
        else:
            logger.info(f"✅ Trade Executed {action} {symbol} at {actual_price} (Slip: {slippage_pct:.3f}%)")
            
        # In production, this data writes back to TimescaleDB via db_writer.py
        return log_entry

class ExecutionManager:
    """
    Receives signals (e.g., from Redis/Brain), checks Circuit Breaker, 
    manages the Dynamic Grid, and executes via Broker API (Mocked).
    """
    def __init__(self, start_equity: float = 10000.0):
        self.circuit_breaker = CircuitBreaker(max_daily_drawdown_pct=0.03)
        self.circuit_breaker.update_equity(start_equity)
        self.slippage_tracker = SlippageTracker()

    async def execute_trade(self, symbol: str, action: str, requested_price: float, confidence: float):
        """Simulates sending an order to the broker (e.g., XM / CCXT)."""
        logger.info(f"📥 Received {action} Signal for {symbol} at {requested_price} (AI Conf: {confidence*100:.0f}%)")
        
        # 1. HARD STOP: Check Circuit Breaker
        if self.circuit_breaker.is_tripped:
            logger.error(f"❌ Trade Rejected: Circuit breaker is active. Safe mode enabled.")
            return False

        # 2. Confidence Gating
        if confidence < 0.60:
            logger.warning(f"⚠️ Trade Rejected: AI Confidence ({confidence*100:.0f}%) is below 60% threshold.")
            return False

        # 3. Simulate Broker Execution Latency and Slippage
        await asyncio.sleep(0.1) # 100ms latency
        
        # Simulate slippage (worse fill for market orders/volatility)
        slip_direction = 1 if action == "BUY" else -1
        actual_price = requested_price + (requested_price * 0.0002 * slip_direction) # 0.02% slip
        
        # 4. Log Execution
        self.slippage_tracker.log_trade(symbol, action, requested_price, actual_price)
        return True

async def test_execution_manager():
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    print("--- Testing Execution Manager ---")
    
    manager = ExecutionManager(start_equity=1000.0)
    
    # 1. Good Trade
    await manager.execute_trade("EURUSD", "BUY", 1.1000, 0.85)
    
    # 2. Bad Confidence Trade
    await manager.execute_trade("EURUSD", "SELL", 1.1050, 0.40)
    
    # 3. Simulate heavy loss
    print("\n--- Simulating Market Crash ---")
    manager.circuit_breaker.update_equity(960.0) # $40 loss on $1000 (4%) -> SHOULD TRIP
    
    # 4. Attempt trade while tripped
    await manager.execute_trade("EURUSD", "BUY", 1.0500, 0.99) # Even high confidence AI is blocked

if __name__ == "__main__":
    asyncio.run(test_execution_manager())
