# ANKARA SAĞLIKNET — MATEMATİKSEL MODEL SPESİFİKASYONU (ELASTİK CFLP)
**Doküman Kodu:** DOC-MODEL-001  
**Sürüm:** v1.1.0-verified  

---

## 1. Notasyonlar ve İndeksler

* $I$: Talep bölgeleri kümesi ($i \in I, \; |I| = 32$)
* $J$: Tüm sağlık tesisleri kümesi ($j \in J, \; |J| = 30$)
* $J_{\text{exist}} \subset J$: Mevcut doğrulanmış resmi hastaneler kümesi ($|J_{\text{exist}}| = 20$)
* $J_{\text{cand}} \subset J$: Yeni yatırım aday lokasyonları kümesi ($|J_{\text{cand}}| = 10$)
* $E_{\text{reach}} \subset I \times J$: Sonlu ve geçerli seyahat süresi sağlanan ulaşılabilir kenarlar kümesi.
* $d_i$: $i$ bölgesinin yıllık acil servis başvuru talebi (Adet/Yıl, $\text{Nüfus}_i \times 0.35$)
* $C_j$: $j$ tesisinin yıllık acil servis kabul kapasitesi (Adet/Yıl)
* $F_j$: $j$ aday sahasının toplam yatırım ve kamulaştırma maliyeti (Milyon TL)
* $T_{ij}(t)$: $i$ bölgesi ile $j$ tesisi arasında $t$ saatindeki seyahat süresi (Dakika)
* $p$: Açılması hedeflenen kesin yeni aday tesis sayısı (`p_candidates`, EXACT_COUNT)
* $w_1, w_2$: Seyahat süresi ve yatırım maliyeti ağırlıkları ($w_1 + w_2 = 1.0, \; w_1, w_2 \ge 0$)

---

## 2. Karar Değişkenleri

* $y_j \in \{0, 1\}$: $j \in J_{\text{cand}}$ aday tesisinin açılıp açılmayacağı (1: Aç, 0: Açma). Mevcut tesisler için $y_j = 1$ sabittir.
* $x_{ij} \in [0, 1]$: $(i,j) \in E_{\text{reach}}$ için $i$ bölgesinin sağlık talebinin $j$ tesisine tahsis edilen oranı.
* $u_i \in [0, 1]$: $i$ bölgesinin kapasite yetersizliği veya ulaşılamazlık nedeniyle açıkta kalan (karşılanamayan) talep oranı.

---

## 3. İki Aşamalı Lexicographic Optimizasyon Yaklaşımı (`use_lexicographic=True`)

Model, insan hayatının ve sağlık hizmetine erişimin maliyet ve süreden üstün olduğu ilkesine dayanarak iki aşamalı öncelik hiyerarşisi uygular:

### Aşama 1: Karşılanamayan Talebin Doğrudan Minimizasyonu
$$\min U = \sum_{i \in I} d_i \cdot u_i$$

Aşama 1'in çözücü statüsü kontrol edilir. **Optimal statü doğrulanmamışsa Aşama 2 ASLA başlatılmaz**, hata durumu derhal raporlanır.

Elde edilen küresel minimum açıkta kalan talep seviyesi $U^*$ olarak kaydedilir.

### Aşama 2: Seyahat Süresi ve Yatırım Maliyetinin Minimizasyonu
Aşama 1'de elde edilen minimum karşılanamayan talep kilitlenir ($10^{-3}$ sayısal toleransla):
$$\sum_{i \in I} d_i \cdot u_i \le U^* + 10^{-3}$$

Bu kısıt altında seyahat süresi ve maliyet minimize edilir:
$$\min Z_2 = w_1 \cdot \left(\frac{\sum_{(i,j) \in E_{\text{reach}}} d_i \cdot T_{ij}(t) \cdot x_{ij}}{\text{NormTime}}\right) + w_2 \cdot \left(\frac{\sum_{j \in J_{\text{cand}}} F_j \cdot y_j}{\text{NormCost}}\right)$$

* $\text{NormTime} = \sum_{i \in I} d_i \times 45.0$: Seyahat süresini normalize eden sabit (45 dakika baz süre).
* $\text{NormCost} = \max(1.0, \sum_{j \in J_{\text{cand}}} F_j)$: Maksimum yatırım bütçesi normalizasyon sabiti.

---

## 4. Kısıtlar ve Güvenlik Kuralları

1. **Elastik Talep Korunumu:**
   $$\sum_{j : (i,j) \in E_{\text{reach}}} x_{ij} + u_i = 1 \quad \forall i \in I$$
   *Bir bölgenin hiçbir hastaneye ulaşamadığı durumda ($E_{\text{reach}} = \emptyset$), $u_i = 1.0$ (karşılanamayan talep) olarak korunur.*

2. **Açık Tesis Mantıksal Bağı:**
   $$x_{ij} \le y_j \quad \forall (i,j) \in E_{\text{reach}}, \; j \in J_{\text{cand}}$$

3. **Kapasite ve Yatak Üst Sınırı:**
   $$\sum_{i : (i,j) \in E_{\text{reach}}} d_i \cdot x_{ij} \le C_j \cdot y_j \quad \forall j \in J$$

4. **Bütçe ve Aday Tesis Doğrulaması (EXACT_COUNT):**
   $$\sum_{j \in J_{\text{cand}}} y_j = p$$
   *Eğer istenen $p$ adedi mevcut aday havuzu büyüklüğünden fazlaysa ($p > |J_{\text{cand}}|$), model çözüme girmeden `Infeasible_Candidate_Count` olarak reddedilir.*

5. **Ulaşılamayan Bağlantılar:**
   $T_{ij} = \infty$ veya geçersiz seyahat süreleri kesinlikle PuLP amaç fonksiyonuna katsayı olarak geçirilmez. İlgili bağlantı $E_{\text{reach}}$ kümesinden çıkarılır.
