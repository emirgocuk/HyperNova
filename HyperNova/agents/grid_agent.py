import pandas_ta as ta
import pandas as pd
from core.llm_service import LLMService

class GridAgent:
    """
    The 'Smart Farmer'.
    Accumulates small profits during sideways markets (Choppy/Ranging).
    Uses AI Sensor to verify if the range is stable.
    """
    def __init__(self, window=35, num_std=2.0):
        # Optimized Default: Window=35 (Found via VectorBT Labs)
        self.adx_threshold = 25
        self.window = window
        self.num_std = num_std
        self.llm = LLMService() # The Sensor
        
    def analyze_range_stability(self, price, upper, lower):
        """
        Ask the AI Sensor: Is this range likely to hold or break?
        """
        if not self.llm.client: return True # Default safe if no AI
        
        range_pct = (upper - lower) / lower * 100
        
        prompt = f"""
        Context: Crypto Price is ranging (ADX Stable).
        Current Price: {price}
        Bollinger Range: {lower} (Bottom) to {upper} (Top).
        Range Width: {range_pct:.2f}%
        
        Question: Is this a safe accumulation range or a potential breakout trap?
        Answer SAFE only if width > 0.5% and price is stable.
        
        Output: SAFE or UNSAFE (One word)
        """
        try:
            resp = self.llm.get_response(prompt, system_prompt="Output SAFE or UNSAFE").strip().upper()
            return "SAFE" in resp
        except:
            return True

    def analyze(self, df):
        """
        Determines if we are in a 'Farmable' state.
        """
        if df.empty or len(df) < 50:
            return {"action": "WAIT", "reason": "Not enough data"}

        # 1. ADX for Trend Strength (We want WEAK trend for grid)
        try:
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            curr_adx = adx_df['ADX_14'].iloc[-1]
        except:
            return {"action": "WAIT", "reason": "ADX Error"}
        
        # 2. If Trending, Don't Grid
        if curr_adx > self.adx_threshold:
            return {"action": "TRENDING", "adx": curr_adx} # Handled by Profit Engine
            
        # 3. Grid Logic (Smart Farmer)
        # Calculate Bollinger Bands
        bb = ta.bbands(df['Close'], length=self.window, std=self.num_std)
        if bb is None or bb.empty:
            return {"action": "WAIT", "reason": "BB Error"}
        
        # Access by index to avoid Column Name issues (BBL, BBM, BBU, BBB, BBP)
        # Standard: Lower(0), Mid(1), Upper(2)
        lower = bb.iloc[-1, 0]
        mid = bb.iloc[-1, 1]
        upper = bb.iloc[-1, 2]
        price = df['Close'].iloc[-1]
        
        # Check if AI approves this range
        # Only verify if we are near edges (about to trade)
        near_threshold = 0.003
        dist_to_lower = (price - lower) / lower
        dist_to_upper = (upper - price) / upper
        
        signal = None
        
        if dist_to_lower < near_threshold:
            # Check AI before catching the knife
            if self.analyze_range_stability(price, upper, lower):
                signal = "LONG"
                
        elif dist_to_upper < near_threshold:
            if self.analyze_range_stability(price, upper, lower):
                signal = "SHORT"
                
        if signal:
            return {
                "action": "GRID_SIGNAL",
                "signal": signal,
                "price": price,
                "lower": lower,
                "upper": upper,
                "reason": f"Range Bound (ADX {curr_adx:.1f})"
            }
            
        return {"action": "WAIT", "reason": f"In Range (ADX {curr_adx:.1f})"}
