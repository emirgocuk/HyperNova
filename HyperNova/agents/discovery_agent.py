import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests

class DiscoveryAgent:
    def __init__(self, exchange_id='hyperliquid'):
        self.exchange_id = exchange_id
        # For HyperLiquid, we might use requests directly as CCXT support varies or use a general CCXT instance for analysis
        # Using binance for "Global Market Data" analysis is often cleaner for indicators if HL history is short,
        # but for trading on HL, we must ensure the pair exists on HL.
        # Strategy: Get list from HL, fetch data from Binance (if HL data is sparse) or HL itself.
        # Let's try to use HL native data via simple API or CCXT if configured.
        
        # For now, we will use CCXT Binance for "Market Discovery" (Deep liquidity reference) 
        # BUT filter only for coins that exist on HyperLiquid.
        self.scanner = ccxt.binance() 
        self.hl_api_url = "https://api.hyperliquid.xyz/info"
        self.blacklist = ['USDC/USDT', 'USDT/USD', 'TUSD/USDT', 'FDUSD/USDT']

    def get_hl_pairs(self):
        """Fetches list of active tradeable pairs on HyperLiquid"""
        try:
            response = requests.post(self.hl_api_url, json={"type": "meta"}, headers={"Content-Type": "application/json"})
            data = response.json()
            universe = data['universe']
            # Convert to CCXT format (e.g., BTC/USDT)
            # HL Universe items are just symbols like {'name': 'BTC', ...}
            symbols = [f"{item['name']}/USDT" for item in universe]
            return symbols
        except Exception as e:
            print(f"Error fetching HL pairs: {e}")
            return []

    def analyze_market(self, limit=30):
        """
        Scans top coins and returns the best one.
        limit: Number of top volume coins to scan.
        """
        print(f"🔍 Hunter Agent: Scanning Top {limit} coins...")
        
        hl_symbols = self.get_hl_pairs()
        if not hl_symbols:
            print("⚠️ Could not fetch HL pairs. Defaulting to BTC.")
            return "BTC/USDT"
            
        # Get Top Volume pairs from Binance (Market Proxy)
        try:
            tickers = self.scanner.fetch_tickers()
            # Filter tickers that also exist on HyperLiquid
            valid_tickers = {k: v for k, v in tickers.items() if k in hl_symbols and k not in self.blacklist}
            
            # Sort by Quote Volume
            sorted_by_vol = sorted(valid_tickers.values(), key=lambda x: x['quoteVolume'], reverse=True)
            top_candidates = sorted_by_vol[:limit]
            
            best_coin = None
            best_score = -1
            
            for t in top_candidates:
                symbol = t['symbol']
                try:
                    # Fetch candles for analysis (1h timeframe for trend)
                    ohlcv = self.scanner.fetch_ohlcv(symbol, '1h', limit=50)
                    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
                    
                    # Calculate ADX (Trend Strength)
                    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
                    if adx_df is None or adx_df.empty: continue
                    adx = adx_df['ADX_14'].iloc[-1]
                    
                    # Calculate Volatility (ATR Normalized)
                    atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
                    price = df['close'].iloc[-1]
                    volatility_pct = (atr / price) * 100
                    
                    # Calculate 24h Change
                    change_pct = (price - df['close'].iloc[0]) / df['close'].iloc[0] * 100
                    
                    # Scoring Logic
                    # We want: High ADX (Trending) + High Volatility (Moving)
                    # We avoid: Low ADX (Chop)
                    
                    if adx > 25:
                        score = adx + (volatility_pct * 10) # Give weight to volatility
                        
                        # Print candidate info
                        # print(f"   Candidate: {symbol} | ADX: {adx:.1f} | Vol: {volatility_pct:.2f}% | Score: {score:.1f}")
                        
                        if score > best_score:
                            best_score = score
                            best_coin = symbol
                            
                except Exception as e:
                    continue
                    
            if best_coin:
                print(f"🦅 Hunter Agent Found: {best_coin} (Score: {best_score:.1f})")
                return best_coin
            else:
                print("⚠️ No strong trends found. Defaulting to BTC.")
                return "BTC/USDT"
                
        except Exception as e:
            print(f"Hunter Agent Error: {e}")
            return "BTC/USDT"

if __name__ == "__main__":
    # Test Run
    agent = DiscoveryAgent()
    hot_coin = agent.analyze_market()
    print(f"Recommended Trade: {hot_coin}")
