import json
import os
from datetime import datetime
from typing import Dict, List, Optional


class PaperAccount:
    """
    High-Performance Leveraged Paper Trading Account.
    Supports up to 1000:1 Leverage, Margin Tracking, and Instant Execution.
    """
    def __init__(self, start_balance: float = 10000.0, leverage: float = 1000.0, filename: str = "paper_data.json"):
        self.filename = filename
        self.start_balance = start_balance
        self.balance = start_balance
        self.leverage = leverage
        self.positions = []
        self.trade_history = []
        self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.balance = float(data.get('balance', self.start_balance))
                    self.positions = data.get('positions', [])
                    self.trade_history = data.get('trade_history', [])
            except Exception:
                pass

    def save(self):
        data = {
            'balance': round(self.balance, 4),
            'positions': self.positions,
            'trade_history': self.trade_history[-100:]  # Keep last 100 trades
        }
        try:
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def execute_trade(self, symbol: str, side: str, size_coin: float, price: float, sl_price: Optional[float] = None, tp_price: Optional[float] = None) -> bool:
        """
        Instant Execution with 1000:1 Margin Calculation.
        """
        # 1. Check if closing existing opposite position
        for i, pos in enumerate(self.positions):
            if pos['symbol'] == symbol:
                if pos['side'] != side:
                    pnl = self._calculate_pnl(pos, price)
                    self.balance += pnl
                    self.trade_history.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'side': pos['side'],
                        'pnl': round(pnl, 2),
                        'entry_price': pos['entry_price'],
                        'exit_price': price,
                        'size': pos['size_coin'],
                        'time': str(datetime.now())
                    })
                    del self.positions[i]
                    self.save()
                    return True
                else:
                    # Already long/short
                    return False

        # 2. Margin Check at 1000:1 Leverage
        notional_value = size_coin * price
        required_margin = notional_value / self.leverage

        if required_margin > self.balance:
            # Insufficient free margin
            return False

        new_pos = {
            'symbol': symbol,
            'side': side,
            'size_coin': size_coin,
            'entry_price': price,
            'required_margin': round(required_margin, 2),
            'sl_price': sl_price,
            'tp_price': tp_price,
            'time': str(datetime.now())
        }
        self.positions.append(new_pos)
        self.save()
        return True

    def _calculate_pnl(self, pos: dict, current_price: float) -> float:
        diff = current_price - pos['entry_price']
        if pos['side'] == 'SHORT':
            diff = -diff
        return diff * pos['size_coin']

    def get_portfolio_status(self, current_prices: Dict[str, float]) -> dict:
        unrealized_pnl = 0.0
        used_margin = 0.0

        for pos in self.positions:
            price = current_prices.get(pos['symbol'], pos['entry_price'])
            unrealized_pnl += self._calculate_pnl(pos, price)
            used_margin += pos.get('required_margin', (pos['size_coin'] * pos['entry_price']) / self.leverage)

        equity = self.balance + unrealized_pnl
        free_margin = max(0.0, equity - used_margin)
        margin_level = (equity / used_margin * 100) if used_margin > 0 else 9999.0

        return {
            'balance': round(self.balance, 2),
            'equity': round(equity, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'used_margin': round(used_margin, 2),
            'free_margin': round(free_margin, 2),
            'margin_level_pct': round(margin_level, 1),
            'leverage': int(self.leverage),
            'open_positions': len(self.positions)
        }
