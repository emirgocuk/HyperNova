import pandas as pd
from typing import Dict, Any, List

class BaseStrategy:
    """
    Abstract base class for all testing strategies.
    Any new strategy must inherit from this and implement generate_signals()
    """
    def __init__(self, name: str, params: Dict[str, Any] = None):
        self.name = name
        self.params = params or {}
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a DataFrame containing historical MT5 data.
        Must return a DataFrame with a new column 'signal' containing:
        1 for BUY
        -1 for SELL
        0 for HOLD/SIDEWAYS
        """
        raise NotImplementedError("Each strategy must implement generate_signals(df)")
