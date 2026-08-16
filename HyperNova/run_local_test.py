import asyncio
import logging
from datetime import datetime

# Local imports
from data_layer.data_ingestor import DataIngestor
from ai_engine.brain_service import BrainService
from execution_engine.execution_manager import ExecutionManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("LocalRunner")

class LocalTestRunner:
    """
    Bypasses Docker/Redis for testing purposes.
    Connects Data Ingestor -> Brain -> Execution Manager using asyncio.Queue over RAM.
    """
    def __init__(self):
        self.message_queue = asyncio.Queue()
        self.ingestor = DataIngestor(symbol="EURUSD", timeframe="1m")
        self.brain = BrainService()
        self.executor = ExecutionManager(start_equity=1000.0)
        
    async def mock_redis_publish(self, data):
        """Overrides the DBWriter behavior to publish to local Queue instead of Redis"""
        await self.message_queue.put(data)
        
    async def dummy_data_ingestor_loop(self):
        """Modified ingestor loop that skips Redis and uses RAM Queue"""
        logger.info("Starting Data Ingestor (Local Memory Mode)...")
        self.ingestor.is_running = True
        
        # Override the db writer method playfully
        self.ingestor.db.publish_hot_stream = lambda data: asyncio.create_task(self.mock_redis_publish(data))
        self.ingestor.db.write_timescale = lambda data: None # Skip postgres
        
        # Pre-seed (Mocking historical DB load)
        logger.info("Pre-seeding 60 candles so Brain can see an 'image'...")
        for _ in range(60):
            candle = await self.ingestor._mock_fetch_candle()
            self.ingestor.df.loc[candle['timestamp']] = [candle['open'], candle['high'], candle['low'], candle['close'], candle['volume']]
            
        while self.ingestor.is_running:
            try:
                candle = await self.ingestor._mock_fetch_candle()
                self.ingestor.df.loc[candle['timestamp']] = [candle['open'], candle['high'], candle['low'], candle['close'], candle['volume']]
                
                # Keep small
                if len(self.ingestor.df) > 100:
                    self.ingestor.df = self.ingestor.df.iloc[-100:]
                    
                engineered_df = self.ingestor._feature_engineering()
                latest = engineered_df.iloc[-1]
                
                payload = {
                    'symbol': self.ingestor.symbol,
                    'open': latest['open'], 'high': latest['high'], 'low': latest['low'], 'close': latest['close'], 'volume': latest['volume'],
                    'log_return': float(latest['log_return']) if not (latest.isna()['log_return']) else 0.0,
                    'atr': float(latest['atr']) if not (latest.isna()['atr']) else 0.0,
                    'std_dev': float(latest['std_dev']) if not (latest.isna()['std_dev']) else 0.0
                }
                
                self.ingestor.db.publish_hot_stream(payload)
                await asyncio.sleep(0.5) # Generate a candle every 0.5s for fast testing
                
            except Exception as e:
                logger.error(f"Ingestor Error: {e}")
                
    async def dummy_brain_loop(self):
        """Listens to the RAM Queue instead of Redis PubSub"""
        logger.info("Starting Brain Service (Local Memory Mode)...")
        while True:
            data = await self.message_queue.get()
            
            # The Brain processes the candle
            await self.brain.process_candle(data)
            
            # Simulate The Brain outputting a signal if confidence is high (hack for testing)
            if len(self.brain.candle_buffer) == self.brain.window_size:
                # Randomly fire a trade for testing Execution Manager
                import random
                if random.random() > 0.7:
                    action = random.choice(["BUY", "SELL"])
                    confidence = random.uniform(0.5, 0.95)
                    price = data['close']
                    await self.executor.execute_trade(data['symbol'], action, price, confidence)

async def main():
    runner = LocalTestRunner()
    
    # Run both microservices concurrently in RAM
    task1 = asyncio.create_task(runner.dummy_data_ingestor_loop())
    task2 = asyncio.create_task(runner.dummy_brain_loop())
    
    # Let it run for 10 seconds to watch the magic happen
    await asyncio.sleep(10)
    logger.info("Test complete. Shutting down mock runners...")
    runner.ingestor.is_running = False
    task1.cancel()
    task2.cancel()

if __name__ == "__main__":
    asyncio.run(main())
