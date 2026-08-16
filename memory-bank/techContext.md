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
- **Mobile Edge & Data Collection (Android)**:
  - **Zero-Local-Tooling Build**: GitHub Actions CI/CD (`.github/workflows/build_apk.yml`) & Google Colab (`build_apk_colab.ipynb`) for cloud APK synthesis without Android Studio.
  - **Android Service Engine**: Native Foreground Service (`HyperNovaService.java`) with `PARTIAL_WAKE_LOCK` for continuous 24/7 background operation.
  - **On-Device Telemetry Storage**: SQLite (`database/trade_memory.db`) & Parquet event logging capturing L2 Orderbook Imbalance (OIR), Funding APR %, Basis Premium, and trade outcomes.
  - **Lightweight Monitoring**: `scrcpy` for 0-latency USB/Wi-Fi screen mirroring and real-time mobile debugging without emulators.

## Development Setup & Running
- **Launch Live Engine (PC / Development)**:
  ```bash
  python -u run_live.py
  ```
- **Web Dashboard**: `http://localhost:5000`
- **Mobile APK Generation (No Android Studio required)**:
  - Push changes to GitHub repository; download compiled `.apk` from Actions Artifacts.
- **Train AI Model From Phone Telemetry**:
  ```bash
  python HyperNova/tools/train_from_phone_data.py
  ```

## Technical Constraints & Guardrails
- **1000:1 Micro-Margin Safety**: Trade sizing ($800 notional) requires only $0.80 margin. Free margin stays above 99.9% of equity to eliminate liquidation risk.
- **Dynamic Trailing Lock**: Profit trailing activates at +0.07% price move (+70% ROE) and locks profits at 0.03% pullback from peak.
- **Stagnant Exit**: Non-moving trades are cleared at 2.5 minutes to prevent capital lockup.
- **Battery & Doze Resistance**: Android Foreground Service with explicit notification channel to prevent OS task killing during 24/7 background market listening.
