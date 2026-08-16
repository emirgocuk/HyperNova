import MetaTrader5 as mt5
import logging
import asyncio
from typing import Dict, Any
import time
from datetime import datetime, timedelta

logger = logging.getLogger("MT5Executor")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MT5Executor:
    """
    Hands-on execution engine. Sends actual orders to the XM terminal based on AI signals
    and the user's active risk profile.
    """
    def __init__(self, symbol: str = "EURUSD"):
        self.symbol = symbol
        self.real_symbol = self.symbol
        self.connected = False
        self.is_active = False # The "Bot Switch"
        self._connect()

    def _resolve_symbol(self, target_symbol: str) -> str:
        """Finds the actual symbol on the broker (e.g. BTCUSDm -> BTCUSD fallback)"""
        if mt5.symbol_select(target_symbol, True):
            return target_symbol
        if target_symbol.endswith('m'):
            base = target_symbol[:-1]
            if mt5.symbol_select(base, True):
                logger.info(f"Auto-resolved {target_symbol} to {base} (Standard Account Fallback)")
                return base
        return target_symbol

    def _connect(self):
        if not mt5.initialize():
            logger.error(f"MT5 Executor initialization failed: {mt5.last_error()}")
            return False
        
        self.connected = True
        self.real_symbol = self._resolve_symbol(self.symbol)
        logger.info(f"✅ MT5 Executor Connected for {self.real_symbol}")
        
        if not mt5.symbol_select(self.real_symbol, True):
            logger.error(f"Failed to select {self.real_symbol} in Market Watch.")
            self.connected = False
        return self.connected

    def set_symbol(self, new_symbol: str):
        if self.symbol == new_symbol:
            return True
        self.symbol = new_symbol
        self.real_symbol = self._resolve_symbol(new_symbol)
        logger.info(f"Switched executor symbol to {self.real_symbol} (Requested: {self.symbol})")
        if self.connected:
            if not mt5.symbol_select(self.real_symbol, True):
                logger.error(f"Failed to select {self.real_symbol} in Market Watch.")
                return False
        return True

    def activate_bot(self):
        self.is_active = True
        logger.info("🟢 BOT LIVE: Execution Engine Armed.")

    def deactivate_bot(self):
        self.is_active = False
        logger.info("🔴 BOT STOPPED: Execution Engine Disarmed.")

    def execute_signal(self, signal: str, confidence: float, config: Dict[str, Any]):
        """
        Executes a trade if the bot is armed and conditions are met.
        signal: "UPTREND" or "DOWNTREND"
        config: the ENGINE_CONFIG dict containing lot_size, active_profile, etc.
        """
        if not self.is_active or not self.connected:
            return None

        # Check if Algo Trading is enabled in the MT5 terminal
        terminal_info = mt5.terminal_info()
        if terminal_info and not terminal_info.trade_allowed:
            logger.error("⚠️ Algo Trading is DISABLED in MT5. Enable it via Tools > Options > Expert Advisors > Allow Algo Trading, or click the 'Algo Trading' button in the toolbar.")
            return {"status": "error", "reason": "Algo Trading disabled in MT5 terminal. Enable it first!"}

        # Determine Order Type
        if not mt5.symbol_select(self.real_symbol, True):
            logger.error(f"Failed to select {self.real_symbol}")
            return {"status": "error", "reason": f"Failed to select {self.real_symbol}"}
            
        tick = mt5.symbol_info_tick(self.real_symbol)
        if tick is None:
            logger.error(f"Failed to get tick for {self.real_symbol}, ensure Market Watch is synced")
            return {"status": "error", "reason": f"No tick data for {self.real_symbol}"}

        order_type = None
        if signal == "UPTREND":
            order_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif signal == "DOWNTREND":
            order_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            return None # SIDEWAYS

        lot_size = config.get("lot_size", 0.01)
        sl_pct = config.get("sl_pct", 1.0)  # percentage
        tp_pct = config.get("tp_pct", 2.0)  # percentage

        symbol_info = mt5.symbol_info(self.real_symbol)
        filling_mode = mt5.ORDER_FILLING_IOC
        digits = 5
        if symbol_info:
            digits = symbol_info.digits
            if symbol_info.filling_mode & 1: # FOK
                filling_mode = mt5.ORDER_FILLING_FOK
            elif symbol_info.filling_mode & 2: # IOC
                filling_mode = mt5.ORDER_FILLING_IOC
            else:
                filling_mode = mt5.ORDER_FILLING_RETURN

        # Calculate SL/TP as percentage of price
        sl_distance = price * (sl_pct / 100.0)
        tp_distance = price * (tp_pct / 100.0)

        if order_type == mt5.ORDER_TYPE_BUY:
            sl_price = round(price - sl_distance, digits)
            tp_price = round(price + tp_distance, digits)
        else:  # SELL
            sl_price = round(price + sl_distance, digits)
            tp_price = round(price - tp_distance, digits)

        logger.info(f"📊 SL/TP: Entry={price}, SL={sl_price} ({sl_pct}%), TP={tp_price} ({tp_pct}%)")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.real_symbol,
            "volume": float(lot_size),
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": 20,
            "magic": 777777,
            "comment": f"AI_{config['active_profile']}_{confidence:.2f}"[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }

        # Send order
        logger.info(f"🚀 SENDING ORDER: {signal} {lot_size} lots on {self.real_symbol}")
        result = mt5.order_send(request)
        
        if result is None:
            logger.error(f"order_send failed to return a result: {mt5.last_error()}")
            return {"status": "error", "reason": f"MT5 internal error: {mt5.last_error()}"}
            
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed, retcode={result.retcode}")
            return {"status": "error", "reason": f"Retcode {result.retcode} (e.g. invalid vol/price/filling)"}
        
        logger.info(f"✅ ORDER SUCCESS: Ticket {result.order}")
        return {
            "status": "success", 
            "ticket": result.order, 
            "price": result.price, 
            "volume": result.volume
        }
        
    def execute_grid_logic(self, current_price: float, config: Dict[str, Any]):
        """
        Elirox Fixed-Grid Logic. Deploys limit orders above and below the current price.
        """
        if not self.is_active or not self.connected: return None
        
        # 1. Clear old pending limit orders for this symbol first
        orders = mt5.orders_get(symbol=self.real_symbol)
        if orders:
            for order in orders:
                if order.type in (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT):
                    request = {
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order": order.ticket,
                    }
                    mt5.order_send(request)
                    
        # 2. Deploy 2 Buy Limits below, 2 Sell Limits above (Simplified Grid Span)
        grid_gap = 25.0 # Example gap distance (needs to be parameter later)
        lot_size = config.get("lot_size", 0.01)
        
        symbol_info = mt5.symbol_info(self.real_symbol)
        if not symbol_info: return
        digits = symbol_info.digits
        
        # BUY LIMIT (Below)
        buy_price = round(current_price - grid_gap, digits)
        buy_tp = round(buy_price + grid_gap, digits) # Take profit at next grid
        
        # SELL LIMIT (Above)
        sell_price = round(current_price + grid_gap, digits)
        sell_tp = round(sell_price - grid_gap, digits) # Take profit at next grid
        
        requests = []
        # Buy Limit setup
        requests.append({
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.real_symbol,
            "volume": float(lot_size),
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": buy_price,
            "sl": 0.0, # Handled by AI circuit breaker
            "tp": buy_tp,
            "deviation": 20,
            "magic": 777777,
            "comment": "Elirox_GRID",
            "type_time": mt5.ORDER_TIME_GTC,
        })
        
        # Sell Limit setup
        requests.append({
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.real_symbol,
            "volume": float(lot_size),
            "type": mt5.ORDER_TYPE_SELL_LIMIT,
            "price": sell_price,
            "sl": 0.0, # Handled by AI circuit breaker
            "tp": sell_tp,
            "deviation": 20,
            "magic": 777777,
            "comment": "Elirox_GRID",
            "type_time": mt5.ORDER_TIME_GTC,
        })
        
        for req in requests:
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ GRID PENDING ORDER SET: {req['type']} at {req['price']}")
                
    def emergency_close_positions(self, ai_trend: str):
        """
        AI Shield: Closes positions that are AGAINST the incoming trend.
        """
        if not self.connected: return
        
        positions = self.get_open_positions()
        if not positions: return
        
        logger.warning(f"🚨 AI EMERGENCY PROTOCOL INITIATED | Incoming Trend: {ai_trend} 🚨")
        
        for pos in positions:
            # If AI says UPTREND, and we hold Short (SELL)
            if ai_trend == "UPTREND" and pos["type"] == "SELL":
                logger.warning(f"Closing {pos['type']} ticket #{pos['ticket']} to prevent grid death.")
                self._close_market_position(pos["ticket"], mt5.ORDER_TYPE_BUY)
                
            # If AI says DOWNTREND, and we hold Long (BUY)
            elif ai_trend == "DOWNTREND" and pos["type"] == "BUY":
                logger.warning(f"Closing {pos['type']} ticket #{pos['ticket']} to prevent grid death.")
                self._close_market_position(pos["ticket"], mt5.ORDER_TYPE_SELL)
                
    def _close_market_position(self, ticket: int, opposing_type: int):
        pos = mt5.positions_get(ticket=ticket)
        if not pos: return
        pos = pos[0]
        
        tick = mt5.symbol_info_tick(pos.symbol)
        price = tick.ask if opposing_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": opposing_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 777777,
            "comment": "AI_EMERGENCY_EXIT",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(request)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"✅ EMERGENCY EXIT COMPLETE: Ticket {ticket} closed at {price}.")
        else:
            logger.error(f"Failed to emergency exit ticket {ticket}")

    def get_open_positions(self):
        """Returns all open positions with Unrealized PnL."""
        if not self.connected:
            self._connect()
            
        positions = mt5.positions_get(symbol=self.real_symbol)
        if positions is None:
            return []
            
        formatted_positions = []
        for p in positions:
            p_dict = p._asdict()
            formatted_positions.append({
                "ticket": p_dict['ticket'],
                "symbol": p_dict['symbol'],
                "type": "BUY" if p_dict['type'] == mt5.ORDER_TYPE_BUY else "SELL",
                "volume": p_dict['volume'],
                "price_open": p_dict['price_open'],
                "price_current": p_dict['price_current'],
                "unrealized_pnl": p_dict['profit'], # MT5 calculates this automatically
                "time_setup": p_dict.get('time', 0)  # MT5 uses 'time', not 'time_setup'
            })
            
        return formatted_positions

    def get_realized_pnl(self, days: int = 1):
        """Calculates realized PnL from closed deals over the last N days."""
        if not self.connected:
            self._connect()
            
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        deals = mt5.history_deals_get(from_date, to_date, group=f"*{self.real_symbol}*")
        if deals is None:
            return 0.0
            
        realized_pnl = sum([deal.profit for deal in deals if deal.entry == mt5.DEAL_ENTRY_OUT])
        return round(realized_pnl, 2)
