"""
ANKARA SAĞLIKNET - Çekirdek Veri Modelleri ve Tipleri
Bu modül, tesis, talep ve senaryo veri yapılarını, uygunluk kurallarını ve şeffaf veri kökenini (provenance) tanımlar.
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


class CandidateSelectionMode(str, Enum):
    """Aday tesis seçim ve bütçe kısıtı türü."""
    EXACT_COUNT = "EXACT_COUNT"         # Tam p adet yeni hastane açılması kuralı: sum y_j == p
    MAX_COUNT = "MAX_COUNT"             # En fazla p adet yeni hastane açılması kuralı: sum y_j <= p
    BUDGET_LIMIT = "BUDGET_LIMIT"       # Toplam yatırım bütçesi sınırı: sum F_j * y_j <= B
    COMBINED = "COMBINED"               # Hem en fazla p adet hem bütçe sınırı: sum y_j <= p AND sum F_j * y_j <= B


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
    
    # Hizmet Verme Yetkinliği ve Tesis Rolü (TEKNİK GÖREV 001.3 Kuralı)
    # Varsayılan False: Açıkça hastane nakil yetkinliği doğrulanmamış hiçbir tesis hastane optimizasyonuna giremez!
    can_receive_hospital_transfer: bool = False
    is_comprehensive_hospital: bool = False  # Üçüncü basamak / kapsamlı hastane statüsü

    # Ayrıntılı Veri Kökeni (Data Provenance)
    name_source: str = ""
    coordinate_source: str = ""
    capacity_source: str = ""
    last_verified_date: Optional[str] = None
    capacity_is_simulated: bool = True

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
            "operational_status": self.operational_status,
            "can_receive_hospital_transfer": self.can_receive_hospital_transfer,
            "is_comprehensive_hospital": self.is_comprehensive_hospital,
            "name_source": self.name_source,
            "coordinate_source": self.coordinate_source,
            "capacity_source": self.capacity_source,
            "last_verified_date": self.last_verified_date,
            "capacity_is_simulated": self.capacity_is_simulated
        }


def is_eligible_for_hospital_optimization(facility: Facility) -> bool:
    """
    Bir tesisin genel hastane nakil optimizasyonunda hasta kabul hedefi olmaya
    uygun olup olmadığını belirler.
    Kural: can_receive_hospital_transfer açıkça True olmalıdır.
    Acil müdahale üsleri (ADAY_ACIL_USSU) genel hastane nakil hedefi olamaz.
    """
    if not getattr(facility, "can_receive_hospital_transfer", False):
        return False
    # Acil müdahale üssü genel hastane olamaz
    if facility.facility_type == FacilityType.ADAY_ACIL_USSU:
        return False
    return True


def is_verified_comprehensive_hospital(facility: Facility) -> bool:
    """
    Bir tesisin kapsamlı (üçüncü basamak / tam teşekküllü) hastane olup olmadığını doğrular.
    Kural: Varsayılan olarak True KABUL EDİLMEZ.
    Tesis açıkça is_comprehensive_hospital=True olarak işaretlenmiş olmalı ve
    geçerli bir hastane türüne (Şehir, Devlet, Üniversite) sahip olmalıdır.
    """
    if not getattr(facility, "is_comprehensive_hospital", False):
        return False
    comprehensive_types = {
        FacilityType.SEHIR_HASTANESI,
        FacilityType.DEVLET_HASTANESI,
        FacilityType.UNIVERSITE_HASTANESI
    }
    return facility.facility_type in comprehensive_types


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
    candidate_selection_mode: CandidateSelectionMode = CandidateSelectionMode.EXACT_COUNT
    p_candidates: int = 1                           # Açılacak hedef aday tesis sayısı
    max_investment_budget_million_tl: Optional[float] = None  # Maksimum parasal yatırım bütçesi (Milyon TL)
    weight_travel_time: float = 1.0                 # Ulaşım süresi ağırlığı [0, 1]
    weight_investment_cost: float = 0.0             # Yatırım maliyeti ağırlığı [0, 1]
    hour: int = 13                                  # Günün saati [0, 23]
    enable_capacity_limits: bool = True             # CFLP vs UFLP
    penalize_unmet_demand: float = 1000.0           # Karşılanamayan talep ceza katsayısı (M)
    use_lexicographic: bool = True                  # İki aşamalı Lexicographic optimizasyon
    max_travel_time_cutoff_min: Optional[float] = None  # Maksimum erişilebilirlik kesim eşiği (dakika)
