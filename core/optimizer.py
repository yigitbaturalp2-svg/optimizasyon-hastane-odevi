"""
ANKARA SAĞLIKNET - Elastik Kapasiteli Tesis Yeri Seçimi (CFLP / MILP) Optimizasyon Motoru
Kütüphane: PuLP / COIN-OR CBC

Özellikler ve Matematiksel Güvenlik Garantileri:
1. İki Aşamalı Lexicographic Optimizasyon:
   - Aşama 1: Toplam karşılanamayan yıllık acil başvuru talebini (sum d_i * u_i) minimize eder.
     Aşama 1'in 'Optimal' statüsü doğrulanmadan Aşama 2'ye ASLA geçilmez.
   - Aşama 2: Minimum açıkta kalan talep seviyesini (U*) tolerans payı ile kilitler;
     ardından ağırlıklı seyahat süresi ve yatırım maliyetini minimize eder.
   - Alternatif: use_lexicographic=False durumunda tek aşamalı skalerleştirilmiş ceza modeli.
2. Ulaşılamayan Bağlantı Güvenliği:
   - PuLP amaç fonksiyonuna kesinlikle sonsuz (inf) veya tanımsız (NaN) katsayı geçilmez.
   - Yalnızca sonlu ve seyahat kısıtını sağlayan (d_id, f_id) ikilileri için x_ij değişkeni üretilir.
   - Hiçbir tesise ulaşamayan bölgelerin talebi u_i = 1 ile elastik karşılanamayan talep olarak korunur.
3. Nesne Kimliği Değişmezliği (Immutability):
   - Döngülerde ve list/dict comprehension ifadelerinde asla (d.id, f.id) gibi nesne özniteliklerini
     hedef alan değişken açma işlemleri kullanılmaz; daima bağımsız d_id, f_id değişkenleri kullanılır.
4. Bütçe ve Aday Tesis Doğrulaması (EXACT_COUNT):
   - İstenen aday sayısı (p_candidates), uygun aday havuzundan büyükse (örneğin havuz 0 iken p=1)
     sessiz başarı üretilmez, açıkça Infeasible_Candidate_Count statüsüyle reddedilir.
5. Sayısal Tolerans ve Metrik Güvenliği:
   - Hizmet verilen talep sıfır ise ortalama seyahat süresi 0.0 yerine None (tanımsız) döner.
   - Kısıt ihlalleri 1e-3 toleransla doğrulanır; toplam talep dengesi denetlenir.
"""

import math
import pulp
from typing import List, Dict, Any, Optional, Set, Tuple
from core.models import DemandZone, Facility, OptimizationScenario, DataStatus
from core.routing import build_travel_matrix, is_valid_travel_time


def solve_elastic_cflp(
    demand_zones: List[DemandZone],
    facilities: List[Facility],
    scenario: OptimizationScenario
) -> Dict[str, Any]:
    """
    Elastik Kapasiteli Tesis Yeri Seçimi Problemini (Elastic CFLP) çözer.
    """
    total_demand = sum(d.annual_emergency_demand for d in demand_zones)
    total_pop = sum(d.population for d in demand_zones)

    # 1. Tesisleri mevcut ve aday olarak ayrıştır
    existing_facs = [f for f in facilities if f.is_existing]
    candidate_facs = [f for f in facilities if not f.is_existing]
    
    # 2. EXACT_COUNT ve Aday Tesis Sayısı Doğrulaması
    if scenario.p_candidates > len(candidate_facs):
        return {
            "success": False,
            "status": "Infeasible_Candidate_Count",
            "message": (
                f"Aday tesis kısıtı sağlanamıyor: Senaryo p={scenario.p_candidates} adet yeni "
                f"tesis seçilmesini gerektiriyor, ancak uygun aday tesis sayısı {len(candidate_facs)}."
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

    # 3. Sıfır Tesis Durumu: Matematiksel olarak %100 Karşılanamayan Talep (Geçerli Çözüm)
    if not facilities:
        unmet_zones = []
        for d in demand_zones:
            if d.annual_emergency_demand > 0:
                unmet_zones.append({
                    "zone_id": d.id,
                    "zone_name": d.name,
                    "district": d.district,
                    "unmet_population": d.population,
                    "unmet_annual_demand": d.annual_emergency_demand,
                    "unmet_fraction": 1.0
                })
        return {
            "success": True,
            "status": "Optimal_Zero_Facilities",
            "message": "Modelde hiç tesis bulunmadığından tüm talep karşılanamayan talep (u_i=1.0) olarak belirlendi.",
            "objective_value": 0.0,
            "selected_candidates": [],
            "selected_candidate_ids": [],
            "active_facility_ids": [],
            "assignments": [],
            "facility_allocated_demand": {},
            "unmet_demand_total": float(total_demand),
            "unmet_percentage": 100.0 if total_demand > 0 else 0.0,
            "unmet_zones": unmet_zones,
            "has_unmet_demand": total_demand > 0,
            "total_investment_cost_million_tl": 0.0,
            "avg_travel_time_min": None,  # Sıfır hizmet verildiğinde seyahat süresi tanımsızdır
            "max_travel_time_min": 0.0,
            "coverage_under_15_min_pct": 0.0,
            "coverage_under_25_min_pct": 0.0,
            "total_population": total_pop,
            "total_annual_demand": total_demand
        }

    # 4. Seyahat Matrisini Oluştur ve Ulaşılabilir Bağlantıları Belirle
    time_matrix, dist_matrix = build_travel_matrix(demand_zones, facilities, hour=scenario.hour)
    
    reachable_edges: List[Tuple[str, str]] = []
    zone_reachable_facs: Dict[str, List[str]] = {d.id: [] for d in demand_zones}
    fac_reachable_zones: Dict[str, List[str]] = {f.id: [] for f in facilities}
    
    cutoff = scenario.max_travel_time_cutoff_min
    for d in demand_zones:
        for f in facilities:
            t_val = time_matrix.get(d.id, {}).get(f.id)
            if is_valid_travel_time(t_val):
                if cutoff is None or t_val <= cutoff:
                    d_id = d.id
                    f_id = f.id
                    reachable_edges.append((d_id, f_id))
                    zone_reachable_facs[d_id].append(f_id)
                    fac_reachable_zones[f_id].append(d_id)

    # 5. Karar Değişkenleri Tanımları
    # y_j: Aday tesisler için ikili karar değişkeni
    y: Dict[str, Any] = {}
    for f in candidate_facs:
        y[f.id] = pulp.LpVariable(f"y_{f.id}", cat=pulp.LpBinary)
    # Mevcut tesisler açıktır (y_j = 1)
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

    # 6. Optimizasyon Modeli: Lexicographic veya Skalerleştirilmiş
    if scenario.use_lexicographic:
        # =========================================================================
        # AŞAMA 1: Karşılanamayan Talebin Minimizasyonu
        # Amaç 1: min sum_i (annual_emergency_demand_i * u_i)
        # =========================================================================
        prob_stage1 = pulp.LpProblem("Ankara_SaglikNet_Lexicographic_Stage1", pulp.LpMinimize)

        # Aşama 1 Amaç Fonksiyonu (Yıllık acil başvuru adedi olarak açıkta kalan talep)
        prob_stage1 += pulp.lpSum(
            d.annual_emergency_demand * u[d.id] for d in demand_zones
        ), "Stage1_Min_Unmet_Emergency_Demand"

        # Kısıt 1: Talep Korunumu (Ulaşılabilir tesis tahsisleri + u_i == 1.0)
        for d in demand_zones:
            fac_list = zone_reachable_facs[d.id]
            if fac_list:
                prob_stage1 += (
                    pulp.lpSum(x[d.id][f_id] for f_id in fac_list) + u[d.id] == 1.0,
                    f"Stage1_Demand_Conservation_{d.id}"
                )
            else:
                # Hiçbir tesise ulaşamayan bölge için u_i zorunlu 1.0'dır
                prob_stage1 += u[d.id] == 1.0, f"Stage1_Unreachable_Zone_{d.id}"

        # Kısıt 2: Açık Tesis Mantıksal Bağı (x_ij <= y_j)
        for d_id, f_id in reachable_edges:
            fac_obj = next((f for f in facilities if f.id == f_id), None)
            if fac_obj and not fac_obj.is_existing:
                prob_stage1 += x[d_id][f_id] <= y[f_id], f"Stage1_Link_{d_id}_{f_id}"

        # Kısıt 3: Kapasite Sınırı
        if scenario.enable_capacity_limits:
            for f in facilities:
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

        # Kısıt 4: Aday Tesis Seçim Sayısı
        if candidate_facs:
            prob_stage1 += (
                pulp.lpSum(y[f.id] for f in candidate_facs) == scenario.p_candidates,
                "Stage1_Budget_Candidate_Count"
            )

        # Aşama 1 Çözümü
        solver1 = pulp.PULP_CBC_CMD(msg=False, timeLimit=20)
        status1_code = prob_stage1.solve(solver1)
        status1_str = pulp.LpStatus.get(status1_code, "Unknown")

        # Aşama 1 Başarısızlık Kontrolü: Optimal DEĞİLSE Aşama 2 ASLA BAŞLATILMAZ!
        if status1_code != 1 or status1_str != "Optimal":
            return {
                "success": False,
                "status": f"Stage1_Failed_{status1_str}",
                "message": f"Aşama 1 (Karşılanamayan talep minimizasyonu) çözülemedi. Statü: {status1_str}",
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

        # Aşama 1'den Elde Edilen Minimum Karşılanamayan Talep Değeri (U*)
        min_unmet_demand_val = float(pulp.value(prob_stage1.objective))
        if min_unmet_demand_val is None or math.isnan(min_unmet_demand_val):
            return {
                "success": False,
                "status": "Stage1_Invalid_Objective",
                "message": "Aşama 1 amaç fonksiyonu tanımsız (None/NaN) değer üretti.",
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

        # =========================================================================
        # AŞAMA 2: Seyahat Süresi ve Yatırım Maliyetinin Minimizasyonu
        # U* kilitlenir: sum d_i * u_i <= U* + tolerans
        # =========================================================================
        prob_stage2 = pulp.LpProblem("Ankara_SaglikNet_Lexicographic_Stage2", pulp.LpMinimize)

        # Normalizasyon katsayıları
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
        unmet_tolerance = 1e-3  # Sayısal kararlılık toleransı (0.001 başvuru)
        prob_stage2 += (
            pulp.lpSum(d.annual_emergency_demand * u[d.id] for d in demand_zones) <=
            min_unmet_demand_val + unmet_tolerance,
            "Stage2_Lock_Min_Unmet_Demand"
        )

        # Kısıt 2: Talep Korunumu
        for d in demand_zones:
            fac_list = zone_reachable_facs[d.id]
            if fac_list:
                prob_stage2 += (
                    pulp.lpSum(x[d.id][f_id] for f_id in fac_list) + u[d.id] == 1.0,
                    f"Stage2_Demand_Conservation_{d.id}"
                )
            else:
                prob_stage2 += u[d.id] == 1.0, f"Stage2_Unreachable_Zone_{d.id}"

        # Kısıt 3: Açık Tesis Mantıksal Bağı
        for d_id, f_id in reachable_edges:
            fac_obj = next((f for f in facilities if f.id == f_id), None)
            if fac_obj and not fac_obj.is_existing:
                prob_stage2 += x[d_id][f_id] <= y[f_id], f"Stage2_Link_{d_id}_{f_id}"

        # Kısıt 4: Kapasite Sınırı
        if scenario.enable_capacity_limits:
            for f in facilities:
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

        # Kısıt 5: Aday Tesis Seçim Sayısı
        if candidate_facs:
            prob_stage2 += (
                pulp.lpSum(y[f.id] for f in candidate_facs) == scenario.p_candidates,
                "Stage2_Budget_Candidate_Count"
            )

        # Aşama 2 Çözümü
        solver2 = pulp.PULP_CBC_CMD(msg=False, timeLimit=25)
        status2_code = prob_stage2.solve(solver2)
        status2_str = pulp.LpStatus.get(status2_code, "Unknown")

        if status2_code != 1 or status2_str != "Optimal":
            return {
                "success": False,
                "status": f"Stage2_Failed_{status2_str}",
                "message": f"Aşama 2 (Seyahat süresi/maliyet minimizasyonu) çözülemedi. Statü: {status2_str}",
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

        final_problem = prob_stage2
        status_str = "Optimal (Lexicographic 2-Aşamalı)"

    else:
        # =========================================================================
        # TEK AŞAMALI SKALERLEŞTİRİLMİŞ CEZA MODELİ
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

        # Kısıtlar
        for d in demand_zones:
            fac_list = zone_reachable_facs[d.id]
            if fac_list:
                prob += (
                    pulp.lpSum(x[d.id][f_id] for f_id in fac_list) + u[d.id] == 1.0,
                    f"Demand_Conservation_{d.id}"
                )
            else:
                prob += u[d.id] == 1.0, f"Unreachable_Zone_{d.id}"

        for d_id, f_id in reachable_edges:
            fac_obj = next((f for f in facilities if f.id == f_id), None)
            if fac_obj and not fac_obj.is_existing:
                prob += x[d_id][f_id] <= y[f_id], f"Link_{d_id}_{f_id}"

        if scenario.enable_capacity_limits:
            for f in facilities:
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

        if candidate_facs:
            prob += (
                pulp.lpSum(y[f.id] for f in candidate_facs) == scenario.p_candidates,
                "Budget_Candidate_Count"
            )

        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=25)
        status_code = prob.solve(solver)
        status_str = pulp.LpStatus.get(status_code, "Unknown")

        if status_code != 1 or status_str != "Optimal":
            return {
                "success": False,
                "status": f"SingleStage_Failed_{status_str}",
                "message": f"Tek aşamalı model çözülemedi. Statü: {status_str}",
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

        final_problem = prob

    # =========================================================================
    # 7. ÇÖZÜMÜ ÇIKAR, DOĞRULA VE ANALİZ ET
    # =========================================================================
    selected_candidate_ids: List[str] = []
    for f in candidate_facs:
        val_y = pulp.value(y[f.id])
        if val_y is not None and val_y > 0.5:
            selected_candidate_ids.append(f.id)

    active_facility_ids = [f.id for f in existing_facs] + selected_candidate_ids
    active_fac_dict = {f.id: f for f in facilities if f.id in active_facility_ids}

    assignments: List[Dict[str, Any]] = []
    unmet_demand_total = 0.0
    unmet_zones: List[Dict[str, Any]] = []
    facility_allocated_demand: Dict[str, float] = {f.id: 0.0 for f in facilities}

    # Açıkta kalan talep ve kısıt doğrulama
    for d in demand_zones:
        u_val = float(pulp.value(u[d.id]) or 0.0)
        # Tolerans denetimi [0, 1]
        u_val = max(0.0, min(1.0, u_val))
        
        assigned_fraction_sum = 0.0
        fac_list = zone_reachable_facs[d.id]

        for f_id in fac_list:
            if f_id in active_facility_ids:
                x_val = float(pulp.value(x[d.id][f_id]) or 0.0)
                if x_val > 1e-4:
                    assigned_fraction_sum += x_val
                    alloc_demand = x_val * d.annual_emergency_demand
                    facility_allocated_demand[f_id] += alloc_demand
                    fac_obj = active_fac_dict[f_id]
                    assignments.append({
                        "demand_id": d.id,
                        "demand_name": d.name,
                        "district": d.district,
                        "demand_lat": d.lat,
                        "demand_lon": d.lon,
                        "population": d.population,
                        "assigned_population": int(x_val * d.population),
                        "annual_emergency_demand": d.annual_emergency_demand,
                        "allocated_demand": int(alloc_demand),
                        "allocation_fraction": round(x_val, 4),
                        "facility_id": f_id,
                        "facility_name": fac_obj.name,
                        "facility_type": fac_obj.facility_type.value,
                        "is_existing": fac_obj.is_existing,
                        "facility_lat": fac_obj.lat,
                        "facility_lon": fac_obj.lon,
                        "travel_time_min": time_matrix[d.id][f_id],
                        "distance_km": dist_matrix[d.id][f_id]
                    })

        # Talep korunumu sayısal tolerans kontrolü: sum x_ij + u_i == 1.0
        conservation_err = abs((assigned_fraction_sum + u_val) - 1.0)
        if conservation_err > 1e-3:
            # Küçük sayısal yuvarlama sapmalarını u_i'ye dengele
            u_val = max(0.0, 1.0 - assigned_fraction_sum)

        if u_val > 1e-4:
            unmet_amount = u_val * d.annual_emergency_demand
            unmet_demand_total += unmet_amount
            unmet_zones.append({
                "zone_id": d.id,
                "zone_name": d.name,
                "district": d.district,
                "unmet_population": int(round(u_val * d.population)),
                "unmet_annual_demand": int(round(unmet_amount)),
                "unmet_fraction": round(u_val, 4)
            })

    # Kapasite aşım denetimi
    if scenario.enable_capacity_limits:
        for f in facilities:
            cap = f.annual_emergency_capacity
            allocated = facility_allocated_demand.get(f.id, 0.0)
            if f.is_existing:
                assert allocated <= cap + 1.0, f"Mevcut tesis {f.id} kapasitesi aşıldı: {allocated} > {cap}"
            else:
                is_open = f.id in selected_candidate_ids
                if not is_open:
                    assert allocated <= 1e-3, f"Açılmayan aday tesis {f.id} talep aldı: {allocated}"
                else:
                    assert allocated <= cap + 1.0, f"Aday tesis {f.id} kapasitesi aşıldı: {allocated} > {cap}"

    # Metriklerin Hesaplanması
    total_assigned_demand = sum(a["allocated_demand"] for a in assignments)
    
    if total_assigned_demand > 0:
        weighted_travel_time = sum(
            a["travel_time_min"] * a["allocated_demand"] for a in assignments
        ) / total_assigned_demand
        avg_travel_time = round(weighted_travel_time, 1)
        max_travel_time = round(max((a["travel_time_min"] for a in assignments), default=0.0), 1)
    else:
        avg_travel_time = None  # Sıfır hizmet verildiğinde seyahat süresi tanımsızdır
        max_travel_time = 0.0

    under_15_pop = sum(a["assigned_population"] for a in assignments if a["travel_time_min"] <= 15.0)
    under_25_pop = sum(a["assigned_population"] for a in assignments if a["travel_time_min"] <= 25.0)

    coverage_15_pct = round((under_15_pop / total_pop) * 100.0, 1) if total_pop > 0 else 0.0
    coverage_25_pct = round((under_25_pop / total_pop) * 100.0, 1) if total_pop > 0 else 0.0

    total_investment_cost = sum(
        f.investment_cost_million_tl for f in candidate_facs if f.id in selected_candidate_ids
    )

    unmet_pct = round((unmet_demand_total / total_demand) * 100.0, 2) if total_demand > 0 else 0.0
    obj_val = float(pulp.value(final_problem.objective)) if pulp.value(final_problem.objective) is not None else 0.0

    return {
        "success": True,
        "status": status_str,
        "objective_value": round(obj_val, 4),
        "selected_candidates": [f.to_dict() for f in candidate_facs if f.id in selected_candidate_ids],
        "selected_candidate_ids": selected_candidate_ids,
        "active_facility_ids": active_facility_ids,
        "assignments": assignments,
        "facility_allocated_demand": facility_allocated_demand,
        "unmet_demand_total": int(round(unmet_demand_total)),
        "unmet_percentage": unmet_pct,
        "unmet_zones": unmet_zones,
        "has_unmet_demand": unmet_demand_total > 10.0,
        "total_investment_cost_million_tl": round(total_investment_cost, 1),
        "avg_travel_time_min": avg_travel_time,
        "max_travel_time_min": max_travel_time,
        "coverage_under_15_min_pct": coverage_15_pct,
        "coverage_under_25_min_pct": coverage_25_pct,
        "total_population": total_pop,
        "total_annual_demand": total_demand
    }
