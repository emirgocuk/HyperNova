# System Patterns — HyperNova + Primo AI Architecture

## Unified Architecture: "Primo-Enhanced Deep Reinforcement Learning Engine"

The HyperNova architecture integrates Primo's academic state-of-the-art DRL pipeline (Botunac et al., 2025) with HyperLiquid's sub-second crypto microstructure feeds and institutional 1000:1 execution.

```mermaid
flowchart TD
    subgraph Layer1 ["1. Multi-Modal Data Ingestion"]
        HL_Market["HyperLiquid 24/7 API (1m OHLCV, Trades, Mid-Price)"]
        HL_Micro["L2 Orderbook (OIR), Funding Rate, Open Interest, Basis"]
        News_Feed["Crypto News & Social Headlines (Finnhub / Coindesk / RSS)"]
    end

    subgraph Layer2 ["2. Dual Feature Generation Engine"]
        TechEngine["Primo Technical Engine (SMA30/60, MACD, BB20, RSI14, CCI20, DX14)"]
        NLP_Module["PrimoGPT NLP Module (7 Structured Features: Sentiment, Trend, Risk...)"]
        MicroEngine["4-Factor Composite Alpha Processor"]

        HL_Market --> TechEngine
        News_Feed --> NLP_Module
        HL_Micro --> MicroEngine
    end

    subgraph Layer3 ["3. Expanded MDP State Space (S_t)"]
        StateConcat["Concatenated State Vector:\n[Balance, Shares, Values, Prices, 6xTechInd, 7xNLP, 4xMicro]"]
        TechEngine --> StateConcat
        NLP_Module --> StateConcat
        MicroEngine --> StateConcat
    end

    subgraph Layer4 ["4. PrimoRL Decision Engine (PPO)"]
        PPO_Agent["PPO Neural Policy π(a|s) (Stable-Baselines3 / Gymnasium)"]
        ContinuousAction["Continuous Action Space A_t ∈ [-1.0, +1.0]\n(Exact Position Sizing & Direction)"]
        
        StateConcat --> PPO_Agent
        PPO_Agent --> ContinuousAction
    end

    subgraph Layer5 ["5. Execution & Dynamic Reward Feedback"]
        ExecutionEngine["1000:1 Scalper Execution (HyperLiquid Perp / Paper Account)"]
        DynamicReward["Two-Phase Dynamic Sharpe Reward:\nPhase 1 (<30): Raw E[r_p]\nPhase 2 (≥30): Differential Sharpe (R_p - R_f) / σ_p"]
        
        ContinuousAction --> ExecutionEngine
        ExecutionEngine --> DynamicReward
        DynamicReward -.-> PPO_Agent
    end

    subgraph Layer6 ["6. Control Tower & UI Ecosystem"]
        UnifiedAPI["FastAPI Unified Server (control_tower/unified_api.py)"]
        NextJS_UI["Next.js Glassmorphic Web Dashboard (:3000)"]
        Android_App["Android Mobile Node (Foreground Service & Telemetry)"]
        
        UnifiedAPI <--> ExecutionEngine
        UnifiedAPI <--> NextJS_UI
        UnifiedAPI <--> Android_App
    end
```

---

## Key System Patterns

### 1. Dual Feature Representation (State Vector S_t)
- **Quantitative Vector**:
  - $SMA_{30}$, $SMA_{60}$ (Long-term Trend)
  - $MACD_{12,26,9}$ (Momentum & Convergence)
  - $Bollinger_{20,2.0}$ (Volatility bands)
  - $RSI_{14}$ (Exponential smoothed momentum)
  - $CCI_{20}$ (Mean Absolute Deviation cycles)
  - $DX_{14}$ (Directional Movement strength)
- **Qualitative Vector (PrimoGPT 7 Features)**:
  - `news_relevance` $[0..2]$, `sentiment` $[-1..1]$, `price_impact` $[-3..3]$, `trend_direction` $[-1..1]$, `earnings_impact` $[-2..2]$, `investor_confidence` $[-3..3]$, `risk_profile_change` $[-2..2]$.
- **Microstructure Vector**:
  - `L2 OIR` $[-100..100]$, `Funding Rate APR`, `Open Interest`, `Basis Premium`.

### 2. Continuous Policy Execution
- Unlike discrete buy/hold/sell frameworks, PrimoRL outputs a scalar $A_t \in [-1.0, 1.0]$.
- Position size is computed smoothly:
  $$\text{Target Position} = \text{round}\left(A_t \times \frac{\text{Max Notional USD}}{\text{Current Price}}\right)$$

### 3. Dynamic Two-Phase Sharpe Ratio Reward
- **Warmup Phase ($t < 30$)**: Uses raw portfolio returns $E[r_p]$ to avoid statistical instability on small sample sizes.
- **Adaptive Risk Phase ($t \ge 30$)**: Switches to rolling Sharpe Ratio $(R_p - R_f)/\sigma_p$ ensuring the agent prioritizes risk-adjusted consistency over volatile gambles.

### 4. Zero-Leakage Architecture
- Strict separation between training data and inference state.
- During live execution, PrimoGPT only parses current news with zero look-ahead bias.
