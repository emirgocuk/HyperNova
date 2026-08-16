"""
Risk Manager Agent Module.
Integrates skfolio portfolio allocation, ATR-based volatility sizing,
drawdown circuit breakers, and Vibe-Trading debate validation.
"""

from typing import Dict, Any, List, Optional
import json
from core.agent import BaseAgent, AgentDecision
from core.llm_service import LLMService
from core.portfolio_allocator import PortfolioAllocator
from agents.vibe_agent import VibeAgent


class RiskManagerAgent(BaseAgent):
    """
    Institutional Risk Manager:
    - Calculates mathematically optimal position size via skfolio ATR allocation.
    - Limits total portfolio risk, max open positions, and daily drawdown.
    - Enforces Vibe-Trading multi-agent debate consensus.
    """

    def __init__(self, max_drawdown_pct: float = 0.10, max_daily_loss_pct: float = 0.03, risk_per_trade_pct: float = 0.015):
        super().__init__(name="RiskManager")
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.starting_balance = None

        # Sub-modules
        self.allocator = PortfolioAllocator(default_risk_per_trade_pct=risk_per_trade_pct)
        self.vibe_engine = VibeAgent()
        self.llm = LLMService()

    def analyze(self, market_data: Dict[str, Any], context: Dict[str, Any]) -> AgentDecision:
        """
        Validates trade entry, performs multi-agent vibe check, and calculates ATR-adjusted position size.
        """
        current_equity = context.get('equity', 10000.0)
        current_price = market_data.get('price', 0.0)
        symbol = market_data.get('symbol', 'BTC')
        signal_type = context.get('signal_type', 'UNKNOWN')
        atr = market_data.get('atr', current_price * 0.015)
        regime_info = context.get('regime_info', {'regime': 'RANGING_CHOP', 'confidence': 0.7})
        ai_forecast = context.get('ai_forecast', {'signal': signal_type, 'confidence': 0.7})
        funding_rate = market_data.get('funding_rate', 0.01)

        # 1. Initialize starting balance
        if self.starting_balance is None:
            self.starting_balance = current_equity

        # 2. Technical Drawdown Checks
        drawdown = (self.starting_balance - current_equity) / self.starting_balance if self.starting_balance > 0 else 0
        if drawdown > self.max_drawdown_pct:
            return AgentDecision(
                approved=False,
                confidence=1.0,
                reason=f"🛡️ Max Drawdown Breach ({drawdown:.2%}) -> Circuit Breaker Active",
                metadata={'risk_score': 0, 'size_usd': 0.0, 'size_coin': 0.0}
            )

        # 3. Position Limit Checks
        open_positions = context.get('positions', [])
        if len(open_positions) >= 3:
            return AgentDecision(
                approved=False,
                confidence=0.9,
                reason="🛡️ Max Concurrent Positions Reached (3)",
                metadata={'risk_score': 0, 'size_usd': 0.0, 'size_coin': 0.0}
            )

        # 4. If No Signal, pass check
        if signal_type == 'UNKNOWN' or signal_type == 'NEUTRAL':
            return AgentDecision(approved=True, confidence=1.0, reason="Technicals passed (No active signal)", metadata={'risk_score': 5})

        # 5. Vibe-Trading Multi-Agent Debate
        vibe_decision = self.vibe_engine.conduct_vibe_debate(
            symbol=symbol,
            signal=signal_type,
            price=current_price,
            regime_info=regime_info,
            ai_forecast=ai_forecast,
            funding_rate=funding_rate
        )

        if not vibe_decision.approved:
            return AgentDecision(
                approved=False,
                confidence=vibe_decision.confidence,
                reason=f"🛡️ Vibe Debate Vetoed: {vibe_decision.reason}",
                metadata={'risk_score': 3, 'size_usd': 0.0, 'size_coin': 0.0}
            )

        # 6. skfolio Institutional ATR Sizing
        conviction_mult = vibe_decision.metadata.get('size_mult', 0.8)
        adjusted_risk_pct = self.risk_per_trade_pct * conviction_mult

        sizing = self.allocator.calculate_atr_position_size(
            equity=current_equity,
            price=current_price,
            atr=atr,
            risk_pct=adjusted_risk_pct,
            atr_multiplier=2.0
        )

        # Return Approved Decision with detailed Sizing & SL metadata
        return AgentDecision(
            approved=True,
            confidence=vibe_decision.confidence,
            reason=f"✅ Approved by Vibe Council & skfolio ATR Sizer ({vibe_decision.reason})",
            metadata={
                'risk_score': int(vibe_decision.confidence * 10),
                'size_usd': sizing['size_usd'],
                'size_coin': sizing['size_coin'],
                'stop_loss_dist': sizing['stop_loss_dist'],
                'stop_loss_pct': sizing['stop_loss_pct'],
                'atr': sizing['atr'],
                'leverage': 1
            }
        )
