# ANKARA SAĞLIKNET — GELİŞTİRME YOL HARİTASI (ROADMAP)
**Doküman Kodu:** DOC-ROADMAP-001  
**Sürüm:** v1.0.0-alpha  

---

## Aşama 1: Temel Dikey Kesit ve Mimari Yeniden Yapılanma (Mevcut Aşama - TAMAMLANDI)
* [x] Doğrulanmış resmi hastaneler ile simülasyon aday lokasyonlarının ayrılması.
* [x] Elastik CFLP matematiksel motorunun (PuLP / CBC) kurulması.
* [x] Açıkta kalan talebin sessizce yok sayılmasını önleyen $u_i$ ceza yapısının eklenmesi.
* [x] Kapsamlı matematiksel birim testlerinin (`pytest`) yazılması ve doğrulanması.
* [x] Senaryo A (Mevcut Durum) vs Senaryo B (Yatırımlar) karşılaştırma analitiği.
* [x] 6 adet resmi mühendislik dokümantasyonunun hazırlanması.

## Aşama 2: 112 Acil Sağlık İstasyonları (ASHİ) ve İki Seviyeli Optimizasyon
* [ ] 112 Acil Sağlık İstasyonlarının (ASHİ) hastanelerden bağımsız ayrı bir tesis türü olarak modellenmesi.
* [ ] İki Aşamalı Sevk Modeli (İstasyon $\to$ Vaka ve Vaka $\to$ Hastane sürelerinin ayrı ayrı optimize edilmesi).
* [ ] Ambulans araç sayısı kısıtları ve dinamik meşguliyet (busy fraction) olasılık hesapları.

## Aşama 3: Gerçekçi Yol Ağı (OSRM) ve Canlı Trafik Entegrasyonu
* [ ] Docker tabanlı yerel OSRM (Open Source Routing Machine) Türkiye/Ankara harita konteynerinin kurulması.
* [ ] Geometrik mesafe yerine gerçek sokak dönemeçleri ve tek yön kısıtlarının yönlendirmeye dahil edilmesi.
* [ ] TomTom / Here API veya açık trafik verileriyle canlı hız doğrulaması.

## Aşama 4: Afet, Kriz ve Yol Kapanma Senaryoları
* [ ] Deprem veya sel durumunda belirli arterlerin (örn: O-20 veya Eskişehir yolu) kapanma simülasyonu.
* [ ] Büyük bir hastanenin (örn: Bilkent veya Etlik) devre dışı kalması durumunda acil tahliye ve yük transferi optimizasyonu.
