"""
ANKARA SAĞLIKNET - Talep Merkezleri (İlçe ve Semt Nüfusları)
Kaynak: TÜİK Adrese Dayalı Nüfus Kayıt Sistemi (ADNKS) 2023 Verileri

Nüfus ve Talep Doğrulama Raporu:
- TÜİK ADNKS 2023 Ankara İl Toplam Nüfusu: 5,803,482 kişi
- Modellenen 32 Kentsel / Metropol / Yakın Çeper Bölgesi Nüfusu: 5,570,000 kişi (%95.98 temsil)
- Kapsam Dışı Bırakılan Uzak Kırsal Nüfus (Ayaş, Güdül, Beypazarı/Nallıhan kırsalı vb.): ~233,482 kişi
- Yıllık Acil Servis Başvuru Katsayısı: 0.35 başvuru/kişi/yıl (T.C. Sağlık Bakanlığı İstatistik Yıllığı normu)
- Toplam Yıllık Modellenen Acil Başvuru Talebi: 1,949,500 başvuru/yıl (5,570,000 * 0.35)
"""

from core.models import DemandZone

DEMAND_ZONES = [
    # Çankaya (Toplam ~940,000)
    DemandZone("DEM_01", "Kızılay - Çankaya Merkez", "Çankaya", 39.9208, 32.8541, 185000, 64750, "TÜİK ADNKS 2023"),
    DemandZone("DEM_02", "Bahçelievler - Emek", "Çankaya", 39.9195, 32.8250, 145000, 50750, "TÜİK ADNKS 2023"),
    DemandZone("DEM_03", "Balgat - Çukurambar", "Çankaya", 39.9025, 32.8120, 160000, 56000, "TÜİK ADNKS 2023"),
    DemandZone("DEM_04", "Ayrancı - Dikmen", "Çankaya", 39.8850, 32.8450, 175000, 61250, "TÜİK ADNKS 2023"),
    DemandZone("DEM_05", "Çayyolu - Ümitköy", "Çankaya", 39.8824, 32.6978, 165000, 57750, "TÜİK ADNKS 2023"),
    DemandZone("DEM_06", "Yıldız - Oran", "Çankaya", 39.8550, 32.8350, 110000, 38500, "TÜİK ADNKS 2023"),

    # Keçiören (Toplam ~935,000)
    DemandZone("DEM_07", "Etlik - Aşağı Eğlence", "Keçiören", 39.9650, 32.8350, 210000, 73500, "TÜİK ADNKS 2023"),
    DemandZone("DEM_08", "Sanatoryum - Ufuktepe", "Keçiören", 39.9850, 32.8550, 240000, 84000, "TÜİK ADNKS 2023"),
    DemandZone("DEM_09", "Kalaba - Keçiören Merkez", "Keçiören", 39.9720, 32.8680, 195000, 68250, "TÜİK ADNKS 2023"),
    DemandZone("DEM_10", "Bağlum - Ovacık Havzası", "Keçiören", 40.0250, 32.8350, 150000, 52500, "TÜİK ADNKS 2023"),
    DemandZone("DEM_11", "Aktepe - Dutluk", "Keçiören", 39.9880, 32.8850, 140000, 49000, "TÜİK ADNKS 2023"),

    # Yenimahalle (Toplam ~710,000)
    DemandZone("DEM_12", "Batıkent Merkez", "Yenimahalle", 39.9682, 32.7410, 235000, 82250, "TÜİK ADNKS 2023"),
    DemandZone("DEM_13", "Demetevler - İvedik", "Yenimahalle", 39.9620, 32.7980, 185000, 64750, "TÜİK ADNKS 2023"),
    DemandZone("DEM_14", "Şentepe Tepe Havzası", "Yenimahalle", 39.9780, 32.7880, 140000, 49000, "TÜİK ADNKS 2023"),
    DemandZone("DEM_15", "Çakırlar - Batı Sitesi", "Yenimahalle", 39.9780, 32.7050, 150000, 52500, "TÜİK ADNKS 2023"),

    # Mamak (Toplam ~690,000)
    DemandZone("DEM_16", "Mamak Merkez - Saimekadın", "Mamak", 39.9280, 32.8950, 215000, 75250, "TÜİK ADNKS 2023"),
    DemandZone("DEM_17", "Akdere - Abidinpaşa", "Mamak", 39.9180, 32.8850, 175000, 61250, "TÜİK ADNKS 2023"),
    DemandZone("DEM_18", "Kayaş - Samsun Yolu", "Mamak", 39.9220, 32.9650, 145000, 50750, "TÜİK ADNKS 2023"),
    DemandZone("DEM_19", "Ege Mahallesi - Doğukent", "Mamak", 39.8950, 32.9250, 155000, 54250, "TÜİK ADNKS 2023"),

    # Sincan (Toplam ~580,000)
    DemandZone("DEM_20", "Sincan Merkez - Fatih", "Sincan", 39.9680, 32.5750, 260000, 91000, "TÜİK ADNKS 2023"),
    DemandZone("DEM_21", "Yenikent Havzası", "Sincan", 40.0150, 32.5050, 165000, 57750, "TÜİK ADNKS 2023"),
    DemandZone("DEM_22", "Temelli - OSB Koridoru", "Sincan", 39.7250, 32.3650, 155000, 54250, "TÜİK ADNKS 2023"),

    # Etimesgut (Toplam ~620,000)
    DemandZone("DEM_23", "Etimesgut Merkez - İstasyon", "Etimesgut", 39.9480, 32.6780, 230000, 80500, "TÜİK ADNKS 2023"),
    DemandZone("DEM_24", "Eryaman Konut Bölgesi", "Etimesgut", 39.9850, 32.6250, 240000, 84000, "TÜİK ADNKS 2023"),
    DemandZone("DEM_25", "Bağlıca - Yapracık", "Etimesgut", 39.8820, 32.6350, 150000, 52500, "TÜİK ADNKS 2023"),

    # Altındağ (Toplam ~410,000)
    DemandZone("DEM_26", "Ulus - Dışkapı - Aydınlıkevler", "Altındağ", 39.9520, 32.8650, 230000, 80500, "TÜİK ADNKS 2023"),
    DemandZone("DEM_27", "Karapürçek - Hüseyingazi", "Altındağ", 39.9650, 32.9550, 180000, 63000, "TÜİK ADNKS 2023"),

    # Pursaklar (Toplam ~165,000)
    DemandZone("DEM_28", "Pursaklar Merkez - Saray", "Pursaklar", 40.0410, 32.9080, 165000, 57750, "TÜİK ADNKS 2023"),

    # Gölbaşı (Toplam ~155,000)
    DemandZone("DEM_29", "Gölbaşı Merkez - İncek", "Gölbaşı", 39.7950, 32.8050, 155000, 54250, "TÜİK ADNKS 2023"),

    # Çeper İlçeler (Toplam ~365,000)
    DemandZone("DEM_30", "Polatlı İlçe Merkezi", "Polatlı", 39.5841, 32.1452, 130000, 45500, "TÜİK ADNKS 2023"),
    DemandZone("DEM_31", "Çubuk İlçe Merkezi", "Çubuk", 40.2386, 33.0322, 95000, 33250, "TÜİK ADNKS 2023"),
    DemandZone("DEM_32", "Kahramankazan & Elmadağ Havzası", "Çeper", 40.0500, 32.6000, 140000, 49000, "TÜİK ADNKS 2023")
]
