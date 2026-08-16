import threading
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import json
import glob
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os

from core.data_logger import TradeDataLogger, CENTRAL_LAKE_DIR
from tools.train_from_phone_data import train_central_federated_model, WEIGHTS_DIR


class TradingDashboard:
    def __init__(self, paper_account, port=5000):
        self.paper_account = paper_account
        self.port = port
        self.logger = TradeDataLogger()
        self.app = Flask(__name__, 
                        template_folder='../templates',
                        static_folder='../static')
        CORS(self.app)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # State tracking
        self.current_price = 0.0
        self.current_symbol = "BTC"
        self.prices = {}  # Multi-symbol price tracker
        self.microstructure = {} # L2 Orderbook Imbalance, Funding, OI tracker
        self.bot_status = "Initializing..."
        self.last_signal = None
        self.recent_logs = []
        
        self._setup_routes()
        self._setup_websocket()
        
    def _setup_routes(self):
        """Setup REST API endpoints"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')

        @self.app.route('/training')
        def training_hub():
            """AI Training & Distributed Telemetry Center Page"""
            return render_template('training.html')
        
        @self.app.route('/api/status')
        def get_status():
            """Get current bot status and portfolio with multi-asset prices & L2 microstructure"""
            stats = self.paper_account.get_portfolio_status(self.prices)
            
            total_realized_pnl = sum(
                trade.get('pnl', 0) 
                for trade in self.paper_account.trade_history
            )
            
            return jsonify({
                'symbol': self.current_symbol,
                'price': self.current_price,
                'prices': self.prices,
                'microstructure': self.microstructure,
                'status': self.bot_status,
                'balance': stats['balance'],
                'equity': stats['equity'],
                'unrealized_pnl': stats['unrealized_pnl'],
                'realized_pnl': total_realized_pnl,
                'used_margin': stats.get('used_margin', 0.0),
                'free_margin': stats.get('free_margin', stats['equity']),
                'margin_level_pct': stats.get('margin_level_pct', 9999.0),
                'leverage': stats.get('leverage', 1000),
                'open_positions': stats['open_positions'],
                'last_signal': self.last_signal,
                'device_id': self.logger.device_id,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/positions')
        def get_positions():
            """Get rich open positions data for detailed UI display"""
            positions = []
            leverage = getattr(self.paper_account, 'leverage', 1000.0)

            for pos in self.paper_account.positions:
                sym = pos['symbol']
                entry_px = float(pos['entry_price'])
                cur_px = float(self.prices.get(sym, entry_px))
                size_coin = float(pos['size_coin'])
                notional_usd = size_coin * cur_px
                req_margin = float(pos.get('required_margin', notional_usd / leverage))
                
                # PnL calculations
                if pos['side'] == 'LONG':
                    price_change_pct = (cur_px - entry_px) / entry_px if entry_px > 0 else 0.0
                    pnl_usd = (cur_px - entry_px) * size_coin
                else:
                    price_change_pct = (entry_px - cur_px) / entry_px if entry_px > 0 else 0.0
                    pnl_usd = (entry_price - cur_px) * size_coin if 'entry_price' in locals() else (entry_px - cur_px) * size_coin
                    
                roe_pct = (pnl_usd / max(req_margin, 0.01)) * 100.0

                try:
                    entry_time = datetime.fromisoformat(pos['time'])
                    dur_secs = int((datetime.now() - entry_time).total_seconds())
                    mins = dur_secs // 60
                    secs = dur_secs % 60
                    dur_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
                except Exception:
                    dur_str = "0m"

                positions.append({
                    'symbol': sym,
                    'side': pos['side'],
                    'size_coin': size_coin,
                    'notional_usd': round(notional_usd, 2),
                    'required_margin': round(req_margin, 2),
                    'leverage': int(leverage),
                    'entry_price': entry_px,
                    'current_price': cur_px,
                    'price_change_pct': round(price_change_pct * 100, 2),
                    'pnl_usd': round(pnl_usd, 2),
                    'roe_pct': round(roe_pct, 1),
                    'sl_price': pos.get('sl_price'),
                    'tp_price': pos.get('tp_price'),
                    'duration_str': dur_str,
                    'entry_time': pos['time']
                })
            
            return jsonify(positions)
        
        @self.app.route('/api/history')
        def get_history():
            """Get trade history with pagination"""
            history = self.paper_account.trade_history[-50:]
            history.reverse()
            return jsonify(history)

        # =============================================================
        # TELEMETRY & TRAINING STATION API ENDPOINTS
        # =============================================================
        @self.app.route('/api/telemetry/export')
        def export_telemetry():
            """Phone / Local node downloads its full telemetry payload"""
            payload = self.logger.export_telemetry_payload()
            return jsonify(payload)

        @self.app.route('/api/telemetry/upload', methods=['POST'])
        def upload_telemetry():
            """Central Hub receives telemetry packages from phones / edge nodes"""
            try:
                data = request.get_json(force=True)
                if not data:
                    return jsonify({'status': 'error', 'message': 'Empty JSON payload'}), 400

                res = TradeDataLogger.save_incoming_telemetry(data)
                self.add_log(f"📥 Telemetri Alındı: {data.get('device_id')} ({data.get('trades_count', len(data.get('trades', [])))} işlem)")
                return jsonify(res)
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/training/status')
        def get_training_status():
            """Returns stats on all connected devices, data files, and current model weights"""
            json_files = glob.glob(os.path.join(CENTRAL_LAKE_DIR, "*.json"))
            nodes_info = {}
            total_crowdsourced_trades = 0

            for jf in json_files:
                try:
                    with open(jf, 'r', encoding='utf-8') as f:
                        payload = json.load(f)
                        dev_id = payload.get('device_id', 'Unknown')
                        cnt = payload.get('trades_count', len(payload.get('trades', [])))
                        total_crowdsourced_trades += cnt
                        nodes_info[dev_id] = {
                            'device_id': dev_id,
                            'trades_count': nodes_info.get(dev_id, {}).get('trades_count', 0) + cnt,
                            'last_sync': payload.get('exported_at', str(datetime.now()))
                        }
                except Exception:
                    pass

            local_stats = self.logger.get_summary_stats()

            # Current learned rules
            rules_file = os.path.join(WEIGHTS_DIR, "edge_learned_rules.json")
            current_rules = None
            if os.path.exists(rules_file):
                try:
                    with open(rules_file, 'r') as f:
                        current_rules = json.load(f)
                except Exception:
                    pass

            return jsonify({
                'total_nodes_connected': max(1, len(nodes_info)),
                'nodes_list': list(nodes_info.values()),
                'total_crowdsourced_trades': total_crowdsourced_trades + local_stats.get('total_trades_logged', 0),
                'local_node_stats': local_stats,
                'current_rules': current_rules,
                'data_lake_files_count': len(json_files)
            })

        @self.app.route('/api/training/start', methods=['POST'])
        def start_training():
            """Triggers central model training on all synchronized phone datasets"""
            try:
                res = train_central_federated_model()
                self.add_log(f"🧠 Yapay Zeka Eğitimi Tamamlandı! ({res.get('rules', {}).get('total_training_samples', 0)} işlem)")
                return jsonify(res)
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500

        @self.app.route('/api/stats')
        def get_stats():
            """Get performance statistics"""
            history = self.paper_account.trade_history
            if not history:
                return jsonify({
                    'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                    'win_rate': 0, 'total_pnl': 0, 'avg_trade_pnl': 0, 'best_trade': 0, 'worst_trade': 0
                })
            
            total_trades = len(history)
            winning_trades = sum(1 for t in history if t.get('pnl', 0) > 0)
            losing_trades = sum(1 for t in history if t.get('pnl', 0) < 0)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            pnls = [t.get('pnl', 0) for t in history]
            total_pnl = sum(pnls)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            best_trade = max(pnls) if pnls else 0
            worst_trade = min(pnls) if pnls else 0
            
            return jsonify({
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_trade_pnl': round(avg_pnl, 2),
                'best_trade': round(best_trade, 2),
                'worst_trade': round(worst_trade, 2)
            })
    
    def _setup_websocket(self):
        @self.socketio.on('connect')
        def handle_connect():
            print("📡 Dashboard client connected")
            emit('connection_response', {'status': 'connected'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            print("📡 Dashboard client disconnected")
    
    def update_price(self, symbol, price):
        self.current_symbol = symbol
        self.current_price = float(price)
        self.prices[symbol] = float(price)
        self.socketio.emit('price_update', {
            'symbol': symbol,
            'price': price,
            'prices': self.prices,
            'microstructure': self.microstructure,
            'timestamp': datetime.now().isoformat()
        })

    def update_microstructure(self, symbol, data):
        self.microstructure[symbol] = data
    
    def update_status(self, status):
        self.bot_status = status
        self.socketio.emit('status_update', {
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    
    def notify_position_change(self, action, position_data):
        self.socketio.emit('position_change', {
            'action': action,
            'position': position_data,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_log(self, message):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.recent_logs.append(log_entry)
        if len(self.recent_logs) > 35:
            self.recent_logs.pop(0)
        
        self.socketio.emit('log_message', {
            'message': log_entry,
            'timestamp': timestamp
        })
    
    def run(self):
        try:
            print(f"Starting Dashboard Server on http://localhost:{self.port}")
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True, log_output=False)
        except Exception as e:
            print(f"Dashboard server error: {e}")
    
    def start_background(self):
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        time.sleep(0.5)
        print(f"Dashboard running at http://localhost:{self.port}")
        return thread
