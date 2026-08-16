import pandas as pd
from backtesting import Backtest
from strategies.stoch_rsi import StochRSIStrategy
from strategies.market_cipher import MarketCipherStrategy
from strategies.kama_strategy import KAMAStrategy
from strategies.profit_engine_strategy import ProfitEngineStrategy
import os

def load_data(filepath):
    """
    Load data from CSV and prepare it for backtesting.
    """
    print(f"Loading data from {filepath}...")
    try:
        # Based on roadmap data format observation
        # It often has headers or sometimes not. We'll try standard read first.
        data = pd.read_csv(filepath)
        
        # Rename columns to standard Backtesting.py format (Open, High, Low, Close, Volume)
        # Check if typically crypto data columns exist
        data.columns = [c.strip().title() for c in data.columns]
        
        # Handle Date index
        if 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date'])
            data.set_index('Date', inplace=True)
        elif 'Timestamp' in data.columns:
             data['Timestamp'] = pd.to_datetime(data['Timestamp'])
             data.set_index('Timestamp', inplace=True)
        # If the index is already datetime string but unnamed
        elif isinstance(data.index, pd.RangeIndex) and 'Datetime' in data.columns:
             data['Datetime'] = pd.to_datetime(data['Datetime'])
             data.set_index('Datetime', inplace=True)
             
        # Ensure numeric
        cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
        
        data = data.dropna()
        return data
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def main():
    # Path to a sample data file
    # Use absolute path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    
    # Fallback default file just in case
    data_file = "BTC-1h-1000wks-data.csv"
    
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
    # Prioritize the fresh data we just fetched
    target_file = "BTCUSDT_5m.csv"
    if target_file in csv_files:
        data_file = target_file
        print(f"Found target data file: {data_file}")
    elif csv_files:
        data_file = csv_files[0]
        print(f"Found data file: {data_file}")
    else:
        print("No CSV files found in data directory!")
        return

    full_path = os.path.join(data_dir, data_file)
    data = load_data(full_path)
    
    if data is None or data.empty:
        print("Data is empty or invalid.")
        return

    print("Starting Backtest (Profit Engine V2: Hunter + Farmer)...")
    # Slice data for speed (Last 10,000 candles ~ 1 Month of 5m data)
    data = data.tail(10000)
    bt = Backtest(data, ProfitEngineStrategy, cash=1_000_000, commission=0.0006)  
    stats = bt.run()
    print(stats)
    
    # Save plot
    # bt.plot(filename='HyperNova_Backtest.html', open_browser=False)
    print("Backtest finished.")

if __name__ == "__main__":
    main()
