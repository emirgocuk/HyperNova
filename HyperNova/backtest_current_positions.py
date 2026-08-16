"""
Backtest for Current Active Positions
Fetches 1 year of 5m data for BTC and PURR and runs the HyperNova strategy
"""
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
import json

# Import strategy components
from core.strategy_utils import calculate_market_cipher_signals
from agents.grid_agent import GridAgent

def fetch_historical_data(symbol, interval="5m", days=365):
    """Fetch historical OHLCV data from HyperLiquid"""
    print(f"📊 Fetching {days} days of {interval} data for {symbol}...")
    
    url = "https://api.hyperliquid.xyz/info"
    
    # Calculate time range
    end_time_ms = int(time.time() * 1000)
    start_time_ms = end_time_ms - (days * 24 * 60 * 60 * 1000)
    
    coin_name = symbol.split('/')[0] if '/' in symbol else symbol
    
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin_name,
            "interval": interval,
            "startTime": start_time_ms,
            "endTime": end_time_ms
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        data = response.json()
        
        candles = data.get('candles', data)
        
        if not candles:
            print(f"⚠️ No data received for {symbol}")
            return pd.DataFrame()
        
        df = pd.DataFrame(candles)
        df['t'] = pd.to_datetime(df['t'], unit='ms')
        df.set_index('t', inplace=True)
        
        df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'}, inplace=True)
        
        for c in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[c] = df[c].astype(float)
        
        df.sort_index(inplace=True)
        
        print(f"✅ Fetched {len(df)} candles for {symbol} ({df.index[0]} to {df.index[-1]})")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def run_strategy_backtest(df, symbol, start_balance=10000):
    """Run HyperNova strategy on historical data"""
    print(f"\n🚀 Running backtest for {symbol}...")
    
    balance = start_balance
    positions = []
    trades = []
    
    grid_agent = GridAgent()
    
    # Use rolling window for analysis
    window_size = 300  # 5m * 300 = 25 hours of data
    
    for i in range(window_size, len(df)):
        window_df = df.iloc[i-window_size:i]
        current_price = window_df['Close'].iloc[-1]
        current_time = window_df.index[-1]
        
        # Check exit conditions for open positions
        for pos in list(positions):
            duration_mins = (current_time - pos['entry_time']).total_seconds() / 60
            
            # Simple exit logic: close after 60 minutes or 5% profit/loss
            pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
            if pos['side'] == 'SHORT':
                pnl_pct = -pnl_pct
            
            should_exit = False
            exit_reason = ""
            
            if duration_mins > 60:
                should_exit = True
                exit_reason = "Time limit"
            elif pnl_pct > 5:
                should_exit = True
                exit_reason = "Take profit"
            elif pnl_pct < -5:
                should_exit = True
                exit_reason = "Stop loss"
            
            if should_exit:
                pnl = (current_price - pos['entry_price']) * pos['size']
                if pos['side'] == 'SHORT':
                    pnl = -pnl
                
                balance += pnl
                
                trades.append({
                    'symbol': symbol,
                    'side': pos['side'],
                    'entry_price': pos['entry_price'],
                    'exit_price': current_price,
                    'entry_time': pos['entry_time'],
                    'exit_time': current_time,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'reason': exit_reason
                })
                
                positions.remove(pos)
        
        # Generate signals if no position
        if len(positions) == 0:
            # Grid Agent Analysis
            grid_res = grid_agent.analyze(window_df)
            
            signal = None
            source = None
            
            if grid_res['action'] == "GRID_SIGNAL":
                signal = grid_res['signal']
                source = "GRID"
            elif grid_res['action'] == "TRENDING":
                # Market Cipher
                mc_signal, _, _, _ = calculate_market_cipher_signals(window_df)
                if mc_signal:
                    signal = mc_signal
                    source = "CIPHER"
            
            if signal:
                # Open position
                position_size_usd = 100
                size_coin = position_size_usd / current_price
                
                positions.append({
                    'side': signal,
                    'entry_price': current_price,
                    'entry_time': current_time,
                    'size': size_coin,
                    'source': source
                })
    
    # Close any remaining positions at the end
    if positions:
        final_price = df['Close'].iloc[-1]
        final_time = df.index[-1]
        for pos in positions:
            pnl = (final_price - pos['entry_price']) * pos['size']
            if pos['side'] == 'SHORT':
                pnl = -pnl
            
            balance += pnl
            pnl_pct = ((final_price - pos['entry_price']) / pos['entry_price']) * 100
            if pos['side'] == 'SHORT':
                pnl_pct = -pnl_pct
            
            trades.append({
                'symbol': symbol,
                'side': pos['side'],
                'entry_price': pos['entry_price'],
                'exit_price': final_price,
                'entry_time': pos['entry_time'],
                'exit_time': final_time,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'reason': 'Final close'
            })
    
    return balance, trades

def analyze_results(symbol, start_balance, final_balance, trades):
    """Analyze backtest results"""
    print(f"\n{'='*60}")
    print(f"📊 BACKTEST RESULTS: {symbol}")
    print(f"{'='*60}")
    
    total_return = final_balance - start_balance
    return_pct = (total_return / start_balance) * 100
    
    print(f"💰 Start Balance: ${start_balance:,.2f}")
    print(f"💰 Final Balance: ${final_balance:,.2f}")
    print(f"📈 Total Return:  ${total_return:,.2f} ({return_pct:+.2f}%)")
    print(f"📊 Total Trades:  {len(trades)}")
    
    if trades:
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        
        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
        
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        
        max_win = max((t['pnl'] for t in trades), default=0)
        max_loss = min((t['pnl'] for t in trades), default=0)
        
        print(f"✅ Winning Trades: {len(wins)} ({win_rate:.1f}%)")
        print(f"❌ Losing Trades:  {len(losses)}")
        print(f"💵 Avg Win:  ${avg_win:,.2f}")
        print(f"💸 Avg Loss: ${avg_loss:,.2f}")
        print(f"🎯 Best Trade:  ${max_win:,.2f}")
        print(f"⚠️ Worst Trade: ${max_loss:,.2f}")
        
        # Show last 5 trades
        print(f"\n📜 Last 5 Trades:")
        for trade in trades[-5:]:
            pnl_color = "+" if trade['pnl'] > 0 else ""
            print(f"  {trade['side']:5} | Entry: ${trade['entry_price']:8.2f} | Exit: ${trade['exit_price']:8.2f} | "
                  f"PnL: {pnl_color}${trade['pnl']:7.2f} ({trade['pnl_pct']:+.2f}%) | {trade['reason']}")
    
    print(f"{'='*60}\n")
    
    return {
        'symbol': symbol,
        'start_balance': start_balance,
        'final_balance': final_balance,
        'total_return': total_return,
        'return_pct': return_pct,
        'total_trades': len(trades),
        'winning_trades': len([t for t in trades if t['pnl'] > 0]),
        'losing_trades': len([t for t in trades if t['pnl'] < 0]),
        'win_rate': win_rate if trades else 0,
        'max_win': max((t['pnl'] for t in trades), default=0),
        'max_loss': min((t['pnl'] for t in trades), default=0)
    }

if __name__ == "__main__":
    print("🔥 HyperNova Backtest - Current Positions")
    print("=" * 60)
    
    # Current positions
    symbols = ["BTC", "PURR"]
    
    all_results = []
    
    for symbol in symbols:
        # Fetch data
        df = fetch_historical_data(symbol, interval="5m", days=365)
        
        if df.empty:
            print(f"⚠️ Skipping {symbol} - no data available")
            continue
        
        # Run backtest
        final_balance, trades = run_strategy_backtest(df, symbol, start_balance=10000)
        
        # Analyze
        results = analyze_results(symbol, 10000, final_balance, trades)
        all_results.append(results)
        
        # Save trades to file
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty:
            filename = f"backtest_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            trades_df.to_csv(f"reports/{filename}", index=False)
            print(f"💾 Trades saved to reports/{filename}")
    
    # Summary
    if all_results:
        print("\n" + "="*60)
        print("📊 OVERALL SUMMARY")
        print("="*60)
        for r in all_results:
            print(f"{r['symbol']:6} | Return: {r['return_pct']:+7.2f}% | Trades: {r['total_trades']:3} | Win Rate: {r['win_rate']:.1f}%")
        
        avg_return = sum(r['return_pct'] for r in all_results) / len(all_results)
        print(f"\n🎯 Average Return: {avg_return:+.2f}%")
