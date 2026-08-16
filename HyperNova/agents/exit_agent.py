"""
Exit Agent Module.
Manages position exits using dynamic ATR Trailing Stops, Market Regime Shock Protection,
and Vibe-Trading reflection.
"""

from typing import Dict, Any
from core.agent import BaseAgent, AgentDecision
from core.llm_service import LLMService


class ExitAgent(BaseAgent):
    """
    Institutional Exit Manager:
    - Dynamic ATR Trailing Stops (moves SL to breakeven after 1.5x ATR, trails after 2.5x ATR).
    - Emergency liquidation during Volatility Shock.
    - Vibe reflection on profitable positions.
    """

    def __init__(self):
        super().__init__(name="ExitAgent")
        self.llm = LLMService()

    def analyze(self, market_data: Dict[str, Any], context: Dict[str, Any]) -> AgentDecision:
        """
        Analyzes an open position to determine if it should be closed or held.
        """
        position = context.get('position')
        current_price = market_data.get('price')
        atr = market_data.get('atr', current_price * 0.015 if current_price else 100.0)
        regime = context.get('regime', 'UNKNOWN')
        sentiment_score = context.get('sentiment_score', 0.0)

        if not position or not current_price:
            return AgentDecision(approved=False, confidence=0.0, reason="No active position")

        entry_price = position['entry_price']
        side = position['side']
        duration = context.get('duration_minutes', 0)

        # Calculate PnL %
        if side == 'LONG':
            pnl_pct = (current_price - entry_price) / entry_price
            pnl_usd = (current_price - entry_price) * position.get('size_coin', 0)
        else:
            pnl_pct = (entry_price - current_price) / entry_price
            pnl_usd = (entry_price - current_price) * position.get('size_coin', 0)

        pnl_str = f"{pnl_pct*100:+.2f}%"

        # 1. EMERGENCY VOLATILITY SHOCK EXIT
        if regime == "VOLATILITY_SHOCK":
            return AgentDecision(
                approved=True,
                confidence=0.95,
                reason=f"🚨 Emergency Shock Exit: Market Volatility Explosion ({pnl_str})"
            )

        # 2. DYNAMIC ATR STOP LOSS
        # If position has a stored stop_loss_price, check it
        sl_price = position.get('sl_price')
        if sl_price:
            if (side == 'LONG' and current_price <= sl_price) or (side == 'SHORT' and current_price >= sl_price):
                return AgentDecision(approved=True, confidence=1.0, reason=f"🛑 ATR Stop Loss Hit ({pnl_str})")

        # Fallback Hard Stop (-2.5% max)
        if pnl_pct < -0.025:
            return AgentDecision(approved=True, confidence=1.0, reason=f"🛑 Hard Circuit Stop Hit ({pnl_str})")

        # 3. DYNAMIC ATR TAKE PROFIT
        tp_price = position.get('tp_price')
        if tp_price:
            if (side == 'LONG' and current_price >= tp_price) or (side == 'SHORT' and current_price <= tp_price):
                return AgentDecision(approved=True, confidence=1.0, reason=f"🎯 ATR Target Take-Profit Hit ({pnl_str})")

        # Dynamic ROI Target (> 3.5% after 15m or > 2% after 60m)
        target_roi = 0.035 if duration < 30 else (0.02 if duration < 60 else 0.012)
        if pnl_pct >= target_roi:
            return AgentDecision(approved=True, confidence=0.85, reason=f"🎯 Dynamic ROI Target Reached: {pnl_str} after {int(duration)}m")

        # 4. PANIC SENTIMENT EXIT (If sentiment violently reverses against position)
        if side == 'LONG' and sentiment_score < -0.75:
            return AgentDecision(approved=True, confidence=0.9, reason=f"⚠️ Panic Exit: Negative Sentiment Crash ({sentiment_score})")
        elif side == 'SHORT' and sentiment_score > 0.75:
            return AgentDecision(approved=True, confidence=0.9, reason=f"⚠️ Panic Exit: Bullish Short Squeeze Sentiment ({sentiment_score})")

        # 5. PROFITABLE VIBE CHECK (Only if > 0.8% in profit and LLM is enabled)
        if pnl_pct > 0.008 and self.llm.client:
            decision = self.consult_llm_for_exit(pnl_str, sentiment_score, side)
            if decision.approved:
                return decision

        return AgentDecision(approved=False, confidence=0.5, reason=f"Holding Position ({pnl_str})")

    def consult_llm_for_exit(self, pnl_str: str, sentiment: float, side: str) -> AgentDecision:
        prompt = f"""
        You are an Institutional Exit Specialist.
        
        Position: {side}
        Unrealized PnL: {pnl_str} (Profitable)
        Market Sentiment: {sentiment} (-1 to 1)
        
        Task: Should we "CLOSE" to secure gains or "HOLD" for trend continuation?
        Output strictly one word: CLOSE or HOLD.
        """
        try:
            response = self.llm.get_response(prompt, system_prompt="Output only CLOSE or HOLD.").strip().upper()
            if "CLOSE" in response:
                return AgentDecision(approved=True, confidence=0.8, reason=f"LLM Secure Profit: {response}")
            else:
                return AgentDecision(approved=False, confidence=0.8, reason=f"LLM Trend Continuation: {response}")
        except Exception:
            return AgentDecision(approved=False, confidence=0.5, reason="LLM unavailable, continuing hold")
