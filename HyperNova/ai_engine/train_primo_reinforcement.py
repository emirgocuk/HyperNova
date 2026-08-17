import os
import sys
import time
import json
import requests
import numpy as np
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any

# Ensure UTF-8 on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add roots to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
hypernova_root = os.path.dirname(current_dir)
sys.path.insert(0, hypernova_root)
sys.path.insert(0, current_dir)

import torch
import torch.nn as nn
import torch.optim as optim

from ai_engine.primo_indicators import PrimoIndicatorEngine
from ai_engine.primo_nlp import PrimoNLPFeatureExtractor
from ai_engine.primo_env import PrimoCryptoTradingEnv
from ai_engine.primo_agent import PrimoPPOAgent, LightweightActorCritic


def fetch_historical_dataset(coins: List[str], interval: str = "1m", num_candles: int = 2000) -> Dict[str, List[Dict[str, float]]]:
    """
    Downloads historical OHLCV data from HyperLiquid info API.
    """
    dataset = {}
    url = "https://api.hyperliquid.xyz/info"
    now_ms = int(time.time() * 1000)
    interval_ms = 60 * 1000 if interval == "1m" else (5 * 60 * 1000)
    start_ms = now_ms - (num_candles * interval_ms)

    for coin in coins:
        payload = {
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": interval, "startTime": start_ms, "endTime": now_ms}
        }
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10.0)
            data = resp.json()
            raw = data if isinstance(data, list) else data.get("candles", [])
            formatted = []
            for c in raw:
                formatted.append({
                    "time": c.get("t", 0),
                    "open": float(c["o"]),
                    "high": float(c["h"]),
                    "low": float(c["l"]),
                    "close": float(c["c"]),
                    "volume": float(c.get("v", 0.0))
                })
            if formatted:
                dataset[coin] = formatted
                print(f"  [OK] {coin}: {len(formatted)} adet gerçek {interval} mum verisi yüklendi.")
            else:
                raise ValueError("Empty candles response")
        except Exception as e:
            print(f"  [UYARI] {coin} API hatası ({e}), sentetik gerçekçi veri üretiliyor...")
            base_p = 145.0 if coin == "SOL" else (58.0 if coin == "HYPE" else 95000.0)
            candles = []
            p = base_p
            for i in range(num_candles):
                drift = np.random.normal(0, p * 0.0008)
                p += drift
                candles.append({
                    "time": start_ms + (i * interval_ms),
                    "open": p - drift * 0.5,
                    "high": p + abs(np.random.normal(0, p * 0.0004)),
                    "low": p - abs(np.random.normal(0, p * 0.0004)),
                    "close": p,
                    "volume": 1000.0
                })
            dataset[coin] = candles

    return dataset


class PrimoDeepPPOTrainer:
    """
    Academic PPO Reinforcement Learning Engine implementing Section 3.3 and 3.4 of the Primo paper:
    - 23-dimensional state space
    - Continuous action distribution [-1.0 .. 1.0]
    - Two-Phase Dynamic Sharpe Ratio Reward with MEXC fee & slippage penalties
    - Actor-Critic PPO clipped surrogate loss with Generalized Advantage Estimation (GAE)
    """
    def __init__(
        self,
        state_dim: int = 23,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_eps: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        weights_dir: Optional[str] = None
    ):
        self.state_dim = state_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_eps = clip_eps
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.weights_dir = weights_dir or os.path.join(current_dir, "weights")
        os.makedirs(self.weights_dir, exist_ok=True)
        self.weights_path = os.path.join(self.weights_dir, "primo_ppo_model.pt")

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = LightweightActorCritic(state_dim=self.state_dim).to(self.device)
        self.optimizer = optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=50, eta_min=1e-5)

        self.tech_engine = PrimoIndicatorEngine()
        self.nlp_engine = PrimoNLPFeatureExtractor()

    def train_on_market_data(
        self,
        dataset: Dict[str, List[Dict[str, float]]],
        epochs: int = 15,
        rollout_steps: int = 512,
        batch_size: int = 64
    ) -> Dict[str, Any]:
        print("\n" + "=" * 65)
        print("  >>> PRIMO RL PEKİŞTİRMELİ EĞİTİM (PPO TRAINING) BAŞLATILDI <<< ")
        print("=" * 65)
        print(f"  • Cihaz:                 {self.device}")
        print(f"  • Durum Boyutu (State):  {self.state_dim} Boyut")
        print(f"  • Epoch Sayısı:          {epochs}")
        print(f"  • Rollout Boyutu:        {rollout_steps} Adım/Epoch")
        print(f"  • Borsa Modeli:          MEXC Vadeli (Taker: %0.02, Slippage: %0.01)")
        print(f"  • Ödül Fonksiyonu:       Two-Phase Dynamic Sharpe Ratio (§3.4)")
        print("=" * 65 + "\n")

        # Create Gymnasium environment with realistic MEXC friction
        env = PrimoCryptoTradingEnv(
            initial_balance=10000.0,
            max_notional=800.0,
            leverage=200.0,
            exchange_preset="MEXC",
            taker_fee_pct=0.0002,
            maker_fee_pct=0.0000,
            slippage_pct=0.0001,
            sharpe_warmup_window=30
        )

        all_coins = list(dataset.keys())
        history_loss = []
        history_rewards = []

        start_time = time.time()

        for epoch in range(1, epochs + 1):
            coin = all_coins[(epoch - 1) % len(all_coins)]
            candles = dataset[coin]
            closes = [c["close"] for c in candles]
            highs = [c["high"] for c in candles]
            lows = [c["low"] for c in candles]

            warmup = 60
            max_idx = len(closes) - 1

            obs, _ = env.reset()
            obs_buffer = []
            action_buffer = []
            log_prob_buffer = []
            reward_buffer = []
            value_buffer = []
            done_buffer = []

            epoch_reward = 0.0

            # 1. Rollout Trajectory Collection
            self.model.eval()
            curr_step = warmup

            for step in range(rollout_steps):
                t_idx = min(curr_step, max_idx)
                curr_step = (curr_step + 1) if curr_step < max_idx else warmup

                p_curr = closes[t_idx]
                w_closes = list(closes[:t_idx + 1])
                w_highs = list(highs[:t_idx + 1])
                w_lows = list(lows[:t_idx + 1])

                # Build 23-dim state vector
                tech_vec = self.tech_engine.get_feature_array(w_highs, w_lows, w_closes, p_curr)
                nlp_vec = self.nlp_engine.get_feature_array(coin)
                oir = np.clip(np.sin(t_idx / 12.0) * 0.5, -0.9, 0.9)
                micro_vec = np.array([oir, 0.05, 0.8, 0.0002], dtype=np.float32)

                pos_ratio = (env.position / env.max_notional * env.position_dir)
                pnl_pct = (p_curr - env.entry_price) / max(env.entry_price, 1e-5) * env.position_dir if env.entry_price > 0 else 0.0
                price_ratio = (p_curr / env.entry_price) if env.entry_price > 0 else 1.0

                state = np.zeros(23, dtype=np.float32)
                state[0] = float(np.clip(env.balance / 10000.0, 0.1, 10.0))
                state[1] = float(pos_ratio)
                state[2] = float(np.clip(pnl_pct * 10.0, -1.0, 1.0))
                state[3] = float(np.clip(price_ratio - 1.0, -0.2, 0.2))
                state[4:12] = tech_vec
                state[12:19] = nlp_vec
                state[19:23] = micro_vec

                state_tensor = torch.from_numpy(state).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    action_pred, value_pred = self.model(state_tensor)
                    mean_action = action_pred.item()
                    value = value_pred.item()

                # Action sampling with Gaussian exploration noise
                sigma = max(0.2 * (1.0 - (epoch / epochs)), 0.05)
                sampled_action = np.clip(mean_action + np.random.normal(0, sigma), -1.0, 1.0)
                log_prob = -0.5 * (((sampled_action - mean_action) / sigma) ** 2) - np.log(sigma * np.sqrt(2 * np.pi))

                # Step the environment with realistic fees & Dynamic Sharpe Reward
                next_obs, reward, terminated, truncated, _ = env.step(
                    action=np.array([sampled_action], dtype=np.float32),
                    current_price=p_curr,
                    tech_vector=tech_vec,
                    nlp_vector=nlp_vec,
                    micro_vector=micro_vec
                )

                obs_buffer.append(state)
                action_buffer.append(sampled_action)
                log_prob_buffer.append(log_prob)
                reward_buffer.append(reward)
                value_buffer.append(value)
                done_buffer.append(terminated or truncated)

                epoch_reward += reward

                if terminated or truncated:
                    obs, _ = env.reset()

            # 2. Generalized Advantage Estimation (GAE)
            values = np.array(value_buffer + [0.0])
            rewards = np.array(reward_buffer)
            dones = np.array(done_buffer + [False])

            advantages = np.zeros_like(rewards, dtype=np.float32)
            last_gae = 0.0

            for t in reversed(range(len(rewards))):
                non_terminal = 1.0 - float(dones[t])
                delta = rewards[t] + self.gamma * values[t + 1] * non_terminal - values[t]
                last_gae = delta + self.gamma * self.gae_lambda * non_terminal * last_gae
                advantages[t] = last_gae

            returns = advantages + values[:-1]
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

            # 3. PPO Surrogate Loss & Optimization
            self.model.train()
            states_t = torch.tensor(np.array(obs_buffer), dtype=torch.float32).to(self.device)
            actions_t = torch.tensor(np.array(action_buffer), dtype=torch.float32).unsqueeze(1).to(self.device)
            old_log_probs_t = torch.tensor(np.array(log_prob_buffer), dtype=torch.float32).unsqueeze(1).to(self.device)
            advantages_t = torch.tensor(advantages, dtype=torch.float32).unsqueeze(1).to(self.device)
            returns_t = torch.tensor(returns, dtype=torch.float32).unsqueeze(1).to(self.device)

            dataset_size = len(obs_buffer)
            indices = np.arange(dataset_size)
            epoch_loss = 0.0
            num_updates = 0

            # 4 PPO optimization passes over mini-batches
            for _ in range(4):
                np.random.shuffle(indices)
                for start in range(0, dataset_size, batch_size):
                    end = start + batch_size
                    b_idx = indices[start:end]

                    b_states = states_t[b_idx]
                    b_actions = actions_t[b_idx]
                    b_old_log_probs = old_log_probs_t[b_idx]
                    b_advantages = advantages_t[b_idx]
                    b_returns = returns_t[b_idx]

                    b_action_preds, b_values = self.model(b_states)

                    # Gaussian log probability under current policy
                    sigma = max(0.15 * (1.0 - (epoch / epochs)), 0.04)
                    b_new_log_probs = -0.5 * (((b_actions - b_action_preds) / sigma) ** 2) - np.log(sigma * np.sqrt(2 * np.pi))

                    # Ratio & PPO Clipped Surrogate Loss
                    ratios = torch.exp(b_new_log_probs - b_old_log_probs)
                    surr1 = ratios * b_advantages
                    surr2 = torch.clamp(ratios, 1.0 - self.clip_eps, 1.0 + self.clip_eps) * b_advantages
                    policy_loss = -torch.min(surr1, surr2).mean()

                    # Value Function Loss
                    value_loss = nn.functional.mse_loss(b_values, b_returns)

                    # Entropy Bonus
                    entropy = 0.5 * (1.0 + np.log(2 * np.pi * sigma ** 2))
                    total_loss = policy_loss + (self.value_coef * value_loss) - (self.entropy_coef * entropy)

                    self.optimizer.zero_grad()
                    total_loss.backward()
                    nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=0.5)
                    self.optimizer.step()

                    epoch_loss += total_loss.item()
                    num_updates += 1

            self.scheduler.step()
            avg_loss = epoch_loss / max(num_updates, 1)
            history_loss.append(avg_loss)
            history_rewards.append(epoch_reward)

            elapsed = time.time() - start_time
            print(f" [Epoch {epoch:02d}/{epochs:02d}] Varlık: {coin:<4} | Ortalama Ödül: {epoch_reward:+8.2f} | Loss: {avg_loss:8.4f} | Bakiye: ${env.balance:9.2f} | Süre: {elapsed:.1f}s")

        # 4. Save Optimized Model Weights
        torch.save(self.model.state_dict(), self.weights_path)
        print(f"\n[BAŞARILI] Optimal PPO Ağırlıkları Kaydedildi: {self.weights_path}")

        return {
            "status": "training_completed",
            "epochs": epochs,
            "final_loss": round(history_loss[-1], 4),
            "final_reward": round(history_rewards[-1], 2),
            "weights_path": self.weights_path,
            "duration_seconds": round(time.time() - start_time, 2)
        }


def main():
    symbols = ["SOL", "HYPE", "BTC"]
    print("Gerçek HyperLiquid Piyasa Veri Seti İndiriliyor...")
    dataset = fetch_historical_dataset(symbols, interval="1m", num_candles=2500)

    trainer = PrimoDeepPPOTrainer(state_dim=23, lr=3e-4)
    result = trainer.train_on_market_data(dataset, epochs=15, rollout_steps=512, batch_size=64)

    print("\n" + "=" * 65)
    print(" >>> PEKİŞTİRMELİ EĞİTİM TAMAMLANDI VE MODEL GÜNCELLENDİ! <<< ")
    print("=" * 65)
    print(f" Durum:              {result['status']}")
    print(f" Tamamlanan Epoch:   {result['epochs']}")
    print(f" Son Model Kaybı:    {result['final_loss']}")
    print(f" Toplam Süre:        {result['duration_seconds']} saniye")
    print(f" Kaydedilen Ağırlık: {result['weights_path']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
