import sqlite3
import os
import time
import json
import uuid
import socket
from datetime import datetime
from typing import Dict, Any, Optional, List

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "trade_memory.db")
CENTRAL_LAKE_DIR = os.path.join(os.path.dirname(__file__), "..", "database", "central_lake")
DEVICE_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "device_id.json")


def get_or_create_device_id() -> str:
    """Returns persistent anonymous device ID (e.g. Device_A8F2)"""
    if os.path.exists(DEVICE_CONFIG_PATH):
        try:
            with open(DEVICE_CONFIG_PATH, 'r') as f:
                return json.load(f).get('device_id', 'Device_' + str(uuid.uuid4())[:6].upper())
        except Exception:
            pass
    device_id = 'Device_' + str(uuid.uuid4())[:6].upper()
    try:
        os.makedirs(os.path.dirname(DEVICE_CONFIG_PATH), exist_ok=True)
        with open(DEVICE_CONFIG_PATH, 'w') as f:
            json.dump({'device_id': device_id, 'created_at': str(datetime.now())}, f, indent=2)
    except Exception:
        pass
    return device_id


class TradeDataLogger:
    """
    Autonomous Edge Experience & Telemetry Logger:
    Records high-frequency market states, L2 orderbook depth, and trade results.
    Packages and synchronizes datasets to the Central Training Station.
    """
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.device_id = get_or_create_device_id()
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(CENTRAL_LAKE_DIR, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Market States Table (High-Frequency Microstructure)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                symbol TEXT,
                price REAL,
                bbl REAL,
                bbm REAL,
                bbu REAL,
                stoch_k REAL,
                oir REAL,
                funding_apr REAL,
                basis_pct REAL,
                composite_alpha REAL
            )
            """)

            # 2. Completed Trades Table (Action-Reward Dataset)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                size_coin REAL,
                notional_usd REAL,
                required_margin REAL,
                leverage REAL,
                pnl_usd REAL,
                roe_pct REAL,
                price_change_pct REAL,
                duration_seconds REAL,
                exit_reason TEXT,
                entry_stoch_k REAL,
                entry_oir REAL,
                entry_alpha REAL,
                entry_time TEXT,
                exit_time TEXT
            )
            """)
            conn.commit()

    def log_market_state(self, symbol: str, price: float, bbl: float, bbm: float, bbu: float, 
                         stoch_k: float, oir: float, funding_apr: float, basis_pct: float, composite_alpha: float):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO market_states 
                (timestamp, symbol, price, bbl, bbm, bbu, stoch_k, oir, funding_apr, basis_pct, composite_alpha)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (time.time(), symbol, price, bbl, bbm, bbu, stoch_k, oir, funding_apr, basis_pct, composite_alpha))
                conn.commit()
        except Exception:
            pass

    def log_trade_experience(self, trade_data: Dict[str, Any]):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO trade_experiences
                (device_id, symbol, side, entry_price, exit_price, size_coin, notional_usd, required_margin, leverage,
                 pnl_usd, roe_pct, price_change_pct, duration_seconds, exit_reason,
                 entry_stoch_k, entry_oir, entry_alpha, entry_time, exit_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.device_id,
                    trade_data.get('symbol'),
                    trade_data.get('side'),
                    trade_data.get('entry_price'),
                    trade_data.get('exit_price'),
                    trade_data.get('size_coin'),
                    trade_data.get('notional_usd'),
                    trade_data.get('required_margin'),
                    trade_data.get('leverage', 1000.0),
                    trade_data.get('pnl_usd'),
                    trade_data.get('roe_pct'),
                    trade_data.get('price_change_pct'),
                    trade_data.get('duration_seconds'),
                    trade_data.get('exit_reason'),
                    trade_data.get('entry_stoch_k', 50.0),
                    trade_data.get('entry_oir', 0.0),
                    trade_data.get('entry_alpha', 0.0),
                    trade_data.get('entry_time'),
                    str(datetime.now())
                ))
                conn.commit()
        except Exception:
            pass

    def export_telemetry_payload(self) -> dict:
        """Packages all local trades into a telemetry JSON payload for upload to Central Training Hub"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trade_experiences ORDER BY id DESC LIMIT 500")
                trades = [dict(row) for row in cursor.fetchall()]

                cursor.execute("SELECT * FROM market_states ORDER BY id DESC LIMIT 500")
                states = [dict(row) for row in cursor.fetchall()]

                return {
                    'device_id': self.device_id,
                    'app_version': '1.0.0',
                    'exported_at': datetime.now().isoformat(),
                    'trades_count': len(trades),
                    'trades': trades,
                    'market_states': states
                }
        except Exception as e:
            return {'device_id': self.device_id, 'error': str(e), 'trades': []}

    @staticmethod
    def save_incoming_telemetry(payload: dict) -> dict:
        """Central Server side: Validates and writes incoming device telemetry to Central Data Lake"""
        device_id = payload.get('device_id', 'Unknown_Node')
        trades = payload.get('trades', [])
        
        if not trades:
            return {'status': 'skipped', 'message': 'No trades in payload', 'saved_count': 0}

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{device_id}_{timestamp_str}_{len(trades)}trades.json"
        filepath = os.path.join(CENTRAL_LAKE_DIR, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)

            return {
                'status': 'success',
                'saved_file': filename,
                'device_id': device_id,
                'saved_count': len(trades),
                'timestamp': timestamp_str
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'saved_count': 0}

    def get_summary_stats(self) -> dict:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), SUM(pnl_usd), AVG(roe_pct) FROM trade_experiences")
                row = cursor.fetchone()
                total_trades = row[0] or 0
                total_pnl = row[1] or 0.0
                avg_roe = row[2] or 0.0

                cursor.execute("SELECT COUNT(*) FROM trade_experiences WHERE pnl_usd > 0")
                win_count = cursor.fetchone()[0] or 0
                win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

                cursor.execute("SELECT COUNT(*) FROM market_states")
                state_count = cursor.fetchone()[0] or 0

                return {
                    'device_id': self.device_id,
                    'total_trades_logged': total_trades,
                    'win_rate': round(win_rate, 2),
                    'total_pnl_usd': round(total_pnl, 2),
                    'avg_roe_pct': round(avg_roe, 2),
                    'market_states_count': state_count
                }
        except Exception:
            return {'device_id': self.device_id, 'total_trades_logged': 0, 'win_rate': 0, 'total_pnl_usd': 0}
