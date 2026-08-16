"""
Walk-Forward Backtester for the CNN-LSTM AI Trading Bot.
Tests the model on the validation set (last 20% of data) and reports
win rate, profit factor, max drawdown, and Sharpe ratio.
"""
import torch
import numpy as np
import pandas as pd
import os
import json
import logging
from datetime import datetime

from ai_engine.model_cnn_lstm import CNNLSTMRegimeDetector
from ai_engine.data_loader import FinancialDataset

logger = logging.getLogger("Backtester")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')


class Backtester:
    """Simulates trading using model predictions on historical data."""
    
    SIGNALS = ["SIDEWAYS", "UPTREND", "DOWNTREND"]
    
    def __init__(self, confidence_threshold: float = 0.35):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.confidence_threshold = confidence_threshold
        
        # Load model
        self.model = CNNLSTMRegimeDetector(num_features=20, window_size=60).to(self.device)
        
        best_path = "ai_engine/weights/brain_cnn_lstm_best.pth"
        latest_path = "ai_engine/weights/brain_cnn_lstm_latest.pth"
        model_path = best_path if os.path.exists(best_path) else latest_path
        
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device, weights_only=True))
            logger.info(f"✅ Loaded model: {model_path}")
        else:
            logger.warning("⚠️ No weights! Backtesting with random model.")
        
        self.model.eval()
        
        # Load normalization params
        norm_path = "ai_engine/weights/normalization_params.json"
        if os.path.exists(norm_path):
            with open(norm_path) as f:
                params = json.load(f)
            self.means = np.array(params["means"], dtype=np.float32)
            self.stds = np.array(params["stds"], dtype=np.float32)
        else:
            self.means = np.zeros(20, dtype=np.float32)
            self.stds = np.ones(20, dtype=np.float32)
    
    def run(self, data_dir: str = "database/training_data", sl_pct: float = 1.0, tp_pct: float = 2.0):
        """Run walk-forward backtest on validation data (last 20%)."""
        logger.info("🏁 Starting Walk-Forward Backtest")
        logger.info(f"   SL: {sl_pct}%, TP: {tp_pct}%, Confidence threshold: {self.confidence_threshold}")
        
        all_trades = []
        
        for f in sorted(os.listdir(data_dir)):
            if not f.endswith('_engineered.csv'):
                continue
            
            df = pd.read_csv(os.path.join(data_dir, f))
            symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else f.split('_')[0]
            
            # Use last 20% as test data (same split as training)
            split_idx = int(len(df) * 0.8)
            test_df = df.iloc[split_idx:].copy()
            
            logger.info(f"📊 Backtesting {symbol}: {len(test_df):,} candles (last 20%)")
            
            trades = self._simulate_symbol(test_df, symbol, sl_pct, tp_pct)
            all_trades.extend(trades)
        
        if not all_trades:
            logger.warning("No trades generated!")
            return {}
        
        # Calculate metrics
        results = self._calculate_metrics(all_trades)
        self._print_report(results)
        
        # Save report
        report_path = "reports/backtest_ai_latest.json"
        os.makedirs("reports", exist_ok=True)
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"💾 Report saved: {report_path}")
        
        return results
    
    def _simulate_symbol(self, df, symbol, sl_pct, tp_pct):
        """Run the model on each window and simulate trades."""
        feature_cols = [
            'rsi_14', 'rsi_7', 'macd', 'macd_signal', 'macd_hist',
            'stoch_rsi', 'ema_cross_9_21', 'ema_cross_21_50', 'price_vs_sma200',
            'adx_14', 'atr_14', 'atr_7', 'bb_width', 'bb_position',
            'log_return', 'vol_sma_ratio', 'obv_norm',
            'candle_body', 'upper_wick', 'lower_wick',
        ]
        
        df = df.copy()
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(subset=feature_cols + ['close'], inplace=True)
        df.reset_index(drop=True, inplace=True)
        
        trades = []
        in_trade = False
        window_size = 60
        
        for i in range(window_size, len(df) - 1):
            if in_trade:
                # Check if SL or TP hit
                current_close = df['close'].iloc[i]
                
                if trade_side == "BUY":
                    pnl_pct = (current_close - entry_price) / entry_price * 100
                else:
                    pnl_pct = (entry_price - current_close) / entry_price * 100
                
                if pnl_pct >= tp_pct:  # TP hit
                    trades.append({
                        "symbol": symbol, "side": trade_side,
                        "entry": entry_price, "exit": current_close,
                        "pnl_pct": round(pnl_pct, 4), "result": "TP",
                        "bars_held": i - entry_idx
                    })
                    in_trade = False
                elif pnl_pct <= -sl_pct:  # SL hit
                    trades.append({
                        "symbol": symbol, "side": trade_side,
                        "entry": entry_price, "exit": current_close,
                        "pnl_pct": round(-sl_pct, 4), "result": "SL",
                        "bars_held": i - entry_idx
                    })
                    in_trade = False
                continue
            
            # Run inference
            window = df[feature_cols].values[i - window_size:i]
            normalized = ((window - self.means) / self.stds).astype(np.float32)
            tensor = torch.tensor(normalized).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                logits, conf = self.model(tensor)
                probs = torch.softmax(logits, dim=1).cpu().numpy().squeeze()
                conf_val = conf.cpu().item()
            
            regime_idx = int(np.argmax(probs))
            signal = self.SIGNALS[regime_idx]
            
            # Use pure softmax probability as confidence (ignore untrained conf_val head)
            confidence = float(probs[regime_idx])
            
            if signal in ("UPTREND", "DOWNTREND") and confidence >= self.confidence_threshold:
                entry_price = df['close'].iloc[i]
                trade_side = "BUY" if signal == "UPTREND" else "SELL"
                entry_idx = i
                in_trade = True
        
        return trades
    
    def _calculate_metrics(self, trades):
        """Calculate performance metrics from trade list."""
        pnls = [t['pnl_pct'] for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]
        
        total_trades = len(trades)
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
        
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Cumulative equity curve
        equity = np.cumsum(pnls)
        max_drawdown = 0
        peak = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = peak - e
            if dd > max_drawdown:
                max_drawdown = dd
        
        # Sharpe Ratio (annualized, assuming hourly bars)
        returns = np.array(pnls)
        if len(returns) > 1 and returns.std() > 0:
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252 * 24)
        else:
            sharpe = 0
        
        # Per-symbol breakdown
        symbols = set(t['symbol'] for t in trades)
        by_symbol = {}
        for sym in symbols:
            sym_trades = [t for t in trades if t['symbol'] == sym]
            sym_pnls = [t['pnl_pct'] for t in sym_trades]
            sym_wins = [p for p in sym_pnls if p > 0]
            by_symbol[sym] = {
                "trades": len(sym_trades),
                "win_rate": round(len(sym_wins) / len(sym_trades) * 100, 1),
                "avg_pnl": round(np.mean(sym_pnls), 4),
                "total_pnl": round(sum(sym_pnls), 2),
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "avg_win": round(np.mean(wins), 4) if wins else 0,
            "avg_loss": round(np.mean(losses), 4) if losses else 0,
            "total_pnl_pct": round(sum(pnls), 2),
            "by_symbol": by_symbol,
        }
    
    def _print_report(self, r):
        logger.info("=" * 60)
        logger.info("📊 BACKTEST REPORT")
        logger.info("=" * 60)
        logger.info(f"Total Trades: {r['total_trades']}")
        logger.info(f"Win Rate: {r['win_rate']}%")
        logger.info(f"Profit Factor: {r['profit_factor']}")
        logger.info(f"Sharpe Ratio: {r['sharpe_ratio']}")
        logger.info(f"Max Drawdown: {r['max_drawdown_pct']}%")
        logger.info(f"Total P/L: {r['total_pnl_pct']}%")
        logger.info(f"Avg Win: {r['avg_win']}% | Avg Loss: {r['avg_loss']}%")
        for sym, data in r['by_symbol'].items():
            logger.info(f"  {sym}: {data['trades']} trades, WR={data['win_rate']}%, P/L={data['total_pnl']}%")
        logger.info("=" * 60)


if __name__ == "__main__":
    bt = Backtester(confidence_threshold=0.35)
    bt.run(sl_pct=1.0, tp_pct=2.0)
