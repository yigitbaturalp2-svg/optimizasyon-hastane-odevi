"""
ANKARA SAĞLIKNET - Matematiksel, Mantıksal ve Entegrasyon Doğrulama Test Paketi
TEKNİK GÖREV 001.3 Kapsamı:
1. Tesis uygunluğu ve rol ayrımı (Hastane vs Acil Müdahale Üssü)
2. Gerçek veri tutarlılığı (5.57M nüfus, 1.9495M talep)
3. Lexicographic Aşama 1 / Aşama 2 hata ve izolasyon denetimi
4. Kesirli tahsis muhasebesi ve gruplama (ezilme kaybı olmaması)
5. Ulaşım motoru (NoRoute vs ServiceError, metadata)
6. Parasal bütçe (BUDGET_LIMIT) ve tesis adedi (EXACT_COUNT vs MAX_COUNT)
7. Sıfır talep / sıfır tesis ve tanımsız ortalama süre denetimi
8. Deterministik tekrarlanabilirlik
"""

import pytest
import pulp
from unittest.mock import patch
from core.models import (
    DemandZone, Facility, FacilityType, DataStatus, OptimizationScenario,
    CandidateSelectionMode, is_eligible_for_hospital_optimization,
    is_verified_comprehensive_hospital
)
from core.optimizer import solve_elastic_cflp
from core.routing import (
    is_valid_travel_time, try_osrm_route, build_travel_matrix,
    RoutingMode, RouteResultStatus
)
from core.metrics import compare_scenarios, group_zone_allocations
from data import (
    get_verified_facilities, get_candidate_facilities, get_demand_zones,
    get_eligible_candidate_hospitals, get_candidate_emergency_posts, get_all_facilities
)


# =============================================================================
# 1. TEMEL CFLP KISIT VE ÇÖZÜCÜ TESTLERİ
# =============================================================================

def test_closed_facility_receives_zero_demand():
    """Kural: Açılmayan (y_j = 0) aday hastane kesinlikle hasta kabul edemez."""
    demands = [DemandZone("D1", "Semt 1", "İlçe 1", 39.9, 32.8, 100000, 35000, "Test")]
    candidates = [
        Facility("C1", "Aday 1 (Yakın)", "İlçe 1", 39.91, 32.81, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 100000, 500.0, "Test", 0.5, False,
                 can_receive_hospital_transfer=True),
        Facility("C2", "Aday 2 (Uzak)", "İlçe 2", 39.50, 32.20, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 100000, 500.0, "Test", 0.5, False,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="Test", description="Test", p_candidates=1,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, candidates, scenario)

    assert res["success"] is True
    assert len(res["selected_candidate_ids"]) == 1
    assert "C1" in res["selected_candidate_ids"]
    assert "C2" not in res["selected_candidate_ids"]

    c2_alloc = res["facility_allocated_demand"].get("C2", 0.0)
    assert c2_alloc == 0.0


def test_capacity_limit_strictly_enforced():
    """Kural: Bir tesise atanan talep, o tesisin acil kapasitesini aşamaz."""
    demands = [DemandZone("D1", "Büyük Semt", "İlçe 1", 39.9, 32.8, 200000, 80000, "Test")]
    facilities = [
        Facility("F1", "Küçük Tesis", "İlçe 1", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 100, 50000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="CapacityTest", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0,
        enable_capacity_limits=True
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    assert res["facility_allocated_demand"]["F1"] <= 50000.0 + 1e-3
    assert res["unmet_demand_total"] == pytest.approx(30000.0, abs=1.0)
    assert res["has_unmet_demand"] is True


def test_unmet_demand_reported_when_capacity_insufficient():
    """Kural: Kapasite yetersizliğinde açıkta kalan talep şeffafça u_i olarak raporlanmalıdır."""
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 100000, 40000, "Test")]
    facilities = [
        Facility("F1", "Yetersiz Tesis", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 50, 15000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="UnmetTest", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["has_unmet_demand"] is True
    assert len(res["unmet_zones"]) == 1
    assert res["unmet_zones"][0]["zone_id"] == "D1"
    assert res["unmet_zones"][0]["unmet_annual_demand"] == pytest.approx(25000, abs=1)


def test_budget_constraint_exact_p_selected():
    """Kural: Açılan yeni aday tesis sayısı bütçe kısıtı p'ye tam olarak uymalıdır."""
    candidates = get_eligible_candidate_hospitals()
    demands = get_demand_zones()

    for target_p in [1, 3, 5]:
        scenario = OptimizationScenario(
            name=f"Budget_{target_p}", description="Test", p_candidates=target_p,
            weight_travel_time=0.7, weight_investment_cost=0.3
        )
        res = solve_elastic_cflp(demands, candidates, scenario)
        assert res["success"] is True
        assert len(res["selected_candidate_ids"]) == target_p


def test_scenarios_produce_different_solutions():
    """Kural: Seyahat öncelikli senaryo ile bütçe tasarruf senaryosu farklı tesisleri seçmelidir."""
    all_facilities = get_all_facilities()
    demands = get_demand_zones()

    scen_travel = OptimizationScenario(
        name="TravelPriority", description="Hızlı Ulaşım", p_candidates=3,
        weight_travel_time=0.90, weight_investment_cost=0.10
    )
    res_travel = solve_elastic_cflp(demands, all_facilities, scen_travel)

    scen_cost = OptimizationScenario(
        name="CostPriority", description="Düşük Maliyet", p_candidates=3,
        weight_travel_time=0.10, weight_investment_cost=0.90
    )
    res_cost = solve_elastic_cflp(demands, all_facilities, scen_cost)

    assert res_travel["success"] is True
    assert res_cost["success"] is True
    assert set(res_travel["selected_candidate_ids"]) != set(res_cost["selected_candidate_ids"])
    assert res_travel["avg_travel_time_min"] <= res_cost["avg_travel_time_min"]
    assert res_cost["total_investment_cost_million_tl"] <= res_travel["total_investment_cost_million_tl"]


def test_toy_cflp_analytical_optimum():
    """Kural: 3 noktalı analitik örnekte beklenen global optimum bulunmalıdır."""
    demands = [
        DemandZone("D1", "Semt 1", "İlçe", 39.90, 32.80, 100000, 35000, "Test"),
        DemandZone("D2", "Semt 2", "İlçe", 39.60, 32.20, 200000, 70000, "Test")
    ]
    candidates = [
        Facility("C1", "Tesis 1", "İlçe", 39.91, 32.81, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 200000, 500.0, "Test", 0.5, False,
                 can_receive_hospital_transfer=True),
        Facility("C2", "Tesis 2", "İlçe", 39.61, 32.21, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 200000, 500.0, "Test", 0.5, False,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="Toy", description="Toy", p_candidates=1,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, candidates, scenario)

    assert res["success"] is True
    assert res["selected_candidate_ids"] == ["C2"]


def test_elastic_conservation_of_demand():
    """Kural: Tüm bölgeler için atanan fraksiyonlar ve u_i toplamı tam 1.0 olmalıdır."""
    demands = get_demand_zones()[:5]
    facilities = get_verified_facilities()[:3]

    scenario = OptimizationScenario(
        name="ConservationTest", description="Test", p_candidates=0,
        weight_travel_time=0.8, weight_investment_cost=0.2
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    for d in demands:
        assigned_frac = sum(
            a["allocation_fraction"] for a in res["assignments"] if a["demand_id"] == d.id
        )
        unmet_info = next((u for u in res["unmet_zones"] if u["zone_id"] == d.id), None)
        unmet_frac = unmet_info["unmet_fraction"] if unmet_info else 0.0
        assert (assigned_frac + unmet_frac) == pytest.approx(1.0, abs=1e-3)


def test_demand_and_facility_ids_remain_immutable_after_optimization():
    """Nesne kimliklerinin optimizasyon sürecinde asla mutasyona uğramadığını doğrular."""
    demands = [
        DemandZone("D_ZONE_100", "Bölge 100", "İlçe A", 39.9, 32.8, 50000, 17500, "Test"),
        DemandZone("D_ZONE_200", "Bölge 200", "İlçe B", 39.8, 32.7, 80000, 28000, "Test")
    ]
    facilities = [
        Facility("FAC_HOSP_01", "Hastane 1", "İlçe A", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 200, 100000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True),
        Facility("FAC_CAND_02", "Aday 2", "İlçe B", 39.82, 32.72, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 400, 150000, 400.0, "Test", 0.5, False,
                 can_receive_hospital_transfer=True)
    ]

    original_demand_ids = [d.id for d in demands]
    original_facility_ids = [f.id for f in facilities]

    scenario = OptimizationScenario(
        name="ImmutabilityCheck", description="Test", p_candidates=1,
        weight_travel_time=0.5, weight_investment_cost=0.5
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    assert [d.id for d in demands] == original_demand_ids
    assert [f.id for f in facilities] == original_facility_ids


# =============================================================================
# 2. TEKNİK GÖREV 001.3 ÖZEL ENTEGRASYON TESTLERİ (15 ZORUNLU TEST)
# =============================================================================

def test_emergency_posts_cannot_be_selected_for_hospital_transfers():
    """
    ENTEGRASYON TESTİ 1 (KRİTİK 1):
    CAND_02, CAND_06, CAND_08, CAND_10 gibi acil müdahale üsleri (ADAY_ACIL_USSU)
    genel hastane nakil optimizasyonunda hastane olarak SEÇİLEMEZ ve hasta kabul hedefi olamaz.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 50000, 17500, "Test")]
    all_cands = get_candidate_facilities()  # 10 adet aday (6 hastane + 4 acil üssü)

    scenario = OptimizationScenario(
        name="PostTest", description="Test", p_candidates=6,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, all_cands, scenario)

    assert res["success"] is True
    # Seçilen tesisler içinde acil üsleri kesinlikle bulunamaz
    excluded_post_ids = {"CAND_02", "CAND_06", "CAND_08", "CAND_10"}
    selected = set(res["selected_candidate_ids"])
    assert selected.isdisjoint(excluded_post_ids), f"Acil üssü hastane olarak seçildi: {selected.intersection(excluded_post_ids)}"
    # Yalnızca uygun sağlık kampüsleri seçilebilir
    assert len(selected) == 6


def test_verified_existing_hospitals_pass_eligibility():
    """
    ENTEGRASYON TESTİ 2:
    Mevcut doğrulanmış 20 resmi kamu hastanesinin tamamı can_receive_hospital_transfer=True
    olarak uygunluk doğrulamasından geçmelidir.
    """
    verified = get_verified_facilities()
    assert len(verified) == 20
    for h in verified:
        assert h.can_receive_hospital_transfer is True
        assert is_eligible_for_hospital_optimization(h) is True
        assert h.is_existing is True


def test_missing_capability_not_defaulted_to_true():
    """
    ENTEGRASYON TESTİ 3:
    can_receive_hospital_transfer alanı belirtilmemiş veya False olan tesisler
    varsayılan olarak hastane kabul edilemez.
    """
    f_raw = Facility(
        id="RAW_01", name="Bilinmeyen Tesis", district="Mamak", lat=39.9, lon=32.8,
        status=DataStatus.CANDIDATE_INVESTMENT, facility_type=FacilityType.ADAY_SAGLIK_KAMPUSU,
        bed_capacity=100, annual_emergency_capacity=50000, investment_cost_million_tl=100.0,
        source="Test"
    )
    assert f_raw.can_receive_hospital_transfer is False
    assert is_eligible_for_hospital_optimization(f_raw) is False


def test_candidate_hospital_pool_count():
    """
    ENTEGRASYON TESTİ 4:
    Aday sayısı uygun hastane adaylarından (6 adet) hesaplanmalıdır.
    10 aday varken tam 7 hastane istendiğinde EXACT_COUNT kuralı başarısız olmalıdır.
    """
    all_cands = get_candidate_facilities()
    eligible_cands = get_eligible_candidate_hospitals()
    assert len(all_cands) == 10
    assert len(eligible_cands) == 6

    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 50000, 17500, "Test")]
    # 7 hastane isteniyor, ancak yalnızca 6 uygun hastane adayı var
    scenario_p7 = OptimizationScenario(
        name="PoolCountTest", description="Test", p_candidates=7,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, all_cands, scenario_p7)

    assert res["success"] is False
    assert res["status"] == "Infeasible_Candidate_Count"


def test_population_and_demand_data_consistency():
    """
    ENTEGRASYON TESTİ 5 (KRİTİK 2):
    32 talep bölgesindeki toplam nüfus tam olarak 5.570.000 olmalı;
    yıllık acil talep 1.949.500 olmalı ve kişi başı 0.35 katsayısı tam tutmalıdır.
    """
    demands = get_demand_zones()
    assert len(demands) == 32

    tot_pop = sum(d.population for d in demands)
    tot_dem = sum(d.annual_emergency_demand for d in demands)

    assert tot_pop == 5570000, f"Nüfus toplamı çelişiyor: {tot_pop} != 5570000"
    assert tot_dem == 1949500, f"Yıllık talep toplamı çelişiyor: {tot_dem} != 1949500"
    assert tot_dem == pytest.approx(tot_pop * 0.35, abs=1e-3)


def test_stage1_invalid_or_none_aborts_stage2():
    """
    ENTEGRASYON TESTİ 6 (KRİTİK 3):
    Aşama 1 amaç fonksiyonu None, geçersiz veya optimal olmayan durumdayken
    Aşama 2 ASLA başlatılmamalıdır.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 50000, 17500, "Test")]
    facilities = [
        Facility("F1", "Tesis", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 100, 50000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="Stage1Abort", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0,
        use_lexicographic=True
    )

    with patch.object(pulp.LpProblem, "solve", return_value=-1) as mock_solve:
        res = solve_elastic_cflp(demands, facilities, scenario)
        assert mock_solve.call_count == 1
        assert res["success"] is False
        assert "Stage1_Failed" in res["status"]


def test_stage2_failure_reported_as_failure():
    """
    ENTEGRASYON TESTİ 7:
    Aşama 1 başarılı olsa bile Aşama 2 çözücüsü başarısız olursa
    sistem asla başarı (success=True) üretmemelidir.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 50000, 17500, "Test")]
    facilities = [
        Facility("F1", "Tesis", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 100, 50000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="Stage2Fail", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0,
        use_lexicographic=True
    )

    def mock_solve_custom(self, *args, **kwargs):
        if "Stage1" in self.name:
            for v in self.variables():
                v.varValue = 0.0
            return 1
        elif "Stage2" in self.name:
            return -1  # Infeasible
        return 1

    with patch.object(pulp.LpProblem, "solve", mock_solve_custom):
        res = solve_elastic_cflp(demands, facilities, scenario)
        assert res["success"] is False
        assert "Stage2_Failed" in res["status"]


def test_small_fractional_allocations_not_discarded():
    """
    ENTEGRASYON TESTİ 8:
    Küçük kesirli tahsisler (örneğin 1e-5 gibi) keyfi bir filtreyle atılmamalı;
    muhasebe dengesinde korunmalıdır.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 100000, 35000, "Test")]
    facilities = [
        Facility("F1", "Hastane 1", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 500, 34999, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True),
        Facility("F2", "Hastane 2", "İlçe", 39.92, 32.82, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 500, 10000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="SmallFractionTest", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    # F2'ye yalnızca 1 birimlik çok küçük bir pay düşse dahi kaydedilmelidir
    alloc_sum = sum(a["allocated_demand"] for a in res["assignments"])
    unmet = res["unmet_demand_total"]
    assert (alloc_sum + unmet) == pytest.approx(35000.0, abs=1e-2)


def test_grouped_zone_allocations_handle_multi_hospital_splits():
    """
    ENTEGRASYON TESTİ 9 (KRİTİK 4):
    Bir talep bölgesi birden fazla hastaneye bölündüğünde (kesirli tahsis),
    karşılaştırma motoru tekil sözlük ezilmesi yapmamalı; ağırlıklı ortalama süreyi tam hesaplamalıdır.
    """
    demands = [DemandZone("D1", "Bölünmüş Semt", "İlçe", 39.9, 32.8, 100000, 40000, "Test")]
    # İki hastane: H1 (10 dk, kapasite 20.000), H2 (20 dk, kapasite 20.000)
    # D1 her ikisine de tam 20.000 bölünecektir. Ağırlıklı süre: (10*20000 + 20*20000)/40000 = 15.0 dk
    facilities = [
        Facility("H1", "Hastane 1", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 100, 20000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True),
        Facility("H2", "Hastane 2", "İlçe", 40.05, 32.95, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 100, 20000, 0.0, "Test", 1.0, True,
                 can_receive_hospital_transfer=True)
    ]
    scenario = OptimizationScenario(
        name="SplitTest", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    assert len(res["assignments"]) == 2  # Her iki hastaneye de tahsis vardır

    # group_zone_allocations fonksiyonunu test et
    groups = group_zone_allocations(res)
    assert "D1" in groups
    assert groups["D1"]["total_allocated_demand"] == pytest.approx(40000.0, abs=1.0)
    assert len(groups["D1"]["facility_allocations"]) == 2

    # Ağırlıklı ortalama süre iki hastanenin ortasında olmalıdır
    t1 = res["assignments"][0]["travel_time_min"]
    t2 = res["assignments"][1]["travel_time_min"]
    expected_weighted = (t1 + t2) / 2.0
    assert groups["D1"]["weighted_avg_travel_time_min"] == pytest.approx(expected_weighted, abs=0.2)


def test_routing_noroute_timeout_nan_inf_handled_distinctly():
    """
    ENTEGRASYON TESTİ 10 (KRİTİK 5):
    OSRM'de NoRoute (fiziksel bağlantı yok) durumu ile ServiceError durumu
    kesinlikle ayrılır ve sonsuz/NaN süreler geçerli kabul edilmez.
    """
    assert is_valid_travel_time(None) is False
    assert is_valid_travel_time(float('inf')) is False
    assert is_valid_travel_time(float('nan')) is False
    assert is_valid_travel_time(-5.0) is False
    assert is_valid_travel_time(15.5) is True

    # OSRM servisi kapalı veya NoRoute iken dönüş durumlarını sına
    with patch("urllib.request.urlopen", side_effect=OSError("Network unreachable")):
        status, dist, dur = try_osrm_route(39.9, 32.8, 40.0, 32.9)
        assert status == RouteResultStatus.SERVICE_ERROR
        assert dist is None
        assert dur is None


def test_geometric_routing_metadata_declares_simulation():
    """
    ENTEGRASYON TESTİ 11:
    Geometrik ulaşım modunun ürettiği seyahat matrisi, simülasyon varsayımı
    ve saatlik trafik profili olduğunu metadata'da açıkça belirtmelidir.
    """
    demands = get_demand_zones()[:2]
    facilities = get_verified_facilities()[:2]

    time_mat, dist_mat, meta = build_travel_matrix(
        demands, facilities, hour=18, routing_mode=RoutingMode.ESTIMATED_GEOMETRIC
    )

    assert meta["is_simulated"] is True
    assert meta["routing_mode"] == RoutingMode.ESTIMATED_GEOMETRIC.value
    assert "18:00" in meta["traffic_profile_label"]
    assert meta["traffic_multiplier"] > 1.5  # Akşam zirve trafiği çarpanı


def test_budget_limit_mode_strictly_respected():
    """
    ENTEGRASYON TESTİ 12 (KRİTİK 6):
    BUDGET_LIMIT modunda seçilen tesislerin toplam yatırım maliyeti,
    belirlenen bütçe tavanını (B) kesinlikle aşamaz.
    """
    candidates = get_eligible_candidate_hospitals()
    demands = get_demand_zones()

    # Bütçe = 1400 Milyon TL. En ucuz tesisler 680 ve 690'dır. İki tesis yaklaşık 1370 M TL eder.
    budget_cap = 1400.0
    scenario = OptimizationScenario(
        name="BudgetCapTest", description="Test",
        candidate_selection_mode=CandidateSelectionMode.BUDGET_LIMIT,
        max_investment_budget_million_tl=budget_cap,
        weight_travel_time=0.5, weight_investment_cost=0.5
    )
    res = solve_elastic_cflp(demands, candidates, scenario)

    assert res["success"] is True
    assert res["total_investment_cost_million_tl"] <= budget_cap + 1e-3


def test_exact_count_vs_max_count_semantics():
    """
    ENTEGRASYON TESTİ 13:
    EXACT_COUNT tam p adet açarken, MAX_COUNT en fazla p adet açabilir.
    """
    candidates = get_eligible_candidate_hospitals()
    demands = get_demand_zones()

    # EXACT_COUNT: p=3 istendiğinde tam 3 adet seçilmelidir
    scen_exact = OptimizationScenario(
        name="Exact3", description="Test",
        candidate_selection_mode=CandidateSelectionMode.EXACT_COUNT,
        p_candidates=3, weight_travel_time=0.8, weight_investment_cost=0.2
    )
    res_exact = solve_elastic_cflp(demands, candidates, scen_exact)
    assert res_exact["success"] is True
    assert len(res_exact["selected_candidate_ids"]) == 3

    # MAX_COUNT: p=5 istendiğinde en fazla 5 tesis seçilebilir
    scen_max = OptimizationScenario(
        name="Max5", description="Test",
        candidate_selection_mode=CandidateSelectionMode.MAX_COUNT,
        p_candidates=5, weight_travel_time=0.8, weight_investment_cost=0.2
    )
    res_max = solve_elastic_cflp(demands, candidates, scen_max)
    assert res_max["success"] is True
    assert len(res_max["selected_candidate_ids"]) <= 5


def test_unserved_demand_has_undefined_travel_time():
    """
    ENTEGRASYON TESTİ 14:
    Hiçbir talebin karşılanmadığı (sıfır tesis veya ulaşılamazlık) durumlarda
    ortalama seyahat süresi 0.0 yerine None (tanımsız) dönmelidir.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 10000, 3500, "Test")]
    facilities = []

    scenario = OptimizationScenario(
        name="ZeroFac", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    assert res["avg_travel_time_min"] is None
    assert res["unmet_percentage"] == 100.0


def test_deterministic_reproducibility():
    """
    ENTEGRASYON TESTİ 15:
    Aynı girdilerle tekrar çalıştırılan senaryo deterministik olarak
    tamamen aynı amaç fonksiyonu ve seçilen tesisleri üretmelidir.
    """
    demands = get_demand_zones()[:10]
    facilities = get_all_facilities()

    scenario = OptimizationScenario(
        name="ReproducibilityTest", description="Test", p_candidates=2,
        weight_travel_time=0.7, weight_investment_cost=0.3
    )

    res1 = solve_elastic_cflp(demands, facilities, scenario)
    res2 = solve_elastic_cflp(demands, facilities, scenario)

    assert res1["success"] is True
    assert res2["success"] is True
    assert res1["selected_candidate_ids"] == res2["selected_candidate_ids"]
    assert res1["objective_value"] == res2["objective_value"]
    assert res1["unmet_demand_total"] == res2["unmet_demand_total"]
