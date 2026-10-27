"""
ANKARA SAĞLIKNET - Veri Paketi
"""
from data.verified_facilities import VERIFIED_HOSPITALS
from data.candidate_sites import CANDIDATE_HOSPITALS
from data.demand_zones import DEMAND_ZONES

def get_all_facilities():
    """Tüm tesisleri (Doğrulanmış Mevcut + Aday Yatırımlar) tek bir liste olarak döner."""
    return VERIFIED_HOSPITALS + CANDIDATE_HOSPITALS

def get_verified_facilities():
    """Yalnızca doğrulanmış resmi mevcut hastaneleri döner."""
    return VERIFIED_HOSPITALS

def get_candidate_facilities():
    """Yalnızca planlanan aday yatırım lokasyonlarını döner."""
    return CANDIDATE_HOSPITALS

def get_demand_zones():
    """TÜİK ADNKS talep bölgelerini döner."""
    return DEMAND_ZONES
