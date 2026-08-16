import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import requests
import time
import json
from termcolor import cprint

BASE_URL = "http://127.0.0.1:5000"


def test_telemetry_and_training_pipeline():
    cprint("="*65, "cyan")
    cprint("🧪 TEST: TELEMETRİ & MERKEZİ EĞİTİM HATTI TESTİ", "yellow", attrs=['bold'])
    cprint("="*65, "cyan")

    # 1. Test Telemetry Export
    cprint("\n1️⃣ Telemetri Paketi Çıkarılıyor (/api/telemetry/export)...", "cyan")
    try:
        r = requests.get(f"{BASE_URL}/api/telemetry/export", timeout=3.0)
        assert r.status_code == 200, f"Export failed: {r.status_code}"
        payload = r.json()
        cprint(f"   ✅ Başarılı! Cihaz ID: {payload.get('device_id')} | İşlem Sayısı: {payload.get('trades_count')}", "green")
    except Exception as e:
        cprint(f"   ❌ Export Hatası: {e}", "red")
        return

    # 2. Simulate Upload from a Remote Phone (e.g. Arkadas_Telefon_A1)
    cprint("\n2️⃣ Simüle Edilmiş Arkadaş Telefonundan Veri Yükleniyor (/api/telemetry/upload)...", "cyan")
    simulated_payload = {
        'device_id': 'Phone_Ahmet_SOL_Node',
        'app_version': '1.0.0',
        'exported_at': str(time.time()),
        'trades_count': 12,
        'trades': [
            {
                'symbol': 'SOL', 'side': 'LONG', 'entry_price': 75.10, 'exit_price': 75.35,
                'pnl_usd': 2.66, 'roe_pct': 330.0, 'duration_seconds': 45.0,
                'exit_reason': '🎯 TEPE TÜKENİŞ KÂR KİLİT',
                'entry_stoch_k': 18.0, 'entry_oir': 0.65, 'entry_alpha': 25.0,
                'entry_time': '2026-08-16T12:00:00', 'exit_time': '2026-08-16T12:00:45'
            },
            {
                'symbol': 'SOL', 'side': 'SHORT', 'entry_price': 75.40, 'exit_price': 75.20,
                'pnl_usd': 2.12, 'roe_pct': 265.0, 'duration_seconds': 60.0,
                'exit_reason': '🚀 SIKI İZ SÜREN TEPE KÂRI',
                'entry_stoch_k': 88.0, 'entry_oir': -0.55, 'entry_alpha': -35.0,
                'entry_time': '2026-08-16T12:05:00', 'exit_time': '2026-08-16T12:06:00'
            },
            {
                'symbol': 'SOL', 'side': 'LONG', 'entry_price': 75.20, 'exit_price': 75.12,
                'pnl_usd': -0.85, 'roe_pct': -106.0, 'duration_seconds': 120.0,
                'exit_reason': '🛑 Sıkı Stop-Loss',
                'entry_stoch_k': 45.0, 'entry_oir': -0.20, 'entry_alpha': -5.0,
                'entry_time': '2026-08-16T12:10:00', 'exit_time': '2026-08-16T12:12:00'
            }
        ]
    }

    try:
        r2 = requests.post(f"{BASE_URL}/api/telemetry/upload", json=simulated_payload, timeout=3.0)
        assert r2.status_code == 200, f"Upload failed: {r2.status_code}"
        res2 = r2.json()
        cprint(f"   ✅ Başarılı! Ambar Dosyası: {res2.get('saved_file')} | Kaydedilen: {res2.get('saved_count')} işlem", "green")
    except Exception as e:
        cprint(f"   ❌ Upload Hatası: {e}", "red")
        return

    # 3. Check Training Status
    cprint("\n3️⃣ Merkezi Eğitim Durumu Sorgulanıyor (/api/training/status)...", "cyan")
    try:
        r3 = requests.get(f"{BASE_URL}/api/training/status", timeout=3.0)
        assert r3.status_code == 200
        stats = r3.json()
        cprint(f"   ✅ Bağlı Cihaz Sayısı: {stats.get('total_nodes_connected')}", "green")
        cprint(f"   ✅ Toplam Biriken İşlem: {stats.get('total_crowdsourced_trades')}", "green")
    except Exception as e:
        cprint(f"   ❌ Status Hatası: {e}", "red")
        return

    # 4. Trigger Central Training
    cprint("\n4️⃣ Merkezi Model Eğitimi Tetikleniyor (/api/training/start)...", "cyan")
    try:
        r4 = requests.post(f"{BASE_URL}/api/training/start", timeout=5.0)
        assert r4.status_code == 200
        res4 = r4.json()
        cprint(f"   ✅ Başarılı! Eğitim Sonucu: {res4.get('status')}", "green", attrs=['bold'])
        rules = res4.get('rules', {})
        if rules:
            cprint(f"   🏆 Kazanma Oranı: %{rules.get('win_rate_achieved')} | Analiz Edilen: {rules.get('total_training_samples')} işlem", "green")
            cprint(f"   🎯 Öğrenilen L2 OIR Eşiği: %{rules.get('optimal_long_oir_min', 0)*100:.0f}", "cyan")
    except Exception as e:
        cprint(f"   ❌ Training Hatası: {e}", "red")
        return

    cprint("\n🎉 TÜM TELEMETRİ, VERİ AMBARI VE EĞİTİM HATTI EKSİKSİZ ÇALIŞIYOR!", "green", attrs=['bold'])


if __name__ == "__main__":
    test_telemetry_and_training_pipeline()
