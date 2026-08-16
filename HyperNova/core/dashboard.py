import os
import time
import threading
from datetime import datetime

class LiveDashboard:
    def __init__(self, paper_account):
        self.paper_account = paper_account
        self.state = {
            "symbol": "BTC",
            "current_price": 0.0,
            "status": "Initializing...",
            "last_log": "Starting...",
            "logs": [],
            "yield_info": None
        }
        self.running = True
        self.lock = threading.Lock()

    def update(self, key, value):
        with self.lock:
            self.state[key] = value
            
    def log(self, message, color="white"):
        # Store log for UI display instead of printing
        timestamp = datetime.now().strftime('%H:%M:%S')
        clean_msg = f"[{timestamp}] {message}"
        with self.lock:
            self.state['logs'].append(clean_msg)
            # Keep last 10 logs
            if len(self.state['logs']) > 10:
                self.state['logs'].pop(0)

    def start(self):
        thread = threading.Thread(target=self._render_loop)
        thread.daemon = True
        thread.start()

    def _render_loop(self):
        while self.running:
            self._render()
            time.sleep(1) # Refresh rate

    def _render(self):
        # FLICKER FIX: Use ANSI Escape Codes instead of cls
        # \033[H = Move Cursor to Top-Left
        # \033[J = Clear Screen from cursor down (optional, good if shrinking)
        # We print directly to stdout to avoid newline lag
        if os.name == 'nt':
             # Windows legacy console support
             os.system('cls') 
        else:
             print("\033[H", end="")
        
        # NOTE: Powershell/CMD often still flickers with cls. 
        # Better: Print a massive string at once.
        
        buffer = []
        with self.lock:
            s = self.state
            
            # Build the UI String
            buffer.append("\n" + "="*60)
            buffer.append(f"🔥 HYPERNOVA PROFIT ENGINE | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            buffer.append("="*60)
            
            # ... (Rest of UI construction)
            # To fix flicker effectively on Windows efficiently without Curses/Rich:
            # We construct one single string and print it.
            
            # 1. LIVE TICKER
            ticker_color = "\033[96m" 
            reset = "\033[0m"
            buffer.append(f"\n🎯 TARGET: {ticker_color}{s['symbol']}{reset} @ ${s['current_price']:.4f}")
            if s['yield_info']:
                buffer.append(f"🌽 YIELD:  {s['yield_info']}")
            
            buffer.append(f"🚀 STATUS: {s['status']}")
            
            # 2. PORTFOLIO
            prices = {s['symbol']: s['current_price']}
            try:
                stats = self.paper_account.get_portfolio_status(prices)
            except:
                stats = {'balance': 0, 'equity': 0, 'unrealized_pnl': 0, 'open_positions': []}
                
            equity_color = "\033[92m" if stats['equity'] >= 10000 else "\033[91m"
            pnl_color = "\033[92m" if stats['unrealized_pnl'] >= 0 else "\033[91m"
            
            buffer.append("-" * 60)
            buffer.append(f"💰 BALANCE: ${stats['balance']:.2f}")
            buffer.append(f"📈 EQUITY:  {equity_color}${stats['equity']:.2f}{reset}")
            buffer.append(f"💸 PnL:     {pnl_color}${stats['unrealized_pnl']:.2f}{reset}")
            buffer.append("-" * 60)
            
            # 3. OPEN POSITIONS
            buffer.append("\n🔓 ACTIVE POSITIONS:")
            if not self.paper_account.positions:
                buffer.append("   [No Open Positions]")
            else:
                for pos in self.paper_account.positions:
                    pnl = self.paper_account._calculate_pnl(pos, s['current_price'])
                    c = "\033[92m" if pnl >= 0 else "\033[91m"
                    buffer.append(f"   • {pos['side']} {pos['symbol']} | Entry: {pos['entry_price']} | PnL: {c}${pnl:.2f}{reset}")
            
            # 4. LOG BUFFER
            buffer.append("\n📜 RECENT ACTIVITY:")
            for log in s['logs'][-7:]: 
                buffer.append(f"   {log}")
                
            buffer.append("\n" + "="*60)
            buffer.append("Press Ctrl+C to Stop")
            
        # CLEAR AND PRINT ONCE
        # For Windows, we might simply print specific newlines if size is fixed, or use cls if unavoidable.
        # But 'rich' or 'curses' is best. For now, let's try just printing the big blob.
        # If user is on Windows Terminal, ANSI works.
        
        # Try a soft approach:
        print("\033[H" + "\n".join(buffer))
