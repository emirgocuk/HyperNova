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
-   **Mobile Edge Data Harvester (Phone 7/24)**: The user installs the standalone APK onto a dedicated mobile phone to autonomously harvest microstructure data (L2 depth, funding rates, trade outcomes) 24/7 without needing a power-hungry PC running constantly.

## How It Should Work
1.  **Sensory Input**: The bot ingests async data from XM & HyperLiquid, processing Log Returns and Volatility Clusters on the fly.
2.  **Brain Evaluation**: The CNN-LSTM model & Kronos Transformer review the market geometry, identify the regime, and output a Confidence Score.
3.  **Adaptive Skeleton**: If confidence > 60%, the Dynamic GRID adjusts its Fibonacci spacing based on the current Volatility. 
4.  **Safety Check**: The Execution Manager verifies daily equity limits, tracks anticipated slippage, and executes.
5.  **Telemetry & Feedback Loop**: Data is logged locally on the phone (`trade_memory.db`) and synced back to the PC central training station to continuously retrain the AI models.
6.  **Lightweight CI/CD**: Zero-local-overhead Android APK generation via GitHub Actions / Google Colab without installing heavy Android Studio suites.
