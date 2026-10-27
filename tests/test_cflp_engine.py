"""
ANKARA SAĞLIKNET - Matematiksel ve Mantıksal Doğrulama Test Paketi
Bu dosya, CFLP optimizasyon motorunun tüm kısıt, varsayım ve güvenlik kapılarını sınar.
"""

import pytest
import pulp
from unittest.mock import patch
from core.models import (
    DemandZone, Facility, FacilityType, DataStatus, OptimizationScenario,
    is_verified_comprehensive_hospital
)
from core.optimizer import solve_elastic_cflp
from core.routing import is_valid_travel_time
from data import get_verified_facilities, get_candidate_facilities, get_demand_zones


def test_closed_facility_receives_zero_demand():
    """Kural: Açılmayan (y_j = 0) tesis kesinlikle hasta kabul edemez."""
    demands = [DemandZone("D1", "Semt 1", "İlçe 1", 39.9, 32.8, 100000, 35000, "Test")]
    candidates = [
        Facility("C1", "Aday 1 (Yakın)", "İlçe 1", 39.91, 32.81, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 100000, 500.0, "Test", 0.5, False),
        Facility("C2", "Aday 2 (Uzak)", "İlçe 2", 39.50, 32.20, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 100000, 500.0, "Test", 0.5, False)
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
                 FacilityType.DEVLET_HASTANESI, 100, 50000, 0.0, "Test", 1.0, True)
    ]
    scenario = OptimizationScenario(
        name="CapacityTest", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0,
        enable_capacity_limits=True
    )
    res = solve_elastic_cflp(demands, facilities, scenario)
    
    assert res["success"] is True
    assert res["facility_allocated_demand"]["F1"] <= 50000.0
    assert res["unmet_demand_total"] == pytest.approx(30000.0, abs=1.0)
    assert res["has_unmet_demand"] is True


def test_unmet_demand_reported_when_capacity_insufficient():
    """Kural: Kapasite yetersizliğinde açıkta kalan talep şeffafça u_i olarak raporlanmalıdır."""
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 100000, 40000, "Test")]
    facilities = [
        Facility("F1", "Yetersiz Tesis", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 50, 15000, 0.0, "Test", 1.0, True)
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
    candidates = get_candidate_facilities()
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
    from data import get_all_facilities
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
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 200000, 500.0, "Test", 0.5, False),
        Facility("C2", "Tesis 2", "İlçe", 39.61, 32.21, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 500, 200000, 500.0, "Test", 0.5, False)
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


# =============================================================================
# TEKNİK GÖREV 001.2-R1 VE TESLİMAT DOĞRULAMA YENİ GÜVENLİK TESTLERİ
# =============================================================================

def test_demand_and_facility_ids_remain_immutable_after_optimization():
    """
    KRİTİK 1 REGRESYON TESTİ:
    Optimizasyon fonksiyonu çalıştırıldığında girdi nesnelerinin (.id vb.) alanları
    kesinlikle mutasyona uğramamalıdır.
    """
    demands = [
        DemandZone("D_ZONE_100", "Bölge 100", "İlçe A", 39.9, 32.8, 50000, 17500, "Test"),
        DemandZone("D_ZONE_200", "Bölge 200", "İlçe B", 39.8, 32.7, 80000, 28000, "Test")
    ]
    facilities = [
        Facility("FAC_HOSP_01", "Hastane 1", "İlçe A", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 200, 100000, 0.0, "Test", 1.0, True),
        Facility("FAC_CAND_02", "Aday 2", "İlçe B", 39.82, 32.72, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 400, 150000, 400.0, "Test", 0.5, False)
    ]

    original_demand_ids = [d.id for d in demands]
    original_facility_ids = [f.id for f in facilities]

    scenario = OptimizationScenario(
        name="ImmutabilityCheck", description="Test", p_candidates=1,
        weight_travel_time=0.5, weight_investment_cost=0.5
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True

    # Optimizasyon sonrası ID değerlerinin bozulmadığını doğrula
    current_demand_ids = [d.id for d in demands]
    current_facility_ids = [f.id for f in facilities]

    assert current_demand_ids == original_demand_ids
    assert current_facility_ids == original_facility_ids
    assert demands[0].id == "D_ZONE_100"
    assert demands[1].id == "D_ZONE_200"
    assert facilities[0].id == "FAC_HOSP_01"
    assert facilities[1].id == "FAC_CAND_02"


def test_zero_facilities_yields_valid_100pct_unmet_demand_solution():
    """
    KRİTİK 2 TESTİ:
    Tesis olmayan senaryoda elastik CFLP çökmek veya infeasible dönmek yerine
    %100 karşılanamayan talep (u_i = 1.0) ile matematiksel olarak geçerli bir çözüm üretmelidir.
    Ayrıca ortalama seyahat süresi tanımsız (None) olmalıdır.
    """
    demands = [
        DemandZone("D1", "Semt 1", "İlçe", 39.9, 32.8, 10000, 3500, "Test"),
        DemandZone("D2", "Semt 2", "İlçe", 39.8, 32.7, 20000, 7000, "Test")
    ]
    facilities = []  # Sıfır tesis!

    scenario = OptimizationScenario(
        name="ZeroFac", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    assert res["status"] == "Optimal_Zero_Facilities"
    assert res["unmet_percentage"] == 100.0
    assert res["unmet_demand_total"] == 10500
    assert res["has_unmet_demand"] is True
    assert res["avg_travel_time_min"] is None  # Sıfır hizmette seyahat süresi tanımsızdır
    assert len(res["assignments"]) == 0
    assert len(res["unmet_zones"]) == 2


def test_exact_count_validation_when_candidates_insufficient():
    """
    TESLİMAT DOĞRULAMA GÖREV 2.1:
    EXACT_COUNT kuralı: Uygun aday sayısı sıfır olsa bile istenen tesis sayısı doğrulanmalıdır.
    Aday yokken p=1 istenirse model sessiz başarı üretmemeli, açıkça reddetmelidir.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 50000, 17500, "Test")]
    # Sadece mevcut tesis var, aday tesis havuzu 0
    existing_only = [
        Facility("F1", "Mevcut", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 100, 50000, 0.0, "Test", 1.0, True)
    ]

    scenario_p1 = OptimizationScenario(
        name="ExactCount_Fail", description="Test", p_candidates=1,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, existing_only, scenario_p1)

    # Sessiz başarı OLMAMALI, Infeasible_Candidate_Count dönmeli
    assert res["success"] is False
    assert res["status"] == "Infeasible_Candidate_Count"
    assert "Aday tesis kısıtı sağlanamıyor" in res["message"]


def test_exact_count_validation_when_p_exceeds_available_candidates():
    """
    Havuzda 2 aday varken p=3 istenirse sessizce p=2'ye düşürmemeli,
    kısıt sağlanamadığı için reddetmelidir.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 50000, 17500, "Test")]
    candidates = [
        Facility("C1", "Aday 1", "İlçe", 39.91, 32.81, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 200, 50000, 200.0, "Test", 0.5, False),
        Facility("C2", "Aday 2", "İlçe", 39.92, 32.82, DataStatus.CANDIDATE_INVESTMENT,
                 FacilityType.ADAY_SAGLIK_KAMPUSU, 200, 50000, 200.0, "Test", 0.5, False)
    ]
    scenario = OptimizationScenario(
        name="ExceedTest", description="Test", p_candidates=3,
        weight_travel_time=1.0, weight_investment_cost=0.0
    )
    res = solve_elastic_cflp(demands, candidates, scenario)

    assert res["success"] is False
    assert res["status"] == "Infeasible_Candidate_Count"


def test_comprehensive_hospital_flag_defaults_to_false_and_requires_verified_type():
    """
    TESLİMAT DOĞRULAMA GÖREV 2.2:
    is_comprehensive_hospital alanı eksik olan tesisler varsayılan olarak True KABUL EDİLEMEZ.
    Açıkça is_comprehensive_hospital=True olarak işaretlenmiş ve
    geçerli bir hastane türüne sahip olması şarttır.
    """
    # 1. Alan belirtilmediğinde varsayılan değer kesinlikle False olmalıdır
    f_default = Facility(
        id="T1", name="Normal Devlet", district="Mamak", lat=39.9, lon=32.8,
        status=DataStatus.VERIFIED_EXISTING, facility_type=FacilityType.DEVLET_HASTANESI,
        bed_capacity=200, annual_emergency_capacity=100000, investment_cost_million_tl=0.0,
        source="Test"
    )
    assert f_default.is_comprehensive_hospital is False
    assert is_verified_comprehensive_hospital(f_default) is False

    # 2. Açıkça True verilmiş ama türü hastane olmayan (ör. Acil Üssü) tesis kapsamlı sayılmaz
    f_non_hospital = Facility(
        id="T2", name="Acil Müdahale Üssü", district="Polatlı", lat=39.5, lon=32.1,
        status=DataStatus.CANDIDATE_INVESTMENT, facility_type=FacilityType.ADAY_ACIL_USSU,
        bed_capacity=0, annual_emergency_capacity=30000, investment_cost_million_tl=50.0,
        source="Test", is_comprehensive_hospital=True
    )
    assert is_verified_comprehensive_hospital(f_non_hospital) is False

    # 3. Açıkça True verilmiş ve üçüncü basamak Şehir Hastanesi olan tesis kapsamlı sayılır
    f_comprehensive = Facility(
        id="T3", name="Şehir Hastanesi", district="Çankaya", lat=39.89, lon=32.76,
        status=DataStatus.VERIFIED_EXISTING, facility_type=FacilityType.SEHIR_HASTANESI,
        bed_capacity=3800, annual_emergency_capacity=1400000, investment_cost_million_tl=0.0,
        source="Test", is_comprehensive_hospital=True
    )
    assert is_verified_comprehensive_hospital(f_comprehensive) is True


def test_stage1_failure_strictly_aborts_stage2():
    """
    KRİTİK 2 (Çözücü Başarısızlığı Mock Testi):
    Aşama 1 çözücüsü başarısız olduğunda (örn. Infeasible veya Not Solved),
    Aşama 2 ASLA başlatılmamalı ve derhal başarısızlık raporlanmalıdır.
    """
    demands = [DemandZone("D1", "Semt", "İlçe", 39.9, 32.8, 50000, 17500, "Test")]
    facilities = [
        Facility("F1", "Tesis", "İlçe", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 100, 50000, 0.0, "Test", 1.0, True)
    ]
    scenario = OptimizationScenario(
        name="Stage1FailMock", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0,
        use_lexicographic=True
    )

    # PuLP solve metodunu taklit ederek Aşama 1'de -1 (Infeasible) döndür
    with patch.object(pulp.LpProblem, "solve", return_value=-1) as mock_solve:
        res = solve_elastic_cflp(demands, facilities, scenario)

        # Yalnızca 1 kez (Aşama 1) çağrılmış olmalıdır; Aşama 2'ye ASLA geçilmemiştir
        assert mock_solve.call_count == 1
        assert res["success"] is False
        assert "Stage1_Failed" in res["status"]


def test_unreachable_edges_excluded_and_zero_infinite_in_objective():
    """
    Ulaşım süresi kesim eşiğini aşan veya ulaşılamayan bağlantılar modele katılmaz;
    kesinlikle float('inf') veya float('nan') PuLP amaç fonksiyonuna eklenmez.
    """
    demands = [
        DemandZone("D1", "Merkez Semt", "İlçe 1", 39.9, 32.8, 50000, 17500, "Test"),
        DemandZone("D_UZAK", "Çok Uzak Köy", "İlçe 2", 38.5, 31.0, 10000, 3500, "Test")
    ]
    facilities = [
        Facility("F1", "Merkez Hastane", "İlçe 1", 39.91, 32.81, DataStatus.VERIFIED_EXISTING,
                 FacilityType.DEVLET_HASTANESI, 500, 200000, 0.0, "Test", 1.0, True)
    ]

    # Maksimum 30 dakika erişim kısıtı koy: Merkez Hastane (yaklaşık 1-2 dk) ulaşabilir,
    # Çok Uzak Köy (>100 km, >90 dk) kesinlikle ulaşamaz.
    scenario = OptimizationScenario(
        name="CutoffTest", description="Test", p_candidates=0,
        weight_travel_time=1.0, weight_investment_cost=0.0,
        max_travel_time_cutoff_min=30.0
    )
    res = solve_elastic_cflp(demands, facilities, scenario)

    assert res["success"] is True
    # D1'in talebi karşılanmalıdır
    d1_alloc = sum(a["allocated_demand"] for a in res["assignments"] if a["demand_id"] == "D1")
    assert d1_alloc == pytest.approx(17500, abs=1)

    # D_UZAK hiçbir tesise ulaşamadığı için %100 açıkta kalan talep olmalıdır
    unmet_uzak = next((u for u in res["unmet_zones"] if u["zone_id"] == "D_UZAK"), None)
    assert unmet_uzak is not None
    assert unmet_uzak["unmet_fraction"] == pytest.approx(1.0, abs=1e-3)
    assert unmet_uzak["unmet_annual_demand"] == pytest.approx(3500, abs=1)
