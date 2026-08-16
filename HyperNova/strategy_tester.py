import pandas as pd
import numpy as np
import argparse
import os
import sys

# Ensure HyperNova is in path
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def run_backtest(strategy_name: str, csv_path: str):
    """
    Simulates a strategy over historical data and calculates core performance metrics.
    """
    print(f"\n=============================================")
    print(f"🚀 Strategist Backtest Engine: {strategy_name}")
    print(f"=============================================")
    print(f"📂 Loading Data: {csv_path}...")
    
    if not os.path.exists(csv_path):
        print(f"❌ Error: Data file '{csv_path}' not found.")
        return

    df = pd.read_csv(csv_path)
    
    # Needs to match MT5 data format: time, open, high, low, close, tick_volume
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
        df.sort_values(by='time', inplace=True)
    
    # 1. Load Strategy
    try:
        # Dynamically import
        if strategy_name == "ema_cross":
            from strategies.example_ema_cross import EMACrossStrategy
            strategy = EMACrossStrategy()
        elif strategy_name == "elirox":
            from strategies.elirox_grid import EliroxGridStrategy
            # Start with $10k, trade BTC 64k to 70k
            strategy = EliroxGridStrategy(high_price=70316, low_price=64597, levels=25, base_lot=0.2)
        else:
            print(f"❌ Error: Strategy '{strategy_name}' is not registered yet.")
            return
            
    except Exception as e:
        print(f"❌ Error loading strategy: {e}")
        return

    print("🧠 Generating Signals...")
    df_signals = strategy.generate_signals(df)
    
    # 2. Simulate Trades (Very Basic Approach)
    print("📊 Simulating Trades...")
    
    initial_balance = 10000.0
    balance = initial_balance
    position = 0 # 0=Flat, 1=Long, -1=Short
    entry_price = 0.0
    
    wins = 0
    losses = 0
    trades = []
    
    # Extremely simplified execution loop (Assuming we enter on close and exit on opposite signal)
    # Ignore spread/commission for fast prototyping
    for idx, row in df_signals.iterrows():
        signal = row.get('signal', 0)
        current_price = row['close']
        
        # If we have a position and get an opposite signal, close it
        if position == 1 and signal == -1:
            # Close Long
            pnl = (current_price - entry_price) / entry_price * balance
            balance += pnl
            if pnl > 0: wins += 1
            else: losses += 1
            trades.append(pnl)
            position = 0
            
        elif position == -1 and signal == 1:
            # Close Short
            pnl = (entry_price - current_price) / entry_price * balance
            balance += pnl
            if pnl > 0: wins += 1
            else: losses += 1
            trades.append(pnl)
            position = 0
            
        # Open new position if flat
        if position == 0 and signal == 1:
            position = 1
            entry_price = current_price
        elif position == 0 and signal == -1:
            position = -1
            entry_price = current_price

    # 3. Calculate Results
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    net_profit = balance - initial_balance
    net_profit_pct = (net_profit / initial_balance) * 100
    
    print("\n========= 📈 BACKTEST RESULTS 📈 =========")
    print(f"Total Trades : {total_trades}")
    print(f"Win Rate     : {win_rate:.2f}% ({wins} W / {losses} L)")
    print(f"Init Balance : ${initial_balance:,.2f}")
    print(f"Final Balance: ${balance:,.2f}")
    print(f"Net Profit   : ${net_profit:,.2f} ({net_profit_pct:+.2f}%)")
    print("=============================================\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Strategy Prototyping Engine")
    parser.add_argument("--strategy", type=str, required=True, help="Name of strategy: ema_cross, elirox, etc.")
    parser.add_argument("--data", type=str, default="database/historical/xm_eurusd_m5_180days_ready.csv", help="Path to historical CSV data")
    
    args = parser.parse_args()
    run_backtest(args.strategy, args.data)
