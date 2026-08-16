import vectorbt as vbt
import pandas as pd
import numpy as np
import os

def run_optimization():
    print("🔬 HyperNova Labs: Starting Parameter Optimization (VectorBT)...")
    
    # 1. Load Data
    data_path = os.path.join(os.path.dirname(__file__), "data", "BTCUSDT_5m.csv")
    if not os.path.exists(data_path):
        print("❌ Data file not found.")
        return

    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    # Ensure clean data
    df.columns = [c.strip().title() for c in df.columns]
    price = df['Close']
    
    # 2. Define Parameter Grid
    # Testing BB Lengths: 10 to 60 (Step 5)
    # Testing BB StdDev: 1.5 to 3.0 (Step 0.25)
    windows = np.arange(10, 60, 5)
    sigmas = np.arange(1.5, 3.1, 0.25)
    
    print(f"🧪 Testing {len(windows) * len(sigmas)} combinations...")
    
    # 3. Vectorized Backtest (The Magic)
    # Calculate all BBands at once
    # vbt.BBANDS.run generates a matrix of indicators
    fast_ma, slow_ma = vbt.MA.run_combs(price, windows) # Just for MA example, but for BB:
    
    # We proceed with BBANDS
    print("   Calculating Indicators...")
    bb = vbt.BBANDS.run(price, window=windows, alpha=sigmas, param_product=True)
    
    # Logic: Long when Price < Lower, Short when Price > Upper
    # Fix: Use Numpy broadcasting (N, 1) vs (N, M)
    # This works regardless of VectorBT version quirks
    
    entries_values = price.values[:, None] < bb.lower.values
    exits_values = price.values[:, None] > bb.upper.values
    
    # Wrap back to DataFrame for VBT Portfolio
    entries = pd.DataFrame(entries_values, index=price.index, columns=bb.wrapper.columns)
    exits = pd.DataFrame(exits_values, index=price.index, columns=bb.wrapper.columns)
    
    # 4. Run Portfolio Simulation
    print("   Simulating Trades...")
    # Use 0.01% fee (Maker) for optimization to see raw signal quality
    pf = vbt.Portfolio.from_signals(price, entries, exits, fees=0.0001, freq='5m')
    
    # 5. Analyze Results
    returns = pf.total_return()
    best_idx = returns.idxmax()
    best_return = returns.max()
    
    print("\n🏆 OPTIMIZATION COMPLETE 🏆")
    print(f"Best Parameters: Length={best_idx[0]}, Std={best_idx[1]}")
    print(f"Total Return: {best_return * 100:.2f}%")
    print("-" * 30)
    print("Comparison:")
    print(f"Default (20, 2.0): {returns[(20, 2.0)] * 100:.2f}%")
    
    # Heatmap logic could go here
    
if __name__ == "__main__":
    run_optimization()
