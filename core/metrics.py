"""
ANKARA SAĞLIKNET - Karşılaştırma, Analitik ve Hakkaniyet Metrikleri
Bu modül, iki farklı senaryoyu (örn: Mevcut Durum vs Yeni Yatırımlar)
aynı veri ve ölçüm tanımlarıyla yan yana karşılaştırır.
"""

from typing import Dict, Any, List

def compare_scenarios(scenario_a_results: Dict[str, Any], scenario_b_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    İki senaryonun optimizasyon sonuçlarını aynı metriklerle karşılaştırır.
    Senaryo A: Genellikle Mevcut Durum (p=0)
    Senaryo B: Genellikle Önerilen Yatırımlar (p>0)
    """
    time_a = scenario_a_results.get("avg_travel_time_min", 0.0)
    time_b = scenario_b_results.get("avg_travel_time_min", 0.0)
    time_diff = time_a - time_b
    time_diff_pct = round((time_diff / time_a) * 100.0, 1) if time_a > 0 else 0.0

    cov15_a = scenario_a_results.get("coverage_under_15_min_pct", 0.0)
    cov15_b = scenario_b_results.get("coverage_under_15_min_pct", 0.0)
    cov15_gain = round(cov15_b - cov15_a, 1)

    max_a = scenario_a_results.get("max_travel_time_min", 0.0)
    max_b = scenario_b_results.get("max_travel_time_min", 0.0)
    max_gain = round(max_a - max_b, 1)

    cost_b = scenario_b_results.get("total_investment_cost_million_tl", 0.0)

    unmet_a = scenario_a_results.get("unmet_percentage", 0.0)
    unmet_b = scenario_b_results.get("unmet_percentage", 0.0)

    # İlçe bazında kazanımların sıralanması
    # Her bölge için A'daki en iyi süre ile B'deki en iyi süreyi karşılaştır
    ass_a = {a["demand_id"]: a for a in scenario_a_results.get("assignments", [])}
    ass_b = {b["demand_id"]: b for b in scenario_b_results.get("assignments", [])}

    district_gains = []
    for d_id, item_b in ass_b.items():
        if d_id in ass_a:
            t_a = ass_a[d_id]["travel_time_min"]
            t_b = item_b["travel_time_min"]
            saved = round(t_a - t_b, 1)
            district_gains.append({
                "demand_id": d_id,
                "demand_name": item_b["demand_name"],
                "district": item_b["district"],
                "population": item_b["population"],
                "scenario_a_time_min": t_a,
                "scenario_b_time_min": t_b,
                "time_saved_min": saved,
                "assigned_facility": item_b["facility_name"],
                "is_new_facility": not item_b["is_existing"]
            })

    district_gains.sort(key=lambda x: x["time_saved_min"], reverse=True)

    return {
        "travel_time_a_min": time_a,
        "travel_time_b_min": time_b,
        "travel_time_saved_min": round(time_diff, 1),
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
        "top_gaining_districts": district_gains[:8],
        "all_district_comparisons": district_gains
    }
