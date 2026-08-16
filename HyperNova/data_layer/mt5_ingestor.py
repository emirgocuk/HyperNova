import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger("MT5Ingestor")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MT5Ingestor:
    """
    Connects to the local MetaTrader 5 Terminal (XM Broker).
    Provides methods to pull thousands of historical candles for AI Training
    and real-time candles for live inference.
    """
    def __init__(self):
        # Establish connection to the MetaTrader 5 terminal
        if not mt5.initialize():
            logger.error(f"initialize() failed, error code = {mt5.last_error()}")
            # It's important that the XM MT5 Terminal is OPEN and logged in on this PC.
            raise ConnectionError("Make sure MetaTrader 5 Terminal is open and logged in.")
            
        logger.info(f"✅ Connected to MetaTrader 5 | Version: {mt5.version()}")

    def fetch_historical_data(self, symbol: str = "EURUSD", timeframe=mt5.TIMEFRAME_M5, days: int = 365) -> pd.DataFrame:
        """
        Fetches 'days' worth of historical data from MT5.
        """
        logger.info(f"Attempting to fetch {days} days of {symbol} data on {timeframe} timeframe...")
        
        # Check if symbol is available in Market Watch
        if not mt5.symbol_select(symbol, True):
            logger.error(f"Failed to select {symbol}. Is it available in your MT5 Market Watch?")
            return pd.DataFrame()

        # Date range calculations
        utc_from = datetime.now() - timedelta(days=days)
        utc_to = datetime.now()
        
        # Pull the rates (Candlesticks)
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to)
        
        if rates is None or len(rates) == 0:
            logger.error(f"No data retrieved for {symbol}. Error code: {mt5.last_error()}")
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(rates)
        
        # Convert the timestamp from Unix to Datetime String (matching our Data Ingestor expectations)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Rename columns to match our existing architecture
        df.rename(columns={'time': 'timestamp', 'real_volume': 'volume'}, inplace=True)
        # Drop unnecessary 'tick_volume' and 'spread' if we don't need them
        df.drop(columns=['tick_volume', 'spread'], inplace=True, errors='ignore')
        
        logger.info(f"✅ Successfully downloaded {len(df)} candles for {symbol}.")
        return df

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """Utility to save raw historical data before feature engineering."""
        os.makedirs("database/historical", exist_ok=True)
        filepath = os.path.join("database/historical", filename)
        df.to_csv(filepath, index=False)
        logger.info(f"💾 Data saved to {filepath}")

    def shutdown(self):
        mt5.shutdown()
        logger.info("MetaTrader 5 connection closed.")

def download_xm_history():
    """Script to trigger a massive historical download for training."""
    try:
        ingestor = MT5Ingestor()
        
        # Adjust TIMEFRAME as needed (e.g., mt5.TIMEFRAME_M1, mt5.TIMEFRAME_M5, mt5.TIMEFRAME_H1)
        # 1-Minute data for a year is huge (~370k rows). 
        # Using 5-Minute data as a good balance for Regime Detection.
        df = ingestor.fetch_historical_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M5, days=180) # 6 Months
        
        if not df.empty:
            ingestor.save_to_csv(df, "xm_eurusd_m5_180days.csv")
            
        ingestor.shutdown()
        
    except Exception as e:
        logger.error(f"Failed to run MT5 Ingestor: {e}")
        logger.error("!!! Ensure MetaTrader 5 Terminal is OPEN and you are logged into your XM account !!!")

if __name__ == "__main__":
    download_xm_history()
