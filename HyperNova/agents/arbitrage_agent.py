import requests
from termcolor import cprint
from core.llm_service import LLMService

class ArbitrageAgent:
    def __init__(self):
        self.hl_api_url = "https://api.hyperliquid.xyz/info"
        self.min_apr_threshold = 20.0 # Notify if APR > 20%
        self.llm = LLMService()

    def get_funding_rates(self):
        """
        Fetches current funding rates for all coins on HyperLiquid.
        Returns a list of dictionaries with {coin, funding_rate, apr_percent}.
        """
        try:
            payload = {"type": "metaAndAssetCtxs"}
            response = requests.post(self.hl_api_url, json=payload, headers={"Content-Type": "application/json"})
            data = response.json()
            
            universe = data[0]['universe']
            asset_ctxs = data[1]
            
            opportunities = []
            
            for i, asset_info in enumerate(universe):
                coin = asset_info['name']
                ctx = asset_ctxs[i]
                
                # 'funding' field is the premium/discount rate or velocity
                funding_rate = float(ctx.get('funding', 0.0))
                mark_price = float(ctx['markPx'])
                
                # Convert to APR (Hourly * 24 * 365)
                # Note: Funding is usually 1H on HL? Depends on epoch.
                hourly_rate = funding_rate
                daily_rate = hourly_rate * 24
                apr = daily_rate * 365 * 100 
                
                if apr > self.min_apr_threshold:
                    # Determine Direction:
                    # Funding > 0: Long pays Short. We want to be SHORT to earn.
                    # Funding < 0: Short pays Long. We want to be LONG to earn.
                    side = "SHORT" if funding_rate > 0 else "LONG"
                    
                    opportunities.append({
                        'coin': coin,
                        'hourly_rate': hourly_rate,
                        'apr': apr,
                        'price': mark_price,
                        'recommended_side': side
                    })
            
            # Sort by APR descending
            opportunities.sort(key=lambda x: x['apr'], reverse=True)
            return opportunities

        except Exception as e:
            print(f"Error fetching funding rates: {e}")
            return []

    def verify_opportunity_with_ai(self, opp):
        """
        Uses LLM to check if the opportunity is a trap (e.g. low liquidity scam coins).
        """
        if not self.llm.client:
            print("⚠️ AI Verification disabled (No Key). Skipping check.")
            return True # Assume safe if no AI
            
        coin = opp['coin']
        apr = opp['apr']
        price = opp['price']
        
        cprint(f"🤖 Asking AI about {coin} ({apr:.1f}% APR)...", "cyan")
        
        prompt = f"""
        You are a Crypto Arbitrage Expert.
        
        Opportunity:
        - Asset: {coin}
        - APR: {apr:.2f}% (Funding Rate Arbitrage)
        - Price: ${price}
        
        Context:
        The coin has abnormally high funding rates. This usually means extreme volatility or a short squeeze.
        
        Task:
        Is this coin ({coin}) generally known as a legit asset with decent liquidity, or is it a "shitcoin" / low-cap trap often manipulated?
        
        Output:
        Respond with "SAFE" or "RISKY". One word only.
        """
        
        try:
            response = self.llm.get_response(prompt, system_prompt="One word answer only: SAFE or RISKY.")
            decision = response.strip().upper()
            
            if "SAFE" in decision:
                return True
            else:
                cprint(f"🛑 AI rejected {coin}: {decision}", "red")
                return False
                
        except Exception as e:
            print(f"AI Verification Error: {e}")
            return True # Fallback to safe

    def scan_opportunities(self):
        """
        Main method to call from the bot.
        """
        # print("⚖️ Arbitrage Agent: Scanning Funding Rates...")
        opps = self.get_funding_rates()
        
        if not opps:
            # print("   No high-yield opportunities found (< 20% APR).")
            return None
            
        # print(f"   Found {len(opps)} opportunities!")
        
        # Check top opportunities
        for op in opps[:3]: 
            # Basic Print
            cprint(f"   💰 {op['coin']}: {op['apr']:.2f}% APR (Px: {op['price']})", "green")
            
            # If APR is VERY high (> 200%), run AI check before returning
            if op['apr'] > 200:
                is_safe = self.verify_opportunity_with_ai(op)
                if is_safe:
                    return op # Return verified opportunity
                # If not safe, continue loop to next best
            else:
                # Moderate APR, return immediately
                return op
            
        return None 
