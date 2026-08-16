# Product Context

## Purpose
The automated trading landscape usually offers either "black-box" systems you can't understand or simplistic retail bots that break under pressure. **The Transparent Strategist** aims to combine institutional-grade deep learning (CNN-LSTM, RL) with an engineering-first safety mindset, ensuring the user always knows *why* a decision was made. It acts as an emotionless, highly disciplined mechanical engineer executing trades with calculated, non-linear safety margins.

## Problems Solved
1.  **The Black-Box Problem (Unexplainable AI)**: Standard neural networks don't account for their actions. We use **Explainable AI (XAI)** to translate complex probability vectors into simple dashboard logs ("Regime detection showed 80% sideways momentum, activating Grid mode").
2.  **Grid Liquidation (The "Crash")**: Traditional static grids get obliterated by trending markets. Our **Dynamic GRID** uses non-linear (Fibonacci) spacing to widen the gap as price accelerates away, and employs dynamic rebalancing to shift risk efficiently.
3.  **Catastrophic Drawdowns**: AI can hallucinate or market conditions can break models. Our **Circuit Breaker** acts as a physical safety valve: a 3% daily equity drop instantly halts all new trades.
4.  **Invisible Costs (Slippage)**: Traders often ignore the gap between signal price and execution price. Our Execution Manager logs slippage inherently, adjusting the AI's cost perception.

## User Experience Goals
-   **The Storyteller UI (Next.js Dashboard)**: 
    -   Users should open the dashboard and immediately see a "Heatmap" of where the bot has placed its Dynamic Grids.
    -   They should see the real-time Confidence Score (above or below the 60% threshold).
    -   They should read an ongoing, human-readable narrative of the bot's decisions.
-   **Zero-Anxiety Operation**: Because of the strict 3% Circuit Breaker and PM2 self-healing containerization, the user should be comfortable going to sleep while the system runs, treating it like a well-oiled mechanical engine.

## How It Should Work
1.  **Sensory Input**: The bot ingests async data from XM, processing Log Returns and Volatility Clusters on the fly.
2.  **Brain Evaluation**: The CNN-LSTM model reviews the chart visual mapping, identifies the market regime, and outputs a Confidence Score.
3.  **Adaptive Skeleton**: If confidence > 60%, the Dynamic GRID adjusts its Fibonacci spacing based on the current Volatility. 
4.  **Safety Check**: The Execution Manager verifies the 3% daily equity limit hasn't been breached, tracks anticipated slippage, and executes.
5.  **Feedback**: Decision logic is converted to XAI logs and sent to the Next.js Dashboard alongside the live Heatmap.
