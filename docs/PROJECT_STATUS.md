# ANKARA SAĞLIKNET — PROJE DURUMU VE MEVCUT DURUM RAPORU
**Doküman Kodu:** DOC-STATUS-001  
**Tarih:** 27 Ekim 2026  
**Sürüm:** v1.0.0-alpha  
**Mühendislik Rolü:** Baş Yazılım Mühendisi  

---

## 1. Yönetici Özeti
Ankara SağlıkNet projesi, Ankara ili genelinde acil sağlık ve hastane altyapısının çok amaçlı optimizasyonunu hedefleyen akademik ve simülasyon tabanlı bir karar destek sistemidir. Projenin önceki sürümlerinde tespit edilen "Ankara nüfusunun yalnızca 2 şehir hastanesine (Bilkent ve Etlik) hizmet aldığı" yönündeki yanıltıcı varsayım tamamen kaldırılmış, sistem doğrulanmış resmi kamu hastaneleri ve yeni yatırım adayları olarak iki ana katmana ayrılmıştır.

---

## 2. Mevcut Bileşenler ve Çalışma Durumları

| Modül | Durum | Teknik Gerçeklik Seviyesi | Açıklama |
| :--- | :---: | :---: | :--- |
| **Elastik CFLP Optimizasyon Motoru** | **TAMAMLANDI** | **%100 Gerçek (MILP)** | PuLP ve CBC çözücüsü ile kapasite, bütçe ve açıkta kalan talep kısıtları matematiksel kesinlikle çözülmektedir. |
| **Doğrulanmış Kamu Hastaneleri Katmanı** | **TAMAMLANDI** | **%100 Doğrulanmış Gerçek** | Sağlık Bakanlığı SHGM ve Ankara İl Sağlık Müdürlüğü veritabanından 20 adet resmi hastane koordinat ve kapasiteleriyle sisteme işlendi. |
| **Aday Yatırım Tesisleri Katmanı** | **TAMAMLANDI** | **Simülasyon Varsayımı** | 10 adet stratejik kentsel koridor adayı, tahmini arsa ve yatırım maliyetleriyle modellendi. |
| **TÜİK ADNKS Talep Bölgeleri** | **TAMAMLANDI** | **Doğrulanmış Nüfus / Standart Talep** | 32 ana kentsel bölgede 5.8M nüfus ve kişi başı 0.35 acil başvuru oranıyla birim tutarlılığı sağlandı. |
| **Mesafe ve Yönlendirme Motoru** | **TAMAMLANDI** | **Kalibre Geometrik Model (Fallback)** | OSRM çevrimdışı olduğunda Haversine * 1.28x kıvrım katsayısı kullanılarak hesaplama yapılır; kullanıcıya simülasyon olduğu açıkça bildirilir. |
| **İki Senaryo Karşılaştırma Analitiği** | **TAMAMLANDI** | **Analitik / Karşılaştırmalı** | Senaryo A (Mevcut Kamu Ağı) ile Senaryo B (Optimize Yeni Yatırımlar) aynı ölçüm kriterleriyle yan yana kıyaslanır. |
| **Birim Test Paketi (Pytest)** | **TAMAMLANDI** | **Doğrulandı (7/7 Test Geçti)** | Kapasite, bütçe, açıkta kalan talep, senaryo ayrımı ve analitik optimum testleri 0.74 saniyede hatasız tamamlandı. |

---

## 3. Bilinen Teknik Borçlar ve Sınırlar
1. **Canlı Trafik API Entegrasyonu:** Gerçek zamanlı sensör veya GPS verisi bulunmamakta, günün 24 saati için ampirik $K(t)$ trafik çarpanı modeli kullanılmaktadır.
2. **OSRM Yerel Konteyner İhtiyacı:** Genel OSRM sunucusu hız kısıtlamalarına tabidir. İlerleyen fazda Docker tabanlı yerel bir OSRM sunucusu kurulması önerilmektedir.
3. **112 İstasyon Ayrımı:** Ambulans istasyonları (ASHİ) ile hastaneler henüz tam olarak bağımsız iki seviyeli (Two-Echelon) hiyerarşik model olarak ayrılmamıştır (Faz 2 kapsamında ele alınacaktır).
