# Technical Context

## Core Technologies
- **Language**: Python 3.10+ (Core, Brain, Execution), Vanilla JS / CSS (Modern Web Dashboard)
- **Quantitative & Portfolio Theory**:
  - `skfolio 0.20.2` (Hierarchical Risk Parity, CVaR, Clarabel, CVXPY)
  - `pandas-ta` (Fast intraday indicator matrix)
  - `numpy`, `pandas`
- **AI & Deep Learning (PyTorch)**:
  - `torch` (CUDA / CPU)
  - `Kronos K-Line Foundation Transformer` (16 Invariant Candlestick Embeddings)
  - `Vibe-Trading Deliberation Protocol` (Multi-agent weighted consensus)
- **Real-Time Data & Execution**:
  - **HyperLiquid 24/7 Public API** (`1m` intraday candles and mid-prices for SOL, HYPE, BTC)
  - `PaperAccount` (1000:1 leverage, margin level %, multi-asset positions)
  - `Nautilus-Style` Event-Driven Backtester
- **Dashboard & Web Stack**:
  - `Flask`, `Flask-SocketIO`, `Flask-CORS` (Running on port 5000)
  - `Chart.js` (Real-time Equity & Balance visualizer)
  - Custom Glassmorphic Dark UI (Vanilla CSS + CSS Grid + Flexbox)

## Development Setup & Running
- **Launch Live Engine**:
  ```bash
  python -u run_live.py
  ```
- **Web Dashboard**: `http://localhost:5000`

## Technical Constraints & Guardrails
- **1000:1 Micro-Margin Safety**: Trade sizing ($800 notional) requires only $0.80 margin. Free margin stays above 99.9% of equity to eliminate liquidation risk.
- **Dynamic Trailing Lock**: Profit trailing activates at +0.07% price move (+70% ROE) and locks profits at 0.03% pullback from peak.
- **Stagnant Exit**: Non-moving trades are cleared at 2.5 minutes to prevent capital lockup.
