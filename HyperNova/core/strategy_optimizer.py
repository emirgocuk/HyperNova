import vectorbt as vbt
import pandas as pd
import numpy as np
import requests
from termcolor import cprint
from datetime import datetime

class StrategyOptimizer:
    def __init__(self):
        self.api_url = "https://api.hyperliquid.xyz/info"

    def fetch_data(self, symbol, interval="5m", limit=1000):
        """Fetches fresh candle data from HyperLiquid."""
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol,
                "interval": interval,
                "startTime": 0,
                "endTime": int(datetime.now().timestamp() * 1000)
            }
        }
        try:
            response = requests.post(self.api_url, json=payload, headers={"Content-Type": "application/json"})
            data = response.json()
            if not data: return pd.DataFrame()
            
            df = pd.DataFrame(data)
            # HL cols: t, T, o, c, h, l, v, n
            df['Close'] = df['c'].astype(float)
            df.set_index('t', inplace=True)
            return df
        except Exception as e:
            cprint(f"❌ Error fetching {symbol} data: {e}", "red")
            return pd.DataFrame()

    def optimize_grid(self, symbol):
        """
        Runs VectorBT optimization for the given symbol to find best BB Window & Std.
        Returns: {'window': int, 'std': float, 'roi': float}
        """
        df = self.fetch_data(symbol)
        if df.empty or len(df) < 500:
            cprint(f"⚠️ Not enough data for {symbol} optimization. Using defaults.", "yellow")
            return None

        price = df['Close']
        
        # Search Space
        # Volatile assets need faster windows (10-30), Stable ones need slower (30-60)
        windows = np.arange(10, 65, 5) 
        sigmas = np.arange(1.5, 3.1, 0.25)
        
        # Run VectorBT BBANDS
        try:
            bb = vbt.BBANDS.run(price, window=windows, alpha=sigmas, param_product=True)
            
            # Signal Logic (Mean Reversion)
            # Numpy broadcasting for speed
            entries_values = price.values[:, None] < bb.lower.values
            exits_values = price.values[:, None] > bb.upper.values
            
            entries = pd.DataFrame(entries_values, index=price.index, columns=bb.wrapper.columns)
            exits = pd.DataFrame(exits_values, index=price.index, columns=bb.wrapper.columns)
            
            # Simulate (Maker Fee 0.01%)
            pf = vbt.Portfolio.from_signals(price, entries, exits, fees=0.0001, freq='5m')
            
            returns = pf.total_return()
            best_idx = returns.idxmax() # (window, std)
            best_return = returns.max()
            
            return {
                'window': int(best_idx[0]),
                'std': float(best_idx[1]),
                'roi': best_return * 100
            }
        except Exception as e:
            cprint(f"❌ Optimization Failed: {e}", "red")
            return None
