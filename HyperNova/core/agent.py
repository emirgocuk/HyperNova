from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class AgentDecision:
    approved: bool
    confidence: float  # 0.0 to 1.0
    reason: str
    metadata: Optional[Dict[str, Any]] = None

class BaseAgent(ABC):
    """
    Abstract base class for all AI Agents in HyperNova.
    Agents act as consultants or gatekeepers for trading decisions.
    """
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def analyze(self, market_data: Dict[str, Any], context: Dict[str, Any]) -> AgentDecision:
        """
        Analyze the current market context and return a decision.
        
        Args:
            market_data: Dictionary containing prices, indicators, etc.
            context: Dictionary containing portfolio state, current positions, etc.
            
        Returns:
            AgentDecision object with approval status and reasoning.
        """
        pass
