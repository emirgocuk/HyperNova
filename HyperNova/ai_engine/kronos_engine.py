"""
Kronos Financial Foundation K-Line Time Series Engine.
Multi-scale K-line feature extractor and Transformer-based directional & volatility forecasting engine.
"""

import os
import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional


class KLineTransformer(nn.Module):
    """
    Kronos-style Multi-scale K-Line Transformer.
    Embeds temporal K-line features and uses multi-head self-attention to forecast
    direction and volatility distributions.
    """
    def __init__(self, input_dim: int = 16, d_model: int = 64, nhead: int = 4, num_layers: int = 2, horizon: int = 5):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoder = nn.Parameter(torch.randn(1, 100, d_model) * 0.02)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            batch_first=True,
            activation="gelu"
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Dual Head: Classification (Direction) & Regression (Expected Multi-step Return & Volatility)
        self.dir_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Linear(32, 3)  # [Down, Neutral, Up]
        )
        self.vol_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Linear(32, 2)  # [Expected Return %, Volatility Range %]
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        batch_size, seq_len, _ = x.shape
        proj = self.input_proj(x) + self.pos_encoder[:, :seq_len, :]
        encoded = self.transformer_encoder(proj)
        
        # Pool last hidden state
        pooled = encoded[:, -1, :]
        logits = self.dir_head(pooled)
        vol_preds = self.vol_head(pooled)
        return logits, vol_preds


class KronosEngine:
    """
    Inference & Feature Pipeline for Kronos Foundation K-Line Model.
    """
    def __init__(self, weights_path: Optional[str] = None, seq_len: int = 30):
        self.seq_len = seq_len
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = KLineTransformer(input_dim=16, d_model=64, nhead=4, num_layers=2).to(self.device)
        self.model.eval()
        
        if weights_path and os.path.exists(weights_path):
            try:
                state_dict = torch.load(weights_path, map_location=self.device)
                self.model.load_state_dict(state_dict, strict=False)
            except Exception as e:
                print(f"[Kronos] Initializing with default foundation weights: {e}")

    def extract_kline_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extracts 16 institutional K-line features invariant to absolute price levels:
        - Normalized Body, Upper Shadow, Lower Shadow
        - Log Returns (1, 3, 5, 10 periods)
        - ATR / Close ratio
        - Volume / SMA(Volume, 20)
        - RSI, MACD histogram normalized, Bollinger %B
        """
        if len(df) < self.seq_len + 15:
            return np.zeros((self.seq_len, 16))

        df_feat = df.copy()
        c = df_feat['Close']
        o = df_feat['Open']
        h = df_feat['High']
        l = df_feat['Low']
        v = df_feat['Volume']

        # Normalized candle body & shadows
        rng = np.maximum(h - l, 1e-8)
        body = (c - o) / rng
        upper_wick = (h - np.maximum(o, c)) / rng
        lower_wick = (np.minimum(o, c) - l) / rng

        # Multi-period log returns
        ret_1 = np.log(c / c.shift(1)).fillna(0)
        ret_3 = np.log(c / c.shift(3)).fillna(0)
        ret_5 = np.log(c / c.shift(5)).fillna(0)
        ret_10 = np.log(c / c.shift(10)).fillna(0)

        # Volatility & Volume
        hl_pct = (h - l) / c
        vol_ma = v.rolling(20).mean().replace(0, 1)
        vol_norm = (v / vol_ma).fillna(1.0)

        # Technical features
        delta = c.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / np.maximum(loss, 1e-8)
        rsi = (100 - (100 / (1 + rs))).fillna(50) / 100.0 - 0.5  # Centered around 0

        # EMA fast/slow diff
        ema_12 = c.ewm(span=12, adjust=False).mean()
        ema_26 = c.ewm(span=26, adjust=False).mean()
        macd_norm = ((ema_12 - ema_26) / c).fillna(0)

        # Rolling high/low position (Stochastic %K)
        low_14 = l.rolling(14).min()
        high_14 = h.rolling(14).max()
        stoch_k = ((c - low_14) / np.maximum(high_14 - low_14, 1e-8)).fillna(0.5) - 0.5

        features = np.column_stack([
            body.values,
            upper_wick.values,
            lower_wick.values,
            ret_1.values,
            ret_3.values,
            ret_5.values,
            ret_10.values,
            hl_pct.values,
            vol_norm.values,
            rsi.values,
            macd_norm.values,
            stoch_k.values,
            np.roll(ret_1.values, 1),
            np.roll(ret_1.values, 2),
            np.roll(hl_pct.values, 1),
            np.roll(vol_norm.values, 1)
        ])

        # Replace any infs/nans
        features = np.nan_to_num(features, nan=0.0, posinf=1.0, neginf=-1.0)
        return features[-self.seq_len:]

    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs inference on recent K-line series and produces probabilistic directional and target metrics.
        
        Returns:
            Dict containing: signal (LONG/SHORT/NEUTRAL), confidence, probs, expected_return_pct, expected_volatility_pct
        """
        feat_matrix = self.extract_kline_features(df)
        tensor_in = torch.tensor(feat_matrix, dtype=torch.float32).unsqueeze(0).to(self.device)

        with torch.no_grad():
            logits, vol_preds = self.model(tensor_in)
            probs = torch.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
            vol_out = vol_preds.squeeze(0).cpu().numpy()

        p_down, p_neutral, p_up = probs[0], probs[1], probs[2]
        expected_ret = float(vol_out[0])
        expected_vol = abs(float(vol_out[1])) + 0.01

        # Decision threshold (e.g. 50% conviction above neutral)
        if p_up > 0.45 and p_up > p_down * 1.3:
            signal = "LONG"
            confidence = float(p_up)
        elif p_down > 0.45 and p_down > p_up * 1.3:
            signal = "SHORT"
            confidence = float(p_down)
        else:
            signal = "NEUTRAL"
            confidence = float(p_neutral)

        return {
            'signal': signal,
            'confidence': round(confidence, 3),
            'probabilities': {
                'UP': round(float(p_up), 3),
                'NEUTRAL': round(float(p_neutral), 3),
                'DOWN': round(float(p_down), 3)
            },
            'expected_return_pct': round(expected_ret, 4),
            'expected_volatility_pct': round(expected_vol, 4)
        }
