# 🧠 PRIMO FRAMEWORK — Akademik Makale Uygulama Ana Planı
# Kaynak: "Automated Trading Framework Using LLM-Driven Features and Deep Reinforcement Learning"
# Yazarlar: Botunac, Petković, Bosna (2025) — Big Data Cogn. Comput. 9, 317
# DOI: 10.3390/bdcc9120317

---

## 📌 DURUM: Makale Okuma İlerleme Takibi

| Bölüm | Konu | Durum |
|:---|:---|:---|
| Abstract + §1 | Giriş, Motivasyon & Temel İddia | ✅ OKUNDU |
| §2.1 | Related Work — NLP in Financial Markets | ✅ OKUNDU |
| §2.2 | Related Work — DRL in Stock Markets | ✅ OKUNDU |
| §3 Giriş | Methodology — Sistem Mimarisi (3 Bileşen) | ✅ OKUNDU |
| §3.1 | Data Collection (Finnhub + Yahoo Finance) | ✅ OKUNDU |
| §3.2 | Technical Indicators — 6 Formül (SMA, MACD, BB, RSI, CCI, DX) | ✅ OKUNDU |
| §3.3 | PrimoGPT — NLP Model, 7 Feature, Fine-Tuning Pipeline | ✅ OKUNDU |
| §3.4 | PrimoRL — State/Action/Reward, MDP, PPO Seçimi, Frameworks | ✅ OKUNDU |
| §4.1 | PrimoGPT Eğitim — QLoRA, Llama 3, Hiperparametreler | ✅ OKUNDU |
| §4.1 | PrimoRL Eğitim — PPO Grid Search, Episode Yapısı | ✅ OKUNDU |
| §4.2 | PrimoGPT Doğruluk Değerlendirmesi (Table 2) | ✅ OKUNDU |
| §4.3 | Karşılaştırmalı Trading Stratejileri (7 Benchmark) | ✅ OKUNDU |
| §4.4 | Performans Metrikleri (Cum. Return, Sharpe, Vol, MDD) | ✅ OKUNDU |
| §5 Giriş | Sonuçlar & Analiz (Giriş, Tablo 3 bekleniyor) | ✅ OKUNDU |
| §5.1 | Bireysel Hisse Sonuçları (Table 3 + DM Test Table 4) | ✅ OKUNDU |
| §5.2 | Portföy Sonuçları (Table 5 + DM Test Table 6) | ✅ OKUNDU |
| §6 | Sonuçlar, Limitasyonlar & Gelecek Çalışma | ✅ OKUNDU |
| Referanslar | 84 Referans Tarandı, Kritik Repolar Belirlendi | ✅ OKUNDU |

**📌 MAKALE %100 OKUNDU — TÜM BÖLÜMLER TAMAMLANDI**

---

## 🔥 UYGULAMA BAŞLIKLARI (Makale Bölümlerine Göre — Detaylı)

---

### BÖLÜM 1: GENEL MİMARİ — PRIMO SİSTEM YAPISI
**Durum:** ✅ TAMAMLANDI (§3 Giriş + Figure 1)

**Sistem 4 Aşamalı Bir İş Akışı İzler (Figure 1):**

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ 1. DATA          │    │ 2. FEATURE        │    │ 3. FEATURE        │    │ 4. DECISION       │
│    COLLECTION    │───▶│    GENERATION      │───▶│    FORWARDING      │───▶│    MAKING          │
│                  │    │                    │    │                    │    │                    │
│ ┌──────────────┐ │    │ ┌────────────────┐ │    │ ┌────────────────┐ │    │ ┌────────────────┐ │
│ │Basic Company │ │    │ │  NLP MODULE    │ │    │ │ NLP Features   │ │    │ │                │ │
│ │Data          │─┼───▶│ │  (PrimoGPT)    │─┼───▶│ │ (7 sayısal     │─┼──┐ │ │ DRL MODULE     │ │
│ └──────────────┘ │    │ └────────────────┘ │    │ │  değer)        │ │  │ │ │ (PrimoRL)      │ │
│ ┌──────────────┐ │    │                    │    │ └────────────────┘ │  │ │ │                │ │
│ │Financial     │ │    │                    │    │                    │  ├─┼▶│ Girdiler:      │ │
│ │News & Press  │─┼───▶│                    │    │                    │  │ │ │ - NLP features │ │
│ │Releases      │ │    │                    │    │                    │  │ │ │ - Tech. ind.   │ │
│ └──────────────┘ │    │                    │    │                    │  │ │ │ - Portfolio     │ │
│ ┌──────────────┐ │    │ ┌────────────────┐ │    │ ┌────────────────┐ │  │ │ │                │ │
│ │Market Stock  │ │    │ │TECHNICAL       │ │    │ │ Technical      │ │  │ │ │ Çıktı:        │ │
│ │Data (OHLCV)  │─┼───▶│ │INDICATOR GEN.  │─┼───▶│ │ Indicators     │─┼──┘ │ │ ACTION        │ │
│ └──────────────┘ │    │ └────────────────┘ │    │ └────────────────┘ │    │ │ DECISION      │ │
│                  │    │                    │    │                    │    │ └────────────────┘ │
└─────────────────┘    └──────────────────┘    └──────────────────┘    │ + Portfolio Info    │
                                                                       └──────────────────┘
```

**Modüler Tasarım Prensipleri:**
- Ölçeklenebilirlik (Scalability)
- Güvenilirlik (Reliability)
- Uyarlanabilirlik (Adaptability)
- Yeni bileşenlerin sorunsuz entegrasyonu
- Değişen piyasa koşullarına uyum

---

### BÖLÜM 2: VERİ TOPLAMA — DATA COLLECTION (§3.1)
**Durum:** ✅ TAMAMLANDI

**Veri Kaynakları:**

| Kaynak | Sağladığı Veri | Kullanım Amacı |
|:---|:---|:---|
| **Finnhub** | Şirket bilgisi (isim, ticker, sektör, piyasa değeri, çalışan sayısı, kapanış fiyatı, fiyat değişimi) | PrimoGPT'ye girdi |
| **Finnhub** | Finansal haberler ve basın bültenleri (başlık + açıklama) | PrimoGPT NLP analizi |
| **Yahoo Finance** | Günlük OHLCV (Open, High, Low, Adjusted Close, Volume) | Teknik indikatör hesaplama |

**Günlük Getiri Hesaplama & Etiketleme Sistemi:**
- Kaynak: Yahoo Finance adjusted closing prices
- Getiri yönü: Pozitif → "U" (Upward), Negatif → "D" (Downward)
- Mutlak yüzde değişim hesaplanır, yuvarlanır
- Etiket örnekleri:
  - %3 artış → "U3"
  - %5 veya üzeri artış → "U5+"
  - %2 düşüş → "D2"
  - %5 veya üzeri düşüş → "D5+"
- Bu etiketler PrimoGPT'nin eğitim datasında kullanılır

**Haber Filtreleme Kuralları:**
- SADECE NYSE işlem saatleri DIŞINDA yayınlanan haberler dahil edilir
- Sebebi: After-hours haberleri bir sonraki açılıştaki fiyatı etkiler

**Haber Kaynakları (11 adet):**
Fintel, InvestorPlace, Seeking Alpha, Yahoo, CNBC, TipRanks,
MarketWatch, The Fly, Benzinga, TalkMarkets, Stock Options Channel

**HyperNova Uyarlaması:**
> HyperNova kripto piyasasında 7/24 çalıştığı için NYSE saati filtresi
> yerine, kripto'ya uygun haber kaynakları (CoinDesk, CoinTelegraph,
> The Block, Twitter/X kripto influencer paylaşımları) ve HyperLiquid
> announcements kullanılacak. Getiri etiketleme sistemi kripto volatilitesine
> uyarlanacak (kripto'da %5+ çok daha yaygın).

---

### BÖLÜM 3: TEKNİK İNDİKATÖR FORMÜLLERİ — TAM MATEMATİK (§3.2)
**Durum:** ✅ TAMAMLANDI — 6 İndikatör, Tüm Formüller

Primo sistemi TAM OLARAK bu 6 teknik indikatörü kullanır.
Seçim gerekçesi: Trend, momentum, volatilite ve döngüsel kalıpların kapsamlı temsili.

---

#### 3.2.1 — SMA (Simple Moving Average)

**Formül:**
```
SMA_t(n) = (1/n) × Σ(i=0 → n-1) P_{t-i}
```

**Parametreler:**
- P_{t-i} = t-i zamanındaki kapanış fiyatı
- n = 30 veya 60 gün (iki farklı pencere)

**Amaç:** Uzun vadeli fiyat trendlerini belirler, gürültüyü azaltır.
**Strateji:** Trend-following (trend takibi)

**Python Implementasyonu:**
```python
def sma(prices: list, n: int) -> float:
    if len(prices) < n:
        return prices[-1] if prices else 0.0
    return sum(prices[-n:]) / n
```

---

#### 3.2.2 — MACD (Moving Average Convergence/Divergence)

**Formül:**
```
MACD_t = EMA_m(t) - EMA_n(t)

Signal_t = EMA_p(MACD_t)
```

**Parametreler:**
- m = 12 gün (kısa vadeli EMA)
- n = 26 gün (uzun vadeli EMA)
- p = 9 gün (sinyal çizgisi EMA penceresi)

**EMA Hesaplama:**
```
EMA_t = α × P_t + (1 - α) × EMA_{t-1}
α (smoothing factor) = 2 / (period + 1)
```

**Amaç:** Momentum kaymaları ve trend dönüşlerini tespit eder.
**Strateji:** Zamanında giriş/çıkış kararları.

**Python Implementasyonu:**
```python
def ema(prices: list, period: int) -> list:
    alpha = 2.0 / (period + 1)
    result = [prices[0]]
    for i in range(1, len(prices)):
        result.append(alpha * prices[i] + (1 - alpha) * result[-1])
    return result

def macd(prices: list, m=12, n=26, p=9):
    ema_short = ema(prices, m)
    ema_long = ema(prices, n)
    macd_line = [s - l for s, l in zip(ema_short, ema_long)]
    signal_line = ema(macd_line, p)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line[-1], signal_line[-1], histogram[-1]
```

---

#### 3.2.3 — Bollinger Bands (BB)

**Formül:**
```
Middle Band = SMA_20
Upper Band  = SMA_20 + 2 × σ
Lower Band  = SMA_20 - 2 × σ
```

**Parametreler:**
- n = 20 gün
- Standart sapma çarpanı = 2

**Amaç:** Volatilite ölçümü, olası dönüş noktaları sinyali.
**Strateji:** Overbought/oversold tespiti, diğer indikatörlerle birlikte trade timing.

**NOT:** HyperNova'nın mevcut Bollinger implementasyonu n=12, std_mult=1.8 kullanıyor.
Primo'nun parametreleri: n=20, std_mult=2.0. Uyarlama gerekecek.

**Python Implementasyonu:**
```python
import math

def bollinger_bands(prices: list, n=20, k=2.0):
    if len(prices) < n:
        p = prices[-1]
        return p * 0.98, p, p * 1.02
    subset = prices[-n:]
    sma_val = sum(subset) / n
    variance = sum((x - sma_val) ** 2 for x in subset) / n
    std = math.sqrt(variance)
    return sma_val - k * std, sma_val, sma_val + k * std
```

---

#### 3.2.4 — RSI (Relative Strength Index)

**Formül:**
```
RSI = 100 - (100 / (1 + RS))

RS = Exponentially Smoothed Average Gains / Exponentially Smoothed Average Losses
```

**Parametreler:**
- n = 14 gün
- Overbought eşiği: > 70
- Oversold eşiği: < 30

**Amaç:** Fiyat aşırı hareketlerini ve potansiyel trend dönüşlerini belirler.
**Strateji:** Momentum ve mean-reversion (ortalamaya dönüş).

**Python Implementasyonu:**
```python
def rsi(prices: list, period=14) -> float:
    if len(prices) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    
    # Exponentially smoothed averages
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
```

---

#### 3.2.5 — CCI (Commodity Channel Index)

**Formül:**
```
CCI = (1 / 0.015) × ((p_t - SMA(p_t)) / σ(p_t))
```

**Burada:**
- `p_t` = Typical Price = (High + Low + Close) / 3
- `SMA(p_t)` = Typical price'ların basit hareketli ortalaması
- `σ(p_t)` = Mean Absolute Deviation (ortalama mutlak sapma)
- Sabit 0.015: Değerlerin çoğunun -100 ile +100 arasında kalmasını sağlar

**Parametreler:**
- n = 20 gün
- ±100 dışındaki değerler → overbought/oversold sinyali

**Amaç:** Döngüsel fiyat kalıpları ve momentum kaymalarını belirler.
**Strateji:** Volatil piyasalarda kısa vadeli ticaret.

**Python Implementasyonu:**
```python
def cci(highs: list, lows: list, closes: list, n=20) -> float:
    if len(closes) < n:
        return 0.0
    typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs[-n:], lows[-n:], closes[-n:])]
    tp_sma = sum(typical_prices) / n
    mean_dev = sum(abs(tp - tp_sma) for tp in typical_prices) / n
    if mean_dev == 0:
        return 0.0
    return (typical_prices[-1] - tp_sma) / (0.015 * mean_dev)
```

---

#### 3.2.6 — DX (Directional Movement Index)

**Formül:**
```
DX = (|+DI - (-DI)| / |+DI + (-DI)|) × 100
```

**Burada:**
- `+DI` = Smoothed positive directional movement / ATR
- `-DI` = Smoothed negative directional movement / ATR
- `ATR` = Average True Range

**Parametreler:**
- n = 14 gün
- DX > 25 → Güçlü trend
- DX < 25 → Zayıf veya trend yok

**Amaç:** Trend yönü ve gücünü ölçer.
**Strateji:** Trend-following optimizasyonu, güçlü trendleri rastgele hareketlerden ayırma.

**Python Implementasyonu:**
```python
def dx(highs: list, lows: list, closes: list, period=14) -> float:
    if len(closes) < period + 1:
        return 0.0
    
    plus_dm, minus_dm, tr_list = [], [], []
    for i in range(1, len(highs)):
        up_move = highs[i] - highs[i-1]
        down_move = lows[i-1] - lows[i]
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else 0.0)
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else 0.0)
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        tr_list.append(tr)
    
    if len(tr_list) < period:
        return 0.0
    
    atr = sum(tr_list[-period:]) / period
    smooth_plus = sum(plus_dm[-period:]) / period
    smooth_minus = sum(minus_dm[-period:]) / period
    
    if atr == 0:
        return 0.0
    plus_di = (smooth_plus / atr) * 100
    minus_di = (smooth_minus / atr) * 100
    
    di_sum = plus_di + minus_di
    if di_sum == 0:
        return 0.0
    return abs(plus_di - minus_di) / di_sum * 100
```

---

### BÖLÜM 4: PrimoGPT — FİNANSAL NLP MODELİ — TAM DETAY (§3.3)
**Durum:** ✅ TAMAMLANDI

#### 4.1 — Üretilen 7 NLP Feature (Table 1 — Tam Tablo)

| # | Feature Adı | Ölçek | Detaylı Açıklama |
|:---|:---|:---|:---|
| 1 | **News Relevance** | 0, 1, 2 | 0: İlgisiz, 1: Biraz ilgili, 2: Yüksek ilgili |
| 2 | **Sentiment** | -1, 0, 1 | -1: Olumsuz, 0: Nötr, 1: Olumlu |
| 3 | **Potential Impact on Price** | -3 → +3 | -3: Güçlü olumsuz, -2: Orta olumsuz, -1: Hafif olumsuz, 0: Etki yok, +1: Hafif olumlu, +2: Orta olumlu, +3: Güçlü olumlu |
| 4 | **Trend Direction** | -1, 0, 1 | -1: Aşağı yönlü, 0: Nötr, 1: Yukarı yönlü |
| 5 | **Earnings Impact** | -2 → +2 | -2: Belirgin olumsuz, -1: Hafif olumsuz, 0: Nötr/belirsiz, +1: Hafif olumlu, +2: Belirgin olumlu |
| 6 | **Investor Confidence** | -3 → +3 | -3: Güçlü azalma, -2: Orta azalma, -1: Hafif azalma, 0: Değişim yok, +1: Hafif artış, +2: Orta artış, +3: Güçlü artış |
| 7 | **Risk Profile Change** | -2 → +2 | -2: Belirgin artan risk, -1: Hafif artan risk, 0: Önemli değişiklik yok, +1: Hafif azalan risk, +2: Belirgin azalan risk |

#### 4.2 — Ölçek Tasarım Gerekçesi

Ölçek aralıkları iteratif testlerle optimize edilmiştir:
- `-3 → +3`: Sentiment ve yatırımcı güveni → yüksek yoğunluk ve değişkenlik
- `-1 → +1`: Trend yönü ve genel sentiment → basit yön belirleme
- `-2 → +2`: Kazanç etkisi ve risk profili → yüksek volatilite olayları
- `0 → 2`: Haber ilgililiği → yalnızca pozitif ölçek

Bu ölçekler PrimoRL'in sentiment uçlarını, trend yönlerini ve etki büyüklüklerini
etkili şekilde işleyebilmesi için kalibre edilmiştir.

#### 4.3 — Model Mimarisi ve Fine-Tuning

**Temel Model:** Llama 3 mimarisi
**Fine-Tuning Yaklaşımı:** Instruction-based training
**Eğitim Veri Seti Üretimi:** GPT-4 tarafından üretilmiş

**Eğitim Veri Formatı — Instruction-Input-Response Triplet:**
```json
{
  "instruction": "Aşağıdaki şirket haberi ve piyasa bilgilerini analiz et...",
  "input": {
    "company_name": "GOOGL",
    "recent_news": "Google yeni AI ürünü tanıttı...",
    "stock_price_change": "U3",
    "next_day_movement": "U2"  // ← SADECE EĞİTİMDE!
  },
  "response": {
    "news_relevance": 2,
    "sentiment": 1,
    "price_impact": 2,
    "trend_direction": 1,
    "earnings_impact": 1,
    "investor_confidence": 2,
    "risk_profile_change": 1
  }
}
```

**KRİTİK NOT — Gelecek Bilgisi Kullanımı:**
- `next_day_movement` bilgisi YALNIZCA eğitim sırasında kullanılır
- Model, metin ile sonraki piyasa hareketi arasındaki örüntüleri ÖĞRENMEK için bu bilgiye maruz kalır
- Operasyonel dağıtımda (deployment) model gelecek verisine ERİŞMEZ
- Sadece mevcut girdilerle (haber + şirket bilgisi) feature üretir

**Eğitim / Test Veri Ayrımı (MUTLAK AYRIM):**
```
EĞİTİM HİSSELERİ (PrimoGPT fine-tuning): GOOGL, META, AMD, TSLA
TEST HİSSELERİ (PrimoRL değerlendirme):   AAPL, NFLX, MSFT, CRM, AMZN
ASLA ÖRTÜŞME YOK — Genelleştirme yeteneğini kanıtlar
```

#### 4.4 — Prompt Mühendisliği

**Kullanılan Kütüphane:** LangChain
**Model Rolü:** "Senior Quantitative Analyst" (Kıdemli Kantitatif Analist)

**Prompt'un Analiz Ettiği Faktörler:**
1. İnce riskler (subtle risks)
2. Piyasa doygunluğu (market saturation)
3. Ton ile içerik arasındaki tutarsızlıklar (discrepancies between tone and content)
4. Aşırı iyimserlik (over-optimism)
5. Kısa vadeli vs uzun vadeli çıkarımlar (short-term vs long-term implications)

**Prompt Yapısı (LangChain):**
```
Statik Talimatlar (sabit) + Dinamik Girdiler (değişken)
                               │
                               ├── Şirket detayları
                               ├── Hisse fiyat değişimleri
                               └── Son haberler/basın bültenleri
```

**Çıktı Formatı:** Tutarlı, makine tarafından okunabilir sayısal format

**Örnek Çıktı (AAPL için):**
```json
{
  "news_relevance": 2,     // Yüksek ilgili
  "sentiment": -1,          // Olumsuz
  "price_impact": -2,       // Orta düzeyde düşüş etkisi
  "trend_direction": -1,    // Aşağı yönlü
  "earnings_impact": 0,     // Nötr
  "investor_confidence": -1, // Hafif azalma
  "risk_profile_change": -1  // Hafif artan risk
}
```

**HyperNova Uyarlaması:**
> Kripto piyasasında PrimoGPT'nin rolünü yerine getirecek modül için:
> - Llama 3 veya GPT-4o-mini API kullanılabilir
> - Kripto haberleri (CoinDesk, CoinTelegraph, Twitter/X) analiz edilecek
> - Prompt kripto terminolojisine uyarlanacak (funding rate, liquidation, whale activity)
> - 7 NLP feature aynen korunacak, ölçekler kripto volatilitesine göre kalibre edilecek
> - LangChain veya doğrudan API call ile entegrasyon

---

### BÖLÜM 5: PrimoRL — DRL TRADING FRAMEWORK — TAM DETAY (§3.4)
**Durum:** ✅ TAMAMLANDI

#### 5.1 — MDP (Markov Decision Process) Framework — SARP Space

PrimoRL, ardışık karar verme (sequential decision-making) için bir **Markov Karar Süreci (MDP)** olarak yapılandırılmıştır.

**SARP = State, Action, Reward, Policy**

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│   STATE     │─────▶│   AGENT      │─────▶│   ACTION     │
│   (S_t)     │      │   (PPO)      │      │   (A_t)      │
│             │      │              │      │              │
│ • Balance   │      │ Policy π(s)  │      │ [-1, +1]     │
│ • Shares    │      │ optimizes    │      │ continuous   │
│ • Prices    │      │ reward       │      │ per stock    │
│ • Tech Ind. │      └──────────────┘      └──────┬───────┘
│ • NLP Feat. │                                   │
└─────────────┘                                   │
       ▲                                          ▼
       │                              ┌──────────────────┐
       │        ┌──────────────┐       │  ENVIRONMENT     │
       └────────│   REWARD     │◀──────│                  │
                │   (R_t)      │       │ • Num. of stocks │
                │              │       │ • Account balance│
                │ Phase 1:     │       │ • Stock prices   │
                │  Raw return  │       └──────────────────┘
                │ Phase 2:     │
                │  Sharpe Ratio│
                └──────────────┘
```

#### 5.2 — Framework Technology Stack

| Bileşen | Teknoloji | Rolü |
|:---|:---|:---|
| **Ortam (Environment)** | OpenAI Gymnasium | Standart, tekrarlanabilir simülasyon ortamları |
| **Finans Simülasyonu** | FinRL | Tarihsel piyasa verisiyle gerçekçi ticaret ortamı |
| **DRL Algoritmaları** | Stable Baselines 3 | A2C, SAC, PPO uygulamaları |
| **Programlama** | Python 3.12 | State vektör birleştirme (list concatenation) |

#### 5.3 — DRL Algoritma Karşılaştırması ve SEÇİM

| Algoritma | Test Sonucu | Seçildi mi? |
|:---|:---|:---|
| **A2C** (Advantage Actor-Critic) | Hiperparametrelere aşırı hassas, karmaşık girdilerle kararsız, yakınsama başarısız | ❌ ELENDI |
| **SAC** (Soft Actor-Critic) | Sürekli eylem için tasarlandı ama volatil piyasalarda kararsız ve tutarsız | ❌ ELENDI |
| **PPO** (Proximal Policy Optimization) | Exploration/exploitation dengesini etkili kurar, dinamik piyasalara sağlam uyum | ✅ **SEÇİLDİ** |

**PPO'nun Seçilme Gerekçeleri:**
1. Exploration ve exploitation arasında etkili denge
2. Dinamik piyasa ortamlarına sağlam (robust) uyum
3. Kararlılık (stability) ve öğrenme tutarlılığı
4. FinRL ve Stable Baselines 3 ile sorunsuz entegrasyon

---

### BÖLÜM 6: STATE SPACE — GENİŞLETİLMİŞ DURUM UZAYI — TAM TANIM (§3.4)
**Durum:** ✅ TAMAMLANDI

**State Vektörü Bileşenleri (her zaman adımı t için):**

```
S_t = [Balance, Shares_owned, Share_values, Close_prices,
       Tech_Indicators, NLP_Features]
```

**Detaylı Bileşenler:**

| # | Bileşen | Boyut | Açıklama |
|:---|:---|:---|:---|
| 1 | **Account Balance** | 1 | Kullanılabilir nakit ($) |
| 2 | **Shares Owned** | N (hisse sayısı) | Her hisse için tutulan miktar |
| 3 | **Share Values** | N | Her hissenin anlık değeri ($) |
| 4 | **Closing Prices** | N | Her hissenin günlük kapanış fiyatı |
| 5 | **Technical Indicators** | N × 6 | Her hisse için 6 indikatör (SMA30, SMA60, MACD, BB, RSI, CCI, DX) |
| 6 | **NLP Features** | N × 7 | Her hisse için 7 PrimoGPT feature |

**State Vektör Birleştirme Yöntemi:**
Tüm feature listeleri Python list concatenation ile TEK BİR DÜZLEŞTIRILMIŞ VEKTÖRE birleştirilir (FinRL standardı).

```python
# FinRL/Primo state vector construction
state = [balance] + list(shares_owned) + list(share_values) + \
        list(close_prices) + list(tech_indicators_flat) + \
        list(nlp_features_flat)
```

**Tek Hisse İçin State Boyutu Hesaplama:**
```
1 (balance) + 1 (shares) + 1 (value) + 1 (close) + 6 (tech) + 7 (nlp) = 17 boyut/hisse
N hisse için: 1 + N×(1+1+1+6+7) = 1 + N×16
5 hisse (makale): 1 + 5×16 = 81 boyutlu state vektörü
```

**HyperNova Uyarlaması (Kripto — 3 coin: SOL, HYPE, BTC):**
```
Primo standart (6 tech + 7 nlp):   1 + 3×16 = 49 boyut
+ HyperNova L2 mikro yapı (4):     1 + 3×(16+4) = 61 boyut
  (OIR, Funding, OI, Basis)
Toplam state vektörü: ~61 boyut
```

---

### BÖLÜM 7: ACTION SPACE — SÜREKLİ EYLEM UZAYI — TAM TANIM (§3.4)
**Durum:** ✅ TAMAMLANDI

**Eylem Tanımı:**
```
A_t ∈ [-1, +1]  (her hisse için sürekli değer)

-1 = Tam SAT (tüm hisseleri sat)
 0 = BEKLE (işlem yapma)
+1 = Tam AL (maksimum hisse al)
```

**Ölçekleme Formülü:**
```
Gerçek_İşlem_Miktarı = round(A_t × h_max)

Burada:
- A_t = DRL agent'ın ürettiği sürekli eylem [-1, +1]
- h_max = Maksimum hisse limiti (hyperparameter)
- round() = Tamsayıya yuvarlama (hisse adedi tam sayı olmalı)
```

**FinRL'den Farkı:**
- FinRL: Ayrık eylemler → {-k, ..., -1, 0, +1, ..., +k}
- PrimoRL: Sürekli eylemler → [-1.0, +1.0] aralığında sonsuz hassasiyet
- **Avantaj:** Daha hassas pozisyon boyutlandırma, daha ince ticaret ayarlamaları

**HyperNova Uyarlaması (Kripto):**
```
Kripto'da hisse adedi yerine coin miktarı (ondalıklı):
Gerçek_Pozisyon = A_t × max_notional_usd / current_price

Örn: A_t = +0.65, max_notional = $800, SOL = $180
→ Pozisyon = 0.65 × 800 / 180 = 2.89 SOL (LONG)

Örn: A_t = -0.30
→ Pozisyon = 0.30 × 800 / 180 = 1.33 SOL (SHORT)
```

---

### BÖLÜM 8: REWARD FUNCTION — DİNAMİK SHARPE RATIO ÖDÜL FONKSİYONU — TAM TANIM (§3.4)
**Durum:** ✅ TAMAMLANDI

**KRİTİK: İKİ FAZLI DİNAMİK ÖDÜL SİSTEMİ**

Ödül fonksiyonu, agent'ın öğrenme aşamasına ve mevcut veri miktarına göre
otomatik olarak geçiş yapar:

#### Faz 1 — Ham Getiri (Yetersiz Veri Dönemi)
```
Koşul: Portföyde kayıtlı getiri sayısı < 30

R_t = E[r_portfolio]  (beklenen ham portföy getirisi)

GERKÇE: İstatistiksel metriklerin (Sharpe) yetersiz veri üzerinde
hesaplanması güvenilmez sonuçlar verir → sayısal kararlılık sağlanır
```

#### Faz 2 — Sharpe Ratio Tabanlı (Yeterli Veri Dönemi)
```
Koşul: Portföyde kayıtlı getiri sayısı ≥ 30

R_t = Sharpe Ratio = (R_p - R_f) / σ_p

Burada:
- R_p = Portföy getirisi (dönemsel)
- R_f = Risksiz faiz oranı (genellikle 0 veya treasury rate)
- σ_p = Portföy getirilerinin standart sapması
```

**Teorik Temel:**
1. **Differential Sharpe Ratio** (Moody & Saffell) → Online learning için türetilmiş
2. **Actor-Critic Sharpe formülasyonları** → Ortalama Sharpe tabanlı ödüller

**Bu Yaklaşımın Avantajları:**
- Agent'ı tutarlı ve istikrarlı getirileri TERCİH ETMEYE yönlendirir
- Volatil ama potansiyel olarak yüksek kısa vadeli kazançlar yerine DENGELİ performans
- Getiri ve risk arasındaki ödünleşimi (trade-off) istatistiksel temelde İÇSELLEŞTİRİR
- Sayısal kararlılık (numerical stability) sağlar
- Yetersiz veri üzerinde güvenilmez tahminlerden kaçınır

**Python Implementasyonu:**
```python
import numpy as np

def compute_reward(portfolio_returns: list, risk_free_rate: float = 0.0) -> float:
    """
    İki fazlı dinamik ödül fonksiyonu.
    Faz 1 (< 30 getiri): Ham beklenen getiri
    Faz 2 (≥ 30 getiri): Sharpe Ratio
    """
    if len(portfolio_returns) < 30:
        # Faz 1: Ham getiri
        return portfolio_returns[-1] if portfolio_returns else 0.0
    else:
        # Faz 2: Sharpe Ratio
        returns = np.array(portfolio_returns)
        excess_returns = returns - risk_free_rate
        mean_excess = np.mean(excess_returns)
        std_returns = np.std(excess_returns)
        if std_returns == 0:
            return 0.0
        return mean_excess / std_returns
```

**HyperNova Uyarlaması:**
> Kripto 7/24 çalıştığından "günlük getiri" yerine "döngüsel getiri" (her 0.8 sn loop)
> kullanılacak. Rolling window 30 döngü yerine 30 dakikalık pencere olabilir.
> Annualize faktörü: kripto → √(365×24×60) vs hisse → √252

---

### BÖLÜM 9: PrimoGPT EĞİTİM PİPELINE'I — TAM HİPERPARAMETRELER (§4.1)
**Durum:** ✅ TAMAMLANDI

#### 9.1 — PrimoGPT Fine-Tuning Detayları

| Parametre | Değer | Açıklama |
|:---|:---|:---|
| **Temel Model** | Llama 3 (8B) | 8 milyar parametre |
| **Fine-Tuning Kütüphanesi** | Unsloth | Hızlı ve verimli LoRA eğitimi |
| **Donanım** | Google Colab A100 GPU | 40/80GB VRAM |
| **Yöntem** | QLoRA | Quantization-aware Low-Rank Adaptation |
| **Quantization** | 32/16-bit → 4/8-bit | Bellek gereksinimini dramatik azaltır |
| **Eğitim Seti Boyutu** | 2973 örnek | Alpaca yapısında (instruction/input/output) |
| **Learning Rate** | 2e-4 | |
| **Batch Size** | 2 | |
| **Gradient Accumulation** | 4 adım | Efektif batch = 2×4 = 8 |
| **LoRA Rank (r)** | 16 | Düşük rank matris ayrıştırma boyutu |
| **LoRA Alpha** | 16 | Ölçeklendirme faktörü |
| **Max Sequence Length** | 8192 token | Uzun finansal metinler için yeterli |
| **Epoch Sayısı** | 1 | Tek geçiş |
| **Optimizer** | AdamW 8-bit | Bellek verimli optimizer |
| **Weight Decay** | 0.01 | Regularization |
| **Eğitilen Parametreler** | 42M / 8B | Toplam parametrenin sadece %0.5196'sı |

**HyperNova Uyarlaması:**
> Seçenek 1: Kendi Llama 3 modelini QLoRA ile fine-tune et (Google Colab A100)
> Seçenek 2: GPT-4o-mini API ile aynı 7 NLP feature'ı doğrudan üret (daha hızlı MVP)
> Seçenek 3: Yerel Ollama + Llama 3.1 8B ile çalıştır (ücretsiz, gizli)

#### 9.2 — PrimoRL Eğitim Detayları

**Eğitim Ortamı:**
- OpenAI Gymnasium + FinRL konfigürasyonu
- Her episode başlangıçta: başlangıç bakiyesi + boş portföy
- Agent döngüsü: State gözlemle → Action seç → Reward al → Environment güncelle
- Ödül: İşlem maliyetleri ve risk metrikleri ile ayarlanmış
- Birden fazla episode boyunca strateji rafine edilir

**PrimoRL Hiperparametreleri (Grid Search ile Optimize):**

| Parametre | Test Edilen Değerler | **Seçilen** |
|:---|:---|:---|
| **Learning Steps** | 1024, 2048, 4096 | **2048** |
| **Batch Size** | 64, 128, 256 | **128** |
| **Algoritma** | A2C, SAC, PPO | **PPO** |

**Karar Frekansı:** Günlük kararlar (buy, sell, hold)
**İzleme Metrikleri:** Kümülatif getiri ve Sharpe ratio

**Post-Training Değerlendirme:**
- Ayrı validasyon veri seti üzerinde
- Metrikler: Total return, Sharpe ratio, Maximum drawdown

---

### BÖLÜM 10: DENEYSEL KURULUM & VERİ SETİ — TAM DETAY (§4)
**Durum:** ✅ TAMAMLANDI

#### 10.1 — Veri Seti Ayrımı (Mutlak İzolasyon)

```
╔══════════════════════════════════════════════════════════════════╗
║  PrimoGPT EĞİTİM HİSSELERİ:  GOOGL, META, AMD, TSLA           ║
║  (NLP modeli bu hisseler üzerinde fine-tune edildi)              ║
║                                                                  ║
║  PrimoRL EĞİTİM & TEST HİSSELERİ:  AAPL, NFLX, MSFT, CRM, AMZN║
║  (DRL agent bu hisseler üzerinde eğitildi ve test edildi)        ║
║                                                                  ║
║  ⚠️  İKİ SET ARASINDA SIFIR ÖRTÜŞME (Data Leakage Önlemi)       ║
╚══════════════════════════════════════════════════════════════════╝
```

#### 10.2 — Zaman Dilimi

```
├── Tam Veri Dönemi: 1 Nisan 2022 → 28 Şubat 2025
│
├── EĞİTİM DÖNEMİ: 1 Nisan 2022 → 31 Temmuz 2024  (~28 ay)
│   └── Çeşitli piyasa koşulları (boğa, ayı, yatay)
│
└── TEST DÖNEMİ:   1 Ağustos 2024 → 28 Şubat 2025  (~7 ay)
    └── Görülmemiş veri üzerinde gerçek dünya simülasyonu
```

#### 10.3 — Seçilen Hisselerin Özellikleri
- Teknoloji sektörü şirketleri
- Yüksek piyasa likiditesi ve volatilitesi
- Çeşitli iş modelleri: tüketici elektroniği (AAPL), streaming (NFLX), kurumsal yazılım (AMZN, CRM, MSFT)
- Farklı piyasa davranışları ve haber sentiment kalıpları

---

### BÖLÜM 10B: PrimoGPT DOĞRULUK DEĞERLENDİRMESİ (§4.2)
**Durum:** ✅ TAMAMLANDI

#### Tahmin Mantığı (Her Gün İçin):
```python
def predict_next_day(sentiment, trend_direction, news_relevance, prev_direction):
    # Haber ilgisiz veya sentiment+trend birbirini götürüyorsa
    if news_relevance == 0 or (sentiment + trend_direction == 0):
        return prev_direction  # Önceki günün yönünü takip et
    
    combined = sentiment + trend_direction
    if combined > 0:
        return "UP"   # Pozitif → fiyat yükselecek
    else:
        return "DOWN"  # Negatif veya sıfır → fiyat düşecek
```

#### Table 2 — PrimoGPT Feature Tahmin Doğruluğu

| Feature | AAPL | NFLX | MSFT | CRM | AMZN |
|:---|:---|:---|:---|:---|:---|
| **Sentiment** | 53% | 50% | 47% | 47% | 50% |
| **Pot. Impact on Price** | 54% | 47% | 46% | 46% | 51% |
| **Trend Direction** | 53% | 46% | 46% | 45% | 50% |
| **Earnings Impact** | **58%** | 50% | 43% | 47% | 47% |
| **Investor Confidence** | **55%** | 48% | 45% | 46% | 50% |
| **Risk Profile Change** | 47% | **52%** | 46% | 43% | 46% |

**Genel Doğruluk Aralığı: %43 — %58**

**KRİTİK YORUM:**
- Mütevazı doğruluk oranları (%43-58) BEKLENEN bir durumdur
- Tek başına yön tahmini olarak düşük görünebilir
- ANCAK asıl değer DRL entegrasyonunda ortaya çıkar
- DRL agent, bu sinyalleri ÖĞRENMEYE DAYALI olarak kullanarak
  çok daha yüksek performans elde eder
- Standalone predictor değil, DRL state space zenginleştirici

---

### BÖLÜM 11: KARŞILAŞTIRMALI STRATEJİLER & PERFORMANS METRİKLERİ (§4.3-4.4)
**Durum:** ✅ TAMAMLANDI

#### 11.1 — Benchmark Trading Stratejileri (7 Adet)

| # | Strateji | Yöntem | Tür |
|:---|:---|:---|:---|
| 1 | **Buy & Hold (B&H)** | Al ve tut, kısa vadeli dalgalanmaları yoksay | Pasif |
| 2 | **Momentum (MOM)** | Mevcut fiyat > önceki dönem → AL, < → SAT | Trend |
| 3 | **Price Minus MA (P-MA)** | Fiyat > hareketli ortalama → AL, < → SAT | Ortalama Takip |
| 4 | **MACD Strategy** | MACD sinyal çizgisini yukarı keserse AL, aşağı keserse SAT | Momentum |
| 5 | **FinRL** | DRL (PPO/A2C/SAC), sadece sayısal veri | AI (Benchmark) |
| 6 | **DJI (Dow Jones)** | Piyasa endeksi benchmark | Piyasa Ortalaması |
| 7 | **Mean-Variance** | Tarihsel veriyle risk-getiri optimizasyonu | Portföy Teorisi |

#### 11.2 — Performans Metrikleri (4 Adet)

| Metrik | Formül / Tanım | Ne Ölçer |
|:---|:---|:---|
| **Cumulative Return** | Belirtilen dönemdeki toplam yatırım değişimi | Uzun vadeli başarı |
| **Sharpe Ratio** | (R_p - R_f) / σ_p | Risk-adjusted performans |
| **Volatility** | Günlük σ ve yıllıklaştırılmış σ (×√252) | Getiri değişkenliği / risk |
| **Maximum Drawdown (MDD)** | Zirveden en düşük noktaya en büyük düşüş | En kötü senaryo kaybı |

**Metrik Yorumlama:**
- Yüksek Cumulative Return + Yüksek Sharpe = İdeal
- Düşük Volatility + Düşük MDD = Düşük risk
- Sharpe > 1.0 = İyi, > 1.5 = Çok iyi, > 2.0 = Mükemmel

---

### BÖLÜM 12: BİREYSEL HİSSE SONUÇLARI — TAM DETAY (§5.1)
**Durum:** ✅ TAMAMLANDI

#### Table 3 — PrimoRL Bireysel Hisse Performans Değerlendirmesi

| Hisse | Model | Kümülatif Getiri | Sharpe Ratio | Yıllık Volatilite | Maks Drawdown |
|:---|:---|:---|:---|:---|:---|
| **AAPL** | **PrimoRL** | **20.20%** | **2.20** | 15.27% | **-5.51%** |
| AAPL | MOM (en iyi alt.) | 21.20% | 2.16 | 16.22% | -9.37% |
| **NFLX** | **PrimoRL** | **58.47%** | **2.80** | **30.52%** | **-7.76%** |
| NFLX | B&H (en iyi alt.) | 58.12% | 2.62 | 32.82% | -10.90% |
| **MSFT** | **PrimoRL** | **0.53%** | **0.14** | 19.35% | -13.39% |
| MSFT | FinRL (en iyi alt.) | 0.24% | 0.12 | 21.03% | **-9.48%** |
| **CRM** | **PrimoRL** | **33.64%** | **2.29** | 23.53% | **-7.56%** |
| CRM | P-MA (en iyi alt.) | 22.36% | 1.77 | 21.27% | -11.53% |
| **AMZN** | **PrimoRL** | **25.45%** | **1.64** | 26.49% | -11.90% |
| AMZN | FinRL (en iyi alt.) | 20.30% | 1.35 | 26.64% | -11.90% |

**Hisse Bazlı Analiz:**

**🟢 AAPL:** PrimoRL'in Sharpe'ı (2.20) MOM'dan (2.16) yüksek. MOM'un getirisi (%21.20)
biraz daha yüksek ama PrimoRL'in drawdown'ı (-5.51% vs -9.37%) ÇOK daha iyi.
Risk yönetimi açısından PrimoRL üstün.

**🟢 NFLX:** En yüksek getiri (%58.47). B&H'den (%58.12) marjinal fark ama
Sharpe (2.80 vs 2.62), volatilite (30.52% vs 32.82%) ve drawdown (-7.76% vs -10.90%)
hepsinde PrimoRL kesin üstün. **Sentiment sinyalleri downside koruması sağlıyor.**

**🟡 MSFT:** Zorlu piyasa koşulları. PrimoRL (%0.53) ve FinRL (%0.24) minimal kâr.
B&H %-4.63 zarar etti. PrimoRL belirsiz piyasalarda bile hafif kârlı kaldı ama
drawdown (-13.39%) FinRL'den (-9.48%) kötü. **İyileştirme gerekli.**

**🟢 CRM:** PrimoRL'in en güçlü performansı. %33.64 getiri, P-MA'dan (%22.36)
%11 fark. Sharpe (2.29), drawdown (-7.56% vs -11.53%) kesin üstün.

**🟢 AMZN:** PrimoRL (%25.45) FinRL'den (%20.30) ve B&H'den (%15.35) üstün.
Sharpe (1.64 vs 1.35) üstün. Benzer risk profili.

#### Table 4 — Diebold-Mariano İstatistiksel Test (HLN Düzeltmeli)

| Hisse | Karşılaştırma | DM İstatistiği | p-Değeri | Anlamlı (α=0.05) |
|:---|:---|:---|:---|:---|
| **AAPL** | PrimoRL vs MOM | -2.408 | **0.0173** | ✅ **EVET** |
| NFLX | PrimoRL vs B&H | 1.991 | 0.0620 | ❌ Hayır |
| MSFT | PrimoRL vs FinRL | 3.656 | **0.0004** | ⚠️ **FinRL KAZANDI** |
| **CRM** | PrimoRL vs P-MA | -5.691 | **7.06e-08** | ✅ **EVET (en güçlü)** |
| AMZN | PrimoRL vs FinRL | 0.166 | 0.8686 | ❌ Hayır |

**DM Test Yorumu:**
- AAPL ve CRM'de PrimoRL İSTATİSTİKSEL OLARAK anlamlı şekilde üstün
- CRM'de p < 0.001 → en güçlü istatistiksel kanıt
- MSFT'de FinRL daha iyi (tek zayıf nokta)
- NFLX ve AMZN'de benzer performans (fark anlamlı değil ama PrimoRL risk metrikleri daha iyi)

---

### BÖLÜM 12B: PORTFÖY SONUÇLARI — TAM DETAY (§5.2)
**Durum:** ✅ TAMAMLANDI

#### Table 5 — PrimoRL Portföy Düzeyi Performans Değerlendirmesi

| Model | Küm. Getiri | Sharpe Ratio | Yıllık Vol. | Maks DD |
|:---|:---|:---|:---|:---|
| Mean Variance | 22.24% | 1.64 | 23.19% | -9.22% |
| DJI (B&H) | 6.35% | 0.94 | 12.24% | -6.91% |
| FinRL (A2C) | **-4.83%** | -0.25 | 23.55% | -11.80% |
| FinRL (SAC) | 24.50% | 1.28 | 34.53% | -16.50% |
| FinRL (PPO) | 13.54% | 0.87 | 31.38% | -18.52% |
| PrimoRL (A2C) | 8.94% | 0.71 | 26.08% | -14.84% |
| PrimoRL (SAC) | 10.02% | 0.77 | 25.96% | -14.86% |
| **PrimoRL (PPO)** | **27.15%** | **1.70** | 27.01% | **-11.44%** |

**📊 SIRALAMA (Kümülatif Getiri):**
```
1. 🥇 PrimoRL (PPO)   27.15%  Sharpe 1.70  ← KAZANAN
2. 🥈 FinRL (SAC)      24.50%  Sharpe 1.28
3. 🥉 Mean Variance    22.24%  Sharpe 1.64
4.    FinRL (PPO)      13.54%  Sharpe 0.87
5.    PrimoRL (SAC)    10.02%  Sharpe 0.77
6.    PrimoRL (A2C)     8.94%  Sharpe 0.71
7.    DJI (B&H)         6.35%  Sharpe 0.94
8.    FinRL (A2C)      -4.83%  Sharpe -0.25  ← EN KÖTÜ
```

**KRİTİK BULGU — PPO + NLP = MÜKEMMEL, SAC + NLP = KÖTÜ:**
```
FinRL (SAC):   24.50% getiri  →  PrimoRL (SAC):  10.02% getiri  ❌ NLP eklendi, KÖTÜLEŞTI
FinRL (PPO):   13.54% getiri  →  PrimoRL (PPO):  27.15% getiri  ✅ NLP eklendi, İYİLEŞTI
```
- PPO, NLP feature'larından FAYDALANIYOR
- SAC, NLP feature'larıyla BOZULUYOR
- Bu, HyperNova'da MUTLAKA PPO kullanmamız gerektiğini doğrular

#### Table 6 — Portföy DM Test (HLN Düzeltmeli)

| Karşılaştırma | DM İst. | p-Değeri | Anlamlı |
|:---|:---|:---|:---|
| PrimoRL (PPO) vs FinRL (SAC) | -2.331 | **0.0212** | ✅ PrimoRL kazandı |
| PrimoRL (PPO) vs Mean Variance | 4.793 | **4.12e-06** | ⚠️ Mean Var. kazandı |

**Yorum:** PrimoRL (PPO) tüm DRL yaklaşımlarını istatistiksel olarak yeniyor.
Ancak klasik Mean-Variance portföy optimizasyonu bazı koşullarda hâlâ rekabetçi.

---

### BÖLÜM 13: SONUÇLAR, LİMİTASYONLAR & GELECEK ÇALIŞMA (§6)
**Durum:** ✅ TAMAMLANDI

#### 13.1 — Makalenin Temel Bulguları Özeti

```
┌──────────────────────────────────────────────────────────────┐
│              PRIMO SİSTEMİ — SONUÇ ÖZETİ                    │
├──────────────────────────────────────────────────────────────┤
│ • Bireysel hisse max getiri:  %58.47 (NFLX)                 │
│ • Portföy getirisi:           %27.15 (PPO)                   │
│ • Portföy Sharpe Ratio:       1.70 (en yüksek)              │
│ • Portföy Max Drawdown:      -11.44%                        │
│ • En iyi algoritma:          PPO (exploration/exploitation)  │
│ • NLP katkısı:               PPO ile sinerji, SAC ile çelişki│
│ • Benchmark yenme:           FinRL, B&H, MOM, MACD, P-MA    │
│ • İstatistiksel anlamlılık:  AAPL, CRM'de p < 0.05          │
└──────────────────────────────────────────────────────────────┘
```

#### 13.2 — Bilinen Limitasyonlar

1. **Gürültülü finansal haberler:** Modelin yanlış sinyaller üretme riski
2. **LLM feature yorumlanabilirliği:** NLP çıktılarının neden o değeri ürettiği belirsiz
3. **Nadir piyasa olayları:** Black swan olaylarına karşı test EDİLMEMİŞ
4. **MSFT zayıf performans:** Bazı hisselerde adaptasyon zorluğu
5. **Canlı dağıtım testlenmemiş:** Latency, slippage, komisyon etkileri bilinmiyor

#### 13.3 — Gelecek Çalışma Önerileri (Makalede Belirtilen)

1. **NLP feature'ları REWARD fonksiyonuna da entegre etmek**
   (şu an sadece state space'te → reward'a da eklenmeli)
2. **Varlık sınıfı genişletme:** ETF'ler, bonolar, **KRİPTO PARALAR** ← DOĞRUDAN HyperNova!
3. **PrimoGPT feature üretimini sektöre özelleştirme**
4. **Canlı dağıtım:** Latency, risk yönetimi, slippage, regülasyon

---

### BÖLÜM 14: HYPERNOVA'YA TAM ENTEGRASYON PLANI (FİNAL)
**Durum:** ✅ TAMAMLANDI — Makale %100 okundu, plan kesinleşti

**Tam Entegrasyon Haritası:**

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    HyperNova → Primo Entegrasyon Tablosu (FİNAL)           ║
╠══════════════════════════════╦═══════════════════════════════════════════════╣
║ HyperNova Mevcut             ║ Primo Uyarlanmış (Hedef)                     ║
╠══════════════════════════════╬═══════════════════════════════════════════════╣
║ Bollinger (n=12, σ=1.8)      ║ Bollinger (n=20, σ=2.0)                      ║
║ StochRSI (custom)            ║ RSI (n=14, exp. smoothing)                   ║
║ (yok)                        ║ + SMA(30), SMA(60)                           ║
║ (yok)                        ║ + MACD (12, 26, 9)                           ║
║ (yok)                        ║ + CCI (n=20)                                 ║
║ (yok)                        ║ + DX (n=14)                                  ║
╠══════════════════════════════╬═══════════════════════════════════════════════╣
║ L2 OIR (HyperLiquid)        ║ State space (Primo'da YOK, EKSTRA AVANTAJ)   ║
║ Funding Rate                 ║ State space (EKSTRA AVANTAJ)                 ║
║ Open Interest                ║ State space (EKSTRA AVANTAJ)                 ║
║ Basis Premium                ║ State space (EKSTRA AVANTAJ)                 ║
╠══════════════════════════════╬═══════════════════════════════════════════════╣
║ (yok)                        ║ + 7 NLP Features (GPT-4o-mini / Llama 3)    ║
╠══════════════════════════════╬═══════════════════════════════════════════════╣
║ Sabit kural (BB+StochRSI)    ║ PPO Agent (MUTLAKA PPO, SAC değil!)          ║
║ Sabit $800 lot               ║ Continuous action [-1,+1] × max_notional     ║
║ Sabit SL/TP %                ║ Dynamic Sharpe Ratio reward (2 fazlı)        ║
║ Sabit 1000:1 kaldıraç        ║ Kaldıraç korunur, pozisyon boyutu DRL belirler║
╠══════════════════════════════╬═══════════════════════════════════════════════╣
║ Eğitim: yok (sabit kurallar) ║ Stable Baselines 3 PPO + Gymnasium           ║
║ Framework: Flask/FastAPI      ║ FastAPI (korunur) + PPO inference loop        ║
╚══════════════════════════════╩═══════════════════════════════════════════════╝
```

**HyperNova'nın Primo'ya Göre 4 EKSTRA AVANTAJI:**
1. L2 Orderbook Derinliği (OIR) — anlık alıcı/satıcı baskısı
2. Fonlama Oranları — sıkışma tespiti
3. Açık Pozisyon (OI) — katılımcı yoğunluğu
4. Basis Premium — spot/vadeli prim farkı

---

## 📚 §2 RELATED WORK — DETAYLI NOTLAR

### §2.1 NLP in Financial Markets
- EMH (Fama): Fiyatlar tüm bilgiyi yansıtır → güncel araştırmalar çürütüyor
- NLP evrimi: İstatistik → ML → Transformer → GPT → FinBERT → FinGPT → PrimoGPT
- Twitter sentiment borsa hareketlerini öngörebiliyor (Bollen et al.)
- Gerçek zamanlı yüksek kaliteli veri şart, overfitting riski var

### §2.2 DRL in Stock Markets
- DRL evrimi: ARMA → Decision Trees → DQN → DDQN → PPO → SAC → PrimoRL
- PPO: Kararlılık ve sample efficiency → SEÇİLEN ALGORİTMA
- Model-agnostic: piyasa dağılımı varsayımı gereksiz
- Exploration vs exploitation dengesi, dışsal sinyal entegrasyonu
- Zorluklar: hesaplama maliyeti, hiperparametre hassasiyeti, overfitting

---

## 🔗 KRİTİK REFERANSLAR & AÇIK KAYNAK REPOLAR

| # | Kaynak | URL | HyperNova İçin Rolü |
|:---|:---|:---|:---|
| [14] | **FinRL** | github.com/AI4Finance-Foundation/FinRL | DRL trading framework temeli |
| [15] | **FinGPT** | github.com/AI4Finance-Foundation/FinGPT | Finansal LLM açık kaynak |
| [39] | **PPO (Schulman)** | arXiv:1707.06347 | Seçilen DRL algoritmasının orijinal makalesi |
| [63] | **LangChain** | langchain.com | Prompt mühendisliği framework |
| [64] | **Llama 3** | arXiv:2407.21783 | PrimoGPT temel modeli |
| [68] | **Gymnasium** | gymnasium.farama.org | DRL ortam standardı |
| [69] | **Stable Baselines 3** | stable-baselines3.readthedocs.io | PPO implementasyonu |
| [71] | **Moody & Saffell** | Differential Sharpe Ratio | Reward fonksiyonu teorik temeli |
| [74] | **Unsloth** | unsloth.ai | Verimli LLM fine-tuning |
| [75] | **QLoRA** | arXiv:2305.14314 | Quantized LoRA fine-tuning |
| YENİ | **FinRL-X (FinRL-Trading)** | github.com/AI4Finance-Foundation/FinRL-Trading | FinRL'in yeni nesli, production-ready |

**📌 REFERANS DÖKÜMANTASYON KONTROLÜ (Yapıldı):**

**SB3 PPO API Yapısı (stable-baselines3.readthedocs.io okundu):**
```python
from stable_baselines3 import PPO

# Model oluşturma (HyperNova'da kullanılacak)
model = PPO(
    "MlpPolicy",           # MLP politika (state vektörümüz için ideal)
    env,                    # Gymnasium environment
    learning_rate=3e-4,     # Varsayılan (Primo: grid search ile optimize)
    n_steps=2048,           # Primo seçimi
    batch_size=128,         # Primo seçimi
    n_epochs=10,            # Varsayılan
    verbose=1
)

# Eğitim
model.learn(total_timesteps=2048)  # Primo learning steps

# Tahmin (inference — canlı trading'de kullanılacak)
action, _states = model.predict(observation, deterministic=True)

# Model kaydetme/yükleme
model.save("ppo_hypernova")
model = PPO.load("ppo_hypernova")
```

**FinRL-X Keşfi (README okundu):**
- FinRL artık "FinRL-X" (Stage 3.0) olarak evrilmiş
- AI-Native paradigma: ML + DRL + LLM-ready
- Modüler, çözülmüş katmanlı mimari
- Production-oriented (live trading, risk kontrolleri)
- HyperNova için FinRL-X'i doğrudan kullanmak yerine, Primo'nun
  FinRL tarzı kendi özel environment'ımızı yazmak daha uygun
  (kripto + L2 mikro yapı verisi FinRL'de yok)

**pip install komutları (implementasyon başladığında):**
```bash
pip install stable-baselines3[extra] gymnasium numpy langchain openai
```

---

## 🔜 İMPLEMENTASYON YOLHARITASI

**MAKALE %100 OKUNDU — TÜM BİLGİLER ÇIKARILDI**

**Tamamlanan Bilgiler (20/20):**
1. ✅ Sistem mimarisi (4 aşamalı akış)
2. ✅ Veri toplama pipeline (Finnhub + Yahoo Finance uyarlaması)
3. ✅ Getiri etiketleme sistemi (U3, D5+ vb.)
4. ✅ SMA formülü (n=30, 60)
5. ✅ MACD formülü (12, 26, 9)
6. ✅ Bollinger Bands formülü (n=20, σ=2)
7. ✅ RSI formülü (n=14, exponential smoothing)
8. ✅ CCI formülü (n=20, typical price)
9. ✅ DX formülü (n=14, ATR bazlı)
10. ✅ PrimoGPT 7 NLP feature tanımı ve ölçekleri
11. ✅ PrimoGPT prompt mühendisliği (LangChain + senior analyst rolü)
12. ✅ PrimoGPT fine-tuning (QLoRA, Llama 3, 2973 örnek, tüm hiperparametreler)
13. ✅ MDP framework (SARP space)
14. ✅ State vektör yapısı ve boyut hesaplaması
15. ✅ Continuous action space [-1, +1] × h_max
16. ✅ İki fazlı dinamik Sharpe ratio reward fonksiyonu
17. ✅ DRL algoritma seçimi: PPO (A2C ve SAC elendi)
18. ✅ PrimoRL hiperparametreleri (grid search: 2048 steps, 128 batch)
19. ✅ Tüm sonuç tabloları (Table 3, 4, 5, 6)
20. ✅ Limitasyonlar ve gelecek çalışma önerileri

**Uygulama Öncelik Sırası:**
```
Faz 1: Teknik Altyapı
  └── 6 teknik indikatörü HyperNova'ya entegre et (SMA, MACD, BB, RSI, CCI, DX)
  └── State vektör yapısını oluştur
  └── Gymnasium/FinRL benzeri kripto environment yaz

Faz 2: NLP Modülü
  └── GPT-4o-mini API ile 7 NLP feature üretici modül oluştur
  └── Kripto haber kaynakları entegrasyonu
  └── LangChain prompt şablonu hazırla

Faz 3: DRL Agent
  └── Stable Baselines 3 PPO agent'ı kur
  └── Continuous action space [-1, +1] tanımla
  └── İki fazlı Sharpe ratio reward fonksiyonunu implemente et
  └── Tarihsel kripto verisiyle eğit

Faz 4: Entegrasyon & Test
  └── PPO agent'ı unified_api.py'ye entegre et
  └── WebSocket üzerinden real-time inference
  └── Backtesting ve paper trading
  └── Android app güncellemesi
```
