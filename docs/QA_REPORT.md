# ANKARA SAĞLIKNET — KALİTE GÜVENCE VE DOĞRULAMA RAPORU (QA REPORT)
**Doküman Kodu:** DOC-QA-001  
**Test Çalıştırma Tarihi:** 28 Ekim 2026  
**Test Çerçevesi:** Pytest 9.1.1  
**Python Sürümü:** 3.14.0 (Windows 64-bit)  
**Sürüm:** v1.2.0-verified (TEKNİK GÖREV 001.3 Kapsamı)  

---

## 1. Test Özeti

* **Test Edilen Dosya:** `tests/test_cflp_engine.py`  
* **Toplam Test Sayısı:** **23 Test** (8 Temel CFLP + 15 Özel Entegrasyon Testi)  
* **Sonuç:** **23 BAŞARILI (%100 Başarı Oranı) — 0 BAŞARISIZ**  
* **Çalışma Süresi:** **1.54 saniye**  
* **Gerçek Log Dosyası:** `docs/pytest_output.txt`

```text
tests/test_cflp_engine.py::test_closed_facility_receives_zero_demand PASSED                          [  4%]
tests/test_cflp_engine.py::test_capacity_limit_strictly_enforced PASSED                             [  8%]
tests/test_cflp_engine.py::test_unmet_demand_reported_when_capacity_insufficient PASSED            [ 13%]
tests/test_cflp_engine.py::test_budget_constraint_exact_p_selected PASSED                        [ 17%]
tests/test_cflp_engine.py::test_scenarios_produce_different_solutions PASSED                   [ 21%]
tests/test_cflp_engine.py::test_toy_cflp_analytical_optimum PASSED                                  [ 26%]
tests/test_cflp_engine.py::test_elastic_conservation_of_demand PASSED                              [ 30%]
tests/test_cflp_engine.py::test_demand_and_facility_ids_remain_immutable_after_optimization PASSED   [ 34%]
tests/test_cflp_engine.py::test_emergency_posts_cannot_be_selected_for_hospital_transfers PASSED    [ 39%]
tests/test_cflp_engine.py::test_verified_existing_hospitals_pass_eligibility PASSED                 [ 43%]
tests/test_cflp_engine.py::test_missing_capability_not_defaulted_to_true PASSED                    [ 47%]
tests/test_cflp_engine.py::test_candidate_hospital_pool_count PASSED                                [ 52%]
tests/test_cflp_engine.py::test_population_and_demand_data_consistency PASSED                       [ 56%]
tests/test_cflp_engine.py::test_stage1_invalid_or_none_aborts_stage2 PASSED                          [ 60%]
tests/test_cflp_engine.py::test_stage2_failure_reported_as_failure PASSED                            [ 65%]
tests/test_cflp_engine.py::test_small_fractional_allocations_not_discarded PASSED                   [ 69%]
tests/test_cflp_engine.py::test_grouped_zone_allocations_handle_multi_hospital_splits PASSED        [ 73%]
tests/test_cflp_engine.py::test_routing_noroute_timeout_nan_inf_handled_distinctly PASSED          [ 78%]
tests/test_cflp_engine.py::test_geometric_routing_metadata_declares_simulation PASSED              [ 82%]
tests/test_cflp_engine.py::test_budget_limit_mode_strictly_respected PASSED                         [ 86%]
tests/test_cflp_engine.py::test_exact_count_vs_max_count_semantics PASSED                           [ 91%]
tests/test_cflp_engine.py::test_unserved_demand_has_undefined_travel_time PASSED                    [ 95%]
tests/test_cflp_engine.py::test_deterministic_reproducibility PASSED                                [100%]
```

---

## 2. TEKNİK GÖREV 001.3 Kapsamında Doğrulanan 15 Yeni Kriter

1. **Aday Acil Üssü İzolasyonu (`test_emergency_posts_cannot_be_selected_for_hospital_transfers`):**  
   `CAND_02, CAND_06, CAND_08, CAND_10` tesislerinin acil müdahale üssü olduğu ve hastane optimizasyonuna dahil edilemeyeceği kanıtlandı.
2. **Mevcut Hastanelerin Uygunluğu (`test_verified_existing_hospitals_pass_eligibility`):**  
   20 resmi hastanenin tamamının `can_receive_hospital_transfer=True` olduğu doğrulandı.
3. **Eksik Yetkinlik Güvenliği (`test_missing_capability_not_defaulted_to_true`):**  
   Yetkinlik alanı belirtilmeyen veya False olan hiçbir tesisin hastane sayılmayacağı kanıtlandı.
4. **Aday Tesis Sayısı Havuzu (`test_candidate_hospital_pool_count`):**  
   Havuzun 10 değil tam 6 aday hastaneden oluştuğu, $p=7$ istendiğinde `Infeasible_Candidate_Count` ile reddedildiği doğrulandı.
5. **Nüfus ve Talep Tutarlılığı (`test_population_and_demand_data_consistency`):**  
   32 bölgede 5,570,000 nüfus, 1,949,500 yıllık talep ve 0.35 katsayısı doğrulandı.
6. **Aşama 1 Hata İzolasyonu (`test_stage1_invalid_or_none_aborts_stage2`):**  
   Aşama 1 çözülemediğinde Aşama 2'nin kesinlikle başlatılmadığı mock ile kanıtlandı.
7. **Aşama 2 Başarısızlık Raporlaması (`test_stage2_failure_reported_as_failure`):**  
   Aşama 2 başarısız olduğunda sistemin hata durumunu koruduğu kanıtlandı.
8. **Küçük Kesirli Tahsisler (`test_small_fractional_allocations_not_discarded`):**  
   $10^{-5}$ gibi küçük kesirli tahsislerin muhasebeden düşmediği kanıtlandı.
9. **Gruplanmış Tahsis ve Karşılaştırma (`test_grouped_zone_allocations_handle_multi_hospital_splits`):**  
   Aynı bölgenin birden fazla hastaneye bölünmesi durumunda veri kaybı olmadan ağırlıklı ortalama sürenin hesaplandığı doğrulandı.
10. **OSRM Ulaşım Güvenliği (`test_routing_noroute_timeout_nan_inf_handled_distinctly`):**  
    `NoRoute`, `SERVICE_ERROR`, `inf` ve `nan` değerlerinin birbirinden ayrıldığı kanıtlandı.
11. **Ulaşım Metadatası (`test_geometric_routing_metadata_declares_simulation`):**  
    Geometrik modelin simülasyon olduğunu ve saatlik trafik profili kullandığını beyan ettiği doğrulandı.
12. **Parasal Bütçe Sınırı (`test_budget_limit_mode_strictly_respected`):**  
    `BUDGET_LIMIT` modunda yatırım maliyetinin $B$ tavanını aşmadığı kanıtlandı.
13. **EXACT_COUNT vs MAX_COUNT (`test_exact_count_vs_max_count_semantics`):**  
    Tam $p$ seçimi ile en fazla $p$ seçimi farkı doğrulandı.
14. **Tanımsız Süre Denetimi (`test_unserved_demand_has_undefined_travel_time`):**  
    Hizmet verilemeyen durumda ortalama sürenin `None` olduğu kanıtlandı.
15. **Deterministik Tekrarlanabilirlik (`test_deterministic_reproducibility`):**  
    Aynı girdilerle çalıştırılan senaryoların özdeş sonuçlar verdiği kanıtlandı.
