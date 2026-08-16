import pandas as pd
import requests
import time
from datetime import datetime
import sys
sys.path.insert(0, 'd:/Projects/playroom/trading-bot/HyperNova')

from core.strategy_utils import calculate_market_cipher_signals
from agents.grid_agent import GridAgent

def fetch_data(symbol, days=365):
    print(f"Fetching {days} days for {symbol}...")
    url = "https://api.hyperliquid.xyz/info"
    
    end_time_ms = int(time.time() * 1000)
    start_time_ms = end_time_ms - (days * 24 * 60 * 60 * 1000)
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": "5m",
            "startTime": start_time_ms,
            "endTime": end_time_ms
        }
    }
    
    response = requests.post(url, json=payload, timeout=30)
    data = response.json()
    
    # Handle both response formats
    if isinstance(data, list):
        candles = data
    elif isinstance(data, dict):
        candles = data.get('candles', data.get('data', []))
    else:
        candles = []
    
    if not candles:
        print(f"No data for {symbol}")
        return pd.DataFrame()
    
    df = pd.DataFrame(candles)
    df['t'] = pd.to_datetime(df['t'], unit='ms')
    df.set_index('t', inplace=True)
    df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'}, inplace=True)
    
    for c in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[c] = df[c].astype(float)
    
    df.sort_index(inplace=True)
    print(f"Got {len(df)} candles")
    return df

def backtest(df, symbol):
    print(f"\nBacktest {symbol}...")
    balance = 10000
    positions = []
    trades = []
    grid_agent = GridAgent()
    
    for i in range(300, len(df)):
        window = df.iloc[i-300:i]
        price = window['Close'].iloc[-1]
        t = window.index[-1]
        
        # Exit logic
        for pos in list(positions):
            mins = (t - pos['time']).total_seconds() / 60
            pnl_pct = ((price - pos['price']) / pos['price']) * 100
            if pos['side'] == 'SHORT':
                pnl_pct = -pnl_pct
            
            if mins > 60 or abs(pnl_pct) > 5:
                pnl = (price - pos['price']) * pos['size']
                if pos['side'] == 'SHORT':
                    pnl = -pnl
                balance += pnl
                trades.append({'pnl': pnl, 'pnl_pct': pnl_pct})
                positions.remove(pos)
        
        # Entry logic
        if not positions:
            grid_res = grid_agent.analyze(window)
            signal = None
            
            if grid_res['action'] == "GRID_SIGNAL":
                signal = grid_res['signal']
            elif grid_res['action'] == "TRENDING":
                mc, _, _, _ = calculate_market_cipher_signals(window)
                if mc:
                    signal = mc
            
            if signal:
                size = 100 / price
                positions.append({'side': signal, 'price': price, 'time': t, 'size': size})
    
    # Stats
    total_return = balance - 10000
    return_pct = (total_return / 10000) * 100
    wins = [t for t in trades if t['pnl'] > 0]
    win_rate = (len(wins) / len(trades) * 100) if trades else 0
    
    print(f"\n=== {symbol} RESULTS ===")
    print(f"Final Balance: ${balance:,.2f}")
    print(f"Return: ${total_return:,.2f} ({return_pct:+.2f}%)")
    print(f"Trades: {len(trades)}")
    print(f"Win Rate: {win_rate:.1f}%")
    
    return {'symbol': symbol, 'balance': balance, 'return': return_pct, 'trades': len(trades), 'win_rate': win_rate}

# Main
print("HyperNova Backtest - BTC and PURR")
print("="*50)

results = []
for symbol in ["BTC", "PURR"]:
    df = fetch_data(symbol)
    if not df.empty:
        res = backtest(df, symbol)
        results.append(res)

print("\n" + "="*50)
print("SUMMARY")
print("="*50)
for r in results:
    print(f"{r['symbol']:6} | Return: {r['return']:+7.2f}% | Trades: {r['trades']:3} | WR: {r['win_rate']:.1f}%")
