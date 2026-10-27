"""
ANKARA SAĞLIKNET - Karşılaştırma, Analitik ve Hakkaniyet Metrikleri
Bu modül, iki farklı senaryoyu (örn: Mevcut Durum vs Yeni Yatırımlar)
aynı veri ve ölçüm tanımlarıyla yan yana karşılaştırır.

Güvenlik Garantisi (TEKNİK GÖREV 001.3):
- Bir talep bölgesinin birden fazla hastaneye bölünerek atanması (kesirli tahsis) durumunda
  tekil sözlük ezilmesi engellenmiş, bölge bazlı ağırlıklı ortalama süre grubu oluşturulmuştur.
- Kapsama oranları farklı olduğunda süre farkı koşulsuz başarı olarak sunulmaz; açıkça
  kapsama farkı uyarısı verilir.
- Sıfır hizmet durumunda ortalama süre 0.0 yerine None (tanımsız) kabul edilir.
"""

from typing import Dict, Any, List, Optional
from core.models import DemandZone


def group_zone_allocations(
    scenario_results: Dict[str, Any]
) -> Dict[str, Dict[str, Any]]:
    """
    Bir senaryodaki tahsisleri bölge (demand_id) bazında gruplar ve
    o bölge için taleple ağırlıklandırılmış ortalama seyahat süresini hesaplar.
    """
    assignments = scenario_results.get("assignments", [])
    unmet_zones = {u["zone_id"]: u for u in scenario_results.get("unmet_zones", [])}

    # Bölgeleri topla
    zone_groups: Dict[str, Dict[str, Any]] = {}

    for a in assignments:
        d_id = a["demand_id"]
        if d_id not in zone_groups:
            zone_groups[d_id] = {
                "demand_id": d_id,
                "demand_name": a["demand_name"],
                "district": a["district"],
                "population": a["population"],
                "annual_emergency_demand": a["annual_emergency_demand"],
                "total_allocated_demand": 0.0,
                "unmet_annual_demand": 0.0,
                "facility_allocations": []
            }
        zone_groups[d_id]["total_allocated_demand"] += float(a["allocated_demand"])
        zone_groups[d_id]["facility_allocations"].append({
            "facility_id": a["facility_id"],
            "facility_name": a["facility_name"],
            "allocated_demand": float(a["allocated_demand"]),
            "travel_time_min": float(a["travel_time_min"]),
            "is_existing": a["is_existing"]
        })

    # Hiçbir hastaneye atanamamış (yalnızca unmet olan) bölgeleri ekle
    for z_id, u_info in unmet_zones.items():
        if z_id not in zone_groups:
            zone_groups[z_id] = {
                "demand_id": z_id,
                "demand_name": u_info["zone_name"],
                "district": u_info["district"],
                "population": u_info.get("unmet_population", 0),
                "annual_emergency_demand": u_info["unmet_annual_demand"],
                "total_allocated_demand": 0.0,
                "unmet_annual_demand": float(u_info["unmet_annual_demand"]),
                "facility_allocations": []
            }
        else:
            zone_groups[z_id]["unmet_annual_demand"] = float(u_info["unmet_annual_demand"])

    # Bölge bazlı ağırlıklı ortalama süreyi hesapla
    for d_id, group in zone_groups.items():
        alloc_tot = group["total_allocated_demand"]
        if alloc_tot > 0.0:
            weighted_time_sum = sum(
                h["travel_time_min"] * h["allocated_demand"] for h in group["facility_allocations"]
            )
            group["weighted_avg_travel_time_min"] = round(weighted_time_sum / alloc_tot, 1)
        else:
            group["weighted_avg_travel_time_min"] = None  # Sıfır hizmet durumunda süre tanımsızdır

    return zone_groups


def compare_scenarios(
    scenario_a_results: Dict[str, Any],
    scenario_b_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    İki senaryonun optimizasyon sonuçlarını aynı metriklerle ve kesirli tahsis kaybı olmadan karşılaştırır.
    Senaryo A: Genellikle Mevcut Durum (Baz Senaryo)
    Senaryo B: Genellikle Önerilen Yatırımlar (Yeni Tesisler)
    """
    # Başarısızlık durumunda güvenli dönüş
    if not scenario_a_results.get("success", False) or not scenario_b_results.get("success", False):
        return {
            "is_valid": False,
            "message": "Senaryolardan biri veya her ikisi çözülemedi; karşılaştırma yapılamaz.",
            "travel_time_saved_min": None,
            "top_gaining_districts": [],
            "all_district_comparisons": []
        }

    raw_time_a = scenario_a_results.get("avg_travel_time_min")
    raw_time_b = scenario_b_results.get("avg_travel_time_min")

    time_a = float(raw_time_a) if raw_time_a is not None else None
    time_b = float(raw_time_b) if raw_time_b is not None else None

    # Seyahat süresi farkı (yalnızca her iki senaryoda da geçerli süre varsa)
    if time_a is not None and time_b is not None:
        time_diff = round(time_a - time_b, 1)
        time_diff_pct = round((time_diff / time_a) * 100.0, 1) if time_a > 0 else 0.0
    else:
        time_diff = None
        time_diff_pct = 0.0

    cov15_a = scenario_a_results.get("coverage_under_15_min_pct", 0.0)
    cov15_b = scenario_b_results.get("coverage_under_15_min_pct", 0.0)
    cov15_gain = round(cov15_b - cov15_a, 1)

    max_a = scenario_a_results.get("max_travel_time_min", 0.0)
    max_b = scenario_b_results.get("max_travel_time_min", 0.0)
    max_gain = round(max_a - max_b, 1)

    cost_b = scenario_b_results.get("total_investment_cost_million_tl", 0.0)

    unmet_a = scenario_a_results.get("unmet_percentage", 0.0)
    unmet_b = scenario_b_results.get("unmet_percentage", 0.0)
    unmet_reduced_pct = round(unmet_a - unmet_b, 2)

    has_coverage_difference = abs(unmet_a - unmet_b) > 0.1
    coverage_warning = (
        f"Dikkat: Senaryoların acil talep karşılama oranları farklıdır (%{100-unmet_a:.1f} vs %{100-unmet_b:.1f}). "
        f"Seyahat süresi kazanımı yalnızca hizmet alan nüfus için hesaplanmıştır."
        if has_coverage_difference else ""
    )

    # Bölge bazında gruplanmış karşılaştırma (kesirli tahsis kaybı olmadan)
    groups_a = group_zone_allocations(scenario_a_results)
    groups_b = group_zone_allocations(scenario_b_results)

    all_zone_ids = set(groups_a.keys()).union(set(groups_b.keys()))
    district_comparisons = []

    for d_id in all_zone_ids:
        za = groups_a.get(d_id)
        zb = groups_b.get(d_id)

        name = zb["demand_name"] if zb else za["demand_name"]
        district = zb["district"] if zb else za["district"]
        pop = zb["population"] if zb else za["population"]

        time_zone_a = za.get("weighted_avg_travel_time_min") if za else None
        time_zone_b = zb.get("weighted_avg_travel_time_min") if zb else None

        allocated_a = za.get("total_allocated_demand", 0.0) if za else 0.0
        allocated_b = zb.get("total_allocated_demand", 0.0) if zb else 0.0

        unmet_zone_a = za.get("unmet_annual_demand", 0.0) if za else 0.0
        unmet_zone_b = zb.get("unmet_annual_demand", 0.0) if zb else 0.0

        # Karşılaştırılabilirlik denetimi
        if time_zone_a is not None and time_zone_b is not None:
            time_saved = round(time_zone_a - time_zone_b, 1)
            is_comparable = True
            comp_status = "Tam Karşılaştırılabilir"
        elif time_zone_a is None and time_zone_b is not None:
            time_saved = None
            is_comparable = False
            comp_status = "Senaryo A'da hizmet verilemiyordu (Yeni Kapsama)"
        elif time_zone_a is not None and time_zone_b is None:
            time_saved = None
            is_comparable = False
            comp_status = "Senaryo B'de hizmet kesildi"
        else:
            time_saved = None
            is_comparable = False
            comp_status = "Her iki senaryoda da hizmet dışı"

        # Yeni açılan bir tesise tahsis var mı?
        has_new_fac = any(not h["is_existing"] for h in (zb.get("facility_allocations", []) if zb else []))
        primary_fac_name = zb["facility_allocations"][0]["facility_name"] if (zb and zb["facility_allocations"]) else "Hizmet Yok"

        district_comparisons.append({
            "demand_id": d_id,
            "demand_name": name,
            "district": district,
            "population": pop,
            "scenario_a_time_min": time_zone_a,
            "scenario_b_time_min": time_zone_b,
            "time_saved_min": time_saved,
            "is_comparable": is_comparable,
            "comparison_status": comp_status,
            "allocated_demand_a": round(allocated_a),
            "allocated_demand_b": round(allocated_b),
            "unmet_demand_a": round(unmet_zone_a),
            "unmet_demand_b": round(unmet_zone_b),
            "unmet_demand_reduced": round(unmet_zone_a - unmet_zone_b),
            "assigned_facility": primary_fac_name,
            "has_new_facility_allocation": has_new_fac
        })

    # Karşılaştırılabilir olanlar arasında en yüksek süre tasarrufu sağlayanları sırala
    comparable_districts = [d for d in district_comparisons if d["time_saved_min"] is not None]
    comparable_districts.sort(key=lambda x: x["time_saved_min"], reverse=True)

    return {
        "is_valid": True,
        "travel_time_a_min": time_a,
        "travel_time_b_min": time_b,
        "travel_time_saved_min": time_diff,
        "travel_time_saved_pct": time_diff_pct,
        "coverage_15_a_pct": cov15_a,
        "coverage_15_b_pct": cov15_b,
        "coverage_15_gain_pct": cov15_gain,
        "max_time_a_min": max_a,
        "max_time_b_min": max_b,
        "max_time_gain_min": max_gain,
        "investment_cost_million_tl": cost_b,
        "unmet_a_pct": unmet_a,
        "unmet_b_pct": unmet_b,
        "unmet_reduced_pct": unmet_reduced_pct,
        "has_coverage_difference": has_coverage_difference,
        "coverage_warning": coverage_warning,
        "top_gaining_districts": comparable_districts[:8],
        "all_district_comparisons": district_comparisons
    }
