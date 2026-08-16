import vectorbt as vbt
import pandas as pd
import numpy as np
import requests
from datetime import datetime

def get_hyperliquid_candles(symbol="ZRO", interval="5m", limit=500):
    url = "https://api.hyperliquid.xyz/info"
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": 0,
            "endTime": int(datetime.now().timestamp() * 1000)
        }
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        df = pd.DataFrame(data)
        # HL cols: t, T, o, c, h, l, v, n
        df['Close'] = df['c'].astype(float)
        df.set_index('t', inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def run_zro_optimization():
    print("🔬 HyperNova Live Labs: Optimizing for ZRO...")
    
    # 1. Fetch Live Data
    df = get_hyperliquid_candles("ZRO")
    if df.empty:
        print("❌ Could not fetch ZRO data.")
        return

    price = df['Close']
    print(f"   Loaded {len(df)} candles for ZRO.")
    
    # 2. Define Parameter Grid
    windows = np.arange(10, 80, 5) # Wider search for volatile assets
    sigmas = np.arange(1.5, 3.5, 0.25)
    
    print(f"🧪 Testing {len(windows) * len(sigmas)} combinations...")
    
    # 3. Vectorized Backtest
    bb = vbt.BBANDS.run(price, window=windows, alpha=sigmas, param_product=True)
    
    # Numpy Broadcasting Fix
    entries_values = price.values[:, None] < bb.lower.values
    exits_values = price.values[:, None] > bb.upper.values
    
    entries = pd.DataFrame(entries_values, index=price.index, columns=bb.wrapper.columns)
    exits = pd.DataFrame(exits_values, index=price.index, columns=bb.wrapper.columns)
    
    # 4. Run Portfolio Simulation
    # Fee: 0.01% (Maker)
    pf = vbt.Portfolio.from_signals(price, entries, exits, fees=0.0001, freq='5m')
    
    # 5. Analyze Results
    returns = pf.total_return()
    best_idx = returns.idxmax()
    best_return = returns.max()
    
    print("\n🏆 ZRO OPTIMIZATION COMPLETE 🏆")
    print(f"Best Parameters: Length={best_idx[0]}, Std={best_idx[1]}")
    print(f"Total Return: {best_return * 100:.2f}%")
    
    # Check current setting (35)
    try:
        current_ret = returns[(35, 2.0)] * 100
        print(f"Current Setting (35, 2.0): {current_ret:.2f}%")
    except:
        print("Current setting not in grid.")

if __name__ == "__main__":
    run_zro_optimization()
