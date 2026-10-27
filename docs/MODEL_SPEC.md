# ANKARA SAĞLIKNET — MATEMATİKSEL MODEL SPESİFİKASYONU (ELASTİK CFLP)
**Doküman Kodu:** DOC-MODEL-001  
**Sürüm:** v1.0.0-alpha  

---

## 1. Notasyonlar ve İndeksler

* $I$: Talep bölgeleri kümesi ($i \in I, \; |I| = 32$)
* $J$: Tüm sağlık tesisleri kümesi ($j \in J, \; |J| = 30$)
* $J_{\text{exist}} \subset J$: Mevcut doğrulanmış resmi hastaneler kümesi ($|J_{\text{exist}}| = 20$)
* $J_{\text{cand}} \subset J$: Yeni yatırım aday lokasyonları kümesi ($|J_{\text{cand}}| = 10$)
* $d_i$: $i$ bölgesinin yıllık acil servis başvuru talebi (Adet/Yıl, $\text{Nüfus}_i \times 0.35$)
* $C_j$: $j$ tesisinin yıllık acil servis kabul kapasitesi (Adet/Yıl)
* $F_j$: $j$ aday sahasının toplam yatırım ve kamulaştırma maliyeti (Milyon TL)
* $T_{ij}(t)$: $i$ bölgesi ile $j$ tesisi arasında $t$ saatindeki seyahat süresi (Dakika)
* $p$: Açılması hedeflenen maksimum yeni aday tesis sayısı (Bütçe kısıtı)
* $w_1, w_2$: Seyahat süresi ve yatırım maliyeti ağırlıkları ($w_1 + w_2 = 1.0, \; w_1, w_2 \ge 0$)
* $M$: Karşılanamayan talep ceza katsayısı ($M = 1000.0$)

---

## 2. Karar Değişkenleri

* $y_j \in \{0, 1\}$: $j \in J_{\text{cand}}$ aday tesisinin açılıp açılmayacağı (1: Aç, 0: Açma). Mevcut tesisler için $y_j = 1$ sabittir.
* $x_{ij} \in [0, 1]$: $i$ bölgesinin sağlık talebinin $j$ tesisine tahsis edilen oranı.
* $u_i \in [0, 1]$: $i$ bölgesinin kapasite yetersizliği nedeniyle açıkta kalan (karşılanamayan) talep oranı.

---

## 3. Amaç Fonksiyonu

$$\min Z = w_1 \cdot \left(\frac{\sum_{i \in I} \sum_{j \in J} d_i \cdot T_{ij}(t) \cdot x_{ij}}{\text{NormTime}}\right) + w_2 \cdot \left(\frac{\sum_{j \in J_{\text{cand}}} F_j \cdot y_j}{\text{NormCost}}\right) + M \cdot \sum_{i \in I} u_i$$

* $\text{NormTime} = \sum_{i \in I} d_i \times 45.0$: Seyahat süresini normalize eden sabit (45 dakika baz süre).
* $\text{NormCost} = \sum_{j \in J_{\text{cand}}} F_j$: Maksimum yatırım bütçesi normalizasyon sabiti.

---

## 4. Kısıtlar

1. **Elastik Talep Korunumu:**
   $$\sum_{j \in J} x_{ij} + u_i = 1 \quad \forall i \in I$$
   *Her bölgenin talebi ya açık bir hastaneye atanır ya da açıkta kalan talep ($u_i$) olarak raporlanır.*

2. **Açık Tesis Mantıksal Bağı:**
   $$x_{ij} \le y_j \quad \forall i \in I, \; \forall j \in J_{\text{cand}}$$
   *Yalnızca inşa edilen ve açılan aday tesislere hasta yönlendirilebilir.*

3. **Kapasite ve Yatak Üst Sınırı:**
   $$\sum_{i \in I} d_i \cdot x_{ij} \le C_j \cdot y_j \quad \forall j \in J$$
   *Bir hastaneye tahsis edilen toplam yıllık acil servis yükü, tesisin fiziki kapasitesini ($C_j$) aşamaz.*

4. **Yatırım Adet Sınırı:**
   $$\sum_{j \in J_{\text{cand}}} y_j = p$$
   *Açılacak yeni hastane sayısı bütçelenen $p$ adedine tam uymalıdır.*

5. **Değişken Alanları:**
   $$y_j \in \{0, 1\}, \quad 0 \le x_{ij} \le 1, \quad 0 \le u_i \le 1$$
