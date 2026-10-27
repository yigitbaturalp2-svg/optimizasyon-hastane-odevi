# ANKARA SAĞLIKNET — VERİ KAYNAKLARI, DOĞRULAMA VE METADATA SÖZLÜĞÜ
**Doküman Kodu:** DOC-DATA-001  
**Sürüm:** v1.0.0-alpha  

---

## 1. Veri Sınıflandırma Prensipleri

Projede "sahte kesinlik" üretimini önlemek adına veriler 3 kesin sınıfa ayrılmıştır:

```
[VERIFIED_EXISTING]   ──► Resmi devlet kayıtlarıyla doğrulanmış gerçek mevcut tesisler
[SIMULATION_ZONE]     ──► TÜİK nüfus sayımına dayalı talep merkezleri
[CANDIDATE_INVESTMENT]──► Simülasyon ve senaryo amacıyla kurgulanan yatırım adayları
```

---

## 2. Doğrulanmış Gerçek Veri Kaynakları

### A. T.C. Sağlık Bakanlığı Sağlık Hizmetleri Genel Müdürlüğü (SHGM)
* **Kapsam:** Ankara'daki kamu ve üniversite hastanelerinin resmi listesi, yatak sayıları ve yasal statüleri.
* **Kaynak URL:** `https://shgmshpdb.saglik.gov.tr/TR-96013/ankara.html`
* **Doğrulanan Tesisler:** Bilkent Şehir Hastanesi, Etlik Şehir Hastanesi, Gülhane EAH, Ankara EAH, Yenimahalle EAH, Sincan Dr. Nafiz Körez Devlet Hastanesi ve çevre ilçe devlet hastaneleri (toplam 20 tesis).

### B. T.C. Ankara İl Sağlık Müdürlüğü
* **Kapsam:** Ankara Devlet Hastaneleri güncel hizmet binaları, acil servis ve poliklinik yerleşkeleri.
* **Kaynak URL:** `https://ankaraism.saglik.gov.tr/TR-69494/devlet-hastaneleri.html`

### C. TÜİK Adrese Dayalı Nüfus Kayıt Sistemi (ADNKS)
* **Kapsam:** 2023-2024 Ankara ilçe ve kentsel mahalle nüfusları.
* **Kaynak URL:** `https://nip.tuik.gov.tr/Home/Adnks`
* **Toplam Kapsanan Nüfus:** 5,810,000 kişi.

---

## 3. Simülasyon Verileri ve Varsayımlar

Aşağıdaki veriler gerçek zamanlı sensör veya ihale verisi olmayıp, simülasyon amacıyla türetilmiştir:

| Parametre | Kabul Edilen Değer | Gerekçe / Varsayım |
| :--- | :---: | :--- |
| **Yıllık Acil Servis Başvuru Oranı** | **0.35 başvuru / kişi / yıl** | Sağlık Bakanlığı Türkiye İstatistik Yıllığı ortalaması. |
| **Aday Tesis Yatırım Maliyetleri** | **430 - 920 Milyon TL** | Arsa kamulaştırma rayici ve tahmini kaba inşaat birim maliyeti. |
| **Kentsel Yol Kıvrım Katsayısı** | **1.28x Haversine** | Ankara ızgara ve radyal yol ağının topoğrafik dolambaç katsayısı. |
| **Saatlik Trafik Gecikme Katsayısı $K(t)$** | **1.00x - 1.85x** | Sabah ve akşam zirve iş çıkışı seyahat süresi uzama profili. |
