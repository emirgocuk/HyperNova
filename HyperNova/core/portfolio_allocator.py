"""
Portfolio Allocator Module using skfolio.
Provides Hierarchical Risk Parity (HRP), Risk Budgeting, and ATR-Adaptive Position Sizing.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

try:
    from skfolio.optimization import HierarchicalRiskParity, EqualWeighted, MinimumRisk
    from skfolio.measures import RiskMeasure
    SKFOLIO_AVAILABLE = True
except ImportError:
    SKFOLIO_AVAILABLE = False


class PortfolioAllocator:
    """
    Manages multi-asset capital allocation and individual position sizing.
    Uses skfolio's Hierarchical Risk Parity (HRP) to prevent correlated drawdown.
    """

    def __init__(self, default_risk_per_trade_pct: float = 0.015, max_leverage: float = 2.0):
        self.default_risk_per_trade_pct = default_risk_per_trade_pct  # 1.5% max risk per trade
        self.max_leverage = max_leverage
        self.last_weights = {}

    def calculate_atr_position_size(
        self,
        equity: float,
        price: float,
        atr: float,
        risk_pct: Optional[float] = None,
        atr_multiplier: float = 2.0,
        max_position_pct: float = 0.25
    ) -> Dict[str, float]:
        """
        Institutional ATR-based Position Sizing.
        Position Size = (Equity * Risk_Pct) / (ATR * atr_multiplier)
        
        Args:
            equity: Total account equity in USD
            price: Current asset price
            atr: 14-period Average True Range in price units
            risk_pct: Max % of equity to risk on this trade (default: 1.5%)
            atr_multiplier: Multiplier for stop-loss distance (default: 2.0x ATR)
            max_position_pct: Maximum position value as % of equity (e.g. 25%)
            
        Returns:
            Dict containing size_usd, size_coin, stop_loss_dist, stop_loss_pct, risk_usd, atr
        """
        if price <= 0 or equity <= 0:
            return {'size_usd': 0.0, 'size_coin': 0.0, 'stop_loss_dist': 0.0, 'stop_loss_pct': 0.0, 'risk_usd': 0.0, 'atr': 0.0}

        risk_pct = risk_pct if risk_pct is not None else self.default_risk_per_trade_pct
        risk_amount_usd = equity * risk_pct

        # If ATR is missing or near zero, fallback to 1.5% price volatility
        if atr is None or atr <= 0 or np.isnan(atr):
            atr = price * 0.015

        stop_loss_dist = atr * atr_multiplier
        stop_loss_pct = stop_loss_dist / price

        # Position size in USD based on risk budget: Size = Risk$ / SL%
        if stop_loss_pct > 0:
            size_usd_by_risk = risk_amount_usd / stop_loss_pct
        else:
            size_usd_by_risk = equity * 0.1

        # Cap by max position percentage (e.g. max 25% equity in one coin)
        max_allowed_usd = equity * max_position_pct * self.max_leverage
        final_size_usd = min(size_usd_by_risk, max_allowed_usd)
        final_size_usd = max(final_size_usd, 10.0)  # Minimum $10 trade

        size_coin = final_size_usd / price

        return {
            'size_usd': round(final_size_usd, 2),
            'size_coin': round(size_coin, 6),
            'stop_loss_dist': round(stop_loss_dist, 4),
            'stop_loss_pct': round(stop_loss_pct * 100, 2),
            'risk_usd': round(risk_amount_usd, 2),
            'atr': round(atr, 4)
        }

    def optimize_multi_asset_weights(
        self,
        returns_df: pd.DataFrame,
        method: str = "HRP"
    ) -> Dict[str, float]:
        """
        Optimizes asset weights across active trading universe using skfolio.
        
        Args:
            returns_df: DataFrame where each column is an asset's periodic return series.
            method: 'HRP' (Hierarchical Risk Parity) or 'MIN_CVAR' or 'EQUAL'
            
        Returns:
            Dict mapping asset symbol to portfolio weight (sums to 1.0)
        """
        if returns_df.empty or len(returns_df.columns) <= 1:
            if not returns_df.empty:
                return {col: 1.0 for col in returns_df.columns}
            return {}

        # Clean NaNs and infs
        cleaned_returns = returns_df.dropna().copy()
        if len(cleaned_returns) < 10:
            # Not enough history, use equal weights
            n = len(returns_df.columns)
            return {col: round(1.0 / n, 4) for col in returns_df.columns}

        if SKFOLIO_AVAILABLE:
            try:
                if method.upper() == "HRP":
                    model = HierarchicalRiskParity(
                        risk_measure=RiskMeasure.CVAR,
                        hierarchical_clustering_algo="ward"
                    )
                elif method.upper() == "MIN_CVAR":
                    model = MinimumRisk(risk_measure=RiskMeasure.CVAR)
                else:
                    model = EqualWeighted()

                model.fit(cleaned_returns)
                weights = dict(zip(cleaned_returns.columns, model.weights_))
                self.last_weights = {k: round(float(v), 4) for k, v in weights.items()}
                return self.last_weights
            except Exception as e:
                # Fallback to Inverse Volatility if solver encounters boundary issues
                pass

        # Fallback: Inverse Volatility Weighting
        volatilities = cleaned_returns.std()
        inv_vol = 1.0 / np.maximum(volatilities, 1e-6)
        weights = inv_vol / inv_vol.sum()
        self.last_weights = {k: round(float(v), 4) for k, v in weights.to_dict().items()}
        return self.last_weights
