# ANKARA SAĞLIKNET — MATEMATİKSEL MODEL SPESİFİKASYONU (ELASTİK CFLP)
**Doküman Kodu:** DOC-MODEL-001  
**Sürüm:** v1.2.0-verified  

---

## 1. Notasyonlar ve İndeksler

* $I$: Talep bölgeleri kümesi ($i \in I, \; |I| = 32$)
* $J_{\text{eligible}}$: Genel hastane nakil yetkinliğine sahip tesisler kümesi ($|J_{\text{eligible}}| = 26$)
* $J_{\text{exist}} \subset J_{\text{eligible}}$: Mevcut doğrulanmış resmi kamu hastaneleri ($|J_{\text{exist}}| = 20$)
* $J_{\text{cand}} \subset J_{\text{eligible}}$: Aday sağlık kampüsleri kümesi ($|J_{\text{cand}}| = 6$, `can_receive_hospital_transfer=True`)
* $J_{\text{post}}$: Faz 002 için ayrılmış acil müdahale üsleri ($|J_{\text{post}}| = 4$, hastane optimizasyonu dışı)
* $E_{\text{reach}} \subset I \times J_{\text{eligible}}$: Sonlu ve kesim süresini aşmayan geçerli seyahat bağlantıları kümesi.
* $d_i$: $i$ bölgesinin yıllık acil servis başvuru talebi (Adet/Yıl, $\text{Nüfus}_i \times 0.35$)
* $C_j$: $j$ tesisinin yıllık acil servis kabul kapasitesi (Adet/Yıl, simüle norm)
* $F_j$: $j$ aday sahasının toplam yeni yatırım maliyeti (Milyon TL)
* $T_{ij}(t)$: $i$ bölgesi ile $j$ tesisi arasında $t$ saatindeki seyahat süresi (Dakika)
* $p$: Açılması hedeflenen aday hastane sayısı (`p_candidates`)
* $B$: Maksimum yeni yatırım bütçesi (Milyon TL, `max_investment_budget_million_tl`)
* $w_1, w_2$: Seyahat süresi ve yatırım maliyeti ağırlıkları ($w_1 + w_2 = 1.0$)

---

## 2. Karar Değişkenleri

* $y_j \in \{0, 1\}$: $j \in J_{\text{cand}}$ aday hastanesinin açılıp açılmayacağı (1: Aç, 0: Açma). Mevcut tesisler için $y_j = 1$ sabittir.
* $x_{ij} \in [0, 1]$: $(i,j) \in E_{\text{reach}}$ için $i$ bölgesinin sağlık talebinin $j$ tesisine tahsis edilen sürekli oranı.
* $u_i \in [0, 1]$: $i$ bölgesinin kapasite yetersizliği veya ulaşılamazlık nedeniyle açıkta kalan (karşılanamayan) talep oranı.

---

## 3. İki Aşamalı Lexicographic Optimizasyon Yaklaşımı

Model, sağlık hizmetine erişimin maliyet ve süreden üstün olduğu ilkesine dayanarak iki aşamalı öncelik hiyerarşisi uygular:

### Aşama 1: Karşılanamayan Talebin Doğrudan Minimizasyonu
$$\min U = \sum_{i \in I} d_i \cdot u_i$$

Aşama 1'in çözücü statüsü kontrol edilir. **Optimal statü doğrulanmadan ve amaç değeri geçerli bir sonlu sayı olmadan Aşama 2 asla başlatılmaz**.
Elde edilen küresel minimum açıkta kalan talep seviyesi $U^*$ olarak kaydedilir.

### Aşama 2: Nakil Süresi ve Yatırım Maliyetinin Minimizasyonu
Aşama 1'de elde edilen minimum karşılanamayan talep kilitlenir ($10^{-3}$ sayısal toleransla):
$$\sum_{i \in I} d_i \cdot u_i \le U^* + 10^{-3}$$

Bu kısıt altında seyahat süresi ve maliyet minimize edilir:
$$\min Z_2 = w_1 \cdot \left(\frac{\sum_{(i,j) \in E_{\text{reach}}} d_i \cdot T_{ij}(t) \cdot x_{ij}}{\text{NormTime}}\right) + w_2 \cdot \left(\frac{\sum_{j \in J_{\text{cand}}} F_j \cdot y_j}{\text{NormCost}}\right)$$

* $\text{NormTime} = \sum_{i \in I} d_i \times 45.0$: Seyahat süresi normalizasyon sabiti.
* $\text{NormCost} = \max(1.0, \sum_{j \in J_{\text{cand}}} F_j)$: Yatırım maliyeti normalizasyon sabiti.

---

## 4. Kısıtlar ve Aday Seçim Modları

1. **Elastik Talep Korunumu:**
   $$\sum_{j : (i,j) \in E_{\text{reach}}} x_{ij} + u_i = 1 \quad \forall i \in I$$
   *Bir bölgenin hiçbir hastaneye ulaşamadığı durumda ($E_{\text{reach}} = \emptyset$), $u_i = 1.0$ (karşılanamayan talep) olarak korunur.*

2. **Açık Tesis Mantıksal Bağı:**
   $$x_{ij} \le y_j \quad \forall (i,j) \in E_{\text{reach}}, \; j \in J_{\text{cand}}$$

3. **Kapasite ve Yatak Üst Sınırı:**
   $$\sum_{i : (i,j) \in E_{\text{reach}}} d_i \cdot x_{ij} \le C_j \cdot y_j \quad \forall j \in J_{\text{eligible}}$$

4. **Aday Seçim ve Bütçe Kısıtları:**
   - **EXACT_COUNT:** $\sum_{j \in J_{\text{cand}}} y_j = p$ ($p > |J_{\text{cand}}|$ ise çözüme girmeden reddedilir).
   - **MAX_COUNT:** $\sum_{j \in J_{\text{cand}}} y_j \le p$
   - **BUDGET_LIMIT:** $\sum_{j \in J_{\text{cand}}} F_j \cdot y_j \le B$
   - **COMBINED:** $\sum_{j \in J_{\text{cand}}} y_j \le p \quad \land \quad \sum_{j \in J_{\text{cand}}} F_j \cdot y_j \le B$

5. **Ulaşılamayan Bağlantı Kuralı:**
   Sonsuz ($T_{ij} = \infty$) veya geçersiz bağlantılar için $x_{ij}$ değişkeni oluşturulmaz; PuLP amaç fonksiyonuna `inf` katsayı geçirilmez.
