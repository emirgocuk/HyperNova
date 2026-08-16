"""
Live Inference Engine — connects the trained CNN-LSTM model to the trading bot.
Pulls the last 60 candles from MT5, applies feature engineering, runs inference,
and returns a signal (UPTREND/DOWNTREND/SIDEWAYS) with confidence.
"""
import torch
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import json
import os
import logging

from ai_engine.model_cnn_lstm import CNNLSTMRegimeDetector

logger = logging.getLogger("LiveInference")

# Symbol name mapping (broker-specific names)
SYMBOL_MAP = {
    "BTCUSDm": "BTCUSD",
    "BTCUSD": "BTCUSD",
    "EURUSD": "EURUSD",
    "XAUUSD": "GOLD",
    "GOLD": "GOLD",
}


class LiveInferenceEngine:
    """
    Real-time AI signal generator.
    - Loads trained weights + normalization parameters
    - Pulls live candle data from MT5
    - Computes 20 technical features
    - Runs CNN-LSTM inference
    - Returns: signal, confidence, attention_weights
    """
    
    FEATURE_COLS = [
        'rsi_14', 'rsi_7', 'macd', 'macd_signal', 'macd_hist',
        'stoch_rsi', 'ema_cross_9_21', 'ema_cross_21_50', 'price_vs_sma200',
        'adx_14', 'atr_14', 'atr_7', 'bb_width', 'bb_position',
        'log_return', 'vol_sma_ratio', 'obv_norm',
        'candle_body', 'upper_wick', 'lower_wick',
    ]
    
    SIGNALS = ["SIDEWAYS", "UPTREND", "DOWNTREND"]
    
    def __init__(self, window_size: int = 60):
        self.window_size = window_size
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load model
        self.model = CNNLSTMRegimeDetector(
            num_features=len(self.FEATURE_COLS),
            window_size=window_size
        ).to(self.device)
        
        weights_dir = "ai_engine/weights"
        best_path = os.path.join(weights_dir, "brain_cnn_lstm_best.pth")
        latest_path = os.path.join(weights_dir, "brain_cnn_lstm_latest.pth")
        
        model_path = best_path if os.path.exists(best_path) else latest_path
        if os.path.exists(model_path):
            self.model.load_state_dict(
                torch.load(model_path, map_location=self.device, weights_only=True)
            )
            logger.info(f"✅ Loaded model weights from: {model_path}")
        else:
            logger.warning("⚠️ No trained weights found! Using random weights (untrained model).")
        
        self.model.eval()
        
        # Load normalization parameters
        norm_path = os.path.join(weights_dir, "normalization_params.json")
        if os.path.exists(norm_path):
            with open(norm_path, 'r') as f:
                params = json.load(f)
                self.means = np.array(params["means"], dtype=np.float32)
                self.stds = np.array(params["stds"], dtype=np.float32)
            logger.info("✅ Loaded normalization parameters.")
        else:
            logger.warning("⚠️ No normalization params found. Using identity transform.")
            self.means = np.zeros(len(self.FEATURE_COLS), dtype=np.float32)
            self.stds = np.ones(len(self.FEATURE_COLS), dtype=np.float32)
    
    def get_signal(self, symbol: str, timeframe=mt5.TIMEFRAME_H1) -> dict:
        """
        Main method: pull candles → compute features → run inference → return signal.
        
        Returns:
            dict with keys: signal, confidence, probabilities, raw_features_shape
        """
        real_symbol = SYMBOL_MAP.get(symbol, symbol)
        
        # Need extra candles for indicator warmup (SMA 200 needs 200 bars)
        total_bars_needed = self.window_size + 250
        
        rates = mt5.copy_rates_from_pos(real_symbol, timeframe, 0, total_bars_needed)
        if rates is None or len(rates) < total_bars_needed:
            logger.warning(f"Not enough data for {real_symbol}: got {len(rates) if rates else 0} bars")
            return {"signal": "SIDEWAYS", "confidence": 0.0, "reason": "Insufficient data"}
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={'real_volume': 'volume'}, inplace=True)
        
        # Compute features
        df = self._compute_features(df)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)
        
        if len(df) < self.window_size:
            return {"signal": "SIDEWAYS", "confidence": 0.0, "reason": "Not enough clean data after feature computation"}
        
        # Take the last window_size rows
        feature_window = df[self.FEATURE_COLS].values[-self.window_size:]
        
        # Normalize using training statistics
        normalized = ((feature_window - self.means) / self.stds).astype(np.float32)
        
        # Run inference
        tensor_input = torch.tensor(normalized).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            logits, confidence = self.model(tensor_input)
            probs = torch.nn.functional.softmax(logits, dim=1).cpu().numpy().squeeze()
            conf_score = confidence.cpu().item()
        
        regime_idx = int(np.argmax(probs))
        signal = self.SIGNALS[regime_idx]
        
        # Use pure softmax probability as confidence. 
        # The auxiliary conf_score head was untrained and outputting random noise.
        signal_confidence = float(probs[regime_idx])
        
        result = {
            "signal": signal,
            "confidence": round(signal_confidence, 4),
            "raw_confidence": round(conf_score, 4),
            "probabilities": {
                "SIDEWAYS": round(float(probs[0]), 4),
                "UPTREND": round(float(probs[1]), 4),
                "DOWNTREND": round(float(probs[2]), 4),
            },
            "symbol": real_symbol,
        }
        
        logger.info(f"🧠 {real_symbol}: {signal} (conf={signal_confidence:.2%}) | "
                    f"Probs: S={probs[0]:.2f} U={probs[1]:.2f} D={probs[2]:.2f}")
        
        return result
    
    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all 20 technical features from raw OHLCV data."""
        c = df['close']
        h = df['high']
        l = df['low']
        v = df['volume'] if 'volume' in df.columns else df.get('tick_volume', pd.Series(0, index=df.index))
        
        delta = c.diff()
        gain = delta.clip(lower=0)
        loss_s = -delta.clip(upper=0)
        
        # RSI(14) and RSI(7)
        df['rsi_14'] = 100 - (100 / (1 + gain.rolling(14).mean() / (loss_s.rolling(14).mean() + 1e-10)))
        df['rsi_7'] = 100 - (100 / (1 + gain.rolling(7).mean() / (loss_s.rolling(7).mean() + 1e-10)))
        
        # MACD
        ema12 = c.ewm(span=12).mean()
        ema26 = c.ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Stochastic RSI
        rsi = df['rsi_14']
        rsi_min = rsi.rolling(14).min()
        rsi_max = rsi.rolling(14).max()
        df['stoch_rsi'] = (rsi - rsi_min) / (rsi_max - rsi_min + 1e-10)
        
        # EMA crosses (normalized)
        ema9 = c.ewm(span=9).mean()
        ema21 = c.ewm(span=21).mean()
        ema50 = c.ewm(span=50).mean()
        sma200 = c.rolling(200).mean()
        df['ema_cross_9_21'] = (ema9 - ema21) / (c + 1e-10)
        df['ema_cross_21_50'] = (ema21 - ema50) / (c + 1e-10)
        df['price_vs_sma200'] = (c - sma200) / (c + 1e-10)
        
        # ADX(14)
        tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
        plus_dm = ((h - h.shift()).clip(lower=0)).where((h - h.shift()) > (l.shift() - l), 0)
        minus_dm = ((l.shift() - l).clip(lower=0)).where((l.shift() - l) > (h - h.shift()), 0)
        atr14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / (atr14 + 1e-10))
        minus_di = 100 * (minus_dm.rolling(14).mean() / (atr14 + 1e-10))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10))
        df['adx_14'] = dx.rolling(14).mean()
        
        # Volatility
        df['atr_14'] = atr14
        df['atr_7'] = tr.rolling(7).mean()
        
        sma20 = c.rolling(20).mean()
        std20 = c.rolling(20).std()
        bb_upper = sma20 + 2 * std20
        bb_lower = sma20 - 2 * std20
        df['bb_width'] = (bb_upper - bb_lower) / (sma20 + 1e-10)
        df['bb_position'] = (c - bb_lower) / (bb_upper - bb_lower + 1e-10)
        
        # Volume & Returns
        df['log_return'] = np.log(c / c.shift(1))
        df['vol_sma_ratio'] = v / (v.rolling(20).mean() + 1e-10)
        obv = (np.sign(delta) * v).cumsum()
        df['obv_norm'] = (obv - obv.rolling(50).mean()) / (obv.rolling(50).std() + 1e-10)
        
        # Price action
        df['candle_body'] = (c - df['open']) / (h - l + 1e-10)
        df['upper_wick'] = (h - pd.concat([c, df['open']], axis=1).max(axis=1)) / (h - l + 1e-10)
        df['lower_wick'] = (pd.concat([c, df['open']], axis=1).min(axis=1) - l) / (h - l + 1e-10)
        
        return df


# Singleton instance for reuse across requests
_engine_instance = None

def get_inference_engine() -> LiveInferenceEngine:
    """Returns a singleton inference engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = LiveInferenceEngine()
    return _engine_instance
