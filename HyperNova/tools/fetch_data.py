import ccxt
import pandas as pd
import time
import os
from datetime import datetime, timedelta

def fetch_data(symbol="BTC/USDT", timeframe="5m", days=30, source='binance'):
    """
    Fetches historical OHLCV data and saves to CSV.
    Note: Using Binance as it has the deepest free history accessible via CCXT.
    HyperLiquid history can also be fetched but Binance is standard for general backtests.
    """
    print(f"🚀 Starting Data Fetcher: {symbol} [{timeframe}] for {days} days...")
    
    # Initialize Exchange
    exchange = ccxt.binance()
    
    # Calculate start time
    since_ms = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    
    all_candles = []
    
    while since_ms < exchange.milliseconds():
        try:
            print(f"   Fetching since {pd.to_datetime(since_ms, unit='ms')}...")
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=1000)
            
            if not candles:
                break
                
            all_candles.extend(candles)
            
            # Update since_ms to the last candle's time + 1 candle duration
            last_timestamp = candles[-1][0]
            since_ms = last_timestamp + 1 # just move slightly forward
            
            # Rate limit
            time.sleep(exchange.rateLimit / 1000)
            
        except Exception as e:
            print(f"Error: {e}")
            break
            
    # Convert to DataFrame
    df = pd.DataFrame(all_candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df.set_index('Date', inplace=True)
    
    # Save
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    safe_symbol = symbol.replace("/", "")
    filename = f"{data_dir}/{safe_symbol}_{timeframe}.csv"
    df.to_csv(filename)
    
    print(f"✅ Data saved to: {filename}")
    print(f"   Total Candles: {len(df)}")
    print(f"   Range: {df.index[0]} to {df.index[-1]}")

if __name__ == "__main__":
    # Example usage: Fetch 365 days (1 Year) of BTC/USDT 5m data
    fetch_data("BTC/USDT", "5m", days=365)
