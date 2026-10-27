# ANKARA SAĞLIKNET — SİSTEM MİMARİSİ VE VERİ AKIŞI
**Doküman Kodu:** DOC-ARCH-001  
**Sürüm:** v1.0.0-alpha  

---

## 1. Katmanlı Sistem Mimarisi

Sistem, sorumlulukların net olarak ayrıldığı 4 ana katmandan oluşur:

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            1. KULLANICI ARAYÜZÜ (UI)                                │
│                   Streamlit GIS Dashboard (app.py) & Folium                         │
│   - Senaryo Denetleyicisi (Mevcut vs Yatırım)                                       │
│   - Taktiksel Harita (Mevcut Hastaneler, Aday Tesisler, Talep Merkezleri)          │
│   - Canlı Karşılaştırma HUD & Açıkta Kalan Talep Alarmı                             │
└──────────────────────────────────────────┬──────────────────────────────────────────┘
                                           │ Parametreler ve Senaryo
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                     2. ÇEKİRDEK İŞ VE OPTİMİZASYON (CORE)                          │
│   ├── core/optimizer.py  ──► Elastik CFLP Çözücüsü (PuLP / CBC Branch-and-Cut)      │
│   ├── core/routing.py    ──► Mesafe Motoru (OSRM REST API & Geometrik Fallback)     │
│   ├── core/metrics.py    ──► Senaryo Karşılaştırma ve Hakkaniyet Metrikleri         │
│   └── core/models.py     ──► Veri Sınıfları ve Güvenilirlik Statüleri (Enum)        │
└──────────────────────────────────────────┬──────────────────────────────────────────┘
                                           │ Veri Talebi
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           3. VERİ VE DOĞRULAMA (DATA)                               │
│   ├── data/verified_facilities.py ──► Sağlık Bakanlığı Resmi 20 Hastane            │
│   ├── data/candidate_sites.py     ──► 10 Aday Stratejik Lokasyon                    │
│   ├── data/demand_zones.py        ──► TÜİK 2023 ADNKS 32 Talep Noktası (5.8M)       │
│   └── data/__init__.py            ──► Veri Getiriciler ve Filtreleme               │
└──────────────────────────────────────────┬──────────────────────────────────────────┘
                                           │ Doğrulama
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       4. KALİTE GÜVENCE VE TEST (TESTS)                             │
│   └── tests/test_cflp_engine.py   ──► 7 Matematiksel ve Mantıksal Birim Testi       │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Veri Akışı (Data Flow)

1. **Girdi Yükleme:** `data/` paketi, doğrulanmış kamu hastanelerini ve aday lokasyonları yükler.
2. **Seyahat Matrisi Üretimi:** `core/routing.py`, 32 talep merkezi ile 30 tesis (20 mevcut + 10 aday) arasındaki $32 \times 30 = 960$ seyahat süresi ve mesafe değerini $T_{ij}(t)$ dinamik katsayısıyla hesaplar.
3. **Optimizasyon:** `core/optimizer.py`, seçilen senaryo (Mevcut durum $p=0$ veya Yatırım senaryosu $p>0$) için karar değişkenlerini çözer.
4. **Metrikleme:** `core/metrics.py`, iki senaryo arasındaki nüfus kapsaması, süre kazançları ve maliyet farklarını çıkarır.
5. **Görselleştirme:** `app.py`, sonuçları koyu lacivert GIS komuta merkezinde Leaflet haritası ve karşılaştırma kartlarıyla ekrana basar.
