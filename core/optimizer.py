"""
ANKARA SAĞLIKNET - Elastik Kapasiteli Tesis Yeri Seçimi (CFLP / MILP) Optimizasyon Motoru
Kütüphane: PuLP / COIN-OR CBC
Özellikler:
- Doğrulanmış mevcut tesisler (y_j = 1 sabit) ile yeni aday yatırımların (y_j in {0,1}) ayrımı
- Karşılanamayan talep için elastik slack değişkeni (u_i) ve ceza katsayısı (M)
- Nüfus, acil başvuru talebi ve yatak/başvuru kapasitesi birim tutarlılığı
"""

import pulp
from typing import List, Dict, Any, Optional
from core.models import DemandZone, Facility, OptimizationScenario, DataStatus
from core.routing import build_travel_matrix

def solve_elastic_cflp(
    demand_zones: List[DemandZone],
    facilities: List[Facility],
    scenario: OptimizationScenario
) -> Dict[str, Any]:
    """
    Elastik Kapasiteli Tesis Yeri Seçimi Problemini (Elastic CFLP) çözer.
    """
    # 1. Tesisleri mevcut ve aday olarak ayrıştır
    existing_facs = [f for f in facilities if f.is_existing]
    candidate_facs = [f for f in facilities if not f.is_existing]
    
    # Seyahat matrisini oluştur
    time_matrix, dist_matrix = build_travel_matrix(demand_zones, facilities, hour=scenario.hour)
    
    # 2. PuLP Problemini Başlat
    prob = pulp.LpProblem("Ankara_SaglikNet_Elastic_CFLP", pulp.LpMinimize)
    
    # 3. Karar Değişkenleri
    # y_j: Aday tesisler için ikili karar değişkeni
    y = {}
    for f in candidate_facs:
        y[f.id] = pulp.LpVariable(f"y_{f.id}", cat=pulp.LpBinary)
    # Mevcut tesisler zaten açıktır (y_j = 1)
    for f in existing_facs:
        y[f.id] = 1.0

    # x_ij: i bölgesinin j tesisine tahsis edilen fraksiyonu [0, 1]
    x = {}
    for d in demand_zones:
        x[d.id] = {}
        for f in facilities:
            x[d.id][f.id] = pulp.LpVariable(f"x_{d.id}_{f.id}", lowBound=0.0, upBound=1.0, cat=pulp.LpContinuous)
            
    # u_i: Karşılanamayan talep fraksiyonu (Elastik gevşetme değişkeni) [0, 1]
    u = {}
    for d in demand_zones:
        u[d.id] = pulp.LpVariable(f"u_{d.id}", lowBound=0.0, upBound=1.0, cat=pulp.LpContinuous)

    # 4. Amaç Fonksiyonu
    total_demand = sum(d.annual_emergency_demand for d in demand_zones)
    max_possible_cost = max(1.0, sum(f.investment_cost_million_tl for f in candidate_facs))
    norm_time = max(1.0, total_demand * 45.0)  # 45 dakika referans normalizasyonu
    norm_cost = max(1.0, max_possible_cost)

    # Ulaşım Süresi Maliyeti
    travel_cost_expr = pulp.lpSum(
        (d.annual_emergency_demand * time_matrix[d.id][f.id] * x[d.id][f.id]) / norm_time
        for d in demand_zones
        for f in facilities
    )
    
    # Yatırım Maliyeti (Yalnızca aday tesisler için)
    investment_cost_expr = pulp.lpSum(
        (f.investment_cost_million_tl * y[f.id]) / norm_cost
        for f in candidate_facs
    )
    
    # Karşılanamayan Talep Cezası (M * sum(u_i))
    unmet_penalty_expr = pulp.lpSum(
        scenario.penalize_unmet_demand * u[d.id]
        for d in demand_zones
    )

    prob += (
        scenario.weight_travel_time * travel_cost_expr +
        scenario.weight_investment_cost * investment_cost_expr +
        unmet_penalty_expr
    ), "Total_Scalarized_Objective"

    # 5. Kısıtlar
    # Kısıt 1: Elastik Talep Karşılama (sum(x_ij) + u_i = 1)
    for d in demand_zones:
        prob += (
            pulp.lpSum(x[d.id][f.id] for f in facilities) + u[d.id] == 1.0,
            f"Demand_Conservation_{d.id}"
        )

    # Kısıt 2: Açık Tesis Mantıksal Bağı (x_ij <= y_j)
    for d in demand_zones:
        for f in facilities:
            if not f.is_existing:
                prob += x[d.id][f.id] <= y[f.id], f"Facility_Link_{d.id}_{f.id}"

    # Kısıt 3: Kapasite Sınırı (sum_i d_i * x_ij <= C_j * y_j)
    if scenario.enable_capacity_limits:
        for f in facilities:
            if not f.is_existing:
                prob += (
                    pulp.lpSum(d.annual_emergency_demand * x[d.id][f.id] for d in demand_zones) <=
                    f.annual_emergency_capacity * y[f.id],
                    f"Capacity_Limit_{f.id}"
                )
            else:
                prob += (
                    pulp.lpSum(d.annual_emergency_demand * x[d.id][f.id] for d in demand_zones) <=
                    f.annual_emergency_capacity,
                    f"Capacity_Limit_Existing_{f.id}"
                )

    # Kısıt 4: Yeni Yatırım Bütçe/Adet Kısıtı (sum_{j in Cand} y_j = p)
    if candidate_facs:
        p_val = min(len(candidate_facs), scenario.p_candidates)
        prob += pulp.lpSum(y[f.id] for f in candidate_facs) == p_val, "Budget_Candidate_Count"

    # 6. Çözücüyü Çalıştır
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=20)
    solver_status_code = prob.solve(solver)
    status_str = pulp.LpStatus[solver_status_code]

    # 7. Çözüm Başarısız ise
    if status_str not in ["Optimal", "Not Solved"] or solver_status_code != 1:
        return {
            "success": False,
            "status": status_str,
            "message": f"Model çözülemedi: {status_str}",
            "objective_value": None,
            "selected_candidates": [],
            "unmet_demand_total": total_demand,
            "unmet_percentage": 100.0
        }

    # 8. Sonuçları Çıkar ve Analiz Et
    selected_candidate_ids = [
        f.id for f in candidate_facs
        if pulp.value(y[f.id]) is not None and pulp.value(y[f.id]) > 0.5
    ]
    
    active_facility_ids = [f.id for f in existing_facs] + selected_candidate_ids
    active_fac_dict = {f.id: f for f in facilities if f.id in active_facility_ids}

    # Tahsisler ve Açıkta Kalan Talep
    assignments = []
    unmet_demand_total = 0.0
    unmet_zones = []
    facility_allocated_demand = {f.id: 0.0 for f in facilities}
    
    for d in demand_zones:
        u_val = float(pulp.value(u[d.id]) or 0.0)
        if u_val > 0.001:
            unmet_amount = u_val * d.annual_emergency_demand
            unmet_demand_total += unmet_amount
            unmet_zones.append({
                "zone_id": d.id,
                "zone_name": d.name,
                "district": d.district,
                "unmet_population": int(u_val * d.population),
                "unmet_annual_demand": int(unmet_amount),
                "unmet_fraction": round(u_val, 3)
            })

        for f_id in active_facility_ids:
            x_val = float(pulp.value(x[d.id][f_id]) or 0.0)
            if x_val > 0.001:
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
                    "allocation_fraction": round(x_val, 3),
                    "facility_id": f_id,
                    "facility_name": fac_obj.name,
                    "facility_type": fac_obj.facility_type.value,
                    "is_existing": fac_obj.is_existing,
                    "facility_lat": fac_obj.lat,
                    "facility_lon": fac_obj.lon,
                    "travel_time_min": time_matrix[d.id][f_id],
                    "distance_km": dist_matrix[d.id][f_id]
                })

    # Metriklerin Hesaplanması
    total_assigned_demand = sum(a["allocated_demand"] for a in assignments)
    total_pop = sum(d.population for d in demand_zones)
    
    if total_assigned_demand > 0:
        weighted_travel_time = sum(a["travel_time_min"] * a["allocated_demand"] for a in assignments) / total_assigned_demand
    else:
        weighted_travel_time = 0.0
        
    max_travel_time = max((a["travel_time_min"] for a in assignments), default=0.0)
    
    under_15_pop = sum(a["assigned_population"] for a in assignments if a["travel_time_min"] <= 15.0)
    under_25_pop = sum(a["assigned_population"] for a in assignments if a["travel_time_min"] <= 25.0)
    
    coverage_15_pct = round((under_15_pop / total_pop) * 100.0, 1)
    coverage_25_pct = round((under_25_pop / total_pop) * 100.0, 1)
    
    total_investment_cost = sum(
        f.investment_cost_million_tl for f in candidate_facs if f.id in selected_candidate_ids
    )

    unmet_pct = round((unmet_demand_total / total_demand) * 100.0, 2) if total_demand > 0 else 0.0

    return {
        "success": True,
        "status": status_str,
        "objective_value": round(float(pulp.value(prob.objective)), 4),
        "selected_candidates": [f.to_dict() for f in candidate_facs if f.id in selected_candidate_ids],
        "selected_candidate_ids": selected_candidate_ids,
        "active_facility_ids": active_facility_ids,
        "assignments": assignments,
        "facility_allocated_demand": facility_allocated_demand,
        "unmet_demand_total": int(unmet_demand_total),
        "unmet_percentage": unmet_pct,
        "unmet_zones": unmet_zones,
        "has_unmet_demand": unmet_demand_total > 10.0,
        "total_investment_cost_million_tl": round(total_investment_cost, 1),
        "avg_travel_time_min": round(weighted_travel_time, 1),
        "max_travel_time_min": round(max_travel_time, 1),
        "coverage_under_15_min_pct": coverage_15_pct,
        "coverage_under_25_min_pct": coverage_25_pct,
        "total_population": total_pop,
        "total_annual_demand": total_demand
    }
