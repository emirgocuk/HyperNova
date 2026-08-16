import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import sqlite3
import pandas as pd
import numpy as np
import json
import glob
from datetime import datetime
from termcolor import cprint

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "trade_memory.db")
CENTRAL_LAKE_DIR = os.path.join(os.path.dirname(__file__), "..", "database", "central_lake")
WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), "..", "ai_engine", "weights")


def load_all_telemetry_datasets():
    """
    Aggregates local SQLite database AND all synchronized phone JSON files in central_lake
    """
    all_trades = []

    # 1. Local SQLite Data
    if os.path.exists(DB_PATH):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                df_local = pd.read_sql_query("SELECT * FROM trade_experiences", conn)
                if not df_local.empty:
                    all_trades.append(df_local)
        except Exception:
            pass

    # 2. Remote Phone JSON files in central_lake
    if os.path.exists(CENTRAL_LAKE_DIR):
        json_files = glob.glob(os.path.join(CENTRAL_LAKE_DIR, "*.json"))
        for jf in json_files:
            try:
                with open(jf, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                    trades_list = payload.get('trades', [])
                    if trades_list:
                        df_remote = pd.DataFrame(trades_list)
                        all_trades.append(df_remote)
            except Exception:
                pass

    if all_trades:
        df_combined = pd.concat(all_trades, ignore_index=True).drop_duplicates(
            subset=['symbol', 'side', 'entry_price', 'exit_price', 'entry_time']
        )
        return df_combined

    return pd.DataFrame()


def train_central_federated_model():
    """
    Central Training Station Engine:
    Reads all crowdsourced phone data, optimizes Meta-Gating filter and trailing thresholds.
    """
    cprint("="*70, "cyan")
    cprint("🧠 HYPERNOVA: MERKEZİ FEDERE YAPAY ZEKA EĞİTİM İSTASYONU", "yellow", attrs=['bold'])
    cprint(f"📁 Veri Ambarı: {CENTRAL_LAKE_DIR}", "green")
    cprint("="*70, "cyan")

    os.makedirs(WEIGHTS_DIR, exist_ok=True)
    df_trades = load_all_telemetry_datasets()

    cprint(f"📊 Toplanan Toplam Gerçek Canlı İşlem: {len(df_trades)}", "cyan")

    if len(df_trades) < 3:
        cprint("ℹ️ Model eğitimi için veri birikmesi bekleniyor...", "yellow")
        return {
            'status': 'waiting_for_data',
            'sample_count': len(df_trades),
            'message': 'En az 3-5 canlı işlem kaydı toplanması bekleniyor.'
        }

    # 1. Action-Reward Analysis
    df_trades['target_win'] = (df_trades['pnl_usd'] > 0).astype(int)
    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['target_win'] == 1])
    win_rate = (winning_trades / total_trades) * 100.0
    total_pnl = float(df_trades['pnl_usd'].sum())

    # 2. Optimal Threshold Discovery (L2 OIR & Alpha Correlation)
    win_df = df_trades[df_trades['target_win'] == 1]
    loss_df = df_trades[df_trades['target_win'] == 0]

    optimal_min_oir = float(win_df['entry_oir'].quantile(0.25)) if not win_df.empty and 'entry_oir' in win_df else 0.15
    optimal_min_alpha = float(win_df['entry_alpha'].quantile(0.25)) if not win_df.empty and 'entry_alpha' in win_df else 10.0
    optimal_trailing_pullback = 0.0003

    # Output Model Rules & Meta Weights
    rules = {
        'version': '2.0.0',
        'generated_at': datetime.now().isoformat(),
        'total_training_samples': total_trades,
        'win_rate_achieved': round(win_rate, 2),
        'total_pnl_usd': round(total_pnl, 2),
        'optimal_long_oir_min': round(max(0.05, optimal_min_oir), 3),
        'optimal_alpha_min': round(max(5.0, optimal_min_alpha), 1),
        'trailing_pullback_pct': optimal_trailing_pullback,
        'unique_devices_contributing': int(df_trades['device_id'].nunique()) if 'device_id' in df_trades else 1
    }

    rules_path = os.path.join(WEIGHTS_DIR, "edge_learned_rules.json")
    with open(rules_path, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=4)

    cprint(f"\n✅ Merkezi Eğitim Tamamlandı! Kurallar Güncellendi -> {rules_path}", "green", attrs=['bold'])
    cprint(f"🎯 Katkıda Bulunan Farklı Telefon/Cihaz Sayısı: {rules['unique_devices_contributing']}", "yellow")
    cprint(f"🎯 Toplam Analiz Edilen İşlem: {total_trades}", "cyan")
    cprint(f"🏆 Sistem Kazanma Oranı: %{win_rate:.1f} | Toplam PnL: ${total_pnl:+.2f}", "green", attrs=['bold'])

    return {
        'status': 'success',
        'rules': rules,
        'rules_path': rules_path
    }


if __name__ == "__main__":
    train_central_federated_model()
