# Active Context — HyperNova AI Trading Bot

## Current Focus
**End-to-End Implementation of Academic DRL + LLM Architecture (Primo Framework — Botunac et al., 2025)**
Transforming HyperNova from static rules into a unified, mathematically grounded Reinforcement Learning (PPO) + LLM Feature Extraction trading system.

---

## 📌 Status: Academic Paper Digested & Master Plan Created
We have completely read, parsed, and mathematically structured the 2025 academic paper:
> **"Automated Trading Framework Using LLM-Driven Features and Deep Reinforcement Learning"**  
> *Ive Botunac, Tomislav Petković, Jurica Bosna (Big Data Cogn. Comput. 2025, 9, 317)*

All 20/20 critical formulas, architectures, hyperparameter grids, and benchmark results are fully documented in [`primo-paper-master-plan.md`](file:///d:/Projects/playroom/trading-bot/memory-bank/primo-paper-master-plan.md).

---

## 🧠 Core Architecture Pillars to Implement

### 1. Mathematical Technical Engine (6 Indicators)
- **SMA(30, 60)**: Trend baseline $(1/n) \sum P_{t-i}$
- **MACD(12, 26, 9)**: Momentum $(EMA_{12} - EMA_{26})$ & Signal Line $EMA_9(MACD)$
- **Bollinger Bands(20, 2.0)**: Volatility bounds $SMA_{20} \pm 2\sigma$
- **RSI(14)**: Momentum $100 - (100 / (1 + RS))$ with exponential smoothing
- **CCI(20)**: Cyclical deviations $(p_t - SMA(p_t)) / (0.015 \times MAD)$
- **DX(14)**: Trend strength $|+DI - (-DI)| / |+DI + (-DI)| \times 100$

### 2. PrimoGPT: Structured 7-Feature NLP Engine
Transforms unstructured financial / crypto texts into structured numeric features:
1. `news_relevance` (0, 1, 2)
2. `sentiment` (-1, 0, 1)
3. `price_impact` (-3 to +3)
4. `trend_direction` (-1, 0, 1)
5. `earnings_impact` (-2 to +2)
6. `investor_confidence` (-3 to +3)
7. `risk_profile_change` (-2 to +2)

### 3. HyperNova 4-Factor Microstructure Advantage (L2 + Perp)
- **1️⃣ L2 Orderbook Imbalance (OIR %)**
- **2️⃣ Real-Time Funding Rate (APR %)**
- **3️⃣ Open Interest ($M) & 24h Volume**
- **4️⃣ Spot/Perp Basis Premium (%)**

### 4. PrimoRL: DRL Trading Agent (PPO + Continuous Space)
- **Algorithm**: Proximal Policy Optimization (PPO) — proven superior over SAC & A2C with textual features.
- **State Space**: Flattened concatenated vector $[Balance, Shares, Values, Prices, TechInd, NLP, Microstructure]$.
- **Action Space**: Continuous $A_t \in [-1.0, +1.0]$ scaled to position size: $ActualPosition = A_t \times MaxNotional / CurrentPrice$.
- **Reward Function**: **Two-Phase Dynamic Sharpe Ratio**:
  - Phase 1 ($< 30$ returns): Raw portfolio expected return $E[r_p]$.
  - Phase 2 ($\ge 30$ returns): Differential / Dynamic Sharpe Ratio $(R_p - R_f) / \sigma_p$.

---

## 🚀 Execution Roadmap (Next Immediate Steps)

- [ ] **Phase 1: Math & Technical Indicators Engine**
  - Create standalone high-performance indicator module (`HyperNova/ai_engine/primo_indicators.py`) implementing SMA, MACD, BB, RSI, CCI, DX with unit tests.
- [ ] **Phase 2: PrimoGPT NLP Feature Extractor**
  - Create `HyperNova/ai_engine/primo_nlp.py` generating the exact 7 structured features via LLM prompt / fallback heuristics.
- [ ] **Phase 3: Gymnasium Crypto Trading Environment & Reward Engine**
  - Build `HyperNova/ai_engine/primo_env.py` with the Two-Phase Dynamic Sharpe Reward function and continuous action space.
- [ ] **Phase 4: PPO Model Training & Live Inference Pipeline**
  - Implement `HyperNova/ai_engine/primo_agent.py` using Stable-Baselines3 PPO.
  - Connect inference output directly to `unified_api.py` execution loop.
