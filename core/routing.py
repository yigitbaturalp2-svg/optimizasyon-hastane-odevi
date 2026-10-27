"""
ANKARA SAĞLIKNET - Ulaşım, Mesafe ve Yönlendirme Motoru
Desteklenen Yöntemler:
1. Tahmini Geometrik Mod (ESTIMATED_GEOMETRIC): Haversine x 1.28 kıvrım katsayısı + saatlik K(t) simülasyon profili.
2. OSRM Yol Ağı Modu (OSRM_NETWORK): OSRM REST servisi üzerinden karayolu süre ve mesafe matrisi.

İlkeler:
- NoRoute (fiziksel karayolu bağlantısı yok) ile ServiceError (zaman aşımı / bağlantı yok) kesinlikle ayırt edilir.
- NoRoute olan eşleşmeler geometrik fallback ile sessizce erişilebilir YAPILMAZ; ulaşılamaz (inf) olarak bırakılır.
- OSRM servis hatasında yalnızca kullanıcının açıkça onayladığı fallback politikası (allow_osrm_fallback_to_geometric=True) uygulanır.
- Sonuç matrisi her zaman kaynak, saat, yöntem ve varsayım metadata'sını taşır.
"""

import math
import urllib.request
import urllib.error
import json
from enum import Enum
from typing import Tuple, Dict, Any, List, Optional
from core.models import DemandZone, Facility


class RoutingMode(str, Enum):
    ESTIMATED_GEOMETRIC = "ESTIMATED_GEOMETRIC"   # Kalibre edilmiş geometrik model (Haversine * 1.28x)
    OSRM_NETWORK = "OSRM_NETWORK"                 # Gerçek karayolu yönlendirme servisi (OSRM)


class RouteResultStatus(str, Enum):
    SUCCESS = "SUCCESS"                           # Rota başarıyla hesaplandı
    NO_ROUTE = "NO_ROUTE"                         # Yol ağı üzerinde fiziksel bağlantı yok
    SERVICE_ERROR = "SERVICE_ERROR"               # OSRM servisi yanıt vermedi / zaman aşımı
    GEOMETRIC_FALLBACK = "GEOMETRIC_FALLBACK"     # Belgelenmiş geometrik yedek devreye alındı


# Ankara saatlik simülasyon trafik çarpanı K(t)
HOURLY_TRAFFIC_PROFILE = {
    0: 1.00, 1: 1.00, 2: 1.00, 3: 1.00, 4: 1.00, 5: 1.05,
    6: 1.20, 7: 1.55, 8: 1.75, 9: 1.50, 10: 1.25, 11: 1.20,
    12: 1.15, 13: 1.15, 14: 1.20, 15: 1.30, 16: 1.45, 17: 1.70,
    18: 1.85, 19: 1.65, 20: 1.40, 21: 1.25, 22: 1.10, 23: 1.05
}


def is_valid_travel_time(t: Any) -> bool:
    """
    Seyahat süresinin geçerli, sonlu ve negatif olmayan bir sayı olduğunu doğrular.
    float('inf'), float('nan') veya negatif değerler için False döner.
    """
    if t is None:
        return False
    try:
        val = float(t)
        return math.isfinite(val) and val >= 0.0
    except (ValueError, TypeError):
        return False


def get_traffic_multiplier(hour: int = 13) -> float:
    """Belirtilen saat için simülasyon trafik çarpanını döner."""
    return HOURLY_TRAFFIC_PROFILE.get(hour, 1.15)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """İki coğrafi koordinat arasındaki küresel büyük daire mesafesini (km) hesaplar."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def try_osrm_route(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    timeout: float = 0.6
) -> Tuple[RouteResultStatus, Optional[float], Optional[float]]:
    """
    OSRM yönlendirme servisine bağlanmayı dener.
    Dönüş: (RouteResultStatus, mesafe_km, süre_dakika)
    Metre -> km ve saniye -> dakika birim dönüşümleri açıkça uygulanır.
    NoRoute durumu ServiceError durumundan kesinlikle ayrılır.
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AnkaraSaglikNet/1.0'})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                code = data.get("code")
                if code == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    dist_km = float(route.get("distance", 0.0)) / 1000.0
                    duration_min = float(route.get("duration", 0.0)) / 60.0
                    if is_valid_travel_time(duration_min) and is_valid_travel_time(dist_km):
                        return RouteResultStatus.SUCCESS, round(dist_km, 2), round(duration_min, 1)
                elif code == "NoRoute":
                    return RouteResultStatus.NO_ROUTE, None, None
                else:
                    return RouteResultStatus.SERVICE_ERROR, None, None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return RouteResultStatus.SERVICE_ERROR, None, None
    except Exception:
        return RouteResultStatus.SERVICE_ERROR, None, None

    return RouteResultStatus.SERVICE_ERROR, None, None


def calculate_geometric_travel(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    hour: int = 13
) -> Dict[str, Any]:
    """
    Kalibre edilmiş geometrik fallback modeline göre seyahat süresi ve mesafesi hesaplar.
    """
    hav_km = haversine_km(lat1, lon1, lat2, lon2)
    # Ankara kentsel ve çeper yol kıvrım faktörü: 1.28
    road_dist_km = max(0.5, hav_km * 1.28)
    
    # Baz serbest hız (km/s)
    if road_dist_km > 25.0:
        base_speed = 78.0  # Şehirlerarası/otoyol bağlantısı
    elif road_dist_km > 10.0:
        base_speed = 60.0  # Ana arterler
    else:
        base_speed = 42.0  # Şehir içi cadde/mahalle
        
    mult = get_traffic_multiplier(hour)
    effective_speed = max(14.0, base_speed / mult)
    
    travel_time_min = round((road_dist_km / effective_speed) * 60.0, 1)
    
    return {
        "distance_km": round(road_dist_km, 1),
        "travel_time_min": travel_time_min,
        "status": RouteResultStatus.SUCCESS,
        "routing_method": "ESTIMATED_GEOMETRIC (Haversine * 1.28x)",
        "traffic_model": f"K({hour:02d}:00) = {mult:.2f}x (Simülasyon)",
        "is_simulated": True
    }


def build_travel_matrix(
    demand_zones: List[DemandZone],
    facilities: List[Facility],
    hour: int = 13,
    routing_mode: RoutingMode = RoutingMode.ESTIMATED_GEOMETRIC,
    allow_osrm_fallback_to_geometric: bool = False
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]], Dict[str, Any]]:
    """
    Tüm talep bölgeleri ile tesisler arasındaki süre ve mesafe matrislerini ve
    açık metodoloji metadata'sını üretir.
    Dönüş: (time_matrix, distance_matrix, routing_metadata)
    """
    time_matrix: Dict[str, Dict[str, float]] = {}
    dist_matrix: Dict[str, Dict[str, float]] = {}
    
    total_pairs = len(demand_zones) * len(facilities)
    unreachable_count = 0
    fallback_count = 0
    osrm_success_count = 0

    for dem in demand_zones:
        time_matrix[dem.id] = {}
        dist_matrix[dem.id] = {}
        for fac in facilities:
            if routing_mode == RoutingMode.OSRM_NETWORK:
                status, dist_km, dur_min = try_osrm_route(dem.lat, dem.lon, fac.lat, fac.lon)
                
                if status == RouteResultStatus.SUCCESS and is_valid_travel_time(dur_min):
                    mult = get_traffic_multiplier(hour)
                    adjusted_dur = round(dur_min * mult, 1)
                    time_matrix[dem.id][fac.id] = adjusted_dur
                    dist_matrix[dem.id][fac.id] = dist_km
                    osrm_success_count += 1
                elif status == RouteResultStatus.NO_ROUTE:
                    # Fiziksel bağlantı yok: Kesinlikle ulaşılamaz kabul edilir (fallback uygulanmaz!)
                    time_matrix[dem.id][fac.id] = float('inf')
                    dist_matrix[dem.id][fac.id] = float('inf')
                    unreachable_count += 1
                else:
                    # ServiceError durumu: Fallback izin verilmişse geometrik model çalışır
                    if allow_osrm_fallback_to_geometric:
                        geo_res = calculate_geometric_travel(dem.lat, dem.lon, fac.lat, fac.lon, hour=hour)
                        time_matrix[dem.id][fac.id] = geo_res["travel_time_min"]
                        dist_matrix[dem.id][fac.id] = geo_res["distance_km"]
                        fallback_count += 1
                    else:
                        time_matrix[dem.id][fac.id] = float('inf')
                        dist_matrix[dem.id][fac.id] = float('inf')
                        unreachable_count += 1
            else:
                # ESTIMATED_GEOMETRIC Modu
                geo_res = calculate_geometric_travel(dem.lat, dem.lon, fac.lat, fac.lon, hour=hour)
                time_matrix[dem.id][fac.id] = geo_res["travel_time_min"]
                dist_matrix[dem.id][fac.id] = geo_res["distance_km"]

    mult = get_traffic_multiplier(hour)
    routing_metadata = {
        "routing_mode": routing_mode.value,
        "hour": hour,
        "traffic_multiplier": mult,
        "traffic_profile_label": f"K({hour:02d}:00) = {mult:.2f}x (Simülasyon Varsayımı)",
        "source": (
            "Open Source Routing Machine (OSRM)"
            if routing_mode == RoutingMode.OSRM_NETWORK
            else "Kalibre Edilmiş Geometrik Model (Haversine x 1.28 Yol Katsayısı)"
        ),
        "total_pairs": total_pairs,
        "unreachable_pairs": unreachable_count,
        "fallback_used": fallback_count > 0,
        "fallback_pairs_count": fallback_count,
        "osrm_success_count": osrm_success_count,
        "is_simulated": True,
        "warning": (
            "Mesafe ve seyahat süreleri simülasyon modelidir; gerçek zamanlı GPS/sensör doğrulaması yapılmamıştır."
        )
    }

    return time_matrix, dist_matrix, routing_metadata
