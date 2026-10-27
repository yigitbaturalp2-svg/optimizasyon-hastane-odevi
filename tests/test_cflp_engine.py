"""
ANKARA SAĞLIKNET - Matematiksel ve Mantıksal Doğrulama Test Paketi
Bu dosya, CFLP optimizasyon motorunun tüm kısıt ve varsayımlarını sınar.
"""

import pytest
from core.models import DemandZone, Facility, FacilityType, DataStatus, OptimizationScenario
from core.optimizer import solve_elastic_cflp
from data import get_verified_facilities, get_candidate_facilities, get_demand_zones


def test_closed_facility_receives_zero_demand():
    """Kural: Açılmayan (y_j = 0) tesis kesinlikle hasta kabul edemez."""
    # 2 aday tesis, 1 talep bölgesi, bütçe p=1
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
    # Yakın olan C1 seçilmeli, Uzak olan C2 seçilmemeli
    assert "C1" in res["selected_candidate_ids"]
    assert "C2" not in res["selected_candidate_ids"]
    
    # C2'ye hiçbir talep atanmamış olmalıdır
    c2_alloc = res["facility_allocated_demand"].get("C2", 0.0)
    assert c2_alloc == 0.0


def test_capacity_limit_strictly_enforced():
    """Kural: Bir tesise atanan talep, o tesisin acil kapasitesini aşamaz."""
    # Talep = 80,000, Tesis Kapasitesi = 50,000
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
    # F1 en fazla 50.000 alabilir
    assert res["facility_allocated_demand"]["F1"] <= 50000.0
    # Kalan 30.000 açıkta kalan talep (u_i) olarak kaydedilmeli
    assert res["unmet_demand_total"] == pytest.approx(30000.0, abs=1.0)
    assert res["has_unmet_demand"] is True


def test_unmet_demand_reported_when_capacity_insufficient():
    """Kural: Kapasite yetersizliğinde çözücü çökmeyip açıkta kalan talebi görünür şekilde raporlamalıdır."""
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
    assert res["unmet_zones"][0]["unmet_annual_demand"] == 25000


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
    
    # Senaryo 1: %90 Ulaşım Önceliği (Hızlı erişim)
    scen_travel = OptimizationScenario(
        name="TravelPriority", description="Hızlı Ulaşım", p_candidates=3,
        weight_travel_time=0.90, weight_investment_cost=0.10
    )
    res_travel = solve_elastic_cflp(demands, all_facilities, scen_travel)
    
    # Senaryo 2: %90 Bütçe Tasarrufu (Düşük Maliyet)
    scen_cost = OptimizationScenario(
        name="CostPriority", description="Düşük Maliyet", p_candidates=3,
        weight_travel_time=0.10, weight_investment_cost=0.90
    )
    res_cost = solve_elastic_cflp(demands, all_facilities, scen_cost)
    
    assert res_travel["success"] is True
    assert res_cost["success"] is True
    # Seçilen tesis kümeleri farklı olmalıdır
    assert set(res_travel["selected_candidate_ids"]) != set(res_cost["selected_candidate_ids"])
    # Seyahat öncelikli senaryo daha iyi seyahat süresi sağlamalıdır
    assert res_travel["avg_travel_time_min"] <= res_cost["avg_travel_time_min"]
    # Bütçe öncelikli senaryo daha düşük maliyet üretmelidir
    assert res_cost["total_investment_cost_million_tl"] <= res_travel["total_investment_cost_million_tl"]


def test_toy_cflp_analytical_optimum():
    """Kural: 3 noktalı bilinen analitik örnekte tam beklenen global optimum bulunmalıdır."""
    # 2 Talep: D1 (pop:100, demand:35), D2 (pop:200, demand:70)
    # 2 Aday: C1 (D1'e 10 dk, C2'ye 30 dk, Maliyet:100, Kapasite:100)
    #         C2 (D1'e 30 dk, D2'ye 10 dk, Maliyet:100, Kapasite:100)
    # p = 1 olduğunda D2'nin nüfusu 2 kat büyük olduğu için C2 seçilmek zorundadır.
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
    # D2'nin talebi 70.000 > D1'in talebi 35.000 olduğu için çözücü C2'yi seçmelidir
    assert res["selected_candidate_ids"] == ["C2"]


def test_elastic_conservation_of_demand():
    """Kural: Tüm bölgeler için atanan fraksiyonlar ve u_i toplamı tam 1.0 olmalıdır."""
    demands = get_demand_zones()[:5]  # İlk 5 bölge
    facilities = get_verified_facilities()[:3]
    
    scenario = OptimizationScenario(
        name="ConservationTest", description="Test", p_candidates=0,
        weight_travel_time=0.8, weight_investment_cost=0.2
    )
    res = solve_elastic_cflp(demands, facilities, scenario)
    
    assert res["success"] is True
    # Her bölge için tahsis toplamı denetimi
    for d in demands:
        assigned_frac = sum(
            a["allocation_fraction"] for a in res["assignments"] if a["demand_id"] == d.id
        )
        unmet_info = next((u for u in res["unmet_zones"] if u["zone_id"] == d.id), None)
        unmet_frac = unmet_info["unmet_fraction"] if unmet_info else 0.0
        assert (assigned_frac + unmet_frac) == pytest.approx(1.0, abs=1e-3)
