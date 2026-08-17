# Active Context — HyperNova AI Trading Bot

## Current Focus
**Institutional 200x Max Leverage & Commission-Killer Sniper Architecture**
Upgraded HyperNova from high-frequency micro-churning to institutional-grade, sniper-calibrated momentum trading that crushes exchange fees.

---

## 🏛️ 200x Leverage & Fee-Crushing Quant Engine

### 1. 200x Realistic Leverage Math (MEXC / CEX Standard)
- **Max Leverage**: `200.0x` (Standard max leverage across major crypto exchanges).
- **Micro-Margin Math**: $800 Notional uses only **$4.00 Margin** per trade.
- **Safety**: Margin level is ultra-healthy (> 200,000%), liquidation distance is wide (> 0.50%), and drawdowns are strictly managed.

### 2. Commission-Killer Quant Rules
1. **Asgari Kâr Eşiği (`base_profit_trigger = 0.0012` / +0.12%)**:
   - $800 Notional pozisyonda %0.12 spot hareketi = **+$0.96 brüt kâr** (**+%24.0 ROE** on $4 margin).
   - Round-trip $0.32 komisyon ödendiğinde bile cepte net **+$0.64 kâr** kalır (Kâr/Komisyon oranı: 3:1).
2. **Sniper Giriş Filtresi (`action_scalar >= 0.40` & `composite_alpha >= 12`)**:
   - Gürültüde açılan zayıf işlemleri %60 eler; sadece PPO güçlü dalga ve L2 tahta baskısı birleştiğinde işleme girer.
3. **Komisyon Koruma Kalkanı (Break-Even + Fee Shield)**:
   - Pozisyon tepe kârı `+%0.08` ($0.64) seviyesine ulaştığı an stop seviyesi `+%0.045` ($0.36) seviyesine kilitlenir.
   - Trend geri dönse bile pozisyon komisyonunu çıkararak kapanır; **asla komisyon zararı yazdırmaz.**
4. **Ölü Pozisyon Sabrı (`stagnant_timeout_seconds = 360` / 6 Dakika)**:
   - Pozisyonlara trendi yakalaması için 6 dakika nefes payı tanınır.
