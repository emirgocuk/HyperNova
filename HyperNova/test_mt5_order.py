import MetaTrader5 as mt5

def test_order():
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return
    
    symbol = "BTCUSD"
    if not mt5.symbol_select(symbol, True):
        print("Failed to select symbol")
    
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print("No tick data")
        return
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.10,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "deviation": 20,
        "magic": 123456,
        "comment": "Test Order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    print("Result with IOC:", result)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        request["type_filling"] = mt5.ORDER_FILLING_FOK
        result = mt5.order_send(request)
        print("Result with FOK:", result)
        
    mt5.shutdown()

if __name__ == "__main__":
    test_order()
