# Project Brief

## Project Overview
**"The Transparent Strategist" (Open-Source Algotrading Engine / Antigravity Integration)**

This project treats the financial market as a mechanical system. We employ a disciplined, engineering-first approach: minimal human intervention and maximum systemic discipline. A candlestick is analyzed like a beam subjected to physical load—determining tension, stress, and potential breakage. The bot gathers data, calculates risk factors, and executes in milliseconds, devoid of emotion. 

*The Golden Rule: The system may be complex, but its output must be simple, transparent, and reliable.*

## Core Goals
1.  **Mechanical System Philosophy**: Integrate static and dynamic engineering analysis concepts into financial trading. Measure "Market Tension" through Volatility Clusters and Log Returns.
2.  **The Sensory System (Async Data)**: Uninterrupted, non-blocking asynchronous data streaming from brokers (XM) directly to TimescaleDB and the AI Brain.
3.  **The Brain (Regime Detection)**: Use a CNN-LSTM Hybrid model running on local GPU to evaluate the "image" of the market to detect regimes (Trend vs. Chop) and output a Confidence Score.
4.  **The Adaptive Skeleton (Dynamic GRID)**: Replace static, fragile grid algorithms with a biologically-inspired, adaptive system. Grids use non-linear spacing (Fibonacci/Logarithmic) and dynamically re-center themselves during market surges.
5.  **The Control Tower (Observability)**: Present a Next.js dashboard that explains *why* the bot took an action via Explainable AI (XAI) logs, while showing live Grid heatmaps.

## Key Features
-   **Explainable AI (XAI)**: Dashboard logs plain-text reasoning for every trade (e.g., Confidence > 60%, Side-ways regime detected).
-   **Circuit Breakers (The Safety Valve)**: Hard-coded cutoffs; automatically locks the system if daily equity drawdown hits 3%.
-   **Slippage Management**: Real-time logging of anticipated vs. actual execution prices to fine-tune strategy cost models.
-   **Self-Healing Infrastructure**: Docker and PM2 configurations ensure immediate state recovery if a microservice crashes.

## Scope
-   **Phase 1**: Architectural Redesign & Philosophy Alignment (Current).
-   **Phase 2**: Sensory System Implementation (Async XM streams, Log Returns, StdDev/ATR features).
-   **Phase 3**: The Brain Prototype (CNN-LSTM Regime Detection, Confidence Scoring).
-   **Phase 4**: The Adaptive Skeleton (Dynamic GRID, Non-linear spacing, Rebalancing).
-   **Phase 5**: Execution Manager & The Safety Valve (3% Circuit Breaker, Slippage Logs).
-   **Phase 6**: The Control Tower (Next.js Dashboard, XAI, Heatmaps).
