# 🚀 BDK Trading Bot

AI destekli paper trading bot - Kripto, ABD Borsası ve BIST

**Versiyon:** 0.1.0
**Yazar:** Bilgehan
**Lisans:** MIT

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Desteklenen Piyasalar](#-desteklenen-piyasalar)
- [Kurulum](#-kurulum)
- [Yapılandırma](#️-yapılandırma)
- [Kullanım](#-kullanım)
- [Klasör Yapısı](#-klasör-yapısı)
- [Geliştirme](#-geliştirme)
- [Lisans](#-lisans)

## ✨ Özellikler

### 📊 Paper Trading
- **$10,000 sanal bakiye** ile risksiz test ortamı
- Gerçek piyasa verileri ile simülasyon
- Risk yönetimi ve stop-loss mekanizmaları
- Günlük maksimum kayıp limiti ($300)
- Pozisyon başına maksimum işlem limiti ($500)
- En fazla 5 eşzamanlı açık pozisyon

### 🔄 Kripto Arbitraj
- 5 farklı borsa arası fiyat farkı tespiti
  - Binance
  - Bybit
  - OKX
  - KuCoin
  - Gate.io
- Minimum %0.15 kâr hedefi
- 60 saniye içinde işlem gerçekleştirme
- %90+ güven skoru gereksinimi

### 📰 Haber Analizi
- AI destekli sentiment (duygu) analizi
- Çoklu kaynak entegrasyonu:
  - NewsAPI
  - CryptoPanic
  - Finnhub
  - Reddit
- Minimum %75 sentiment skoru filtresi
- Gerçek zamanlı haber takibi

### 📱 Telegram Bot
- Türkçe arayüz
- Anlık işlem bildirimleri
- Günlük performans raporları (08:00)
- Portfolio özeti ve analizi
- Kâr/zarar takibi

### 🌙 Gece Modu
- 7/24 otomatik çalışma
- 23:00-07:00 arası sessiz mod
- Kritik fırsatlar için otomatik uyanma
- $1,000+ fırsat tespitinde bildirim

### 🧠 Öğrenen Sistem
- Her trade'den öğrenme
- Strateji optimizasyonu
- Performans analizi ve iyileştirme
- Tarihsel veri analizi

### 🛡️ Risk Yönetimi
- %2.0 stop-loss
- %5.0 take-profit hedefi
- Trailing stop desteği (%1.5)
- Günlük ve pozisyon bazlı limitler
- Otomatik risk değerlendirmesi

## 🌍 Desteklenen Piyasalar

### 💰 Kripto Para (5 Borsa)
**15 farklı kripto para birimi:**
- BTC (Bitcoin)
- ETH (Ethereum)
- SOL (Solana)
- XRP (Ripple)
- ADA (Cardano)
- AVAX (Avalanche)
- DOGE (Dogecoin)
- DOT (Polkadot)
- MATIC (Polygon)
- LINK (Chainlink)
- UNI (Uniswap)
- LTC (Litecoin)
- ATOM (Cosmos)
- NEAR (NEAR Protocol)
- APT (Aptos)

**İşlem Çifti:** USDT bazlı

### 🇺🇸 ABD Borsası (Alpaca)
**10 teknoloji hissesi:**
- AAPL (Apple)
- MSFT (Microsoft)
- GOOGL (Alphabet/Google)
- AMZN (Amazon)
- NVDA (NVIDIA)
- TSLA (Tesla)
- META (Meta/Facebook)
- AMD (Advanced Micro Devices)
- NFLX (Netflix)
- CRM (Salesforce)

**5 popüler ETF:**
- SPY (S&P 500)
- QQQ (Nasdaq-100)
- IWM (Russell 2000)
- DIA (Dow Jones)
- VTI (Total Market)

### 🇹🇷 BIST (Borsa İstanbul)
**10 büyük hisse:**
- THYAO (Türk Hava Yolları)
- SISE (Şişe Cam)
- ASELS (Aselsan)
- GARAN (Garanti Bankası)
- AKBNK (Akbank)
- KCHOL (Koç Holding)
- TUPRS (Tüpraş)
- EREGL (Ereğli Demir Çelik)
- BIMAS (BİM)
- FROTO (Ford Otosan)

## 🔧 Kurulum

### Gereksinimler
- Python 3.11 veya üzeri
- PostgreSQL 14+
- Redis 7+
- pip (Python paket yöneticisi)

### Adım 1: Projeyi Klonlayın
```bash
git clone https://github.com/yourusername/bdk-trading-bot.git
cd bdk-trading-bot
```

### Adım 2: Sanal Ortam Oluşturun
```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Adım 3: Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### Adım 4: Veritabanı Kurulumu
```bash
# PostgreSQL veritabanı oluşturun
createdb bdk_trading

# Alembic ile migrationları çalıştırın (yakında eklenecek)
# alembic upgrade head
```

### Adım 5: Redis'i Başlatın
```bash
# Linux/Mac
redis-server

# Windows (Docker kullanarak)
docker run -d -p 6379:6379 redis:7-alpine
```

### Adım 6: Ortam Değişkenlerini Ayarlayın
```bash
# .env dosyası oluşturun
cp .env.example .env

# .env dosyasını düzenleyerek API anahtarlarınızı ekleyin
nano .env
```

### Adım 7: Yapılandırma Dosyasını Düzenleyin
```bash
# config.yaml dosyasını düzenleyin
cp config/config.example.yaml config/config.yaml
nano config/config.yaml
```

## ⚙️ Yapılandırma

### API Anahtarları (.env)

Kullanmak istediğiniz exchange ve servisler için API anahtarlarını `.env` dosyasına ekleyin:

```env
# Binance (Kripto)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_secret

# Alpaca (ABD Hisseleri)
ALPACA_API_KEY=your_alpaca_api_key
ALPACA_API_SECRET=your_alpaca_secret

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Diğer servisler...
```

### Yapılandırma Dosyası (config/config.yaml)

`config/config.yaml` dosyasından bot ayarlarını özelleştirebilirsiniz:

- **Paper Trading:** Başlangıç bakiyesi, işlem limitleri
- **Piyasalar:** Hangi piyasaların aktif olacağı
- **Risk Yönetimi:** Stop-loss, take-profit oranları
- **Telegram:** Bildirim ayarları, gece modu
- **Arbitraj:** Minimum kâr yüzdesi, güven skoru

## 🚀 Kullanım

### Botu Başlatma
```bash
# Doğrudan Python ile
python src/main.py

# veya kurulu paket olarak (geliştirme aşamasında)
bdk
```

### Geliştirme Modu
```bash
# Testleri çalıştırın
pytest

# Kod kalitesi kontrolü
black .
isort .
mypy src/

# Tüm kontroller
ruff check .
```

### Telegram Bot Komutları (Yakında)
```
/start - Botu başlat
/status - Mevcut durum ve pozisyonlar
/balance - Bakiye bilgisi
/trades - Son işlemler
/report - Günlük rapor
/stop - Botu durdur
```

## 📁 Klasör Yapısı

```
bdk-trading-bot/
├── src/                          # Ana kaynak kodu
│   ├── __init__.py
│   ├── main.py                   # Giriş noktası
│   ├── core/                     # Temel sistem bileşenleri
│   │   ├── __init__.py
│   │   ├── config.py             # Yapılandırma yönetimi
│   │   ├── logger.py             # Loglama sistemi
│   │   └── exceptions.py         # Özel exception sınıfları
│   ├── exchanges/                # Borsa entegrasyonları
│   │   └── __init__.py
│   ├── analysis/                 # Teknik/fundamental analiz
│   │   └── __init__.py
│   ├── strategies/               # İşlem stratejileri
│   │   └── __init__.py
│   ├── notifications/            # Bildirim sistemleri (Telegram)
│   │   └── __init__.py
│   ├── database/                 # Veritabanı modelleri
│   │   └── __init__.py
│   └── utils/                    # Yardımcı fonksiyonlar
│       ├── __init__.py
│       └── helpers.py            # Genel yardımcılar
├── config/                       # Yapılandırma dosyaları
│   ├── config.yaml               # Ana yapılandırma
│   └── config.example.yaml       # Örnek yapılandırma
├── tests/                        # Test dosyaları
│   └── __init__.py
├── logs/                         # Log dosyaları
│   └── .gitkeep
├── data/                         # Veri dosyaları
│   └── .gitkeep
├── requirements.txt              # Üretim bağımlılıkları
├── requirements-dev.txt          # Geliştirme bağımlılıkları
├── pyproject.toml                # Proje yapılandırması
├── .env.example                  # Örnek ortam değişkenleri
├── .gitignore                    # Git ignore kuralları
└── README.md                     # Bu dosya
```

### Modül Açıklamaları

#### `src/core/` - Temel Sistem
- **config.py:** YAML ve .env dosyalarından yapılandırma yükleme
- **logger.py:** Yapılandırılabilir loglama sistemi (structlog)
- **exceptions.py:** Özel exception sınıfları (BDKException, ExchangeError, vb.)

#### `src/exchanges/` - Borsa Entegrasyonları
- Binance, Bybit, OKX, KuCoin, Gate.io için adaptörler
- Alpaca (ABD hisseleri) entegrasyonu
- BIST (Borsa İstanbul) veri akışı
- Birleşik exchange API

#### `src/analysis/` - Analiz Araçları
- Teknik analiz indikatörleri (RSI, MACD, Bollinger Bands)
- Fundamental analiz
- Sentiment analizi
- Fiyat tahmini modelleri

#### `src/strategies/` - İşlem Stratejileri
- Arbitraj stratejisi
- Haber bazlı işlemler
- Trend takip
- Mean reversion
- Özel strateji framework'ü

#### `src/notifications/` - Bildirimler
- Telegram bot entegrasyonu
- Türkçe mesaj şablonları
- Günlük raporlar
- Anlık uyarılar

#### `src/database/` - Veritabanı
- SQLAlchemy modelleri
- İşlem geçmişi
- Performans metrikleri
- Yapılandırma saklama

#### `src/utils/` - Yardımcılar
- Para birimi formatlama
- Zaman dilimi dönüşümleri
- Yüzde hesaplamaları
- Piyasa açık/kapalı kontrolleri
- Retry mekanizmaları

## 👨‍💻 Geliştirme

### Geliştirme Ortamı Kurulumu
```bash
# Geliştirme bağımlılıklarını yükleyin
pip install -r requirements-dev.txt

# Pre-commit hooks kurun (opsiyonel)
pre-commit install
```

### Kod Stili
- **PEP 8** standartlarına uygun
- **Black** ile otomatik formatlama (100 karakter satır uzunluğu)
- **isort** ile import sıralama
- **mypy** ile tip kontrolü
- **ruff** ile kapsamlı linting

### Test Yazma
```python
# tests/test_example.py
import pytest
from src.utils.helpers import format_currency

def test_format_currency():
    assert format_currency(1234.56, "USD") == "$1,234.56"
    assert format_currency(1234.56, "TRY") == "₺1.234,56"
```

### Testleri Çalıştırma
```bash
# Tüm testler
pytest

# Coverage raporu ile
pytest --cov=src --cov-report=html

# Belirli bir test dosyası
pytest tests/test_helpers.py
```

### Yeni Exchange Ekleme
1. `src/exchanges/` altında yeni exchange adaptörü oluşturun
2. Birleşik exchange interface'ini implement edin
3. `config/config.yaml` dosyasına exchange ekleyin
4. Testler yazın

### Yeni Strateji Ekleme
1. `src/strategies/` altında yeni strateji sınıfı oluşturun
2. Base strategy sınıfını extend edin
3. `generate_signal()` metodunu implement edin
4. Backtest edin ve optimize edin

## 🔒 Güvenlik

- **API Anahtarları:** Asla git'e commit etmeyin, `.env` dosyasını kullanın
- **Paper Trading:** Gerçek para kullanmadan önce paper trading ile test edin
- **Rate Limiting:** Exchange API limitlerini aşmamaya dikkat edin
- **2FA:** Mümkün olduğunda exchange hesaplarınızda 2FA kullanın

## 📊 Performans İzleme

Bot otomatik olarak şu metrikleri takip eder:
- Toplam kâr/zarar
- Win rate (kazanma oranı)
- Sharpe ratio
- Maximum drawdown
- İşlem başına ortalama kâr
- Günlük, haftalık, aylık performans

## 🐛 Sorun Giderme

### Veritabanı Bağlantı Hatası
```bash
# PostgreSQL'in çalıştığından emin olun
sudo systemctl status postgresql

# Veritabanının oluşturulduğunu kontrol edin
psql -l | grep bdk_trading
```

### Redis Bağlantı Hatası
```bash
# Redis'in çalıştığından emin olun
redis-cli ping
# Yanıt: PONG
```

### Import Hataları
```bash
# PYTHONPATH'i ayarlayın
export PYTHONPATH="${PYTHONPATH}:/path/to/bdk-trading-bot"
```

## 🗺️ Yol Haritası

### v0.2.0 (Sonraki Sürüm)
- [ ] Veritabanı modelleri ve migrationları
- [ ] Exchange adaptörleri (Binance, Alpaca)
- [ ] Temel arbitraj stratejisi
- [ ] Telegram bot entegrasyonu

### v0.3.0
- [ ] Teknik analiz indikatörleri
- [ ] Haber analizi ve sentiment
- [ ] Backtest framework'ü
- [ ] Web dashboard

### v1.0.0
- [ ] Tüm exchange'ler aktif
- [ ] Çoklu strateji desteği
- [ ] Gelişmiş risk yönetimi
- [ ] Mobil uygulama

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen şu adımları izleyin:

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'feat: Add amazing feature'`)
4. Branch'inizi push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

### Commit Mesaj Formatı
```
feat: Yeni özellik ekleme
fix: Hata düzeltme
docs: Dokümantasyon güncellemesi
style: Kod formatlama
refactor: Kod yeniden yapılandırma
test: Test ekleme/güncelleme
chore: Genel bakım
```

## 📝 Lisans

Bu proje MIT Lisansı ile lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 📧 İletişim

**Bilgehan**

Sorularınız veya önerileriniz için issue açabilirsiniz.

## ⚠️ Yasal Uyarı

Bu yazılım yalnızca eğitim amaçlıdır. Paper trading modu gerçek para kullanmaz ancak gerçek para ile trading yapmayı planlıyorsanız:

- Finansal riskleri anlayın
- Yerel yasalara uyun
- Profesyonel tavsiye alın
- Kaybetmeyi göze alamayacağınız para ile işlem yapmayın

**BDK Trading Bot geliştiricileri, kullanımdan kaynaklanan hiçbir finansal kayıptan sorumlu değildir.**

---

Made with ❤️ by Bilgehan
