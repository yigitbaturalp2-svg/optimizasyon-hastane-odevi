# ANKARA SAĞLIKNET — VERİ KAYNAKLARI, DOĞRULAMA VE METADATA SÖZLÜĞÜ
**Doküman Kodu:** DOC-DATA-001  
**Sürüm:** v1.2.0-verified  

---

## 1. Veri Sınıflandırma Prensipleri ve Tesis Rolleri

Projede "sahte kesinlik" üretimini önlemek adına veriler kesin sınıflara ve hizmet yetkinliklerine ayrılmıştır:

```
[VERIFIED_EXISTING]   ──► Resmi devlet kayıtlarıyla doğrulanmış faal 20 kamu hastanesi
[CANDIDATE_INVESTMENT]──► 6 Aday Sağlık Kampüsü (Genel hastane nakline uygun)
                      ──► 4 Aday Acil Müdahale Üssü (Yataksız ilk müdahale, Faz 002 için ayrılmış)
[SIMULATION_ZONE]     ──► TÜİK 2023 ADNKS verisiyle modellenen 32 kentsel ve yakın çeper talep bölgesi
```

---

## 2. Nüfus ve Talep Doğrulama Raporu (TÜİK ADNKS 2023)

Bağımsız denetim sonucunda tespit edilen nüfus çelişkisi giderilmiş, il geneli ile model kapsamı açıkça ayrılmıştır:

| Gösterge | Resmi Değer | Temsil / Açıklama |
| :--- | :---: | :--- |
| **TÜİK ADNKS 2023 Ankara İl Geneli Nüfusu** | **5,803,482 kişi** | Ankara'nın 25 ilçesinin resmi toplam nüfusu. |
| **Modellenen 32 Kentsel & Yakın Çeper Talep Bölgesi** | **5,570,000 kişi** | **%95.98 Metropol Temsil Oranı** (Merkez, metropol ve yakın çeper ilçeler). |
| **Kapsam Dışı Uzak Kırsal Nüfus** | **~233,482 kişi** | Güdül, Ayaş, Beypazarı/Nallıhan uzak kırsalı, Evren, Çamlıdere vb. (Faz 002/003 bölgesel acil sağlık genişlemesine ayrılmıştır). |
| **Yıllık Acil Servis Başvuru Katsayısı** | **0.35 başvuru/kişi/yıl** | T.C. Sağlık Bakanlığı Sağlık İstatistikleri Yıllığı normu. |
| **Toplam Yıllık Modellenen Acil Başvuru Talebi** | **1,949,500 başvuru/yıl** | $5,570,000 \times 0.35 = 1,949,500$ acil başvuru/yıl. |

---

## 3. Doğrulanmış Gerçek Veri Kaynakları ve Provenance Alanları

Her sağlık tesisi kaydı için veri kökeni (`provenance`) açık alanlarla tutulur:

- `name_source`: Tesis isminin doğrulandığı resmi kurum listesi.
- `coordinate_source`: Koordinatların doğrulandığı CBS/harita kaynağı.
- `capacity_source`: Yatak sayısı veya kapasite katsayısının dayanağı.
- `last_verified_date`: İlgili kaydın resmi kaynaktan teyit edildiği tarih.
- `capacity_is_simulated`: Yıllık acil servis kabul kapasitesinin doğrudan ölçüm mü yoksa yatak normundan türetilmiş bir simülasyon mu olduğunu belirten bayrak.
- `can_receive_hospital_transfer`: Tesisin genel yataklı hastane nakillerini kabul etmeye yetkin olup olmadığı.

### A. T.C. Sağlık Bakanlığı Sağlık Hizmetleri Genel Müdürlüğü (SHGM)
* **Kapsam:** Ankara'daki kamu ve üniversite hastanelerinin resmi listesi, yatak sayıları ve yasal statüleri.
* **Kaynak URL:** `https://shgmshpdb.saglik.gov.tr/TR-96013/ankara.html`
* **Doğrulanan 20 Tesis:** Bilkent Şehir Hastanesi (3810 yatak), Etlik Şehir Hastanesi (4050 yatak), Gülhane EAH (1000 yatak), Hacettepe Üniversitesi (1040 yatak), Ankara Üniversitesi (1200 yatak), Gazi Üniversitesi (1000 yatak), Ankara EAH Ulucanlar (750 yatak), Yenimahalle EAH (550 yatak), Sincan Dr. Nafiz Körez DH (480 yatak), Etimesgut Şehit Sait Ertürk DH (250 yatak), Keçiören EAH Sanatoryum (450 yatak), Mamak DH (200 yatak), Gölbaşı Şehit Ahmet Özsoy DH (200 yatak), Pursaklar DH (150 yatak), Polatlı Duatepe DH (300 yatak), Çubuk Halil Şıvgın DH (150 yatak), Kahramankazan Hamdi Eriş DH (100 yatak), Elmadağ Hulusi Alataş DH (50 yatak), Beypazarı DH (100 yatak), Dışkapı Yıldırım Beyazıt Ek Bina (400 yatak).
* **Kapasite Bildirimi:** Tescilli yatak sayıları gerçektir; yıllık acil başvuru kabul kapasiteleri ise planlama normuyla simüle edilmiştir (`capacity_is_simulated = True`).

---

## 4. Aday Tesisler ve Rol Ayrımı

### A. Aday Sağlık Kampüsleri (6 Adet — Genel Hastane Nakline Uygun)
* **KODLAR:** `CAND_01`, `CAND_03`, `CAND_04`, `CAND_05`, `CAND_07`, `CAND_09`
* **Yetkinlik:** `can_receive_hospital_transfer = True`, `facility_type = FacilityType.ADAY_SAGLIK_KAMPUSU`
* **Hedef Yatak:** 450 - 800 yatak.
* **Tahmini Yatırım Maliyeti:** 520 - 920 Milyon TL.

### B. Aday Acil Müdahale Üsleri (4 Adet — Faz 002 İçin Ayrılmış)
* **KODLAR:** `CAND_02`, `CAND_06`, `CAND_08`, `CAND_10`
* **Yetkinlik:** `can_receive_hospital_transfer = False`, `facility_type = FacilityType.ADAY_ACIL_USSU`
* **Yatak:** 0 (Yataklı hastane servisi bulunmaz).
* **Rol:** Faz 002 ambulans ağı ve ileri ilk müdahale istasyonu olarak değerlendirilmek üzere ayrılmıştır. Genel hastane optimizasyonuna dahil edilmez.
