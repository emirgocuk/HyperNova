import os
import eth_account
from eth_account.signers.local import LocalAccount
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from dotenv import load_dotenv
import json

load_dotenv()

class HyperLiquidInterface:
    def __init__(self):
        self.private_key = os.getenv("HL_PRIVATE_KEY")
        self.account_address = os.getenv("HL_ACCOUNT_ADDRESS")
        self.is_mainnet = os.getenv("HL_MAINNET", "False").lower() == "true"
        
        if not self.private_key or not self.account_address:
            print("⚠️ WARNING: HyperLiquid credentials not found in .env. Live trading will loop harmlessly or fail.")
            self.account = None
            self.info = None
            self.exchange = None
            return

        try:
            # Setup Account
            self.account: LocalAccount = eth_account.Account.from_key(self.private_key)
            if self.account.address != self.account_address:
                print(f"⚠️ Mismatch! Generated: {self.account.address}, .env: {self.account_address}")

            # Initialize SDK
            base_url = constants.MAINNET_API_URL if self.is_mainnet else constants.TESTNET_API_URL
            self.info = Info(base_url, skip_ws=True)
            self.exchange = Exchange(self.account, base_url, account_address=self.account_address)
            
            print(f"✅ HyperLiquid Interface Initialized (Mainnet: {self.is_mainnet})")
            
        except Exception as e:
            print(f"❌ Error initializing HyperLiquid: {e}")
            self.account = None

    def get_market_price(self, symbol: str):
        """Fetches the latest mid-price for a symbol."""
        if not self.info: return None
        try:
            # Info.all_mids() returns a dict {coin: float, ...}
            mids = self.info.all_mids()
            return float(mids.get(symbol, 0.0))
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None

    def get_positions(self):
        """Returns open positions."""
        if not self.info or not self.account_address: return []
        try:
            user_state = self.info.user_state(self.account_address)
            return user_state.get("assetPositions", [])
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return []

    def get_l2_snapshot(self, symbol: str):
        """Fetches Order Book (L2) to find Best Bid/Ask for Maker Strategy."""
        if not self.info: return None
        try:
            return self.info.l2_snapshot(symbol)
        except Exception as e:
            print(f"Error fetching L2 Snapshot: {e}")
            return None

    
    def place_order(self, symbol: str, is_buy: bool, size: float, price: float = None, order_type: str = "limit"):
        """
        Place an order on HyperLiquid.
        For Market orders, price should be None or aggressive.
        """
        if not self.exchange: return None
        
        print(f"🚀 Execution: {'BUY' if is_buy else 'SELL'} {size} {symbol} @ {price if price else 'MARKET'}")
        
        try:
            # Determine coin index (SDK might need coin name directly)
            # The SDK handles name-to-asset lookup internally mostly
            
            result = self.exchange.order(
                name=symbol,
                is_buy=is_buy,
                sz=size,
                limit_px=price,
                order_type={"limit": {"tif": "Gtc"}} if order_type == "limit" else {"market": {}},
                reduce_only=False
            )
            return result
        except Exception as e:
            print(f"❌ Order Failed: {e}")
            return None

    def cancel_all_orders(self, symbol: str):
        if not self.exchange: return
        try:
            print(f"🗑️ Cancelling all orders for {symbol}...")
            # Requires fetching open orders first
            open_orders = self.info.open_orders(self.account_address)
            for order in open_orders:
                if order['coin'] == symbol:
                    self.exchange.cancel(symbol, order['oid'])
        except Exception as e:
             print(f"Error cancelling orders: {e}")

if __name__ == "__main__":
    # Test Script
    hl = HyperLiquidInterface()
    if hl.account:
        print("Address:", hl.account.address)
        btc_price = hl.get_market_price("BTC")
        print("BTC Price:", btc_price)
