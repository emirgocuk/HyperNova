# 📱 HyperNova Android APK Derleme & Veri Hattı Kılavuzu

Bu belge, **HyperNova Android APK** uygulamasının nasıl derleneceğini ve telefonda biriken verilerin bilgisayardaki yapay zeka eğitim istasyonuna nasıl aktarılacağını açıklar.

---

## 🏗️ 1. APK Nasıl Derlenir? (2 Kolay Yöntem)

### Yöntem A: Android Studio ile Tek Tıkla Derleme (Önerilen)
1. Bilgisayarınızda **Android Studio**'yu açın.
2. `Open Project` diyerek bu dizindeki `android/` klasörünü seçin.
3. Üst menüden **`Build` ➔ `Build Bundle(s) / APK(s)` ➔ `Build APK(s)`** seçeneğine tıklayın.
4. Derleme bittiğinde ekranda çıkan **`locate`** butonuna tıklayın:
   - APK Dosyanız: `android/app/build/outputs/apk/debug/app-debug.apk`
5. Bu `.apk` dosyasını telefonunuza atıp (WhatsApp, Telegram veya USB ile) tek tıkla kurun!

---

### Yöntem B: GitHub Actions ile Bulutta Derleme (Sıfır Kurulum)
Bilgisayarınıza Android Studio kurmak istemiyorsanız:
1. Projeyi GitHub reponuza yükleyin (`git push`).
2. `.github/workflows/build-apk.yml` otomatik olarak devreye girer.
3. GitHub sayfanızın **Actions** sekmesinden derlenmiş hazır **`HyperNova.apk`** dosyasını doğrudan telefonunuza indirin.

---

## 🔄 2. Telefondaki Verileri Bilgisayara Aktarma & Model Eğitimi

Telefonunuz 7/24 çalışırken tüm L2 tahta derinliğini, fonlama oranlarını ve trade sonuçlarını dahili **`database/trade_memory.db`** içine kaydeder.

### Adım Adım Eğitim Döngüsü:

1. **Veriyi Bilgisayara Çekme:**
   - Telefonunuzu bilgisayara bağlayın (veya WiFi üzerinden) `trade_memory.db` dosyasını `HyperNova/database/` içine kopyalayın.
2. **Bilgisayarda Eğitimi Başlatma:**
   ```bash
   python HyperNova/tools/train_from_phone_data.py
   ```
3. **Eğitim Sonucu:**
   - Script tüm işlemleri analiz eder.
   - Kazanma oranını (Win Rate) maksimize edecek **yeni optimal kuralları ve yapay zeka ağırlıklarını** (`edge_learned_rules.json`) üretir.
4. **Yeni Zekayı Telefona Aktarma:**
   - Üretilen kurallar telefonunuzdaki bota yüklenir ve bot dünkünden daha akıllı olarak işlem yapmaya devam eder!
