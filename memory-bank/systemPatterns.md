# System Patterns

## System Architecture: "Next-Gen Institutional Hybrid Engine"

The HyperNova architecture integrates institutional quantitative portfolio theory, K-line foundation transformers, multi-agent debate protocols, and a sub-second 1000:1 leverage execution loop.

```mermaid
flowchart TD
    subgraph Sensory_Data ["1. Sensory & Real-Time Data"]
        HyperLiquid_Stream["HyperLiquid 24/7 API (1m Candles & Mid-Prices)"]
        FeatureExtractor["16 Invariant K-Line Candle Features"]
        HyperLiquid_Stream --> FeatureExtractor
    end

    subgraph The_Brain ["2. The AI & Multi-Agent Brain"]
        Kronos["Kronos K-Line Foundation Transformer (Direction & Quantiles)"]
        Regime["Regime Classifier (Bull, Bear, Chop, Shock)"]
        Vibe_Deliberation["Vibe-Trading 3-Agent Protocol (Macro, Quant Critic, Risk Auditor)"]
        FeatureExtractor --> Kronos
        FeatureExtractor --> Regime
        Kronos & Regime --> Vibe_Deliberation
    end

    subgraph Portfolio_Execution ["3. Sizing & 1000:1 Scalp Execution"]
        Skfolio_Alloc["skfolio Portfolio Allocator (HRP & Dynamic ATR)"]
        Paper_Account["1000:1 Paper Engine (Margin, Equity, Multi-Asset Tracking)"]
        Trailing_Engine["Dynamic Trailing Profit Maximizer (ROE Calibrated)"]
        Vibe_Deliberation --> Skfolio_Alloc
        Skfolio_Alloc --> Paper_Account
        Paper_Account <--> Trailing_Engine
    end


    subgraph Control_Tower ["4. Real-Time Glassmorphic Control Tower"]
        Dashboard["Flask + SocketIO Real-Time Dashboard (:5000)"]
        Dashboard <--> Paper_Account
    end

    subgraph Edge_Mobile_Collector ["5. 24/7 Mobile Telemetry & Data Harvest Node"]
        Phone_Service["Android Foreground Service (HyperNovaService + WakeLock)"]
        Data_Logger["Autonomous Microstructure Logger (core/data_logger.py)"]
        Local_DB[("Local trade_memory.db (L2, Funding, OI, PnL)")]
        
        Phone_Service --> Data_Logger
        Data_Logger --> Local_DB
    end

    subgraph Central_AI_Hub ["6. Central AI Training & Model Synthesis"]
        DB_Sync["Telemetry Sync (USB/WiFi/Cloud Transfer)"]
        Trainer["Federated Trainer (tools/train_from_phone_data.py)"]
        Learned_Rules["edge_learned_rules.json (AI Weights & Filters)"]

        Local_DB -.-> DB_Sync
        DB_Sync --> Trainer
        Trainer --> Learned_Rules
        Learned_Rules -.-> Phone_Service
    end
```

### Core Components
1. **Sensory System & Feature Ingestion:**
   - Real-time 1m candle fetching from HyperLiquid with in-memory caching.
   - Extracts 16 scale-invariant candle features for the foundation transformer.
2. **The Brain (Kronos + Vibe-Trading + Regime Classifier):**
   - **Kronos Foundation Model**: PyTorch transformer evaluating raw candle geometry without scale dependencies.
   - **Regime Classifier**: Determines Bull/Bear/Chop/Shock using ADX, EMA ribbons, and ATR ratios.
   - **Vibe-Trading Protocol**: Multi-agent consensus gating before risk is committed.
3. **Institutional Allocator (`skfolio`):**
   - Implements Hierarchical Risk Parity (HRP) and CVaR optimization for multi-asset risk balancing.
4. **1000:1 Execution Engine & Dynamic Profit Maximizer:**
   - **Micro-Margin Math**: $800 Notional uses $0.80 Margin per trade.
   - **Dynamic Trailing**: Winning trades (`+%0.07` / `+%70 ROE`) are never cut by time, riding trends until a 0.03% pullback occurs.
   - **Dead-Weight Timeout**: Stagnant trades are cleared at 2.5 minutes.
5. **Real-Time Control Tower:**
   - Flask + SocketIO streaming multi-asset prices, 6-metric position cards, ROE %, and auto-refreshing trade history.
6. **Mobile Edge Node & Telemetry Harvester:**
   - **Zero-Setup Cloud Build**: Derives APKs via GitHub Actions / Colab CI/CD, eliminating the need for heavy local Android Studio installations.
   - **24/7 Phone Data Collection**: Operates as a persistent Android Foreground Service, capturing orderbook imbalances (OIR), funding rates, and trade telemetry into `trade_memory.db`.
   - **Feedback & Rule Refinement**: Telemetry from mobile devices is synced to PC to train `edge_learned_rules.json`, continuously boosting bot win rate.
