# ANKARA SAĞLIKNET — KALİTE GÜVENCE VE DOĞRULAMA RAPORU (QA REPORT)
**Doküman Kodu:** DOC-QA-001  
**Test Çalıştırma Tarihi:** 27 Ekim 2026  
**Test Çerçevesi:** Pytest 9.1.1  
**Python Sürümü:** 3.14.0 (Windows 64-bit)  

---

## 1. Birim Test Özeti

Test edilen dosya: `tests/test_cflp_engine.py`  
Sonuç: **7 Test Çalıştırıldı — 7 Başarılı (%100 Başarı Oranı) — 0 Başarısız**  
Çalışma Süresi: **0.74 saniye**

```
tests/test_cflp_engine.py::test_closed_facility_receives_zero_demand PASSED          [ 14%]
tests/test_cflp_engine.py::test_capacity_limit_strictly_enforced PASSED             [ 28%]
tests/test_cflp_engine.py::test_unmet_demand_reported_when_capacity_insufficient PASSED [ 42%]
tests/test_cflp_engine.py::test_budget_constraint_exact_p_selected PASSED             [ 57%]
tests/test_cflp_engine.py::test_scenarios_produce_different_solutions PASSED        [ 71%]
tests/test_cflp_engine.py::test_toy_cflp_analytical_optimum PASSED                  [ 85%]
tests/test_cflp_engine.py::test_elastic_conservation_of_demand PASSED               [100%]
```

---

## 2. Test Edilen Matematiksel Kriterler ve Doğrulama Kanıtları

### Test 1: `test_closed_facility_receives_zero_demand`
* **Amaç:** $x_{ij} \le y_j$ kısıtının çalıştığını ve açılmayan adaya ($y_j = 0$) kesinlikle hasta yönlendirilmediğini sınamak.
* **Sonuç:** PASSED. Seçilmeyen `C2` tesisine yönlendirilen talep $0.0$ olarak doğrulandı.

### Test 2: `test_capacity_limit_strictly_enforced`
* **Amaç:** $\sum_i d_i x_{ij} \le C_j y_j$ kısıtının aşılmadığını sınamak.
* **Test Senaryosu:** 80,000 talep, 50,000 kapasiteli tesis.
* **Sonuç:** PASSED. Tesis tam 50,000 talep aldı, kalan 30,000 talep elastik açıkta kalan talep ($u_i$) olarak ayrıldı.

### Test 3: `test_unmet_demand_reported_when_capacity_insufficient`
* **Amaç:** Kapasite yetersizliğinde çözücünün çökmeyip açıkta kalan nüfusu ekrana bildirdiğini sınamak.
* **Sonuç:** PASSED. `has_unmet_demand == True` ve açıkta kalan yıllık talep 25,000 adet olarak raporlandı.

### Test 4: `test_budget_constraint_exact_p_selected`
* **Amaç:** $\sum_{j \in \text{Cand}} y_j = p$ kısıtının tam $p$ adet tesis açtığını sınamak.
* **Sonuç:** PASSED. $p \in \{1, 3, 5\}$ için tam $1, 3, 5$ aday tesis seçildi.

### Test 5: `test_scenarios_produce_different_solutions`
* **Amaç:** Seyahat öncelikli ($w_1=0.9, w_2=0.1$) ve bütçe öncelikli ($w_1=0.1, w_2=0.9$) iki senaryonun farklı tesis kümeleri seçtiğini doğrulamak.
* **Sonuç:** PASSED. Seyahat öncelikli senaryo `['CAND_01', 'CAND_02', 'CAND_10']` seçerken bütçe öncelikli senaryo en ucuz arazileri barındıran `['CAND_06', 'CAND_08', 'CAND_10']` tesislerini seçti.

### Test 6: `test_toy_cflp_analytical_optimum`
* **Amaç:** Analitik global optimumu bilinen 2 talep - 2 adaylı problemde çözücünün doğruluğunu denetlemek.
* **Sonuç:** PASSED. Büyük nüfuslu D2 bölgesine yakın olan `C2` tesisi seçildi.

### Test 7: `test_elastic_conservation_of_demand`
* **Amaç:** Tüm bölgeler için $\sum_j x_{ij} + u_i = 1.0$ eşitliğinin korunduğunu doğrulamak.
* **Sonuç:** PASSED. Tüm talep bölgelerinde hata payı $< 10^{-5}$ olarak doğrulandı.
