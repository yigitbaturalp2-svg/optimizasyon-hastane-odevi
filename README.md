# Ankara İli Çok Amaçlı Hastane Yerleşimi, Dinamik Trafik ve Toplu Taşıma GIS Optimizasyonu (CFLP)

Bu proje, **Optimizasyona Giriş** dersi kapsamında Ankara ilinde hastanelerin:
1. **Nüfus Kapsaması & Talep Dağılımı** (TÜİK ~5.8M nüfus, 32 ilçe/semt merkezi),
2. **Dinamik Ulaşım Süresi & Karayolu Trafiği** (24 saatlik $K(t)$ trafik sıkışıklık çarpanı, O-20 Çevre Yolu ve 7 ana arter),
3. **Hastane Yapım & Arsa Kamulaştırma Maliyeti** (Bütçe optimizasyonu),
4. **Raylı Sistem & Toplu Taşıma Entegrasyonu** (M1-M4 metro hatları, Başkentray, Ankaray, AŞTİ ve Gar aktarma göbekleri)

faktörlerine göre matematiksel olarak optimize edilmesi ve **akıllı tahta / projeksiyon uyumlu taktiksel GIS haritası** üzerinde canlı simüle edilmesi amacıyla geliştirilmiştir.

---

## 🏥 Optimizasyon Teorisi ve Kullanılan Model

Hocanın derste bahsettiği modeller ve matematiksel altyapı:
- **CFLP (Capacitated Facility Location Problem - Kapasiteli Tesis Yeri Seçimi):** Her hastanenin belirli bir yatak ve hizmet kapasitesi kısıtının ($C_j$) bulunduğu ana model.
- **UFLP (Uncapacitated Facility Location Problem):** Kapasite sınırı olmaksızın sadece sabit açılış maliyeti ve seyahat süresini dengeleyen alternatif model.
- **MILP (Mixed Integer Linear Programming - Karma Tamsayılı Doğrusal Programlama):** Modelin matematiksel çözüm paradigması.
- **Çözücü (Solver):** COIN-OR CBC / HiGHS (PuLP kütüphanesi üzerinden, global optimum garantili < 0.5 saniyede çözüm).

### Matematiksel Formülasyon

#### Karar Değişkenleri:
* $y_j \in \{0, 1\}$: $j$ konumuna hastane açılsın mı? ($1$ = Evet, $0$ = Hayır)
* $x_{ij} \in [0, 1]$: $i$ semtindeki nüfus talebinin $j$ hastanesine tahsis edilen oranı

#### Dinamik Çok Amaçlı Amaç Fonksiyonu (Scalarized Multi-Objective with Dynamic Traffic):
$$\min Z = w_1 \cdot \left(\frac{\sum_{i \in I} \sum_{j \in J} h_i \cdot T_{ij}(t) \cdot x_{ij}}{\text{NormTime}}\right) + w_2 \cdot \left(\frac{\sum_{j \in J} F_j \cdot y_j}{\text{NormCost}}\right)$$

Burada:
- $T_{ij}(t) = T_{ij}^{\text{baz}} \times K(t)$: Seçilen saate ($t$) bağlı gerçek seyahat süresi (Akşam zirvesinde $K(18) = 1.85$, gece $K(2) = 1.00$).
- $h_i$: $i$ semtinin nüfusu (sağlık talebi ağırlığı).
- $F_j$: $j$ aday sahasının arsa ve inşaat maliyeti (Milyon TL).
- $w_1, w_2$: Karar vericinin belirlediği ağırlıklar ($w_1 + w_2 = 1.0$).

#### Temel Kısıtlar:
1. $\sum_{j \in J} x_{ij} = 1 \quad \forall i \in I$: Her semtin talebi tam olarak karşılanmalıdır.
2. $x_{ij} \le y_j \quad \forall i, j$: Yalnızca fiziksel olarak açılan ($y_j = 1$) hastanelere hasta yönlendirilebilir.
3. $\sum_{i \in I} h_i x_{ij} \le C_j y_j \quad \forall j \in J$: Hastane kapasitesi aşılamaz (CFLP kısıtı).
4. $\sum_{j \in J} y_j = p$: Toplam açılacak hastane sayısı bütçeyle sınırlandırılmıştır.

---

## 🚀 Nasıl Çalıştırılır?

### Windows (1 Tıkla Başlat):
Klasör içerisindeki **`run.bat`** dosyasına çift tıklayın. Gerekli kütüphaneleri otomatik doğrular ve Streamlit arayüzünü tarayıcınızda açar.

### macOS & Linux (Terminalden):
Terminal açıp repo dizininde şu komutu verin:
```bash
chmod +x run.sh
./run.sh
```
Bu betik macOS ve Linux ortamında sanal ortamı (`venv`) hazırlar, bağımlılıkları yükler ve uygulamayı doğrudan başlatır.

### Manuel Başlatma (Tüm Platformlar):
```bash
pip install -r requirements.txt
python -m streamlit run app.py
```
Otomatik olarak `http://localhost:8501` açılacaktır.

---

## 📌 Proje Fazları ve Yol Haritası
* **Faz 001 (Tamamlandı & Doğrulandı):** Ankara Çok Katmanlı Hastane Yerleşimi ve Kapasite Tahsis Karar Destek Sistemi (25/25 test geçildi, bağımsız denetim onaylandı).
* **Faz 002 (Sonraki Faz Görevi):** 112 Ambulans İstasyonları ve Acil Müdahale Optimizasyonu (MCLP + Çift Bacaklı Sevk Simülasyonu).
  * Görev detayları ve teknik şartname: [SONRAKI_FAZ_GOREVI.md](SONRAKI_FAZ_GOREVI.md) / [docs/TEKNIK_GOREV_002.md](docs/TEKNIK_GOREV_002.md)

---

## 🎯 Akıllı Tahta / Projeksiyon Sunum Senaryoları (Hocaya Karşı Taktikler)

### 1. "Tek Tıkla" Akıllı Tahta Presets (Sol Panel En Üstte):
Hocanın karşısındayken tek tek slider ayarlamakla uğraşmayın, sol üstteki butonlara doğrudan dokunun:
- **🌟 Önerilen Model:** 5 stratejik hastane, dengeli süre ve maliyet ağırlığı (%65 / %35).
- **🚨 Akşam Zirvesi:** 18:30 yoğun trafik senaryosu (+%85 gecikme), sistem 6 hastane açarak trafiğe meydan okur.
- **🌙 Gece Nöbeti:** 02:00 serbest trafik akışı, ambulanslar 11 dakikada tüm Ankara'ya erişir.
- **💰 Düşük Bütçe:** Minimum harcamayla sadece 3 kritik noktada (Batıkent, Mamak, Çankaya) sağlık üssü açar.

### 2. Canlı Ambulans Sevk Simülatörü (Acil Çağrı Deneyimi):
- Üstteki açılır menüden **Sincan Merkez**, **Mamak** veya **Pursaklar**'ı seçin.
- Harita üzerinde ambulans ikonunun (`🚑 ACİL ÇAĞRI`) yanıp söndüğünü ve hastaneye doğru neon cyan çizgiyle (`AntPath`) hareket ettiğini hocaya gösterin.
- HUD kutusundaki kıyaslamayı okuyun:
  > *"Hocam bakın Sincan'daki bir kalp krizi vakası mevcut sistemde Etlik/Bilkent'e 32.2 dakikada giderken, optimize modelimiz sayesinde 15.6 dakikada Sincan Batı Hastanesi'ne ulaşıyor. Tam **16.6 dakika hayat kurtaran kazanç** sağlıyoruz!"*

### 3. Taktiksel Harita Göstergeleri:
- **Pulsing Radar Dalgaları:** Açılan hastane ikonları Leaflet CSS radar halkaları ile ekranda parlar (`AÇIK #1`, `AÇIK #2`).
- **Canlı Trafik Koridorları:** O-20 Çevre Yolu, Eskişehir Yolu, Konya Yolu ve Samsun Yolu saat 18:30'da kırmızı-bordo neon ışıkla yanar.
- **Hinterlant Havzaları (Convex Hull):** Her hastanenin sorumlu olduğu coğrafi hizmet bölgesini renkli şeffaf poligonlarla gösterir.
- **Isı Haritası (HeatMap):** Sol panelden *"🔥 Nüfus Yoğunluğu Isı Haritası"* kutusunu açarak Ankara'nın nüfus ağırlık merkezlerini gösterin.
- **Tam Ekran (Fullscreen):** Haritanın sol üstündeki tam ekran ikonuna basarak tahtayı dev bir komuta merkezine çevirin.

### 4. Sekme 2: Mevcut Durum vs Optimize Model (Ölümcül Kıyaslama):
- Sadece Bilkent ve Etlik Şehir Hastaneleri'ne mahkûm kalındığında ortalama ambulans süresinin **28.4 dakika** olduğunu, önerilen CFLP modeliyle bunun **21.6 dakikaya** (%24 daha hızlı) indiğini gösterin.
- *"En Yüksek Zaman Tasarrufu Sağlanan Çeper Semtler"* tablosunu hocaya gösterip, Polatlı ve Sincan gibi uzak ilçelerin 20-38 dakika kazandığını kanıtlayın.
