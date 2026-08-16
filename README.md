# 🔥 HyperNova: 1000:1 High-Frequency Profit Engine & Edge-Cloud AI Trading

**HyperNova**, 1000:1 kaldıraçlı mikro-teminatlı kripto piyasalarında (SOL, HYPE, BTC) 7/24 kesintisiz yüksek frekanslı al-sat yapan, L2 derinlik dengesini (Orderbook Imbalance) takip eden, Android üzerinde otonom çalışan ve toplanan telemetri verileriyle merkezi yapay zekayı eğiten yeni nesil kurumsal bir ticaret mimarisidir.

---

## 🌟 Temel Özellikler

- ⚡ **1000:1 Mikro-Teminat Scalper Engine:** $800 notional pozisyon boyutu başına sadece **$0.80 teminat** kullanarak maksimum sermaye verimliliği sağlar.
- 📊 **4-Faktörlü Kurumsal Mikroyapı Akışı:**
  1. **L2 Orderbook Derinliği & Dengesizliği (OIR %)**: Top-5 kademe alış/satış baskısı.
  2. **Anlık Fonlama Oranları (Funding APR %)**: Sıkışma (Squeeze) tespiti.
  3. **Açık Pozisyon (Open Interest $M) & Hacim Akışı**.
  4. **Spot / Vadeli Prim Ayrışması (Basis Premium %)**.
- 🎯 **Dinamik Tepe Kâr Kilitleyici (Trend-Rider):**
  - Kârlı işlemler asla süreyle kesilmez; zirveden %0.03 geri çekilene kadar dalga sürülür.
  - Tepe tükenişlerinde (Exhaustion) anında kâr kilitlenir.
- 📱 **Standalone Android APK & 7/24 Kesintisiz Çalışma:**
  - Android telefonun kendi işlemcisinde bağımsız çalışan mobil APK.
  - Ekran kapalıyken bile kesintisiz çalışan Android Foreground Service (`WakeLock`).
- 🧠 **Merkezi Yapay Zeka Eğitim İstasyonu (`/training`):**
  - Arkadaşlarınızın telefonlarından ve yerel cihazınızdan gelen tüm L2 tahta ve işlem tecrübelerini ambar havuzunda birleştirir (Federe Veri Madenciliği).
  - Tek tıkla zarar ettiren sahte sinyalleri ayıklar ve yeni optimal strateji kurallarını üretir.
- 🛡️ **Kurumsal Güvenlik & Gizlilik Kalkanı (`.gitignore`):**
  - Hiçbir API anahtarı, cüzdan şifresi veya kişisel kullanıcı verisi GitHub'a sızmaz.

---

## 🚀 Hızlı Başlangıç

### 💻 1. Bilgisayarda Canlı Motoru & Web Panelini Başlatma:
```bash
# Gerekli bağımlılıkları yükleyin
pip install -r HyperNova/requirements.txt

# Canlı Scalper ve Web Panelini Başlatın
python HyperNova/run_live.py
```
- **Canlı Scalper Paneli:** `http://localhost:5000`
- **Merkezi AI Eğitim İstasyonu:** `http://localhost:5000/training`

---

## 📱 Android APK İndirme & Derleme

Bu repo GitHub Actions CI/CD hattı ile yapılandırılmıştır.
- GitHub reponuzun **[Actions](https://github.com/emirgocuk/HyperNova/actions)** sekmesine giderek bulutta otomatik derlenen hazır **`HyperNova-Standalone-Android-APK`** paketini telefonunuza indirebilirsiniz.

---

## 📄 Lisans
Bu proje özel kullanım ve kurumsal algoritmik ticaret için geliştirilmiştir.
