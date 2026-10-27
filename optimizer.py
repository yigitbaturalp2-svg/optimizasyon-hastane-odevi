"""
Ankara Hastane Konumlandırma Optimizasyonu - Matematiksel Model (CFLP / UFLP)
(Capacitated / Uncapacitated Facility Location Problem Formulation)

Kullanılan Yaklaşım:
- Karma Tamsayılı Doğrusal Programlama (Mixed Integer Linear Programming - MILP)
- Çözücü: PuLP / COIN-OR CBC Solver
- Çok Amaçlı Skalarizasyon (Multi-Objective Scalarization):
    Amaç 1: Toplam Nüfus-Seyahat Süresi Minimizasyonu (Ulaşım Verimliliği)
    Amaç 2: Toplam Hastane Yapım & Arsa Maliyeti Minimizasyonu (Bütçe Verimliliği)
"""

import pulp
from data import DEMAND_POINTS, CANDIDATE_SITES, build_travel_matrix

def solve_hospital_location(
    p_hospitals=5,
    weight_travel_time=0.6,
    weight_cost=0.4,
    enable_capacity=True,
    max_travel_time_threshold=None,
    budget_max_million=None,
    force_hospitals=None,
    hour=13
):
    """
    Parametreler:
    - p_hospitals (int): Açılması hedeflenen toplam hastane sayısı
    - weight_travel_time (float): Ulaşım süresinin amaç fonksiyonundaki ağırlığı (0.0 - 1.0)
    - weight_cost (float): Hastane yapım maliyetinin ağırlığı (0.0 - 1.0)
    - enable_capacity (bool): CFLP (True) veya UFLP (False)
    - max_travel_time_threshold (float): Acil servis için maks seyahat süresi (dakika)
    - budget_max_million (float): Üst bütçe sınırı (opsiyonel)
    - force_hospitals (list): Zorunlu açılması istenen hastane ID'leri
    - hour (int): Günün saati (0-23) - Trafik senaryosu için
    """
    time_matrix, dist_matrix = build_travel_matrix(hour=hour)
    
    demand_ids = [d["id"] for d in DEMAND_POINTS]
    candidate_ids = [c["id"] for c in CANDIDATE_SITES]
    
    dem_dict = {d["id"]: d for d in DEMAND_POINTS}
    cand_dict = {c["id"]: c for c in CANDIDATE_SITES}
    
    # 1. MODEL TANIMI
    prob = pulp.LpProblem("Ankara_Hospital_Location_Problem", pulp.LpMinimize)
    
    # 2. KARAR DEĞİŞKENLERİ
    # y[j] = 1 ise j aday konumuna hastane inşa edilir, aksi halde 0
    y = pulp.LpVariable.dicts("Hospital_Open", candidate_ids, cat=pulp.LpBinary)
    
    # x[i, j] = i talep noktasının j hastanesine tahsis edilen nüfus oranı (0.0 - 1.0)
    x = pulp.LpVariable.dicts("Assign_Dem_Hosp", 
                              ((i, j) for i in demand_ids for j in candidate_ids),
                              lowBound=0.0, upBound=1.0, cat=pulp.LpContinuous)
    
    # Normalizasyon faktörleri (Ağırlıklı toplamı adil ölçeklemek için)
    # Temsili normalizasyon: Ortalama seyahat süresi x toplam nüfus & Ortalama maliyet
    total_population = sum(d["population"] for d in DEMAND_POINTS)
    base_time_norm = total_population * 25.0  # ~25 dk ortalama kabulü
    base_cost_norm = p_hospitals * 800.0     # ~800M TL hastane başı ortalama maliyet
    
    # 3. AMAÇ FONKSİYONU BİLEŞENLERİ
    # Terim 1: Nüfus x Seyahat Süresi toplamı
    travel_time_term = pulp.lpSum(
        dem_dict[i]["population"] * time_matrix[i][j] * x[i, j]
        for i in demand_ids for j in candidate_ids
    ) / base_time_norm
    
    # Terim 2: Hastane Yapım & Arsa Maliyetleri toplamı
    construction_cost_term = pulp.lpSum(
        cand_dict[j]["cost_million_tl"] * y[j]
        for j in candidate_ids
    ) / base_cost_norm
    
    prob += (weight_travel_time * travel_time_term + weight_cost * construction_cost_term), "Total_Weighted_Objective"
    
    # 4. KISITLAR (CONSTRAINTS)
    
    # Kısıt 1: Her talep noktasının nüfusu tam olarak karşılanmalıdır
    for i in demand_ids:
        prob += pulp.lpSum(x[i, j] for j in candidate_ids) == 1.0, f"Demand_Satisfaction_{i}"
        
    # Kısıt 2: Sadece açık hastanelere tahsis yapılabilir (Linking Constraint)
    for i in demand_ids:
        for j in candidate_ids:
            prob += x[i, j] <= y[j], f"Link_{i}_{j}"
            
    # Kısıt 3: Toplam açılacak hastane sayısı kısıtı
    if p_hospitals is not None and p_hospitals > 0:
        prob += pulp.lpSum(y[j] for j in candidate_ids) == p_hospitals, "Target_Hospital_Count"
        
    # Kısıt 4: Bütçe kısıtı (varsa)
    if budget_max_million is not None and budget_max_million > 0:
        prob += pulp.lpSum(cand_dict[j]["cost_million_tl"] * y[j] for j in candidate_ids) <= budget_max_million, "Max_Budget"
        
    # Kısıt 5: Kapasite kısıtı (CFLP)
    if enable_capacity:
        for j in candidate_ids:
            prob += pulp.lpSum(dem_dict[i]["population"] * x[i, j] for i in demand_ids) <= cand_dict[j]["capacity"] * y[j], f"Capacity_{j}"
            
    # Kısıt 6: Maksimum Ulaşım Süresi Eşik Kısıtı (Acil Erişim Güvencesi)
    if max_travel_time_threshold is not None and max_travel_time_threshold > 0:
        for i in demand_ids:
            for j in candidate_ids:
                if time_matrix[i][j] > max_travel_time_threshold:
                    prob += x[i, j] == 0.0, f"Max_Time_Cutoff_{i}_{j}"
                    
    # Kısıt 7: Zorunlu Açık Konumlar
    if force_hospitals:
        for f_id in force_hospitals:
            if f_id in candidate_ids:
                prob += y[f_id] == 1.0, f"Force_Open_{f_id}"
                
    # 5. ÇÖZÜM
    # Sessiz modda CBC çözücüsünü çalıştır
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)
    
    if pulp.LpStatus[status] != "Optimal":
        return {
            "success": False,
            "status": pulp.LpStatus[status],
            "message": "Belirtilen kısıtlar altında uygun bir optimal çözüm bulunamadı. Lütfen hastane sayısını artırın veya acil servis süre kısıtını gevşetin."
        }
        
    # 6. SONUÇLARIN DERLENMESİ
    selected_hospitals = []
    total_cost = 0.0
    hospital_allocated_pop = {j: 0 for j in candidate_ids}
    
    for j in candidate_ids:
        if pulp.value(y[j]) > 0.5:
            cand_info = cand_dict[j].copy()
            selected_hospitals.append(cand_info)
            total_cost += cand_info["cost_million_tl"]
            
    # Eşleşmeler (Assignments)
    assignments = []
    total_pop_weighted_time = 0.0
    coverage_under_15_min = 0
    coverage_under_25_min = 0
    max_travel_time_observed = 0.0
    
    for i in demand_ids:
        dem = dem_dict[i]
        pop = dem["population"]
        # En yüksek tahsis alan hastaneyi bul
        assigned_hosp_id = None
        max_ratio = -1.0
        for j in candidate_ids:
            ratio = pulp.value(x[i, j])
            if ratio and ratio > 0.01:
                hospital_allocated_pop[j] += int(pop * ratio)
                if ratio > max_ratio:
                    max_ratio = ratio
                    assigned_hosp_id = j
                    
        hosp_info = cand_dict[assigned_hosp_id]
        t_time = time_matrix[i][assigned_hosp_id]
        d_dist = dist_matrix[i][assigned_hosp_id]
        
        total_pop_weighted_time += pop * t_time
        if t_time <= 15.0:
            coverage_under_15_min += pop
        if t_time <= 25.0:
            coverage_under_25_min += pop
            
        if t_time > max_travel_time_observed:
            max_travel_time_observed = t_time
            
        assignments.append({
            "demand_id": i,
            "demand_name": dem["name"],
            "district": dem["district"],
            "demand_lat": dem["lat"],
            "demand_lon": dem["lon"],
            "population": pop,
            "hospital_id": assigned_hosp_id,
            "hospital_name": hosp_info["name"],
            "hospital_lat": hosp_info["lat"],
            "hospital_lon": hosp_info["lon"],
            "travel_time_min": t_time,
            "distance_km": d_dist
        })
        
    avg_travel_time = total_pop_weighted_time / total_population
    rate_15_min = (coverage_under_15_min / total_population) * 100.0
    rate_25_min = (coverage_under_25_min / total_population) * 100.0
    
    # Seçilen hastanelere yüklenen nüfus bilgilerini ekle
    for hosp in selected_hospitals:
        h_id = hosp["id"]
        hosp["allocated_population"] = hospital_allocated_pop[h_id]
        hosp["utilization_pct"] = round((hospital_allocated_pop[h_id] / hosp["capacity"]) * 100.0, 1)
        
    return {
        "success": True,
        "status": "Optimal",
        "p_hospitals": p_hospitals,
        "selected_hospitals": selected_hospitals,
        "assignments": assignments,
        "total_cost_million_tl": round(total_cost, 1),
        "avg_travel_time_min": round(avg_travel_time, 1),
        "max_travel_time_min": round(max_travel_time_observed, 1),
        "coverage_under_15_min_pct": round(rate_15_min, 1),
        "coverage_under_25_min_pct": round(rate_25_min, 1),
        "total_population": total_population
    }

if __name__ == "__main__":
    res = solve_hospital_location(p_hospitals=5, weight_travel_time=0.5, weight_cost=0.5)
    print("Çözüm Durumu:", res["status"])
    print("Toplam Maliyet:", res["total_cost_million_tl"], "Milyon TL")
    print("Ortalama Seyahat Süresi:", res["avg_travel_time_min"], "dk")
    print("15 Dk Altı Nüfus Kapsama Oranı: %", res["coverage_under_15_min_pct"])
    print("Seçilen Hastaneler:")
    for h in res["selected_hospitals"]:
        print(f" - {h['name']} ({h['district']}): Kapasite Kullanımı %{h['utilization_pct']} ({h['cost_million_tl']} Milyon TL)")
