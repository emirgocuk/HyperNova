import subprocess
import os
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    hypernova_dir = os.path.join(root_dir, "HyperNova")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("=================================================================")
    print("      >>> HYPERNOVA: 1000:1 UNIFIED PROFIT & AI ENGINE <<<       ")
    print("=================================================================")

    try:
        # Start Unified Backend (FastAPI + Async 1000:1 Scalper Engine + WebSockets)
        print("\n[1/2] Launching HyperNova Unified Backend (FastAPI + Primo DRL + WebSocket Engine)...")
        subprocess.Popen(
            f'start "HyperNova Backend (Port 8000)" cmd /k "cd /d {hypernova_dir} && title HyperNova Backend && python control_tower\\unified_api.py"', 
            shell=True
        )

        # Start Unified Mobile-First Frontend (Next.js Dashboard)
        print("[2/2] Launching HyperNova Premium Dashboard (Next.js)...")
        subprocess.Popen(
            f'start "HyperNova Frontend (Port 3000)" cmd /k "cd /d {frontend_dir} && title HyperNova Frontend && npm run dev"', 
            shell=True
        )

        print("\n=================================================================")
        print("[OK] Her iki servis de ayri terminallerde basariyla baslatildi!")
        print("  - Web & Mobil Dashboard: http://localhost:3000")
        print("  - Birlesik FastAPI Core: http://localhost:8000")
        print("  - Primo DRL Telemetri:   http://localhost:8000/api/v1/primo")
        print("  - AI Telemetri Hub:      http://localhost:3000 (AI Sekmesi)")
        print("  - Android Baglanti API:  http://<BILGISAYAR_IP>:8000/api/v1")
        print("=================================================================")
        print("Servislerin calismasi icin acilan komut pencerelerini kapatmayin.\n")
        
    except Exception as e:
        print(f"Hata olustu: {e}")

if __name__ == "__main__":
    main()
