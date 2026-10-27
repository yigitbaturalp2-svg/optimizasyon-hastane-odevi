"""
ANKARA SAĞLIKNET - Çekirdek Veri Modelleri ve Tipleri
Bu modül, tesis, talep ve senaryo veri yapılarını ve güvenilirlik statülerini tanımlar.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class DataStatus(str, Enum):
    """Verinin doğruluk ve güvenilirlik seviyesi."""
    VERIFIED_EXISTING = "VERIFIED_EXISTING"         # Resmi makamlarca doğrulanmış gerçek mevcut tesis
    CANDIDATE_INVESTMENT = "CANDIDATE_INVESTMENT"   # Yeni yatırım/planlama önerisi (Aday tesis)
    SIMULATION_ZONE = "SIMULATION_ZONE"             # TÜİK verisiyle modellenen talep bölgesi


class FacilityType(str, Enum):
    """Tesis sınıflandırması."""
    SEHIR_HASTANESI = "Şehir Hastanesi (KÖİ)"
    DEVLET_HASTANESI = "Devlet Hastanesi (Sağlık Bakanlığı)"
    UNIVERSITE_HASTANESI = "Üniversite Hastanesi"
    ADAY_SAGLIK_KAMPUSU = "Aday Sağlık Kampüsü"
    ADAY_ACIL_USSU = "Aday Acil Müdahale Üssü"


@dataclass
class Facility:
    """Sağlık tesisi veri modeli."""
    id: str
    name: str
    district: str
    lat: float
    lon: float
    status: DataStatus
    facility_type: FacilityType
    bed_capacity: int                     # Tescilli/Hedef Yatak Kapasitesi (Yatak)
    annual_emergency_capacity: int        # Yıllık Acil Servis ve Poliklinik Başvuru Kapasitesi (Kişi/Yıl)
    investment_cost_million_tl: float     # Yatırım Maliyeti (Mevcut tesisler için 0.0)
    source: str                           # Resmi veri kaynağı URL / doküman bilgisi
    confidence_score: float = 1.0         # 1.0 = Resmi doğrulanmış, 0.5 = Tahmini
    is_existing: bool = True
    operational_status: str = "Aktif Hizmette"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "district": self.district,
            "lat": self.lat,
            "lon": self.lon,
            "status": self.status.value,
            "facility_type": self.facility_type.value,
            "bed_capacity": self.bed_capacity,
            "annual_emergency_capacity": self.annual_emergency_capacity,
            "investment_cost_million_tl": self.investment_cost_million_tl,
            "source": self.source,
            "confidence_score": self.confidence_score,
            "is_existing": self.is_existing,
            "operational_status": self.operational_status
        }


@dataclass
class DemandZone:
    """Talep bölgesi (İlçe/Semt) veri modeli."""
    id: str
    name: str
    district: str
    lat: float
    lon: float
    population: int                       # TÜİK ADNKS Nüfusu
    annual_emergency_demand: int          # Yıllık Acil Servis Başvuru Talebi (Nüfus * 0.35)
    source: str                           # Veri kaynağı (TÜİK ADNKS)
    confidence_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "district": self.district,
            "lat": self.lat,
            "lon": self.lon,
            "population": self.population,
            "annual_emergency_demand": self.annual_emergency_demand,
            "source": self.source,
            "confidence_score": self.confidence_score
        }


@dataclass
class OptimizationScenario:
    """Optimizasyon çalıştırma senaryosu."""
    name: str
    description: str
    p_candidates: int                     # Açılacak yeni aday tesis sayısı
    weight_travel_time: float             # Ulaşım süresi ağırlığı [0, 1]
    weight_investment_cost: float         # Yatırım maliyeti ağırlığı [0, 1]
    hour: int = 13                        # Günün saati [0, 23]
    enable_capacity_limits: bool = True   # CFLP vs UFLP
    penalize_unmet_demand: float = 1000.0 # Karşılanamayan talep ceza katsayısı (M)
