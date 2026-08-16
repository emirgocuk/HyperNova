import pandas as pd
import logging
from data_layer.data_ingestor import DataIngestor
import os

logger = logging.getLogger("HistoricalPipeline")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def process_historical_csv_for_training(csv_path: str):
    """
    Reads a raw MT5 CSV file, passes it through our Data Ingestor's 
    Feature Engineering block (Log Returns, ATR, StdDev), and saves an AI-ready dataset.
    """
    if not os.path.exists(csv_path):
        logger.error(f"Could not find historical data file: {csv_path}")
        logger.error("Please run `mt5_ingestor.py` first while your MT5 terminal is open.")
        return
        
    logger.info(f"Loading raw data from: {csv_path}")
    raw_df = pd.read_csv(csv_path)
    
    # Needs to match DataIngestor format
    raw_df['timestamp'] = pd.to_datetime(raw_df['timestamp'])
    
    # Initialize a temporary Ingestor
    ingestor = DataIngestor(symbol="EURUSD", timeframe="5m")
    
    logger.info("Applying Feature Engineering to the entire dataset (Log Returns, ATR, StdDev)...")
    
    # We feed the dataframe directly to the ingestor
    ingestor.df = raw_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
    ingestor.df.set_index('timestamp', inplace=True)
    
    engineered_df = ingestor._feature_engineering()
    
    # Drop rows with NaN values created by windowed calculations (like ATR 14)
    engineered_df.dropna(inplace=True)
    
    output_path = csv_path.replace(".csv", "_ready.csv")
    engineered_df.to_csv(output_path, index=True)  # Keep timestamp as index for reference
    
    logger.info(f"✅ AI-Ready Dataset generated: {output_path}")
    logger.info(f"Size: {len(engineered_df)} rows.")
    logger.info("Next Step: Point the `trainer.py` to this file to update CNN-LSTM weights!")

if __name__ == "__main__":
    # Example expected file path from mt5_ingestor.py
    process_historical_csv_for_training("database/historical/xm_eurusd_m5_180days.csv")
