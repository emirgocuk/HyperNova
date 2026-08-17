"""
Primo Technical Indicators Engine
=================================
Source Paper: "Automated Trading Framework Using LLM-Driven Features and Deep Reinforcement Learning"
Authors: Ive Botunac, Tomislav Petković, Jurica Bosna (2025)
DOI: 10.3390/bdcc9120317

Implements exact mathematical formulas for the 6 technical indicators defined in Section 3.2:
1. SMA (Simple Moving Average) - n=30, n=60
2. MACD (Moving Average Convergence/Divergence) - m=12, n=26, p=9
3. Bollinger Bands (BB) - n=20, k=2.0
4. RSI (Relative Strength Index) - n=14 (exponential smoothing)
5. CCI (Commodity Channel Index) - n=20, constant=0.015
6. DX (Directional Movement Index) - n=14, ATR-based
"""

import math
from typing import Dict, List, Tuple, Union, Optional
import numpy as np


# ==============================================================================
# 1. SMA (Simple Moving Average) - Equation (1)
# SMA_t(n) = (1/n) * sum_{i=0}^{n-1} P_{t-i}
# ==============================================================================
def calculate_sma(prices: Union[List[float], np.ndarray], n: int = 30) -> float:
    """
    Computes Simple Moving Average over n periods.
    """
    if len(prices) == 0:
        return 0.0
    if len(prices) < n:
        return float(np.mean(prices))
    return float(np.mean(prices[-n:]))


# ==============================================================================
# 2. EMA & MACD (Moving Average Convergence/Divergence) - Equations (2) & (3)
# MACD_t = EMA_m(t) - EMA_n(t)
# Signal_t = EMA_p(MACD_t)
# typically m=12, n=26, p=9
# ==============================================================================
def calculate_ema_series(values: Union[List[float], np.ndarray], period: int) -> np.ndarray:
    """
    Calculates Exponential Moving Average series using standard alpha = 2 / (period + 1).
    """
    values = np.asarray(values, dtype=np.float64)
    if len(values) == 0:
        return np.array([])
    if len(values) == 1:
        return values.copy()

    alpha = 2.0 / (period + 1.0)
    ema = np.empty_like(values)
    ema[0] = values[0]
    for i in range(1, len(values)):
        ema[i] = alpha * values[i] + (1.0 - alpha) * ema[i - 1]
    return ema


def calculate_macd(
    prices: Union[List[float], np.ndarray],
    m: int = 12,
    n: int = 26,
    p: int = 9
) -> Tuple[float, float, float]:
    """
    Returns (macd_line, signal_line, histogram)
    """
    prices = np.asarray(prices, dtype=np.float64)
    if len(prices) < 2:
        return 0.0, 0.0, 0.0

    ema_short = calculate_ema_series(prices, m)
    ema_long = calculate_ema_series(prices, n)
    macd_series = ema_short - ema_long
    signal_series = calculate_ema_series(macd_series, p)

    macd_val = float(macd_series[-1])
    signal_val = float(signal_series[-1])
    hist_val = macd_val - signal_val

    return macd_val, signal_val, hist_val


# ==============================================================================
# 3. Bollinger Bands (BB) - Section 3.2.3
# Middle Band = SMA_20
# Upper Band  = SMA_20 + 2 * sigma
# Lower Band  = SMA_20 - 2 * sigma
# ==============================================================================
def calculate_bollinger_bands(
    prices: Union[List[float], np.ndarray],
    n: int = 20,
    k: float = 2.0
) -> Tuple[float, float, float]:
    """
    Returns (lower_band, middle_band, upper_band)
    """
    prices = np.asarray(prices, dtype=np.float64)
    if len(prices) == 0:
        return 0.0, 0.0, 0.0
    if len(prices) < n:
        sma = float(np.mean(prices))
        std = float(np.std(prices)) if len(prices) > 1 else 0.0
        return sma - k * std, sma, sma + k * std

    window = prices[-n:]
    sma = float(np.mean(window))
    std = float(np.std(window))
    return sma - k * std, sma, sma + k * std


# ==============================================================================
# 4. RSI (Relative Strength Index) - Equation (4)
# RSI = 100 - (100 / (1 + RS))
# RS = AvgGain / AvgLoss (exponentially smoothed over 14 periods)
# ==============================================================================
def calculate_rsi(prices: Union[List[float], np.ndarray], period: int = 14) -> float:
    """
    Calculates Wilder's Exponentially Smoothed RSI over 14 periods.
    """
    prices = np.asarray(prices, dtype=np.float64)
    if len(prices) < period + 1:
        return 50.0

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    if len(gains) < period:
        return 50.0

    # Initial average
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))

    # Wilder's exponential smoothing
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(np.clip(rsi, 0.0, 100.0))


# ==============================================================================
# 5. CCI (Commodity Channel Index) - Equation (5)
# CCI = (1 / 0.015) * (p_t - SMA(p_t)) / sigma(p_t)
# p_t = (High + Low + Close) / 3
# sigma(p_t) = Mean Absolute Deviation (MAD)
# ==============================================================================
def calculate_cci(
    highs: Union[List[float], np.ndarray],
    lows: Union[List[float], np.ndarray],
    closes: Union[List[float], np.ndarray],
    n: int = 20
) -> float:
    """
    Calculates Commodity Channel Index (CCI) with 0.015 scaling factor.
    """
    highs = np.asarray(highs, dtype=np.float64)
    lows = np.asarray(lows, dtype=np.float64)
    closes = np.asarray(closes, dtype=np.float64)

    min_len = min(len(highs), len(lows), len(closes))
    if min_len < 2:
        return 0.0

    highs = highs[-min_len:]
    lows = lows[-min_len:]
    closes = closes[-min_len:]

    typical_prices = (highs + lows + closes) / 3.0
    if len(typical_prices) < n:
        tp_window = typical_prices
    else:
        tp_window = typical_prices[-n:]

    sma_tp = float(np.mean(tp_window))
    # Mean Absolute Deviation
    mad = float(np.mean(np.abs(tp_window - sma_tp)))

    if mad == 0.0:
        return 0.0

    current_tp = typical_prices[-1]
    cci = (current_tp - sma_tp) / (0.015 * mad)
    return float(cci)


# ==============================================================================
# 6. DX (Directional Movement Index) - Equation (6)
# DX = |+DI - (-DI)| / |+DI + (-DI)| * 100
# +DI, -DI calculated via smoothed directional movement and ATR (n=14)
# ==============================================================================
def calculate_dx(
    highs: Union[List[float], np.ndarray],
    lows: Union[List[float], np.ndarray],
    closes: Union[List[float], np.ndarray],
    period: int = 14
) -> float:
    """
    Calculates Directional Movement Index (DX) over 14 periods.
    """
    highs = np.asarray(highs, dtype=np.float64)
    lows = np.asarray(lows, dtype=np.float64)
    closes = np.asarray(closes, dtype=np.float64)

    min_len = min(len(highs), len(lows), len(closes))
    if min_len < period + 1:
        return 0.0

    highs = highs[-min_len:]
    lows = lows[-min_len:]
    closes = closes[-min_len:]

    # Calculate True Range and Directional Movements
    plus_dm = np.zeros(min_len - 1, dtype=np.float64)
    minus_dm = np.zeros(min_len - 1, dtype=np.float64)
    tr = np.zeros(min_len - 1, dtype=np.float64)

    for i in range(1, min_len):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm[i - 1] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i - 1] = down_move

        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i - 1])
        tr3 = abs(lows[i] - closes[i - 1])
        tr[i - 1] = max(tr1, tr2, tr3)

    if len(tr) < period:
        return 0.0

    # Wilder's Smoothing for ATR, +DM, -DM
    smooth_tr = float(np.mean(tr[:period]))
    smooth_plus = float(np.mean(plus_dm[:period]))
    smooth_minus = float(np.mean(minus_dm[:period]))

    for i in range(period, len(tr)):
        smooth_tr = (smooth_tr * (period - 1) + tr[i]) / period
        smooth_plus = (smooth_plus * (period - 1) + plus_dm[i]) / period
        smooth_minus = (smooth_minus * (period - 1) + minus_dm[i]) / period

    if smooth_tr == 0.0:
        return 0.0

    plus_di = (smooth_plus / smooth_tr) * 100.0
    minus_di = (smooth_minus / smooth_tr) * 100.0

    di_sum = plus_di + minus_di
    if di_sum == 0.0:
        return 0.0

    dx = (abs(plus_di - minus_di) / di_sum) * 100.0
    return float(np.clip(dx, 0.0, 100.0))


# ==============================================================================
# Full Primo Technical Vector Generator
# ==============================================================================
class PrimoIndicatorEngine:
    """
    Stateful & High-Performance Technical Indicator Engine.
    Computes the standard Primo 6-Indicator feature set from price candles.
    """

    def __init__(self):
        pass

    def compute_vector(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Computes all 6 Primo academic indicators:
        - SMA_30 (normalized ratio: SMA_30 / CurrentPrice - 1)
        - SMA_60 (normalized ratio: SMA_60 / CurrentPrice - 1)
        - MACD_LINE (normalized: MACD / CurrentPrice)
        - MACD_SIGNAL (normalized: Signal / CurrentPrice)
        - BB_PERCENT_B (Oscillator [0, 1] position within bands)
        - RSI_14 (Normalized [0, 1]: RSI / 100)
        - CCI_20 (Normalized [-1, 1]: np.tanh(CCI / 100))
        - DX_14 (Normalized [0, 1]: DX / 100)
        """
        if not closes:
            return {
                "sma_30": 0.0,
                "sma_60": 0.0,
                "macd_line": 0.0,
                "macd_signal": 0.0,
                "macd_hist": 0.0,
                "bb_lower": 0.0,
                "bb_middle": 0.0,
                "bb_upper": 0.0,
                "bb_pct_b": 0.5,
                "rsi_14": 50.0,
                "cci_20": 0.0,
                "dx_14": 0.0,
            }

        p_curr = current_price if current_price is not None and current_price > 0 else closes[-1]

        # 1. SMAs
        sma_30 = calculate_sma(closes, n=30)
        sma_60 = calculate_sma(closes, n=60)

        # 2. MACD
        macd_line, macd_signal, macd_hist = calculate_macd(closes, m=12, n=26, p=9)

        # 3. Bollinger Bands
        bb_lower, bb_middle, bb_upper = calculate_bollinger_bands(closes, n=20, k=2.0)
        bb_width = bb_upper - bb_lower
        bb_pct_b = (p_curr - bb_lower) / bb_width if bb_width > 0 else 0.5

        # 4. RSI
        rsi_14 = calculate_rsi(closes, period=14)

        # 5. CCI
        cci_20 = calculate_cci(highs, lows, closes, n=20)

        # 6. DX
        dx_14 = calculate_dx(highs, lows, closes, period=14)

        return {
            "sma_30": sma_30,
            "sma_60": sma_60,
            "macd_line": macd_line,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "bb_lower": bb_lower,
            "bb_middle": bb_middle,
            "bb_upper": bb_upper,
            "bb_pct_b": float(bb_pct_b),
            "rsi_14": float(rsi_14),
            "cci_20": float(cci_20),
            "dx_14": float(dx_14),
        }

    def get_feature_array(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: Optional[float] = None
    ) -> np.ndarray:
        """
        Returns a normalized 8-element numerical feature array suitable for DRL State Vector:
        [
            sma_30_diff,    # (price - sma30) / price
            sma_60_diff,    # (price - sma60) / price
            macd_norm,      # macd_line / price * 100
            macd_sig_norm,  # macd_signal / price * 100
            bb_pct_b,       # (price - lower) / (upper - lower) [0..1]
            rsi_norm,       # (rsi - 50) / 50 [-1..1]
            cci_norm,       # tanh(cci / 100) [-1..1]
            dx_norm         # dx / 100 [0..1]
        ]
        """
        feats = self.compute_vector(highs, lows, closes, current_price)
        p = current_price if current_price is not None and current_price > 0 else (closes[-1] if closes else 1.0)
        p = max(p, 1e-8)

        sma30_diff = (p - feats["sma_30"]) / p
        sma60_diff = (p - feats["sma_60"]) / p
        macd_norm = (feats["macd_line"] / p) * 100.0
        macd_sig_norm = (feats["macd_signal"] / p) * 100.0
        bb_pct_b = float(np.clip(feats["bb_pct_b"], -1.0, 2.0))
        rsi_norm = (feats["rsi_14"] - 50.0) / 50.0
        cci_norm = float(np.tanh(feats["cci_20"] / 100.0))
        dx_norm = feats["dx_14"] / 100.0

        return np.array([
            sma30_diff,
            sma60_diff,
            macd_norm,
            macd_sig_norm,
            bb_pct_b,
            rsi_norm,
            cci_norm,
            dx_norm
        ], dtype=np.float32)
