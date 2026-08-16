import subprocess
import os

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    hypernova_dir = os.path.join(root_dir, "HyperNova")
    frontend_dir = os.path.join(root_dir, "frontend")

    print("===================================================")
    print("      Starting Transparent Strategist Bot...       ")
    print("===================================================")

    try:
        # Start backend in a new command prompt window
        print("\n[1/2] Launching Backend API (FastAPI)...")
        subprocess.Popen(
            f'start "Trading Bot Backend" cmd /k "cd /d {hypernova_dir} && title Trading Bot Backend && python control_tower\\dashboard_api.py"', 
            shell=True
        )

        # Start frontend in a new command prompt window
        print("[2/2] Launching Frontend Dashboard (Next.js)...")
        subprocess.Popen(
            f'start "Trading Bot Frontend" cmd /k "cd /d {frontend_dir} && title Trading Bot Frontend && npm run dev"', 
            shell=True
        )

        print("\nBoth services have been launched in separate terminal windows!")
        print("- Backend will run on:  http://localhost:8000")
        print("- Frontend will run on: http://localhost:3000")
        print("\nKeep those windows open to keep the bot running.")
        
    except Exception as e:
        print(f"Error starting services: {e}")

if __name__ == "__main__":
    main()
