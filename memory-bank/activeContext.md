# Active Context — HyperNova AI Trading Bot

## Current Focus
**1000:1 Live Crypto Scalper Running 24/7 with Dynamic Trailing Profit Maximizer & Next-Gen Institutional Stack**

## What Was Just Done (2026-08-16)

1. **Next-Gen Institutional Quant Integration**:
   - **`skfolio` (Portfolio Optimization)**: Installed `skfolio 0.20.2` (with `clarabel`, `cvxpy`). Implemented `PortfolioAllocator` using Hierarchical Risk Parity (HRP), CVaR optimization, and dynamic ATR-based sizing.
   - **`Kronos K-Line Foundation Model`**: Built PyTorch K-Line transformer extracting 16 invariant candle features (open/high/low/close ratios, volume, return momentum) for directional probability & multi-horizon quantile outputs.
   - **`Vibe-Trading Protocol`**: Built 3-agent deliberation protocol (Macro & Funding Analyst, Quant Critic, Risk Auditor) with weighted consensus gating.
   - **`Market Regime Classifier`**: Multi-indicator classification (`TRENDING_BULL`, `TRENDING_BEAR`, `RANGING_CHOP`, `VOLATILITY_SHOCK`).
   - **`Nautilus-Style Event Backtester`**: Bar-by-bar backtest engine with realistic spreads, slippage, and maker/taker fee modeling.

2. **1000:1 Leverage Fast Scalper Engine (`HyperNova/run_live.py`)**:
   - **24/7 Live Crypto Markets**: Connected to HyperLiquid 1-minute live data feeds for `SOL`, `HYPE`, and `BTC`.
   - **Micro-Margin Math (1000:1)**: $800 Notional position size uses only **$0.80 margin** per trade.
   - **Instant Signal Reversals (Flip)**: Automatically flips LONG ↔ SHORT on indicator extremes without lag.
   - **Dynamic Trailing Profit Maximizer (Trend-Rider)**:
     - Winning trades (`+%0.07` / `+%70 ROE`) are **never cut by time** — trailed dynamically to capture full waves until a 0.03% pullback from peak.
     - 2.5-minute timeout applies **only** to stagnant/dead-weight positions.
   - **Paper Account Upgrades**: Real-time margin levels %, used margin, free margin, and trade history tracking.

3. **Rich Glassmorphic Web Dashboard**:
   - Upgraded UI at `http://localhost:5000` with live PnL, ROE % badges, 6-metric position cards (Entry, Current, TP, SL, Margin, Notional), and real-time 2s auto-refreshing trade history.

4. **100% Ücretsiz 4 Faktörlü Kurumsal Mikroyapı Entegrasyonu (4-Factor Quant Engine)**:
   - **1️⃣ L2 Orderbook Derinliği (OIR %)**: Top 5 Bid/Ask kademe dengesiyle anlık alıcı/satıcı baskısı.
   - **2️⃣ Gerçek Zamanlı Fonlama Oranları (Funding APR %)**: Piyasadaki aşırı Long/Short sıkışmalarını önceden tespit eder.
   - **3️⃣ Açık Pozisyon (Open Interest $M) & 24s Hacim**: Piyasaya giren kurumsal para akışı.
   - **4️⃣ Prim Farkı (Basis Premium %)**: Spot (Oracle) ile Vadeli (Mark) fiyat ayrışması.
   - **🎯 Birleşik Alpha Skoru (Composite Alpha Score [-100..+100])**: 4 faktörün ağırlıklı toplamı ile sahte kırılımları (fakeouts) filtreleyen nihai onay motoru.

5. **Android APK & Edge-Cloud Eğitim İstasyonu (Edge-Cloud Pipeline)**:
   - **`android/` Proje Şablonu**: `AndroidManifest.xml` (Foreground Service + WakeLock), `MainActivity.java` (Tam Ekran Koyu Arayüz), `HyperNovaService.java` (7/24 Kesintisiz Arka Plan Motoru).
   - **`HyperNova/core/data_logger.py`**: Telefonda SQLite'a (`trade_memory.db`) 7/24 otonom mikroyapı ve trade sonucu kaydı.
   - **`HyperNova/tools/train_from_phone_data.py`**: Telefondan gelen verileri bilgisayarda analiz edip modeli eğiten eğitim istasyonu scripti.
   - **`.github/workflows/build_apk.yml`**: GitHub Actions ile tek tıkla bulutta APK derleme pipeline'ı.

6. **Güvenlik, Gizlilik & Telif Kalkanı (`.gitignore` & `.env.example`)**:
   - API anahtarları, şifreler, cüzdan özel anahtarları, `.env` dosyaları engellendi.
   - SQLite veritabanları, kullanıcı telemetri kayıtları, device ID'ler engellendi.
   - 3. parti telifli veya devasa referans repolar (`reference_projects/`, `roadmap-moondev/`) engellendi.
   - Android derleme çıktıları (`.apk`, `build/`, `.gradle/`, `.buildozer/`) engellendi.

## What To Do Next
- Collect live trade logs into a persistent Parquet/SQLite experience buffer (Replay Buffer).
- Train Offline Reinforcement Learning (Decision Transformer / PPO) on collected trade data for continuous self-improving policy updates.
- Expand asset universe to top trending tokens during high-volatility sessions.

## Key File Locations
- Live Scalper: `HyperNova/run_live.py`
- Paper Account Engine: `HyperNova/core/paper_account.py`
- Web Dashboard Server: `HyperNova/core/web_server.py`
- Dashboard UI: `HyperNova/templates/index.html`, `HyperNova/static/app.js`, `HyperNova/static/style.css`
- skfolio Allocator: `HyperNova/core/portfolio_allocator.py`
- Kronos AI Engine: `HyperNova/ai_engine/kronos_engine.py`
- Vibe Agent Deliberation: `HyperNova/agents/vibe_agent.py`
- Regime Classifier: `HyperNova/core/regime_classifier.py`
- Event Backtester: `HyperNova/core/event_backtester.py`
