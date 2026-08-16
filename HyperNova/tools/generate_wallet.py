from eth_account import Account
import secrets
from termcolor import cprint

def generate_wallet():
    # Generate a secure private key
    priv = secrets.token_hex(32)
    private_key = "0x" + priv
    
    # Create account from key
    acct = Account.from_key(private_key)
    
    cprint("="*60, "cyan")
    cprint("🔑 NEW HYPERLIQUID WALLET GENERATED", "green", attrs=['bold'])
    cprint("="*60, "cyan")
    
    print(f"\n1. Address (Public):     {acct.address}")
    print(f"2. Private Key (Secret): {private_key}")
    
    cprint("\n⚠️  IMPORTANT INSTRUCTIONS:", "yellow")
    print("1. Copy the 'Private Key' into your HyperNova/.env file (HL_PRIVATE_KEY).")
    print("2. Copy the 'Address' into your HyperNova/.env file (HL_ACCOUNT_ADDRESS).")
    print("3. Go to: https://app.hyperliquid-testnet.xyz/")
    print("4. Connect a wallet (e.g. Rabby/MetaMask) by importing this Private Key.")
    print("5. Click 'Faucet' or 'Trade' -> 'Faucet' to get free Testnet USDC.")
    print("\nDO NOT SHARE THIS PRIVATE KEY WITH ANYONE! (Even for testnet, it's good practice).")

if __name__ == "__main__":
    generate_wallet()
