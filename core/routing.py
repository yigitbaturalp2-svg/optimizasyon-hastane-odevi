"""
ANKARA SAĞLIKNET - Ulaşım, Mesafe ve Yönlendirme Motoru
Desteklenen Yöntemler:
1. OSRM (Open Source Routing Machine) REST API (Yerel veya Açık Kaynak)
2. Kalibre Edilmiş Geometrik Mesafe (Haversine + 1.28x Ankara Şehir İçi Eğrilik Katsayısı)
Uyarı: Gerçek zamanlı trafik sensörü bulunmadığında simülasyon profili K(t) açıkça belirtilir.
"""

import math
import urllib.request
import json
from typing import Tuple, Dict, Any, List
from core.models import DemandZone, Facility

# Ankara saatlik simülasyon trafik çarpanı K(t)
HOURLY_TRAFFIC_PROFILE = {
    0: 1.00, 1: 1.00, 2: 1.00, 3: 1.00, 4: 1.00, 5: 1.05,
    6: 1.20, 7: 1.55, 8: 1.75, 9: 1.50, 10: 1.25, 11: 1.20,
    12: 1.15, 13: 1.15, 14: 1.20, 15: 1.30, 16: 1.45, 17: 1.70,
    18: 1.85, 19: 1.65, 20: 1.40, 21: 1.25, 22: 1.10, 23: 1.05
}

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

def try_osrm_route(lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[bool, float, float]:
    """
    Yerel veya genel OSRM yönlendirme servisine bağlanmayı dener.
    Dönüş: (başarılı_mı, mesafe_km, süre_dakika)
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'AnkaraSaglikNet/1.0'})
        with urllib.request.urlopen(req, timeout=0.6) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    dist_km = route["distance"] / 1000.0
                    duration_min = route["duration"] / 60.0
                    return True, round(dist_km, 2), round(duration_min, 1)
    except Exception:
        pass
    return False, 0.0, 0.0

def calculate_travel_time(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    hour: int = 13,
    allow_osrm: bool = False
) -> Dict[str, Any]:
    """
    İki nokta arasındaki seyahat süresi ve mesafesini hesaplar.
    Varsayılan olarak doğrulanmış kalibre geometrik modeli kullanır.
    """
    # 1. OSRM denenmesi (opsiyonel)
    if allow_osrm:
        success, dist_km, dur_min = try_osrm_route(lat1, lon1, lat2, lon2)
        if success:
            mult = get_traffic_multiplier(hour)
            adjusted_dur = round(dur_min * mult, 1)
            return {
                "distance_km": dist_km,
                "travel_time_min": adjusted_dur,
                "routing_method": "OSRM_ONLINE_ROUTING",
                "traffic_model": f"K({hour:02d}:00) = {mult:.2f}x (Simülasyon)",
                "is_simulated": True
            }

    # 2. Kalibre Edilmiş Geometrik Fallback Modeli
    hav_km = haversine_km(lat1, lon1, lat2, lon2)
    # Ankara kentsel ve çeper yol kıvrım faktörü: 1.28
    road_dist_km = max(0.5, hav_km * 1.28)
    
    # Baz serbest hız (km/s)
    if road_dist_km > 25.0:
        base_speed = 78.0  # Şehirlerarası/otoyol bağlantısı
    elif road_dist_km > 10.0:
        base_speed = 60.0  # Ana arterler (Eskişehir, Konya, Çevre yolu)
    else:
        base_speed = 42.0  # Şehir içi cadde/mahalle
        
    mult = get_traffic_multiplier(hour)
    effective_speed = max(14.0, base_speed / mult)
    
    travel_time_min = round((road_dist_km / effective_speed) * 60.0, 1)
    
    return {
        "distance_km": round(road_dist_km, 1),
        "travel_time_min": travel_time_min,
        "routing_method": "ESTIMATED_GEOMETRIC_FALLBACK (Haversine * 1.28x)",
        "traffic_model": f"K({hour:02d}:00) = {mult:.2f}x (Simülasyon)",
        "is_simulated": True,
        "warning": "Mesafe ve süreler kalibre edilmiş geometrik model varsayımıdır; gerçek zamanlı GPS/sensör doğrulaması yapılmamıştır."
    }

def build_travel_matrix(
    demand_zones: List[DemandZone],
    facilities: List[Facility],
    hour: int = 13
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """
    Tüm talep bölgeleri ile tesisler arasındaki süre ve mesafe matrislerini üretir.
    Dönüş: (time_matrix, distance_matrix)
    """
    time_matrix = {}
    dist_matrix = {}
    
    for dem in demand_zones:
        time_matrix[dem.id] = {}
        dist_matrix[dem.id] = {}
        for fac in facilities:
            res = calculate_travel_time(dem.lat, dem.lon, fac.lat, fac.lon, hour=hour)
            time_matrix[dem.id][fac.id] = res["travel_time_min"]
            dist_matrix[dem.id][fac.id] = res["distance_km"]
            
    return time_matrix, dist_matrix
