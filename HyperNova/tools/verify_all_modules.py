"""
End-to-End Verification Test Script for HyperNova Next-Gen Architecture.
Tests skfolio, Kronos Engine, Regime Classifier, Vibe Agent, and Nautilus-style Event Backtester.
"""

import sys
import os
import io

# Force UTF-8 stdout on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.portfolio_allocator import PortfolioAllocator
from core.regime_classifier import RegimeClassifier, MarketRegime
from ai_engine.kronos_engine import KronosEngine
from agents.vibe_agent import VibeAgent
from agents.risk_manager import RiskManagerAgent
from agents.exit_agent import ExitAgent
from core.event_backtester import EventDrivenBacktester


def generate_synthetic_ohlcv(n_bars: int = 500, trend: str = "random", start_price: float = 65000.0) -> pd.DataFrame:
    """Generates realistic synthetic OHLCV data for unit testing."""
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=n_bars, freq="5min")
    
    if trend == "bull":
        drift = 0.0008
        vol = 0.004
    elif trend == "bear":
        drift = -0.0008
        vol = 0.004
    elif trend == "shock":
        drift = 0.0
        vol = 0.025
    else:  # Chop / Range
        drift = 0.0
        vol = 0.003

    returns = np.random.normal(drift, vol, n_bars)
    price_series = start_price * np.exp(np.cumsum(returns))
    
    highs = price_series * (1 + np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    lows = price_series * (1 - np.abs(np.random.normal(0, vol * 0.5, n_bars)))
    opens = np.roll(price_series, 1)
    opens[0] = start_price
    volumes = np.random.uniform(50, 500, n_bars)

    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': price_series,
        'Volume': volumes
    }, index=dates)
    return df


def test_skfolio_allocator():
    print("\n--- [1/5] Testing skfolio Portfolio Allocator ---")
    allocator = PortfolioAllocator(default_risk_per_trade_pct=0.015)
    
    # 1. Test ATR Sizing
    sizing = allocator.calculate_atr_position_size(
        equity=10000.0,
        price=65000.0,
        atr=650.0,  # 1% ATR
        risk_pct=0.015,
        atr_multiplier=2.0
    )
    print(f"ATR Sizing: Size ${sizing['size_usd']} ({sizing['size_coin']} BTC), SL Dist: ${sizing['stop_loss_dist']} ({sizing['stop_loss_pct']}%)")
    assert sizing['size_usd'] > 0, "Size USD must be positive"
    assert sizing['size_coin'] > 0, "Size Coin must be positive"

    # 2. Test Multi-Asset HRP
    np.random.seed(123)
    ret_df = pd.DataFrame({
        'BTC': np.random.normal(0.001, 0.02, 100),
        'ETH': np.random.normal(0.0012, 0.03, 100),
        'SOL': np.random.normal(0.0015, 0.04, 100),
        'GOLD': np.random.normal(0.0002, 0.008, 100)
    })
    weights = allocator.optimize_multi_asset_weights(ret_df, method="HRP")
    print(f"skfolio HRP Multi-Asset Weights: {weights}")
    assert len(weights) == 4, "Must return weights for all 4 assets"
    assert abs(sum(weights.values()) - 1.0) < 0.05, "Weights must sum to ~1.0"
    print("[PASS] skfolio Portfolio Allocator verified.")


def test_regime_classifier():
    print("\n--- [2/5] Testing Market Regime Classifier ---")
    classifier = RegimeClassifier()

    bull_df = generate_synthetic_ohlcv(200, trend="bull")
    bull_res = classifier.classify(bull_df)
    print(f"Bullish Data -> Regime: {bull_res['regime']}, Confidence: {bull_res['confidence']}, ADX: {bull_res['metrics']['adx']}")

    chop_df = generate_synthetic_ohlcv(200, trend="chop")
    chop_res = classifier.classify(chop_df)
    print(f"Choppy Data  -> Regime: {chop_res['regime']}, Confidence: {chop_res['confidence']}, ADX: {chop_res['metrics']['adx']}")

    shock_df = generate_synthetic_ohlcv(200, trend="shock")
    shock_res = classifier.classify(shock_df)
    print(f"Shock Data   -> Regime: {shock_res['regime']}, Confidence: {shock_res['confidence']}, ATR Ratio: {shock_res['metrics']['atr_ratio']}")

    assert 'regime' in bull_res and 'permissions' in bull_res
    print("[PASS] Regime Classifier verified.")


def test_kronos_engine():
    print("\n--- [3/5] Testing Kronos K-Line Foundation Engine ---")
    kronos = KronosEngine(seq_len=30)
    df = generate_synthetic_ohlcv(150, trend="bull")

    pred = kronos.predict(df)
    print(f"Kronos Prediction: Signal={pred['signal']}, Confidence={pred['confidence']}, Probs={pred['probabilities']}")
    print(f"Expected Horizon Return: {pred['expected_return_pct']*100:.2f}%, Volatility: {pred['expected_volatility_pct']*100:.2f}%")
    
    assert pred['signal'] in ["LONG", "SHORT", "NEUTRAL"]
    assert pred['confidence'] > 0
    print("[PASS] Kronos Engine verified.")


def test_vibe_agent():
    print("\n--- [4/5] Testing Vibe-Trading Multi-Agent Deliberation ---")
    vibe = VibeAgent()
    
    regime_info = {'regime': 'TRENDING_BULL', 'confidence': 0.85, 'metrics': {'adx': 32.0}}
    ai_forecast = {'signal': 'LONG', 'confidence': 0.75}
    
    decision = vibe.conduct_vibe_debate(
        symbol="BTC",
        signal="LONG",
        price=65000.0,
        regime_info=regime_info,
        ai_forecast=ai_forecast,
        funding_rate=0.01
    )
    print(f"Vibe Consensus: Approved={decision.approved}, Confidence={decision.confidence:.2f}, Reason={decision.reason}")
    assert decision.confidence >= 0.0
    print("[PASS] Vibe-Trading Agent verified.")


def test_event_backtester():
    print("\n--- [5/5] Running Nautilus-Style Event-Driven Backtest ---")
    backtester = EventDrivenBacktester(
        initial_capital=10000.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        spread_pct=0.0003,
        slippage_pct=0.0002
    )

    df = generate_synthetic_ohlcv(400, trend="bull", start_price=60000.0)
    results = backtester.run(df, symbol="BTC")

    print(f"Backtest Result: Initial: ${results['initial_capital']}, Final Equity: ${results['final_equity']}")
    print(f"Net Profit: ${results['net_profit_usd']} ({results['net_return_pct']:+.2f}%)")
    print(f"Win Rate: {results['win_rate_pct']:.1f}% | Total Trades: {results['total_trades']} | Max DD: {results['max_drawdown_pct']:.2f}% | Sharpe: {results['sharpe_ratio']}")
    assert 'final_equity' in results
    print("[PASS] Nautilus-Style Event-Driven Backtester verified.")


if __name__ == "__main__":
    print("Starting HyperNova Next-Gen Architecture Verification...")
    try:
        test_skfolio_allocator()
        test_regime_classifier()
        test_kronos_engine()
        test_vibe_agent()
        test_event_backtester()
        print("\nALL 5 MODULES SUCCESSFULLY INTEGRATED AND VERIFIED!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
