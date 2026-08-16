# Backtest Optimization Report
**Date:** 2026-01-27
**Data:** BTC/USDT (Binance), Last 365 Days (1 Year) (2025-01-27 to 2026-01-27)
**Strategy:** Market Cipher + MTF TEMA Filter + Time-Based ROI + **Trailing Stop (New)**

## 1. Context: Recent Market Conditions
*   **Period:** Last 1 Year
*   **Buy & Hold Return:** **-10.59%** (Bitcoin lost value consistently over this period)
*   **Market Type:** Bearish / Choppy Down-trend.

## 2. Strategy Performance (Trailing Stop Mode)
*   **Trades:** 123 (Increased from 76)
*   **Return:** **-7.25%** 
    *   **Previous Safe Mode:** -4.06%
    *   **Observation:** Performance slightly *decreased* with simple Trailing Stop.
*   **Win Rate:** 37.4% (Increased slightly from 35.5%)
*   **Profit Factor:** 0.62 (Decreased from 0.67)

## 3. Analysis: Why did it get worse?
*   **Choppy Market Poison:** In a choppy market (zigzag), Trailing Stops are often hit prematurely ("Whipsaw"). Price goes up slightly, pulls back just enough to hit the trailing stop, then goes back up. The "Safe Mode" fixed TP was actually better for this specific market condition.
*   **Over-Trading:** The "Trend Boost" logic (entering on any cross if trend is confirmed) caused more trades (123 vs 76), but many were false alarms in the chop.

## Conclusion & Action
The **"Safe Mode" (Version 2)** was actually superior for the current market conditions.
*   "Proven" features like Trailing Stop work best in **Bull Runs** (Parabolic moves).
*   In **Bear/Chop** markets (like 2025), they bleed money via small cuts.

**Recommendation:**
1.  Revert to the **Safe Mode** configuration (Fixed TP/SL + ROI + Strict Trend Filter).
2.  Keep "Trailing Stop" as an *optional* switch to turn on only when we confirm a Bull Market.
3.  Deploy the Safe Mode version to Termux.

## Live Trading Plan
*   **Default:** Safe Mode (Capital Preservation).
*   **Bull Mode:** Enable Trailing Stop manually if BTC breaks $110k (or similar resistance).
