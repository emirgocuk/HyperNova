# HyperNova AI Agents 🧠

 This document outlines the architecture and specific implementations of AI Agents in the HyperNova system.

## 1. Agent Architecture
All agents inherit from `core.agent.BaseAgent`.
-   **Input:** `market_data` (price, indicators) and `context` (portfolio, signals).
-   **Output:** `AgentDecision` (Approved: bool, Reason: str, Confidence: float).

## 2. Implemented Agents

### 🛡️ Risk Manager Agent (`RiskManagerAgent`)
**Role:** Guardian of the portfolio. Prevents trading during unsafe conditions.
**Location:** `HyperNova/agents/risk_manager.py`

**Capabilities:**
1.  **Technical Checks:**
    *   **Max Drawdown:** Rejects trades if portfolio drawdown > 10%.
    *   **Daily Loss:** Rejects if daily loss > 3%.
    *   **Position Sizing:** Ensures max positions limit (default 1).
2.  **Semantic Analysis ("Vibe Check"):**
    *   **Brain:** NVIDIA Nemotron 3 Nano (30B) via OpenRouter.
    *   **Logic:** detailed prompt analyzing the trade context (Asset, Price, Signal Type).
    *   **Output:** Returns "YES" or "NO" based on a conservative risk persona.

## 3. Planned Agents

### 📰 Sentiment Analysis Agent (Planned)
**Role:** Market mood analyzer.
**Data Source:** News API / Twitter Scraper.
**Logic:**
*   Fetch recent headlines for BTC/ETH.
*   Ask LLM: "Is the news sentiment Bullish, Bearish, or Neutral?"
*   Filter signals: E.g., Don't Long if Sentiment is "Extreme Fear".

### 🚪 Exit Agent (Planned)
**Role:** Dynamic position manager.
**Logic:**
*   Monitor open trades.
*   Decide when to take profit or cut loss based on changing market conditions (not just fixed TP/SL).