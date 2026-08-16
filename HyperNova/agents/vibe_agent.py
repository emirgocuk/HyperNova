"""
Vibe-Trading Multi-Agent Reasoning & Consensus Engine.
Inspired by HKUDS Vibe-Trading: implements multi-agent debate, macro vibe check,
and quantitative reflection to filter out low-conviction or dangerous trades.
"""

import json
from typing import Dict, Any, List, Optional
from core.agent import BaseAgent, AgentDecision
from core.llm_service import LLMService


class VibeAgent(BaseAgent):
    """
    Orchestrates a 3-agent debate protocol before trade entry or exit:
    1. Macro & Social Vibe Analyst (Funding rates, social sentiment, macro risk)
    2. Quantitative Critic (Regime alignment, indicator confluence)
    3. Risk Auditor (Reward/Risk ratio, position safety)
    """

    def __init__(self):
        super().__init__(name="VibeTradingEngine")
        self.llm = LLMService()

    def analyze(self, market_data: Dict[str, Any], context: Dict[str, Any]) -> AgentDecision:
        """
        Implements BaseAgent interface. Extracts parameters from market_data & context and runs debate.
        """
        symbol = market_data.get('symbol', 'BTC')
        signal = context.get('signal_type', 'LONG')
        price = market_data.get('price', 0.0)
        regime_info = context.get('regime_info', {'regime': 'RANGING_CHOP', 'confidence': 0.7})
        ai_forecast = context.get('ai_forecast', {'signal': signal, 'confidence': 0.7})
        funding_rate = market_data.get('funding_rate', 0.01)
        sentiment_score = context.get('sentiment_score', 0.0)

        return self.conduct_vibe_debate(
            symbol=symbol,
            signal=signal,
            price=price,
            regime_info=regime_info,
            ai_forecast=ai_forecast,
            funding_rate=funding_rate,
            sentiment_score=sentiment_score
        )

    def _generate_rule_based_consensus(
        self,
        symbol: str,
        signal: str,
        regime: str,
        confidence: float,
        funding_rate: float,
        adx: float
    ) -> Dict[str, Any]:
        """
        Deterministic quantitative debate fallback when LLM is unavailable.
        """
        critique_points = []
        score = 0.5  # Base neutral

        # 1. Regime alignment check
        if signal == "LONG":
            if regime == "TRENDING_BULL":
                score += 0.25
                critique_points.append("Quant: Bullish trend alignment confirmed.")
            elif regime == "TRENDING_BEAR":
                score -= 0.35
                critique_points.append("Quant Warning: Attempting to Long against Bearish trend.")
            elif regime == "VOLATILITY_SHOCK":
                score -= 0.40
                critique_points.append("Risk Auditor: Volatility shock active, high liquidation risk.")
        elif signal == "SHORT":
            if regime == "TRENDING_BEAR":
                score += 0.25
                critique_points.append("Quant: Bearish trend alignment confirmed.")
            elif regime == "TRENDING_BULL":
                score -= 0.35
                critique_points.append("Quant Warning: Attempting to Short against Bullish trend.")
            elif regime == "VOLATILITY_SHOCK":
                score -= 0.40
                critique_points.append("Risk Auditor: Volatility shock active.")

        # 2. Funding rate vibe check
        if funding_rate > 0.05 and signal == "LONG":
            score -= 0.15
            critique_points.append(f"Macro Vibe: Extremely crowded Longs (Funding {funding_rate*100:.2f}%), squeeze risk.")
        elif funding_rate < -0.05 and signal == "SHORT":
            score -= 0.15
            critique_points.append(f"Macro Vibe: Extremely crowded Shorts (Funding {funding_rate*100:.2f}%), squeeze risk.")
        else:
            score += 0.10
            critique_points.append("Macro Vibe: Funding rate healthy and neutral.")

        # 3. Model confidence contribution
        score += (confidence - 0.5) * 0.3
        final_score = max(0.0, min(1.0, score))
        approved = final_score >= 0.65

        return {
            'approved': approved,
            'conviction_score': round(final_score, 2),
            'consensus_summary': " | ".join(critique_points),
            'agent_votes': {
                'macro_analyst': "APPROVE" if funding_rate <= 0.03 else "CAUTION",
                'quant_critic': "APPROVE" if (regime != "VOLATILITY_SHOCK") else "REJECT",
                'risk_auditor': "APPROVE" if approved else "REJECT"
            }
        }

    def conduct_vibe_debate(
        self,
        symbol: str,
        signal: str,
        price: float,
        regime_info: Dict[str, Any],
        ai_forecast: Dict[str, Any],
        funding_rate: float = 0.01,
        sentiment_score: float = 0.0
    ) -> AgentDecision:
        """
        Executes multi-agent consensus debate using LLM (with robust rule-based fallback).
        """
        regime = regime_info.get('regime', 'UNKNOWN')
        ai_conf = ai_forecast.get('confidence', 0.5)
        adx = regime_info.get('metrics', {}).get('adx', 20.0)

        # If LLM client is available, run multi-agent chain of thought prompt
        if self.llm.client:
            prompt = f"""
            You are the HKUDS Vibe-Trading Multi-Agent Deliberation Council for Algorithmic Trading.
            
            Evaluate this proposed trade:
            - Symbol: {symbol}
            - Current Price: ${price}
            - Proposed Action: {signal}
            - Market Regime: {regime} (ADX: {adx})
            - AI Foundation Confidence: {ai_conf}
            - Funding Rate: {funding_rate}%
            - Social/Sentiment Score (-1.0 to 1.0): {sentiment_score}
            
            Simulate a 3-agent debate:
            1. Macro & Social Vibe Analyst: Evaluate sentiment & funding crowding.
            2. Quant Critic: Evaluate technical indicators and regime traps (e.g. longing in bear trend).
            3. Risk Auditor: Calculate risk-to-reward and veto unsafe trades.
            
            Output strictly valid JSON:
            {{
                "approved": true/false,
                "conviction_score": (0.0 to 1.0),
                "consensus_reason": "Summary of debate conclusion",
                "risk_multiplier": (0.2 to 1.0)
            }}
            """
            try:
                raw_resp = self.llm.get_response(prompt, system_prompt="You are a strict financial risk debate agent. Output only JSON.")
                # Clean json markers
                if "```json" in raw_resp:
                    raw_resp = raw_resp.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_resp:
                    raw_resp = raw_resp.split("```")[1].strip()

                data = json.loads(raw_resp)
                approved = bool(data.get('approved', False))
                score = float(data.get('conviction_score', 0.5))
                reason = data.get('consensus_reason', 'Multi-Agent Consensus Reached')
                mult = float(data.get('risk_multiplier', 0.5))

                return AgentDecision(
                    approved=approved,
                    confidence=score,
                    reason=f"[Vibe-Debate {score*100:.0f}%] {reason}",
                    metadata={'conviction_score': score, 'size_mult': mult, 'source': 'LLM_DEBATE'}
                )
            except Exception as e:
                # Fallback on LLM failure
                pass

        # Deterministic Quant Consensus Fallback
        res = self._generate_rule_based_consensus(symbol, signal, regime, ai_conf, funding_rate, adx)
        return AgentDecision(
            approved=res['approved'],
            confidence=res['conviction_score'],
            reason=f"[Vibe-Rule {res['conviction_score']*100:.0f}%] {res['consensus_summary']}",
            metadata={'conviction_score': res['conviction_score'], 'size_mult': res['conviction_score'], 'source': 'QUANT_DEBATE'}
        )
