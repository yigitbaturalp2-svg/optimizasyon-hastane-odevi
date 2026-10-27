"""
ANKARA SAĞLIKNET - Elastik Kapasiteli Tesis Yeri Seçimi (CFLP / MILP) Optimizasyon Motoru
Kütüphane: PuLP / COIN-OR CBC

Matematiksel ve Yapısal Güvenlik Kuralları (TEKNİK GÖREV 001.3):
1. Tesis Uygunluğu ve Rol Ayrımı:
   - Yalnızca is_eligible_for_hospital_optimization() doğrulaması geçen tesisler genel hastane
     nakil optimizasyonunda hasta kabul hedefi ve aday hastane olarak değerlendirilir.
   - Acil müdahale üsleri (ADAY_ACIL_USSU) genel hastane nakil hedefi olamaz; bütçe/aday seçiminde
     hastane adayı sayılmaz.
2. Bütçe ve Aday Tesis Modları:
   - EXACT_COUNT: Tam p adet yeni hastane açılması (sum y_j == p).
   - MAX_COUNT: En fazla p adet yeni hastane açılması (sum y_j <= p).
   - BUDGET_LIMIT: Toplam yatırım maliyeti sınırı (sum F_j * y_j <= B).
   - COMBINED: Hem en fazla p adet hem yatırım bütçesi sınırı.
3. İki Aşamalı Lexicographic Optimizasyon:
   - Aşama 1: Toplam karşılanamayan acil başvuru talebini (sum d_i * u_i) minimize eder.
   - Aşama 1 'Optimal' olmadan Aşama 2 ASLA başlatılmaz.
   - Aşama 2: U* kilitlenir; toplam seyahat süresi ve yatırım maliyeti minimize edilir.
4. Ulaşılamayan Bağlantı Güvenliği:
   - PuLP amaç fonksiyonuna inf/NaN eklenmez; ulaşılamayan bağlantılar için x_ij oluşturulmaz.
5. Sayısal Muhasebe ve Tolerans:
   - Erken yuvarlama yapılmaz; küçük kesirli tahsisler korunur.
   - Çalışma zamanında assert yerine açık denetimler uygulanır.
   - Hizmet verilmemiş talep durumunda seyahat süresi 0 yerine None (tanımsız) döner.
"""

import math
import pulp
from typing import List, Dict, Any, Optional, Set, Tuple
from core.models import (
    DemandZone, Facility, OptimizationScenario, DataStatus,
    CandidateSelectionMode, is_eligible_for_hospital_optimization
)
from core.routing import build_travel_matrix, is_valid_travel_time, RoutingMode


def solve_elastic_cflp(
    demand_zones: List[DemandZone],
    facilities: List[Facility],
    scenario: OptimizationScenario,
    routing_mode: RoutingMode = RoutingMode.ESTIMATED_GEOMETRIC,
    allow_osrm_fallback_to_geometric: bool = False
) -> Dict[str, Any]:
    """
    Elastik Kapasiteli Tesis Yeri Seçimi Problemini (Elastic CFLP) çözer.
    """
    total_demand = sum(float(d.annual_emergency_demand) for d in demand_zones)
    total_pop = sum(d.population for d in demand_zones)

    # 1. Tesis Uygunluk Filtresi (TEKNİK GÖREV 001.3: Yalnızca hastane nakil yetkinliği olanlar)
    eligible_facs = [f for f in facilities if is_eligible_for_hospital_optimization(f)]
    existing_facs = [f for f in eligible_facs if f.is_existing]
    candidate_facs = [f for f in eligible_facs if not f.is_existing]

    # 2. Aday Tesis ve Bütçe Kısıtı Doğrulaması
    mode = scenario.candidate_selection_mode

    if mode == CandidateSelectionMode.EXACT_COUNT:
        if scenario.p_candidates > len(candidate_facs):
            return {
                "success": False,
                "status": "Infeasible_Candidate_Count",
                "message": (
                    f"Aday hastane kısıtı sağlanamıyor: Senaryo tam p={scenario.p_candidates} adet "
                    f"yeni hastane seçilmesini gerektiriyor, ancak uygun aday hastane sayısı {len(candidate_facs)}."
                ),
                "objective_value": None,
                "selected_candidates": [],
                "selected_candidate_ids": [],
                "active_facility_ids": [f.id for f in existing_facs],
                "assignments": [],
                "facility_allocated_demand": {f.id: 0.0 for f in facilities},
                "unmet_demand_total": float(total_demand),
                "unmet_percentage": 100.0 if total_demand > 0 else 0.0,
                "unmet_zones": [],
                "has_unmet_demand": total_demand > 0,
                "total_investment_cost_million_tl": 0.0,
                "avg_travel_time_min": None,
                "max_travel_time_min": 0.0,
                "coverage_under_15_min_pct": 0.0,
                "coverage_under_25_min_pct": 0.0,
                "total_population": total_pop,
                "total_annual_demand": total_demand
            }

    if mode in (CandidateSelectionMode.BUDGET_LIMIT, CandidateSelectionMode.COMBINED):
        if scenario.max_investment_budget_million_tl is not None and scenario.max_investment_budget_million_tl < 0:
            return {
                "success": False,
                "status": "Infeasible_Budget",
                "message": f"Yatırım bütçesi negatif olamaz: {scenario.max_investment_budget_million_tl}",
                "objective_value": None,
                "selected_candidates": [],
                "selected_candidate_ids": [],
                "active_facility_ids": [f.id for f in existing_facs],
                "assignments": [],
                "facility_allocated_demand": {f.id: 0.0 for f in facilities},
                "unmet_demand_total": float(total_demand),
                "unmet_percentage": 100.0 if total_demand > 0 else 0.0,
                "unmet_zones": [],
                "has_unmet_demand": total_demand > 0,
                "total_investment_cost_million_tl": 0.0,
                "avg_travel_time_min": None,
                "max_travel_time_min": 0.0,
                "coverage_under_15_min_pct": 0.0,
                "coverage_under_25_min_pct": 0.0,
                "total_population": total_pop,
                "total_annual_demand": total_demand
            }

    # 3. Sıfır Talep Durumu: Matematiksel olarak anında geçerli
    if total_demand == 0.0:
        return {
            "success": True,
            "status": "Optimal_Zero_Demand",
            "message": "Modeldeki tüm talep bölgelerinin talebi sıfırdır.",
            "objective_value": 0.0,
            "selected_candidates": [],
            "selected_candidate_ids": [],
            "active_facility_ids": [f.id for f in existing_facs],
            "assignments": [],
            "facility_allocated_demand": {f.id: 0.0 for f in facilities},
            "unmet_demand_total": 0.0,
            "unmet_percentage": 0.0,
            "unmet_zones": [],
            "has_unmet_demand": False,
            "total_investment_cost_million_tl": 0.0,
            "avg_travel_time_min": None,
            "max_travel_time_min": 0.0,
            "coverage_under_15_min_pct": 0.0,
            "coverage_under_25_min_pct": 0.0,
            "total_population": total_pop,
            "total_annual_demand": 0.0
        }

    # 4. Sıfır Tesis Durumu: Matematiksel olarak %100 Karşılanamayan Talep (Geçerli Çözüm)
    if not eligible_facs:
        unmet_zones = []
        for d in demand_zones:
            if d.annual_emergency_demand > 0:
                unmet_zones.append({
                    "zone_id": d.id,
                    "zone_name": d.name,
                    "district": d.district,
                    "unmet_population": d.population,
                    "unmet_annual_demand": float(d.annual_emergency_demand),
                    "unmet_fraction": 1.0
                })
        return {
            "success": True,
            "status": "Optimal_Zero_Facilities",
            "message": "Modelde uygun hastane bulunmadığından tüm talep karşılanamayan talep (u_i=1.0) olarak belirlendi.",
            "objective_value": 0.0,
            "selected_candidates": [],
            "selected_candidate_ids": [],
            "active_facility_ids": [],
            "assignments": [],
            "facility_allocated_demand": {f.id: 0.0 for f in facilities},
            "unmet_demand_total": float(total_demand),
            "unmet_percentage": 100.0,
            "unmet_zones": unmet_zones,
            "has_unmet_demand": True,
            "total_investment_cost_million_tl": 0.0,
            "avg_travel_time_min": None,
            "max_travel_time_min": 0.0,
            "coverage_under_15_min_pct": 0.0,
            "coverage_under_25_min_pct": 0.0,
            "total_population": total_pop,
            "total_annual_demand": total_demand
        }

    # 5. Seyahat Matrisini Oluştur ve Ulaşılabilir Bağlantıları Belirle
    time_matrix, dist_matrix, routing_metadata = build_travel_matrix(
        demand_zones, eligible_facs,
        hour=scenario.hour,
        routing_mode=routing_mode,
        allow_osrm_fallback_to_geometric=allow_osrm_fallback_to_geometric
    )

    reachable_edges: List[Tuple[str, str]] = []
    zone_reachable_facs: Dict[str, List[str]] = {d.id: [] for d in demand_zones}
    fac_reachable_zones: Dict[str, List[str]] = {f.id: [] for f in eligible_facs}

    cutoff = scenario.max_travel_time_cutoff_min
    for d in demand_zones:
        for f in eligible_facs:
            t_val = time_matrix.get(d.id, {}).get(f.id)
            if is_valid_travel_time(t_val):
                if cutoff is None or t_val <= cutoff:
                    d_id = d.id
                    f_id = f.id
                    reachable_edges.append((d_id, f_id))
                    zone_reachable_facs[d_id].append(f_id)
                    fac_reachable_zones[f_id].append(d_id)

    # 6. Karar Değişkenleri Tanımları
    # y_j: Yalnızca uygun aday hastaneler için ikili karar değişkeni
    y: Dict[str, Any] = {}
    for f in candidate_facs:
        y[f.id] = pulp.LpVariable(f"y_{f.id}", cat=pulp.LpBinary)
    for f in existing_facs:
        y[f.id] = 1.0

    # x_ij: Yalnızca ulaşılabilir bağlantılar için [0, 1] sürekli değişken
    x: Dict[str, Dict[str, Any]] = {d.id: {} for d in demand_zones}
    for d_id, f_id in reachable_edges:
        x[d_id][f_id] = pulp.LpVariable(f"x_{d_id}_{f_id}", lowBound=0.0, upBound=1.0, cat=pulp.LpContinuous)

    # u_i: Karşılanamayan talep fraksiyonu [0, 1]
    u: Dict[str, Any] = {}
    for d in demand_zones:
        u[d.id] = pulp.LpVariable(f"u_{d.id}", lowBound=0.0, upBound=1.0, cat=pulp.LpContinuous)

    def apply_candidate_budget_constraints(prob_obj: pulp.LpProblem, prefix: str):
        """Aday tesis seçim moduna göre kısıtları ekler."""
        if not candidate_facs:
            return
        if mode == CandidateSelectionMode.EXACT_COUNT:
            prob_obj += (
                pulp.lpSum(y[f.id] for f in candidate_facs) == scenario.p_candidates,
                f"{prefix}_Exact_Candidate_Count"
            )
        elif mode == CandidateSelectionMode.MAX_COUNT:
            prob_obj += (
                pulp.lpSum(y[f.id] for f in candidate_facs) <= scenario.p_candidates,
                f"{prefix}_Max_Candidate_Count"
            )
        elif mode == CandidateSelectionMode.BUDGET_LIMIT:
            budget = scenario.max_investment_budget_million_tl if scenario.max_investment_budget_million_tl is not None else float('inf')
            prob_obj += (
                pulp.lpSum(f.investment_cost_million_tl * y[f.id] for f in candidate_facs) <= budget,
                f"{prefix}_Investment_Budget_Limit"
            )
        elif mode == CandidateSelectionMode.COMBINED:
            prob_obj += (
                pulp.lpSum(y[f.id] for f in candidate_facs) <= scenario.p_candidates,
                f"{prefix}_Combined_Max_Count"
            )
            budget = scenario.max_investment_budget_million_tl if scenario.max_investment_budget_million_tl is not None else float('inf')
            prob_obj += (
                pulp.lpSum(f.investment_cost_million_tl * y[f.id] for f in candidate_facs) <= budget,
                f"{prefix}_Combined_Budget_Limit"
            )

    # 7. Model Oluşturma ve Çözüm
    if scenario.use_lexicographic:
        # =========================================================================
        # AŞAMA 1: Karşılanamayan Talebin Minimizasyonu
        # =========================================================================
        prob_stage1 = pulp.LpProblem("Ankara_SaglikNet_Lexicographic_Stage1", pulp.LpMinimize)

        prob_stage1 += pulp.lpSum(
            d.annual_emergency_demand * u[d.id] for d in demand_zones
        ), "Stage1_Min_Unmet_Demand"

        for d in demand_zones:
            fac_list = zone_reachable_facs[d.id]
            if fac_list:
                prob_stage1 += (
                    pulp.lpSum(x[d.id][f_id] for f_id in fac_list) + u[d.id] == 1.0,
                    f"Stage1_Conservation_{d.id}"
                )
            else:
                prob_stage1 += u[d.id] == 1.0, f"Stage1_Unreachable_Zone_{d.id}"

        for d_id, f_id in reachable_edges:
            fac_obj = next((f for f in eligible_facs if f.id == f_id), None)
            if fac_obj and not fac_obj.is_existing:
                prob_stage1 += x[d_id][f_id] <= y[f_id], f"Stage1_Link_{d_id}_{f_id}"

        if scenario.enable_capacity_limits:
            for f in eligible_facs:
                zones_for_f = fac_reachable_zones[f.id]
                if zones_for_f:
                    demand_sum_expr = pulp.lpSum(
                        next(d.annual_emergency_demand for d in demand_zones if d.id == d_id) * x[d_id][f.id]
                        for d_id in zones_for_f
                    )
                    if not f.is_existing:
                        prob_stage1 += (
                            demand_sum_expr <= f.annual_emergency_capacity * y[f.id],
                            f"Stage1_Capacity_Candidate_{f.id}"
                        )
                    else:
                        prob_stage1 += (
                            demand_sum_expr <= f.annual_emergency_capacity,
                            f"Stage1_Capacity_Existing_{f.id}"
                        )

        apply_candidate_budget_constraints(prob_stage1, "Stage1")

        solver1 = pulp.PULP_CBC_CMD(msg=False, timeLimit=20)
        status1_code = prob_stage1.solve(solver1)
        status1_str = pulp.LpStatus.get(status1_code, "Unknown")

        # Aşama 1 Başarısızlık Kontrolü: Kesinlikle Aşama 2'ye geçilmez
        if status1_code != 1 or status1_str != "Optimal":
            return {
                "success": False,
                "status": f"Stage1_Failed_{status1_str}",
                "message": f"Aşama 1 (Karşılanamayan talep minimizasyonu) çözülemedi: {status1_str}",
                "objective_value": None,
                "selected_candidates": [],
                "selected_candidate_ids": [],
                "active_facility_ids": [f.id for f in existing_facs],
                "assignments": [],
                "facility_allocated_demand": {f.id: 0.0 for f in facilities},
                "unmet_demand_total": float(total_demand),
                "unmet_percentage": 100.0 if total_demand > 0 else 0.0,
                "unmet_zones": [],
                "has_unmet_demand": total_demand > 0,
                "total_investment_cost_million_tl": 0.0,
                "avg_travel_time_min": None,
                "max_travel_time_min": 0.0,
                "coverage_under_15_min_pct": 0.0,
                "coverage_under_25_min_pct": 0.0,
                "total_population": total_pop,
                "total_annual_demand": total_demand,
                "routing_metadata": routing_metadata
            }

        # Amaç fonksiyonu değerini float() öncesinde güvenle doğrula
        obj_raw_val = pulp.value(prob_stage1.objective)
        if obj_raw_val is None or not math.isfinite(obj_raw_val):
            return {
                "success": False,
                "status": "Stage1_Invalid_Objective",
                "message": "Aşama 1 amaç fonksiyonu tanımsız (None/NaN/inf) değer üretti.",
                "objective_value": None,
                "selected_candidates": [],
                "selected_candidate_ids": [],
                "active_facility_ids": [f.id for f in existing_facs],
                "assignments": [],
                "facility_allocated_demand": {f.id: 0.0 for f in facilities},
                "unmet_demand_total": float(total_demand),
                "unmet_percentage": 100.0 if total_demand > 0 else 0.0,
                "unmet_zones": [],
                "has_unmet_demand": total_demand > 0,
                "total_investment_cost_million_tl": 0.0,
                "avg_travel_time_min": None,
                "max_travel_time_min": 0.0,
                "coverage_under_15_min_pct": 0.0,
                "coverage_under_25_min_pct": 0.0,
                "total_population": total_pop,
                "total_annual_demand": total_demand,
                "routing_metadata": routing_metadata
            }
        min_unmet_demand_val = float(obj_raw_val)

        # =========================================================================
        # AŞAMA 2: Seyahat Süresi ve Yatırım Maliyetinin Minimizasyonu
        # =========================================================================
        prob_stage2 = pulp.LpProblem("Ankara_SaglikNet_Lexicographic_Stage2", pulp.LpMinimize)

        norm_time = max(1.0, float(total_demand) * 45.0)
        max_possible_cost = max(1.0, sum(f.investment_cost_million_tl for f in candidate_facs))
        norm_cost = max(1.0, float(max_possible_cost))

        travel_cost_expr = pulp.lpSum(
            (next(d.annual_emergency_demand for d in demand_zones if d.id == d_id) *
             time_matrix[d_id][f_id] * x[d_id][f_id]) / norm_time
            for d_id, f_id in reachable_edges
        )
        investment_cost_expr = pulp.lpSum(
            (f.investment_cost_million_tl * y[f.id]) / norm_cost
            for f in candidate_facs
        )

        prob_stage2 += (
            scenario.weight_travel_time * travel_cost_expr +
            scenario.weight_investment_cost * investment_cost_expr
        ), "Stage2_Weighted_Time_And_Cost"

        # Kısıt 1: Aşama 1 Optimum Karşılanamayan Talep Kilidi (U* + 1e-3 tolerans)
        unmet_tolerance = 1e-3
        prob_stage2 += (
            pulp.lpSum(d.annual_emergency_demand * u[d.id] for d in demand_zones) <=
            min_unmet_demand_val + unmet_tolerance,
            "Stage2_Lock_Min_Unmet_Demand"
        )

        for d in demand_zones:
            fac_list = zone_reachable_facs[d.id]
            if fac_list:
                prob_stage2 += (
                    pulp.lpSum(x[d.id][f_id] for f_id in fac_list) + u[d.id] == 1.0,
                    f"Stage2_Conservation_{d.id}"
                )
            else:
                prob_stage2 += u[d.id] == 1.0, f"Stage2_Unreachable_Zone_{d.id}"

        for d_id, f_id in reachable_edges:
            fac_obj = next((f for f in eligible_facs if f.id == f_id), None)
            if fac_obj and not fac_obj.is_existing:
                prob_stage2 += x[d_id][f_id] <= y[f_id], f"Stage2_Link_{d_id}_{f_id}"

        if scenario.enable_capacity_limits:
            for f in eligible_facs:
                zones_for_f = fac_reachable_zones[f.id]
                if zones_for_f:
                    demand_sum_expr = pulp.lpSum(
                        next(d.annual_emergency_demand for d in demand_zones if d.id == d_id) * x[d_id][f.id]
                        for d_id in zones_for_f
                    )
                    if not f.is_existing:
                        prob_stage2 += (
                            demand_sum_expr <= f.annual_emergency_capacity * y[f.id],
                            f"Stage2_Capacity_Candidate_{f.id}"
                        )
                    else:
                        prob_stage2 += (
                            demand_sum_expr <= f.annual_emergency_capacity,
                            f"Stage2_Capacity_Existing_{f.id}"
                        )

        apply_candidate_budget_constraints(prob_stage2, "Stage2")

        solver2 = pulp.PULP_CBC_CMD(msg=False, timeLimit=25)
        status2_code = prob_stage2.solve(solver2)
        status2_str = pulp.LpStatus.get(status2_code, "Unknown")

        if status2_code != 1 or status2_str != "Optimal":
            return {
                "success": False,
                "status": f"Stage2_Failed_{status2_str}",
                "message": f"Aşama 2 (Seyahat süresi/maliyet minimizasyonu) çözülemedi: {status2_str}",
                "objective_value": None,
                "selected_candidates": [],
                "selected_candidate_ids": [],
                "active_facility_ids": [f.id for f in existing_facs],
                "assignments": [],
                "facility_allocated_demand": {f.id: 0.0 for f in facilities},
                "unmet_demand_total": float(total_demand),
                "unmet_percentage": 100.0 if total_demand > 0 else 0.0,
                "unmet_zones": [],
                "has_unmet_demand": total_demand > 0,
                "total_investment_cost_million_tl": 0.0,
                "avg_travel_time_min": None,
                "max_travel_time_min": 0.0,
                "coverage_under_15_min_pct": 0.0,
                "coverage_under_25_min_pct": 0.0,
                "total_population": total_pop,
                "total_annual_demand": total_demand,
                "routing_metadata": routing_metadata
            }

        final_problem = prob_stage2
        status_str = "Optimal (Lexicographic 2-Aşamalı)"

    else:
        # =========================================================================
        # TEK AŞAMALI SKALERLEŞTİRİLMİŞ MODEL
        # =========================================================================
        prob = pulp.LpProblem("Ankara_SaglikNet_SingleStage_CFLP", pulp.LpMinimize)

        norm_time = max(1.0, float(total_demand) * 45.0)
        max_possible_cost = max(1.0, sum(f.investment_cost_million_tl for f in candidate_facs))
        norm_cost = max(1.0, float(max_possible_cost))

        travel_cost_expr = pulp.lpSum(
            (next(d.annual_emergency_demand for d in demand_zones if d.id == d_id) *
             time_matrix[d_id][f_id] * x[d_id][f_id]) / norm_time
            for d_id, f_id in reachable_edges
        )
        investment_cost_expr = pulp.lpSum(
            (f.investment_cost_million_tl * y[f.id]) / norm_cost
            for f in candidate_facs
        )
        unmet_penalty_expr = pulp.lpSum(
            scenario.penalize_unmet_demand * u[d.id]
            for d in demand_zones
        )

        prob += (
            scenario.weight_travel_time * travel_cost_expr +
            scenario.weight_investment_cost * investment_cost_expr +
            unmet_penalty_expr
        ), "Scalarized_Objective"

        for d in demand_zones:
            fac_list = zone_reachable_facs[d.id]
            if fac_list:
                prob += (
                    pulp.lpSum(x[d.id][f_id] for f_id in fac_list) + u[d.id] == 1.0,
                    f"Conservation_{d.id}"
                )
            else:
                prob += u[d.id] == 1.0, f"Unreachable_Zone_{d.id}"

        for d_id, f_id in reachable_edges:
            fac_obj = next((f for f in eligible_facs if f.id == f_id), None)
            if fac_obj and not fac_obj.is_existing:
                prob += x[d_id][f_id] <= y[f_id], f"Link_{d_id}_{f_id}"

        if scenario.enable_capacity_limits:
            for f in eligible_facs:
                zones_for_f = fac_reachable_zones[f.id]
                if zones_for_f:
                    demand_sum_expr = pulp.lpSum(
                        next(d.annual_emergency_demand for d in demand_zones if d.id == d_id) * x[d_id][f.id]
                        for d_id in zones_for_f
                    )
                    if not f.is_existing:
                        prob += (
                            demand_sum_expr <= f.annual_emergency_capacity * y[f.id],
                            f"Capacity_Candidate_{f.id}"
                        )
                    else:
                        prob += (
                            demand_sum_expr <= f.annual_emergency_capacity,
                            f"Capacity_Existing_{f.id}"
                        )

        apply_candidate_budget_constraints(prob, "SingleStage")

        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=25)
        status_code = prob.solve(solver)
        status_str = pulp.LpStatus.get(status_code, "Unknown")

        if status_code != 1 or status_str != "Optimal":
            return {
                "success": False,
                "status": f"SingleStage_Failed_{status_str}",
                "message": f"Tek aşamalı model çözülemedi: {status_str}",
                "objective_value": None,
                "selected_candidates": [],
                "selected_candidate_ids": [],
                "active_facility_ids": [f.id for f in existing_facs],
                "assignments": [],
                "facility_allocated_demand": {f.id: 0.0 for f in facilities},
                "unmet_demand_total": float(total_demand),
                "unmet_percentage": 100.0 if total_demand > 0 else 0.0,
                "unmet_zones": [],
                "has_unmet_demand": total_demand > 0,
                "total_investment_cost_million_tl": 0.0,
                "avg_travel_time_min": None,
                "max_travel_time_min": 0.0,
                "coverage_under_15_min_pct": 0.0,
                "coverage_under_25_min_pct": 0.0,
                "total_population": total_pop,
                "total_annual_demand": total_demand,
                "routing_metadata": routing_metadata
            }

        final_problem = prob

    # =========================================================================
    # 8. SONUÇLARI ÇIKAR, DOĞRULA VE ANALİZ ET
    # =========================================================================
    selected_candidate_ids: List[str] = []
    for f in candidate_facs:
        val_y = pulp.value(y[f.id])
        if val_y is not None and val_y > 0.5:
            selected_candidate_ids.append(f.id)

    active_facility_ids = [f.id for f in existing_facs] + selected_candidate_ids
    active_fac_dict = {f.id: f for f in eligible_facs if f.id in active_facility_ids}

    assignments: List[Dict[str, Any]] = []
    unmet_demand_total = 0.0
    unmet_zones: List[Dict[str, Any]] = []
    facility_allocated_demand: Dict[str, float] = {f.id: 0.0 for f in facilities}

    for d in demand_zones:
        u_val = float(pulp.value(u[d.id]) or 0.0)
        u_val = max(0.0, min(1.0, u_val))

        assigned_fraction_sum = 0.0
        fac_list = zone_reachable_facs[d.id]

        for f_id in fac_list:
            if f_id in active_facility_ids:
                x_val = float(pulp.value(x[d.id][f_id]) or 0.0)
                # Küçük kesirli tahsisler korunur (TEKNİK GÖREV 001.3 Kuralı: erken yuvarlama ve kesme yapılmaz)
                if x_val > 1e-7:
                    assigned_fraction_sum += x_val
                    alloc_demand = x_val * float(d.annual_emergency_demand)
                    facility_allocated_demand[f_id] += alloc_demand
                    fac_obj = active_fac_dict[f_id]
                    assignments.append({
                        "demand_id": d.id,
                        "demand_name": d.name,
                        "district": d.district,
                        "demand_lat": d.lat,
                        "demand_lon": d.lon,
                        "population": d.population,
                        "assigned_population": x_val * float(d.population),
                        "annual_emergency_demand": float(d.annual_emergency_demand),
                        "allocated_demand": alloc_demand,
                        "allocation_fraction": x_val,
                        "facility_id": f_id,
                        "facility_name": fac_obj.name,
                        "facility_type": fac_obj.facility_type.value,
                        "is_existing": fac_obj.is_existing,
                        "facility_lat": fac_obj.lat,
                        "facility_lon": fac_obj.lon,
                        "travel_time_min": time_matrix[d.id][f_id],
                        "distance_km": dist_matrix[d.id][f_id]
                    })

        # Sayısal dengeleme: Talep korunumu denetimi
        conservation_err = abs((assigned_fraction_sum + u_val) - 1.0)
        if conservation_err > 1e-4:
            u_val = max(0.0, 1.0 - assigned_fraction_sum)

        if u_val > 1e-7:
            unmet_amount = u_val * float(d.annual_emergency_demand)
            unmet_demand_total += unmet_amount
            unmet_zones.append({
                "zone_id": d.id,
                "zone_name": d.name,
                "district": d.district,
                "unmet_population": u_val * float(d.population),
                "unmet_annual_demand": unmet_amount,
                "unmet_fraction": u_val
            })

    # Çözüm Sonrası Kapasite ve Kısıt Açık Denetimi (Assert yerine explicit exception)
    if scenario.enable_capacity_limits:
        for f in eligible_facs:
            cap = float(f.annual_emergency_capacity)
            allocated = facility_allocated_demand.get(f.id, 0.0)
            if f.is_existing:
                if allocated > cap + 1.0:
                    raise ValueError(f"Kapasite ihlali: Mevcut tesis {f.id} ({allocated:.2f} > {cap:.2f})")
            else:
                is_open = f.id in selected_candidate_ids
                if not is_open and allocated > 1e-3:
                    raise ValueError(f"Açılmayan tesis kısıt ihlali: Aday {f.id} kapalı olmasına rağmen talep aldı ({allocated})")
                if is_open and allocated > cap + 1.0:
                    raise ValueError(f"Kapasite ihlali: Aday tesis {f.id} ({allocated:.2f} > {cap:.2f})")

    # Bütçe denetimi
    total_investment_cost = sum(
        f.investment_cost_million_tl for f in candidate_facs if f.id in selected_candidate_ids
    )
    if mode in (CandidateSelectionMode.BUDGET_LIMIT, CandidateSelectionMode.COMBINED):
        if scenario.max_investment_budget_million_tl is not None:
            if total_investment_cost > scenario.max_investment_budget_million_tl + 1e-3:
                raise ValueError(f"Bütçe kısıtı ihlali: Yatırım maliyeti ({total_investment_cost}) > Bütçe ({scenario.max_investment_budget_million_tl})")

    # Metriklerin Hesaplanması
    total_assigned_demand = sum(a["allocated_demand"] for a in assignments)

    if total_assigned_demand > 0.0:
        weighted_travel_time = sum(
            a["travel_time_min"] * a["allocated_demand"] for a in assignments
        ) / total_assigned_demand
        avg_travel_time = round(weighted_travel_time, 1)
        max_travel_time = round(max((a["travel_time_min"] for a in assignments), default=0.0), 1)
    else:
        avg_travel_time = None  # Sıfır hizmet verildiğinde süre tanımsızdır
        max_travel_time = 0.0

    under_15_pop = sum(a["assigned_population"] for a in assignments if a["travel_time_min"] <= 15.0)
    under_25_pop = sum(a["assigned_population"] for a in assignments if a["travel_time_min"] <= 25.0)

    coverage_15_pct = round((under_15_pop / total_pop) * 100.0, 1) if total_pop > 0 else 0.0
    coverage_25_pct = round((under_25_pop / total_pop) * 100.0, 1) if total_pop > 0 else 0.0

    unmet_pct = round((unmet_demand_total / total_demand) * 100.0, 2) if total_demand > 0 else 0.0

    obj_raw_final = pulp.value(final_problem.objective)
    obj_val = float(obj_raw_final) if obj_raw_final is not None and math.isfinite(obj_raw_final) else 0.0

    return {
        "success": True,
        "status": status_str,
        "objective_value": round(obj_val, 4),
        "selected_candidates": [f.to_dict() for f in candidate_facs if f.id in selected_candidate_ids],
        "selected_candidate_ids": selected_candidate_ids,
        "active_facility_ids": active_facility_ids,
        "assignments": assignments,
        "facility_allocated_demand": facility_allocated_demand,
        "unmet_demand_total": round(unmet_demand_total, 2),
        "unmet_percentage": unmet_pct,
        "unmet_zones": unmet_zones,
        "has_unmet_demand": unmet_demand_total > 1.0,
        "total_investment_cost_million_tl": round(total_investment_cost, 1),
        "avg_travel_time_min": avg_travel_time,
        "max_travel_time_min": max_travel_time,
        "coverage_under_15_min_pct": coverage_15_pct,
        "coverage_under_25_min_pct": coverage_25_pct,
        "total_population": total_pop,
        "total_annual_demand": total_demand,
        "routing_metadata": routing_metadata
    }
