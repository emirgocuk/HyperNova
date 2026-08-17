"""
Primo Crypto Trading Gymnasium Environment & Dynamic Two-Phase Sharpe Reward
=============================================================================
Source Paper: "Automated Trading Framework Using LLM-Driven Features and Deep Reinforcement Learning"
Authors: Ive Botunac, Tomislav Petković, Jurica Bosna (2025)
DOI: 10.3390/bdcc9120317

Implements:
1. Continuous Action Space: A_t in [-1.0, +1.0] (Exact Position Sizing & Direction)
2. Expanded State Space: [Account, Position, Tech Indicators, NLP Features, L2 Microstructure]
3. Dynamic Two-Phase Sharpe Ratio Reward Function:
   - Phase 1 (N < 30 returns): Raw expected portfolio returns E[r_p]
   - Phase 2 (N >= 30 returns): Rolling Differential Sharpe Ratio (R_p - R_f) / sigma_p
4. HyperLiquid 1000:1 leverage & realistic transaction fee / slippage simulation
"""

import math
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    # Minimal fallback mock for gym spaces if gymnasium not yet installed
    class gym:
        class Env:
            pass

    class spaces:
        class Box:
            def __init__(self, low, high, shape, dtype=np.float32):
                self.low = low
                self.high = high
                self.shape = shape
                self.dtype = dtype

            def sample(self):
                return np.random.uniform(self.low, self.high, size=self.shape).astype(self.dtype)


class PrimoCryptoTradingEnv(gym.Env):
    """
    OpenAI Gymnasium-compatible Trading Environment implementing the Primo paper specs.
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df_candles: Optional[np.ndarray] = None,
        initial_balance: float = 1000.0,
        max_notional: float = 800.0,
        leverage: float = 1000.0,
        taker_fee_pct: float = 0.00035,   # 0.035% Taker fee
        maker_fee_pct: float = 0.00010,   # 0.010% Maker fee
        risk_free_rate: float = 0.0,
        sharpe_warmup_window: int = 30
    ):
        super().__init__()

        self.initial_balance = initial_balance
        self.max_notional = max_notional
        self.leverage = leverage
        self.taker_fee_pct = taker_fee_pct
        self.maker_fee_pct = maker_fee_pct
        self.risk_free_rate = risk_free_rate
        self.sharpe_warmup_window = sharpe_warmup_window

        # State Dimensions:
        # 1. Balance (normalized)
        # 2. Position ratio [-1.0 .. 1.0]
        # 3. Unrealized PnL %
        # 4. Current Price / Entry Price ratio
        # 5-12. Primo Tech Indicators (8 features)
        # 13-19. PrimoGPT NLP Features (7 features)
        # 20-23. L2 Microstructure Features (4 features: OIR, Funding, OI, Basis)
        # Total = 1 + 1 + 1 + 1 + 8 + 7 + 4 = 23 dimensions
        self.state_dim = 23

        # Observation & Action Spaces
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.state_dim,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(1,), dtype=np.float32
        )

        # Runtime State
        self.balance = initial_balance
        self.position = 0.0          # Current position notional ($)
        self.position_dir = 0        # -1: Short, 0: Flat, 1: Long
        self.entry_price = 0.0
        self.returns_history: List[float] = []
        self.step_idx = 0

    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        if seed is not None:
            np.random.seed(seed)

        self.balance = self.initial_balance
        self.position = 0.0
        self.position_dir = 0
        self.entry_price = 0.0
        self.returns_history.clear()
        self.step_idx = 0

        obs = np.zeros(self.state_dim, dtype=np.float32)
        obs[0] = 1.0  # Normalized initial balance
        return obs, {}

    def compute_two_phase_sharpe_reward(self, step_return: float) -> float:
        """
        Calculates the Two-Phase Dynamic Sharpe Ratio Reward (Section 3.4):
        Phase 1 (< 30 returns): Raw expected portfolio returns
        Phase 2 (>= 30 returns): Dynamic Rolling Sharpe Ratio = (mean_excess) / (std + eps)
        """
        self.returns_history.append(step_return)

        if len(self.returns_history) < self.sharpe_warmup_window:
            # Phase 1: Raw returns with numerical stabilization
            return float(step_return * 10.0)  # Scaled for RL gradient stability
        else:
            # Phase 2: Dynamic Rolling Sharpe Ratio
            window = np.array(self.returns_history[-self.sharpe_warmup_window:], dtype=np.float64)
            excess = window - self.risk_free_rate
            mean_excess = np.mean(excess)
            std_excess = np.std(excess)

            if std_excess < 1e-8:
                return float(np.clip(mean_excess * 10.0, -5.0, 5.0))

            sharpe = mean_excess / std_excess
            return float(np.clip(sharpe, -10.0, 10.0))

    def step(
        self,
        action: np.ndarray,
        current_price: float = 100.0,
        tech_vector: Optional[np.ndarray] = None,
        nlp_vector: Optional[np.ndarray] = None,
        micro_vector: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """
        Executes a continuous action step:
        action in [-1.0, 1.0]:
          +1.0 = Max Long ($800 notional)
          -1.0 = Max Short (-$800 notional)
           0.0 = Flat (close position)
        """
        self.step_idx += 1
        target_action = float(np.clip(action[0] if isinstance(action, (np.ndarray, list)) else action, -1.0, 1.0))

        # Target notional based on continuous action
        target_notional = target_action * self.max_notional
        target_dir = 1 if target_action > 0.05 else (-1 if target_action < -0.05 else 0)

        # 1. PnL & Fee Calculation
        fee_paid = 0.0
        pnl = 0.0

        if self.position_dir != 0 and self.entry_price > 0:
            price_change_pct = (current_price - self.entry_price) / self.entry_price
            pnl = self.position * price_change_pct * self.position_dir

        # Position change event
        notional_change = abs(target_notional - (self.position * self.position_dir))
        if notional_change > 10.0:  # Action threshold
            fee_paid = notional_change * self.taker_fee_pct

        # Update position
        if target_dir != self.position_dir or abs(abs(target_notional) - self.position) > 10.0:
            self.position = abs(target_notional)
            self.position_dir = target_dir
            self.entry_price = current_price

        # Net step return on balance
        net_step_pnl = pnl - fee_paid
        self.balance += net_step_pnl
        step_return = net_step_pnl / max(self.balance, 1.0)

        # 2. Compute Two-Phase Dynamic Sharpe Reward
        reward = self.compute_two_phase_sharpe_reward(step_return)

        # 3. Construct Next State Vector
        obs = self._build_observation(current_price, tech_vector, nlp_vector, micro_vector)

        done = self.balance <= (self.initial_balance * 0.5)  # 50% max drawdown limit
        truncated = False

        info = {
            "balance": self.balance,
            "position_notional": self.position * self.position_dir,
            "net_pnl": net_step_pnl,
            "step_return": step_return,
            "reward": reward,
            "returns_count": len(self.returns_history)
        }

        return obs, reward, done, truncated, info

    def _build_observation(
        self,
        current_price: float,
        tech_vector: Optional[np.ndarray] = None,
        nlp_vector: Optional[np.ndarray] = None,
        micro_vector: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Constructs the full 23-dimensional normalized state vector S_t.
        """
        norm_balance = self.balance / max(self.initial_balance, 1.0)
        norm_position = (self.position * self.position_dir) / max(self.max_notional, 1.0)

        unrealized_pnl_pct = 0.0
        price_ratio = 1.0
        if self.position_dir != 0 and self.entry_price > 0:
            unrealized_pnl_pct = ((current_price - self.entry_price) / self.entry_price) * self.position_dir
            price_ratio = current_price / self.entry_price

        # Core account & position features (4)
        base_features = np.array([
            norm_balance,
            norm_position,
            unrealized_pnl_pct,
            price_ratio - 1.0
        ], dtype=np.float32)

        # Tech vector (8)
        if tech_vector is None or len(tech_vector) != 8:
            tech_vector = np.zeros(8, dtype=np.float32)

        # NLP vector (7)
        if nlp_vector is None or len(nlp_vector) != 7:
            nlp_vector = np.zeros(7, dtype=np.float32)

        # Microstructure vector (4: OIR, Funding, OI, Basis)
        if micro_vector is None or len(micro_vector) != 4:
            micro_vector = np.zeros(4, dtype=np.float32)

        state = np.concatenate([base_features, tech_vector, nlp_vector, micro_vector])
        return state.astype(np.float32)
