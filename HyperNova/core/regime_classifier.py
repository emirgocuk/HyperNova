"""
Market Regime Classifier Module.
Identifies whether the current market state is Trending Bull, Trending Bear, Ranging Chop, or Volatility Shock.
Gives strategies exact permission rules (e.g. Trend vs Mean-Reversion vs Risk-Off).
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
from enum import Enum
from typing import Dict, Any, Tuple


class MarketRegime(Enum):
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    RANGING_CHOP = "RANGING_CHOP"
    VOLATILITY_SHOCK = "VOLATILITY_SHOCK"
    UNKNOWN = "UNKNOWN"


class RegimeClassifier:
    """
    Classifies market conditions using multi-indicator regime detection:
    - ADX & Directional Movement (Trend Strength)
    - EMA Ribbon (Trend Alignment)
    - ATR Expansion / Volatility Ratio (Shock Detection)
    - Bollinger Band Width (Chop / Squeeze Detection)
    """

    def __init__(self, adx_threshold: float = 25.0, chop_adx_threshold: float = 20.0, shock_atr_ratio: float = 2.2):
        self.adx_threshold = adx_threshold
        self.chop_adx_threshold = chop_adx_threshold
        self.shock_atr_ratio = shock_atr_ratio

    def classify(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyzes OHLCV dataframe and returns market regime with strategy permission flags.
        
        Returns:
            Dict with regime (MarketRegime), confidence (float), metrics (Dict), permissions (Dict)
        """
        if df.empty or len(df) < 50:
            return {
                'regime': MarketRegime.UNKNOWN.value,
                'confidence': 0.0,
                'metrics': {},
                'permissions': {
                    'allow_trend_following': False,
                    'allow_grid_mean_reversion': False,
                    'allow_arbitrage': True,
                    'risk_mode': 'DEFENSIVE'
                }
            }

        df_calc = df.copy()

        # Calculate indicators if not present
        if 'EMA_20' not in df_calc.columns:
            df_calc['EMA_20'] = ta.ema(df_calc['Close'], length=20)
        if 'EMA_50' not in df_calc.columns:
            df_calc['EMA_50'] = ta.ema(df_calc['Close'], length=50)
        if 'EMA_200' not in df_calc.columns:
            df_calc['EMA_200'] = ta.ema(df_calc['Close'], length=min(200, len(df_calc)-1))

        # ADX & DMI
        adx_df = ta.adx(df_calc['High'], df_calc['Low'], df_calc['Close'], length=14)
        if adx_df is not None and not adx_df.empty:
            adx_val = adx_df.iloc[-1, 0]  # ADX_14
            dmp_val = adx_df.iloc[-1, 1]  # DMP_14
            dmn_val = adx_df.iloc[-1, 2]  # DMN_14
        else:
            adx_val, dmp_val, dmn_val = 20.0, 20.0, 20.0

        # ATR & ATR Expansion (Shock detection)
        atr_series = ta.atr(df_calc['High'], df_calc['Low'], df_calc['Close'], length=14)
        if atr_series is not None and not atr_series.empty:
            current_atr = atr_series.iloc[-1]
            rolling_avg_atr = atr_series.tail(30).mean()
            atr_ratio = (current_atr / rolling_avg_atr) if rolling_avg_atr > 0 else 1.0
        else:
            current_atr, atr_ratio = df_calc['Close'].iloc[-1] * 0.01, 1.0

        # Bollinger Bands & Bandwidth
        bb = ta.bbands(df_calc['Close'], length=20, std=2)
        if bb is not None and not bb.empty:
            # Bandwidth: (Upper - Lower) / Middle
            bb_cols = [c for c in bb.columns if 'BBM' in c or 'BBL' in c or 'BBU' in c]
            if len(bb_cols) >= 3:
                bb_width = (bb.iloc[-1, 2] - bb.iloc[-1, 0]) / bb.iloc[-1, 1]
            else:
                bb_width = 0.04
        else:
            bb_width = 0.04

        # Current Price vs EMAs
        close = df_calc['Close'].iloc[-1]
        ema20 = df_calc['EMA_20'].iloc[-1] if not np.isnan(df_calc['EMA_20'].iloc[-1]) else close
        ema50 = df_calc['EMA_50'].iloc[-1] if not np.isnan(df_calc['EMA_50'].iloc[-1]) else close

        # --- REGIME DECISION MATRIX ---
        regime = MarketRegime.RANGING_CHOP
        confidence = 0.6

        # 1. Volatility Shock Check
        if atr_ratio >= self.shock_atr_ratio:
            regime = MarketRegime.VOLATILITY_SHOCK
            confidence = min(0.95, 0.7 + (atr_ratio - self.shock_atr_ratio) * 0.2)

        # 2. Trending Market Check
        elif adx_val >= self.adx_threshold:
            if close > ema20 >= ema50 and dmp_val > dmn_val:
                regime = MarketRegime.TRENDING_BULL
                confidence = min(0.95, 0.6 + (adx_val - self.adx_threshold) / 50.0)
            elif close < ema20 <= ema50 and dmn_val > dmp_val:
                regime = MarketRegime.TRENDING_BEAR
                confidence = min(0.95, 0.6 + (adx_val - self.adx_threshold) / 50.0)
            else:
                # ADX high but EMAs crossed or mixed
                regime = MarketRegime.TRENDING_BULL if close > ema50 else MarketRegime.TRENDING_BEAR
                confidence = 0.65

        # 3. Ranging / Chop Market
        elif adx_val < self.chop_adx_threshold or bb_width < 0.025:
            regime = MarketRegime.RANGING_CHOP
            confidence = min(0.90, 0.6 + (self.chop_adx_threshold - adx_val) / 25.0)

        # Permissions based on detected regime
        permissions = {
            'allow_trend_following': regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR],
            'allow_grid_mean_reversion': regime == MarketRegime.RANGING_CHOP,
            'allow_arbitrage': regime != MarketRegime.VOLATILITY_SHOCK,
            'risk_mode': 'EMERGENCY_LOCK' if regime == MarketRegime.VOLATILITY_SHOCK else ('AGGRESSIVE' if confidence > 0.8 else 'NORMAL')
        }

        return {
            'regime': regime.value,
            'confidence': round(float(confidence), 2),
            'metrics': {
                'adx': round(float(adx_val), 2),
                'atr': round(float(current_atr), 4),
                'atr_ratio': round(float(atr_ratio), 2),
                'bb_width': round(float(bb_width), 4),
                'dmp': round(float(dmp_val), 2),
                'dmn': round(float(dmn_val), 2)
            },
            'permissions': permissions
        }
