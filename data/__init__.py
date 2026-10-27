"""
ANKARA SAĞLIKNET - Veri Paketi
Doğrulanmış mevcut hastaneler, aday sağlık kampüsleri, acil müdahale üsleri ve talep merkezleri.
"""

from data.verified_facilities import VERIFIED_HOSPITALS
from data.candidate_sites import CANDIDATE_HOSPITALS
from data.demand_zones import DEMAND_ZONES
from core.models import is_eligible_for_hospital_optimization, FacilityType

def get_all_facilities():
    """Tüm tesisleri (Doğrulanmış Mevcut + Tüm Aday Yatırımlar) tek bir liste olarak döner."""
    return VERIFIED_HOSPITALS + CANDIDATE_HOSPITALS

def get_verified_facilities():
    """Yalnızca doğrulanmış resmi mevcut hastaneleri (20 adet) döner."""
    return VERIFIED_HOSPITALS

def get_candidate_facilities():
    """Tüm aday yatırım sahalarını (6 hastane + 4 acil üssü = 10 adet) döner."""
    return CANDIDATE_HOSPITALS

def get_eligible_candidate_hospitals():
    """Genel hastane optimizasyonuna uygun aday hastane kampüslerini (6 adet) döner."""
    return [f for f in CANDIDATE_HOSPITALS if is_eligible_for_hospital_optimization(f)]

def get_candidate_emergency_posts():
    """Faz 002 için ayrılmış acil müdahale ve takviye istasyonu adaylarını (4 adet) döner."""
    return [f for f in CANDIDATE_HOSPITALS if f.facility_type == FacilityType.ADAY_ACIL_USSU]

def get_demand_zones():
    """TÜİK ADNKS 2023 32 kentsel ve yakın çeper talep bölgesini döner."""
    return DEMAND_ZONES
