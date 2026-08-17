import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any


class PaperAccount:
    """
    High-Performance Leveraged Paper Trading Account with Realistic Exchange Friction.
    Supports MEXC / HyperLiquid / Binance fee tiers, slippage, margin tracking, and net PnL calculations.
    """
    def __init__(
        self,
        start_balance: float = 10000.0,
        leverage: float = 200.0,
        exchange_preset: str = "MEXC",
        maker_fee_pct: float = 0.0000,    # MEXC Futures: 0.00% Maker
        taker_fee_pct: float = 0.0002,    # MEXC Futures: 0.02% Taker
        slippage_pct: float = 0.0001,     # 0.01% execution slippage
        filename: str = "paper_data.json"
    ):
        self.filename = filename
        self.start_balance = start_balance
        self.balance = start_balance
        self.leverage = leverage
        self.exchange_preset = exchange_preset
        self.maker_fee_pct = maker_fee_pct
        self.taker_fee_pct = taker_fee_pct
        self.slippage_pct = slippage_pct

        self.total_fees_paid = 0.0
        self.total_slippage_cost = 0.0
        self.total_gross_pnl = 0.0
        self.positions: List[Dict[str, Any]] = []
        self.trade_history: List[Dict[str, Any]] = []
        self.load()

    def set_exchange_preset(self, preset: str):
        """
        Presets for popular crypto derivatives exchanges.
        """
        preset_upper = preset.upper()
        if preset_upper == "MEXC":
            self.exchange_preset = "MEXC"
            self.maker_fee_pct = 0.0000   # 0.00%
            self.taker_fee_pct = 0.0002   # 0.02%
            self.slippage_pct = 0.0001
        elif preset_upper == "HYPERLIQUID":
            self.exchange_preset = "HYPERLIQUID"
            self.maker_fee_pct = 0.00010  # 0.010%
            self.taker_fee_pct = 0.00035  # 0.035%
            self.slippage_pct = 0.00008
        elif preset_upper == "BINANCE":
            self.exchange_preset = "BINANCE"
            self.maker_fee_pct = 0.00020  # 0.020%
            self.taker_fee_pct = 0.00050  # 0.050%
            self.slippage_pct = 0.00010
        elif preset_upper == "ZERO_FEE":
            self.exchange_preset = "ZERO_FEE"
            self.maker_fee_pct = 0.0
            self.taker_fee_pct = 0.0
            self.slippage_pct = 0.0

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.balance = float(data.get('balance', self.start_balance))
                    self.total_fees_paid = float(data.get('total_fees_paid', 0.0))
                    self.total_gross_pnl = float(data.get('total_gross_pnl', 0.0))
                    self.total_slippage_cost = float(data.get('total_slippage_cost', 0.0))
                    self.exchange_preset = data.get('exchange_preset', self.exchange_preset)
                    self.positions = data.get('positions', [])
                    self.trade_history = data.get('trade_history', [])
            except Exception:
                pass

    def save(self):
        data = {
            'balance': round(self.balance, 4),
            'start_balance': round(self.start_balance, 2),
            'total_fees_paid': round(self.total_fees_paid, 4),
            'total_gross_pnl': round(self.total_gross_pnl, 4),
            'total_slippage_cost': round(self.total_slippage_cost, 4),
            'exchange_preset': self.exchange_preset,
            'positions': self.positions,
            'trade_history': self.trade_history[-100:]  # Keep last 100 trades
        }
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass

    def execute_trade(
        self,
        symbol: str,
        side: str,
        size_coin: float,
        price: float,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        is_maker: bool = False
    ) -> bool:
        """
        Executes trade with real-world slippage, taker/maker fee deduction, and 1000:1 margin tracking.
        """
        fee_rate = self.maker_fee_pct if is_maker else self.taker_fee_pct

        # 1. Check if closing existing opposite position
        for i, pos in enumerate(self.positions):
            if pos['symbol'] == symbol:
                if pos['side'] != side:
                    # Closing Position with Slippage & Exit Fee
                    exit_slip = price * self.slippage_pct * (-1.0 if pos['side'] == 'LONG' else 1.0)
                    effective_exit_price = price + exit_slip
                    slip_cost = abs(exit_slip) * pos['size_coin']

                    gross_pnl = self._calculate_gross_pnl(pos, effective_exit_price)
                    exit_notional = pos['size_coin'] * effective_exit_price
                    exit_fee = exit_notional * fee_rate
                    entry_fee = pos.get('entry_fee', 0.0)

                    net_pnl = gross_pnl - exit_fee  # Entry fee was already deducted upon entry

                    self.balance += (gross_pnl - exit_fee)
                    self.total_fees_paid += exit_fee
                    self.total_slippage_cost += slip_cost
                    self.total_gross_pnl += gross_pnl

                    self.trade_history.append({
                        'action': 'CLOSE',
                        'symbol': symbol,
                        'side': pos['side'],
                        'gross_pnl': round(gross_pnl, 4),
                        'entry_fee': round(entry_fee, 4),
                        'exit_fee': round(exit_fee, 4),
                        'total_fees': round(entry_fee + exit_fee, 4),
                        'net_pnl': round(gross_pnl - entry_fee - exit_fee, 4),
                        'pnl': round(gross_pnl - entry_fee - exit_fee, 2),  # Backward compatibility
                        'entry_price': pos['entry_price'],
                        'exit_price': round(effective_exit_price, 4),
                        'raw_exit_price': price,
                        'size': pos['size_coin'],
                        'exchange': self.exchange_preset,
                        'time': str(datetime.now())
                    })
                    del self.positions[i]
                    self.save()
                    return True
                else:
                    return False

        # 2. Margin & Free Balance Check
        # Apply entry slippage
        entry_slip = price * self.slippage_pct * (1.0 if side == 'LONG' else -1.0)
        effective_entry_price = price + entry_slip
        slip_cost = abs(entry_slip) * size_coin

        notional_value = size_coin * effective_entry_price
        required_margin = notional_value / self.leverage
        entry_fee = notional_value * fee_rate

        total_required = required_margin + entry_fee
        if total_required > self.balance:
            return False

        # Deduct entry fee immediately from balance
        self.balance -= entry_fee
        self.total_fees_paid += entry_fee
        self.total_slippage_cost += slip_cost

        new_pos = {
            'symbol': symbol,
            'side': side,
            'size_coin': size_coin,
            'entry_price': round(effective_entry_price, 4),
            'raw_entry_price': price,
            'entry_fee': round(entry_fee, 4),
            'required_margin': round(required_margin, 2),
            'notional_usd': round(notional_value, 2),
            'sl_price': sl_price,
            'tp_price': tp_price,
            'exchange': self.exchange_preset,
            'time': str(datetime.now())
        }
        self.positions.append(new_pos)
        self.save()
        return True

    def _calculate_gross_pnl(self, pos: dict, current_price: float) -> float:
        diff = current_price - pos['entry_price']
        if pos['side'] == 'SHORT':
            diff = -diff
        return diff * pos['size_coin']

    def get_portfolio_status(self, current_prices: Dict[str, float]) -> dict:
        unrealized_gross_pnl = 0.0
        unrealized_exit_fees = 0.0
        used_margin = 0.0

        for pos in self.positions:
            price = current_prices.get(pos['symbol'], pos['entry_price'])
            gross = self._calculate_gross_pnl(pos, price)
            unrealized_gross_pnl += gross
            unrealized_exit_fees += (pos['size_coin'] * price) * self.taker_fee_pct
            used_margin += pos.get('required_margin', (pos['size_coin'] * pos['entry_price']) / self.leverage)

        unrealized_net_pnl = unrealized_gross_pnl - unrealized_exit_fees
        equity = self.balance + unrealized_net_pnl
        free_margin = max(0.0, equity - used_margin)
        margin_level = (equity / used_margin * 100) if used_margin > 0 else 9999.0

        total_realized_net = sum(t.get('net_pnl', t.get('pnl', 0.0)) for t in self.trade_history)

        return {
            'balance': round(self.balance, 2),
            'equity': round(equity, 2),
            'unrealized_gross_pnl': round(unrealized_gross_pnl, 2),
            'unrealized_pnl': round(unrealized_net_pnl, 2),
            'realized_net_pnl': round(total_realized_net, 2),
            'total_fees_paid': round(self.total_fees_paid, 2),
            'total_slippage_cost': round(self.total_slippage_cost, 2),
            'exchange_preset': self.exchange_preset,
            'maker_fee_pct': round(self.maker_fee_pct * 100.0, 3),
            'taker_fee_pct': round(self.taker_fee_pct * 100.0, 3),
            'slippage_pct': round(self.slippage_pct * 100.0, 3),
            'used_margin': round(used_margin, 2),
            'free_margin': round(free_margin, 2),
            'margin_level_pct': round(margin_level, 1),
            'leverage': int(self.leverage),
            'open_positions': len(self.positions)
        }
