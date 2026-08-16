"""
HyperNova Android Entry Point
Starts the embedded 1000:1 quant scalper engine and local UI server on Android
"""
import sys
import os

# Add local directory to path
sys.path.insert(0, os.path.dirname(__file__))

from run_live import run_full_microstructure_quant_engine

if __name__ == "__main__":
    print("🔥 HyperNova Standalone Android Engine Başlatılıyor...")
    run_full_microstructure_quant_engine()
