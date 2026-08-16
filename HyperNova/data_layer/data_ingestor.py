import asyncio
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from data_layer.db_writer import DBWriter

# Configure logging for XAI (Explainable AI) and general debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataIngestor")

class DataIngestor:
    """
    The Sensory System: Asynchronously fetches data from broker (XM/CCXT),
    computes log returns and volatility clusters, and prepares for DB insertion.
    """
    def __init__(self, symbol: str, timeframe: str = '1m', atr_period: int = 14):
        self.symbol = symbol
        self.timeframe = timeframe
        self.atr_period = atr_period
        
        # In-memory dataframe to hold recent candles for feature engineering
        # We only need enough history to calculate indicators (e.g., 200 periods)
        self.df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        self.df.set_index('timestamp', inplace=True)
        
        self.db = DBWriter()
        self.is_running = False

    def _feature_engineering(self) -> pd.DataFrame:
        """
        Applies mechanical system analogies to financial data.
        Calculates Log Returns (velocity) and Volatility Clusters (stress).
        """
        df = self.df.copy()
        
        # Minimum data required for ATR
        if len(df) <= self.atr_period:
            return df
            
        # 1. Log Returns: ln(P_t / P_{t-1})
        # Better statistical properties than simple percentage returns
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        # 2. Volatility Clusters (ATR - Average True Range)
        # TR = max(H-L, |H-Cp|, |L-Cp|)
        df['prev_close'] = df['close'].shift(1)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['prev_close'])
        df['tr3'] = abs(df['low'] - df['prev_close'])
        df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Wilder's Smoothing for ATR
        df['atr'] = df['true_range'].ewm(alpha=1/self.atr_period, min_periods=self.atr_period).mean()
        
        # 3. Standard Deviation of Log Returns (Volatility metric)
        df['std_dev'] = df['log_return'].rolling(window=self.atr_period).std()
        
        # Cleanup temporary columns
        df.drop(columns=['prev_close', 'tr1', 'tr2', 'tr3', 'true_range'], inplace=True)
        
        return df

    async def _mock_fetch_candle(self) -> dict:
        """
        Mocking an async stream from XM Broker since actual FIX/API requires real keys.
        In production, this would be an async websocket client or ccxt.watch_ohlcv
        """
        await asyncio.sleep(1) # Simulate network latency
        
        # Simulate price movement based on random walk
        last_close = self.df['close'].iloc[-1] if not self.df.empty else 100.0
        movement = np.random.normal(0, 0.1) # Mean 0, Std 0.1
        
        now = datetime.now()
        new_close = last_close + movement
        
        return {
            'timestamp': pd.Timestamp(now),
            'open': last_close,
            'high': max(last_close, new_close) + abs(np.random.normal(0, 0.05)),
            'low': min(last_close, new_close) - abs(np.random.normal(0, 0.05)),
            'close': new_close,
            'volume': np.random.randint(10, 1000)
        }

    async def stream_data(self):
        """
        Main async loop for the Data Ingestor.
        """
        logger.info(f"Starting Data Ingestor for {self.symbol} on {self.timeframe}")
        self.is_running = True
        
        # Pre-seed with some dummy data to avoid startup NaN issues
        logger.info("Pre-seeding historical data...")
        for _ in range(50):
            candle = await self._mock_fetch_candle()
            self.df.loc[candle['timestamp']] = [candle['open'], candle['high'], candle['low'], candle['close'], candle['volume']]
        
        while self.is_running:
            try:
                # 1. Fetch data asynchronously (non-blocking)
                candle = await self._mock_fetch_candle()
                
                # 2. Append to in-memory DataFrame
                self.df.loc[candle['timestamp']] = [
                    candle['open'], 
                    candle['high'], 
                    candle['low'], 
                    candle['close'], 
                    candle['volume']
                ]
                
                # Keep DataFrame size manageable (e.g., last 500 candles)
                if len(self.df) > 500:
                    self.df = self.df.iloc[-500:]
                
                # 3. Perform Feature Engineering (Fly-by calculation)
                engineered_df = self._feature_engineering()
                
                # Get the latest computed row
                latest = engineered_df.iloc[-1]
                
                # 4. Stream to Redis / DB
                payload = {
                    'timestamp': latest.name.isoformat(),
                    'symbol': self.symbol,
                    'timeframe': self.timeframe,
                    'open': latest['open'],
                    'high': latest['high'],
                    'low': latest['low'],
                    'close': latest['close'],
                    'volume': latest['volume'],
                    'log_return': float(latest['log_return']) if not pd.isna(latest['log_return']) else None,
                    'atr': float(latest['atr']) if not pd.isna(latest['atr']) else None,
                    'std_dev': float(latest['std_dev']) if not pd.isna(latest['std_dev']) else None
                }
                
                # Push Hot Data to Redis for "The Brain" to consume instantly
                self.db.publish_hot_stream(payload)
                
                # Write to TimescaleDB for Historical Training
                self.db.write_timescale(payload)
                
                logger.info(
                    f"Processed {self.symbol} | Close: {latest['close']:.4f} | "
                    f"Log Return: {latest['log_return']:.5f} | ATR: {latest['atr']:.4f} | "
                    f"StdDev: {latest['std_dev']:.5f}"
                )
                
            except Exception as e:
                logger.error(f"Error in data stream: {e}", exc_info=True)
                await asyncio.sleep(5) # Delay before retry on failure

    def stop(self):
        self.is_running = False
        self.db.disconnect()
        logger.info("Stopping Data Ingestor...")

if __name__ == "__main__":
    # Test execution
    ingestor = DataIngestor(symbol="EURUSD", timeframe="1m")
    
    try:
        asyncio.run(ingestor.stream_data())
    except KeyboardInterrupt:
        ingestor.stop()
