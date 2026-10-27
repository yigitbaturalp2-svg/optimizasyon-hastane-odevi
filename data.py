"""
Ankara İli Hastane Yeri Seçimi, Toplu Taşıma ve Dinamik Trafik Veri Seti
(Ankara Facility Location, High-Fidelity Road Network, Transit & Live Traffic Dataset)
"""

import math
import pandas as pd
import numpy as np

# 1. TALEP NOKTALARI (DEMAND POINTS - NÜFUS MERKEZLERİ)
DEMAND_POINTS = [
    # Çankaya Semtleri (~950.000)
    {"id": "DEM_01", "name": "Kızılay - Çankaya Merkez", "district": "Çankaya", "lat": 39.9208, "lon": 32.8541, "population": 220000},
    {"id": "DEM_02", "name": "Çayyolu - Ümitköy", "district": "Çankaya", "lat": 39.8824, "lon": 32.6978, "population": 190000},
    {"id": "DEM_03", "name": "Balgat - Öveçler", "district": "Çankaya", "lat": 39.8967, "lon": 32.8189, "population": 160000},
    {"id": "DEM_04", "name": "Ayrancı - Dikmen", "district": "Çankaya", "lat": 39.8856, "lon": 32.8425, "population": 230000},
    {"id": "DEM_05", "name": "İncek - Beytepe", "district": "Çankaya", "lat": 39.8315, "lon": 32.7380, "population": 150000},

    # Keçiören Semtleri (~940.000)
    {"id": "DEM_06", "name": "Keçiören Merkez - Gazino", "district": "Keçiören", "lat": 39.9875, "lon": 32.8652, "population": 360000},
    {"id": "DEM_07", "name": "Etlik - Ayvalı", "district": "Keçiören", "lat": 39.9723, "lon": 32.8291, "population": 280000},
    {"id": "DEM_08", "name": "Ovacık - Bağlum", "district": "Keçiören", "lat": 40.0312, "lon": 32.8489, "population": 300000},

    # Yenimahalle Semtleri (~710.000)
    {"id": "DEM_09", "name": "Batıkent - Çakırlar", "district": "Yenimahalle", "lat": 39.9682, "lon": 32.7410, "population": 320000},
    {"id": "DEM_10", "name": "Demetevler - İvedik", "district": "Yenimahalle", "lat": 39.9678, "lon": 32.7985, "population": 250000},
    {"id": "DEM_11", "name": "Şentepe", "district": "Yenimahalle", "lat": 39.9862, "lon": 32.7931, "population": 140000},

    # Mamak Semtleri (~690.000)
    {"id": "DEM_12", "name": "Mamak Merkez - Abidinpaşa", "district": "Mamak", "lat": 39.9285, "lon": 32.8942, "population": 280000},
    {"id": "DEM_13", "name": "Natoyolu - Ege Mahallesi", "district": "Mamak", "lat": 39.8974, "lon": 32.9231, "population": 240000},
    {"id": "DEM_14", "name": "Kayaş - Yeşilbayır", "district": "Mamak", "lat": 39.9412, "lon": 32.9685, "population": 170000},

    # Etimesgut Semtleri (~620.000)
    {"id": "DEM_15", "name": "Eryaman", "district": "Etimesgut", "lat": 39.9812, "lon": 32.6189, "population": 250000},
    {"id": "DEM_16", "name": "Etimesgut Merkez - Elvankent", "district": "Etimesgut", "lat": 39.9392, "lon": 32.6684, "population": 230000},
    {"id": "DEM_17", "name": "Bağlıca", "district": "Etimesgut", "lat": 39.9015, "lon": 32.6398, "population": 140000},

    # Sincan Semtleri (~580.000)
    {"id": "DEM_18", "name": "Sincan Merkez - Fatih", "district": "Sincan", "lat": 39.9612, "lon": 32.5789, "population": 360000},
    {"id": "DEM_19", "name": "Yenikent", "district": "Sincan", "lat": 40.0125, "lon": 32.5120, "population": 220000},

    # Altındağ Semtleri (~410.000)
    {"id": "DEM_20", "name": "Ulus - Altındağ Merkez", "district": "Altındağ", "lat": 39.9421, "lon": 32.8592, "population": 160000},
    {"id": "DEM_21", "name": "Aydınlıkevler - Siteler", "district": "Altındağ", "lat": 39.9615, "lon": 32.8831, "population": 120000},
    {"id": "DEM_22", "name": "Karapürçek", "district": "Altındağ", "lat": 39.9642, "lon": 32.9421, "population": 130000},

    # Çevre ve Metropol İlçeler
    {"id": "DEM_23", "name": "Pursaklar Merkez - Saray", "district": "Pursaklar", "lat": 40.0384, "lon": 32.9014, "population": 165000},
    {"id": "DEM_24", "name": "Gölbaşı Merkez", "district": "Gölbaşı", "lat": 39.7895, "lon": 32.8091, "population": 155000},
    {"id": "DEM_25", "name": "Polatlı Merkez", "district": "Polatlı", "lat": 39.5841, "lon": 32.1452, "population": 130000},
    {"id": "DEM_26", "name": "Çubuk Merkez", "district": "Çubuk", "lat": 40.2389, "lon": 33.0315, "population": 95000},
    {"id": "DEM_27", "name": "Kahramankazan", "district": "Kahramankazan", "lat": 40.1982, "lon": 32.6841, "population": 60000},
    {"id": "DEM_28", "name": "Elmadağ", "district": "Elmadağ", "lat": 39.9192, "lon": 33.2289, "population": 45000},
    {"id": "DEM_29", "name": "Akyurt", "district": "Akyurt", "lat": 40.1312, "lon": 33.0841, "population": 42000},
    {"id": "DEM_30", "name": "Beypazarı", "district": "Beypazarı", "lat": 40.1685, "lon": 31.9214, "population": 50000},
    {"id": "DEM_31", "name": "Kızılcahamam", "district": "Kızılcahamam", "lat": 40.4715, "lon": 32.6512, "population": 28000},
    {"id": "DEM_32", "name": "Haymana", "district": "Haymana", "lat": 39.4325, "lon": 32.4981, "population": 27000},
]

# 2. ADAY HASTANE KONUMLARI
CANDIDATE_SITES = [
    {"id": "CAND_01", "name": "Batıkent - Çakırlar Batı Aksı", "district": "Yenimahalle", "lat": 39.9750, "lon": 32.7210, "cost_million_tl": 850, "capacity": 1400000, "icu_beds": 140, "ambulances": 14},
    {"id": "CAND_02", "name": "Eryaman - Göksu Parkı Kuzeyi", "district": "Etimesgut", "lat": 39.9920, "lon": 32.6050, "cost_million_tl": 750, "capacity": 1200000, "icu_beds": 120, "ambulances": 12},
    {"id": "CAND_03", "name": "Sincan - Yenikent Çevre Yolu", "district": "Sincan", "lat": 39.9980, "lon": 32.5350, "cost_million_tl": 620, "capacity": 1100000, "icu_beds": 110, "ambulances": 10},
    {"id": "CAND_04", "name": "Etimesgut - Bağlıca Bulvarı", "district": "Etimesgut", "lat": 39.9120, "lon": 32.6510, "cost_million_tl": 890, "capacity": 1200000, "icu_beds": 120, "ambulances": 12},
    {"id": "CAND_05", "name": "Çayyolu - Alacaatlı Kavşağı", "district": "Çankaya", "lat": 39.8650, "lon": 32.6820, "cost_million_tl": 1150, "capacity": 1300000, "icu_beds": 130, "ambulances": 14},
    {"id": "CAND_06", "name": "İncek - Beytepe Gelişme Alanı", "district": "Çankaya", "lat": 39.8240, "lon": 32.7480, "cost_million_tl": 1050, "capacity": 1100000, "icu_beds": 100, "ambulances": 10},
    {"id": "CAND_07", "name": "Balgat - Mevlana Bulvarı (Konya Yolu)", "district": "Çankaya", "lat": 39.9050, "lon": 32.8250, "cost_million_tl": 1400, "capacity": 1800000, "icu_beds": 180, "ambulances": 18},
    {"id": "CAND_08", "name": "Gölbaşı - Konya Yolu Girişi", "district": "Gölbaşı", "lat": 39.8050, "lon": 32.8150, "cost_million_tl": 720, "capacity": 1000000, "icu_beds": 90, "ambulances": 10},
    {"id": "CAND_09", "name": "Mamak - Doğukent Bulvarı", "district": "Mamak", "lat": 39.8910, "lon": 32.9350, "cost_million_tl": 780, "capacity": 1400000, "icu_beds": 140, "ambulances": 14},
    {"id": "CAND_10", "name": "Mamak - Kayaş Samsun Yolu", "district": "Mamak", "lat": 39.9480, "lon": 32.9850, "cost_million_tl": 650, "capacity": 1100000, "icu_beds": 100, "ambulances": 10},
    {"id": "CAND_11", "name": "Altındağ - Karapürçek Tepe", "district": "Altındağ", "lat": 39.9720, "lon": 32.9550, "cost_million_tl": 680, "capacity": 1200000, "icu_beds": 110, "ambulances": 12},
    {"id": "CAND_12", "name": "Keçiören - Ovacık Kuzey Çevre Yolu", "district": "Keçiören", "lat": 40.0210, "lon": 32.8350, "cost_million_tl": 880, "capacity": 1600000, "icu_beds": 160, "ambulances": 16},
    {"id": "CAND_13", "name": "Pursaklar - Saray Sanayi Kavşağı", "district": "Pursaklar", "lat": 40.0520, "lon": 32.9150, "cost_million_tl": 690, "capacity": 1100000, "icu_beds": 100, "ambulances": 10},
    {"id": "CAND_14", "name": "Kahramankazan - İstanbul Yolu", "district": "Kahramankazan", "lat": 40.1850, "lon": 32.6710, "cost_million_tl": 520, "capacity": 800000, "icu_beds": 70, "ambulances": 8},
    {"id": "CAND_15", "name": "Polatlı - Eskişehir Yolu Girişi", "district": "Polatlı", "lat": 39.5950, "lon": 32.1620, "cost_million_tl": 450, "capacity": 600000, "icu_beds": 60, "ambulances": 8},
    {"id": "CAND_16", "name": "Çubuk - Esenboğa Bölgesi", "district": "Çubuk", "lat": 40.2150, "lon": 33.0180, "cost_million_tl": 490, "capacity": 600000, "icu_beds": 60, "ambulances": 8},
    {"id": "CAND_17", "name": "Elmadağ - Kırıkkale Yolu", "district": "Elmadağ", "lat": 39.9250, "lon": 33.2050, "cost_million_tl": 430, "capacity": 500000, "icu_beds": 50, "ambulances": 6},
    {"id": "CAND_18", "name": "Demetevler - Marangozlar Sitesi", "district": "Yenimahalle", "lat": 39.9610, "lon": 32.7820, "cost_million_tl": 1250, "capacity": 1700000, "icu_beds": 170, "ambulances": 16}
]

# MEVCUT BÜYÜK ŞEHİR HASTANELERİ
EXISTING_HOSPITALS = [
    {
        "id": "EXIST_01",
        "name": "Bilkent Şehir Hastanesi (Mevcut)",
        "district": "Çankaya",
        "lat": 39.8970,
        "lon": 32.7560,
        "beds": 3810,
        "capacity": 2500000,
        "desc": "Avrupa'nın en büyük hastanelerinden biri; Güneybatı aksında hiper-merkezi kampüs"
    },
    {
        "id": "EXIST_02",
        "name": "Etlik Şehir Hastanesi (Mevcut)",
        "district": "Keçiören / Yenimahalle",
        "lat": 39.9750,
        "lon": 32.8250,
        "beds": 4050,
        "capacity": 2700000,
        "desc": "Kuzey aksındaki mega şehir hastanesi kampüsü"
    }
]

# 3. ANKARA RAYLI SİSTEM HATLAR VE İSTASYONLAR
TRANSIT_LINES = [
    {
        "name": "🚇 M1-M2-M3 Metrosu (Törekent ↔ Batıkent ↔ Kızılay ↔ Çayyolu Koru)",
        "type": "Metro",
        "color": "#ef4444",
        "weight": 5.0,
        "coords": [
            [39.9612, 32.5789],
            [39.9720, 32.6010],
            [39.9812, 32.6189],
            [39.9750, 32.6850],
            [39.9682, 32.7410],
            [39.9678, 32.7985],
            [39.9550, 32.8250],
            [39.9421, 32.8592],
            [39.9320, 32.8550],
            [39.9208, 32.8541],
            [39.9120, 32.8120],
            [39.8970, 32.7500],
            [39.8900, 32.7200],
            [39.8824, 32.6978],
            [39.8750, 32.6850],
        ]
    },
    {
        "name": "🚇 M4 Keçiören Metrosu (Kızılay ↔ AKM ↔ Şehitler)",
        "type": "Metro",
        "color": "#8b5cf6",
        "weight": 5.0,
        "coords": [
            [39.9208, 32.8541],
            [39.9320, 32.8520],
            [39.9380, 32.8480],
            [39.9510, 32.8540],
            [39.9600, 32.8580],
            [39.9723, 32.8620],
            [39.9875, 32.8652],
        ]
    },
    {
        "name": "🚈 A1 Ankaray (AŞTİ ↔ Kızılay ↔ Dikimevi)",
        "type": "Hafif Raylı",
        "color": "#10b981",
        "weight": 4.5,
        "coords": [
            [39.9165, 32.8130],
            [39.9200, 32.8220],
            [39.9230, 32.8280],
            [39.9250, 32.8420],
            [39.9208, 32.8541],
            [39.9240, 32.8680],
            [39.9280, 32.8790],
            [39.9320, 32.8900],
        ]
    },
    {
        "name": "🚆 Başkentray Banliyö Hattı (Sincan ↔ YHT Gar ↔ Sıhhiye ↔ Kayaş)",
        "type": "Banliyö Treni",
        "color": "#0ea5e9",
        "weight": 4.5,
        "coords": [
            [39.9580, 32.5850],
            [39.9520, 32.6250],
            [39.9450, 32.6650],
            [39.9410, 32.7050],
            [39.9390, 32.7450],
            [39.9370, 32.7750],
            [39.9360, 32.8050],
            [39.9355, 32.8450],
            [39.9320, 32.8560],
            [39.9300, 32.8750],
            [39.9290, 32.8950],
            [39.9350, 32.9300],
            [39.9412, 32.9685],
        ]
    }
]

# METRO ARA İSTASYON DÜĞÜMLERİ (GÖRSEL ZENGİNLİK İÇİN)
METRO_STATIONS = [
    {"name": "Milli Kütüphane İstasyonu", "lat": 39.9150, "lon": 32.8320},
    {"name": "ODTÜ Metro İstasyonu", "lat": 39.8970, "lon": 32.7780},
    {"name": "Bilkent Metro İstasyonu", "lat": 39.8950, "lon": 32.7560},
    {"name": "Ümitköy Metro İstasyonu", "lat": 39.8880, "lon": 32.7120},
    {"name": "Akköprü İstasyonu", "lat": 39.9550, "lon": 32.8250},
    {"name": "İvedik İstasyonu", "lat": 39.9630, "lon": 32.8120},
    {"name": "Hastane Metro İstasyonu", "lat": 39.9680, "lon": 32.7850},
    {"name": "Ostim Sanayi Metro İstasyonu", "lat": 39.9710, "lon": 32.7550},
    {"name": "Dışkapı Metro İstasyonu", "lat": 39.9600, "lon": 32.8580},
    {"name": "Kolej Ankaray İstasyonu", "lat": 39.9240, "lon": 32.8680},
    {"name": "Kurtuluş İstasyonu", "lat": 39.9280, "lon": 32.8790},
]

# 4. KRİTİK AKTARMA MERKEZLERİ
TRANSIT_HUBS = [
    {
        "id": "HUB_01",
        "name": "AŞTİ Şehirlerarası Otobüs Terminali & Ankaray İstasyonu",
        "type": "Terminal / Metro",
        "lat": 39.9165,
        "lon": 32.8130,
        "daily_passengers": 180000,
        "desc": "Ankara'nın ana şehirlerarası otobüs kapısı ve Ankaray batı uç aktarması"
    },
    {
        "id": "HUB_02",
        "name": "Ankara YHT Garı & Sıhhiye Ana Aktarma Göbeği",
        "type": "YHT Garı & Metro & Başkentray",
        "lat": 39.9355,
        "lon": 32.8450,
        "daily_passengers": 250000,
        "desc": "Yüksek Hızlı Tren, Başkentray ve merkezi EGO otobüs durakları kesişimi"
    },
    {
        "id": "HUB_03",
        "name": "Kızılay Meydanı Ortak Metro & EGO Aktarma Merkezi",
        "type": "Metro Kavşağı",
        "lat": 39.9208,
        "lon": 32.8541,
        "daily_passengers": 400000,
        "desc": "M1, M2, M4, Ankaray ve yüzlerce otobüs hattının başkent çekirdeğindeki kesişim noktası"
    },
    {
        "id": "HUB_04",
        "name": "Batıkent Metro & EGO Ring Aktarma İstasyonu",
        "type": "Metro & Otobüs Ring",
        "lat": 39.9682,
        "lon": 32.7410,
        "daily_passengers": 95000,
        "desc": "Batıkent, Çakırlar ve Ostim işçi ve konut servislerinin aktarma göbeği"
    },
    {
        "id": "HUB_05",
        "name": "Koru Metro İstasyonu & Güneybatı Aktarma Terminali",
        "type": "Metro & Ring",
        "lat": 39.8750,
        "lon": 32.6850,
        "daily_passengers": 75000,
        "desc": "Çayyolu, Yaşamkent, Bağlıca ve İncek EGO besleme hatları terminali"
    },
    {
        "id": "HUB_06",
        "name": "Sincan Lale Meydanı & Banliyö Aktarma Garı",
        "type": "Başkentray & EGO",
        "lat": 39.9580,
        "lon": 32.5850,
        "daily_passengers": 85000,
        "desc": "Sincan ve Yenikent bölgelerinin en büyük toplu taşıma transfer merkezi"
    },
    {
        "id": "HUB_07",
        "name": "Dışkapı / Etlik EGO Otobüs Aktarma Meydanı",
        "type": "Otobüs & Minibüs",
        "lat": 39.9600,
        "lon": 32.8580,
        "daily_passengers": 65000,
        "desc": "Etlik Şehir Hastanesi, Keçiören ve Altındağ minibüs/otobüs koridoru"
    },
    {
        "id": "HUB_08",
        "name": "Mamak Akdere / Abidinpaşa EGO Transfer Noktası",
        "type": "Otobüs Göbeği",
        "lat": 39.9285,
        "lon": 32.8942,
        "daily_passengers": 60000,
        "desc": "Doğu Ankara konut bölgelerinin merkeze bağlanan en işlek toplu taşıma durağı"
    },
    {
        "id": "HUB_09",
        "name": "Gölbaşı EGO Hareket Noktası & Mogan Girişi",
        "type": "Otobüs Terminali",
        "lat": 39.7895,
        "lon": 32.8091,
        "daily_passengers": 40000,
        "desc": "Güney Ankara üniversiteler ve yerel banliyö EGO ring merkezi"
    }
]

# 5. YÜKSEK ÇÖZÜNÜRLÜKLÜ GERÇEK KARAYOLU ARTERLERİ (CURVED REAL GEOMETRY)
ROAD_ARTERIES = [
    {
        "id": "ROAD_ESKISEHIR",
        "name": "D200 Eskişehir Yolu (Kızılay ↔ Çayyolu ↔ Polatlı)",
        "base_speed": 70,
        "coords": [
            [39.9208, 32.8541], [39.9160, 32.8350], [39.9120, 32.8050],
            [39.9050, 32.7800], [39.8970, 32.7500], [39.8900, 32.7250],
            [39.8824, 32.6978], [39.8700, 32.6500], [39.8550, 32.5800],
            [39.8500, 32.5500], [39.8100, 32.4500], [39.7500, 32.3500],
            [39.6800, 32.2500], [39.5841, 32.1452]
        ],
        "traffic_profile": {
            8: {"level": 3, "speed": 22, "status": "Ağır Trafik (İşe Gidiş)", "color": "#ef4444", "glow": "#7f1d1d"},
            13: {"level": 1, "speed": 62, "status": "Akıcı", "color": "#10b981", "glow": "#064e3b"},
            18: {"level": 4, "speed": 16, "status": "Kilitli Trafik (İş Çıkışı)", "color": "#dc2626", "glow": "#450a0a"},
            2: {"level": 1, "speed": 80, "status": "Tamamen Açık", "color": "#10b981", "glow": "#064e3b"}
        }
    },
    {
        "id": "ROAD_ISTANBUL",
        "name": "D750 İstanbul Yolu (Ulus ↔ Batıkent ↔ Eryaman ↔ Kazan)",
        "base_speed": 75,
        "coords": [
            [39.9421, 32.8592], [39.9500, 32.8350], [39.9550, 32.8100],
            [39.9620, 32.7750], [39.9682, 32.7410], [39.9780, 32.6950],
            [39.9850, 32.6500], [39.9950, 32.6100], [40.0150, 32.5800],
            [40.0700, 32.6100], [40.1400, 32.6500], [40.1982, 32.6841]
        ],
        "traffic_profile": {
            8: {"level": 3, "speed": 25, "status": "Yoğun Trafik", "color": "#ef4444", "glow": "#7f1d1d"},
            13: {"level": 1, "speed": 65, "status": "Akıcı", "color": "#10b981", "glow": "#064e3b"},
            18: {"level": 4, "speed": 18, "status": "Kilitli Trafik (Batı Çıkışı)", "color": "#dc2626", "glow": "#450a0a"},
            2: {"level": 1, "speed": 85, "status": "Tamamen Açık", "color": "#10b981", "glow": "#064e3b"}
        }
    },
    {
        "id": "ROAD_KONYA",
        "name": "Mevlana Bulvarı (Konya Yolu / Balgat ↔ Gölbaşı)",
        "base_speed": 65,
        "coords": [
            [39.9421, 32.8592], [39.9250, 32.8450], [39.9050, 32.8250],
            [39.8800, 32.8200], [39.8500, 32.8150], [39.8200, 32.8120],
            [39.7895, 32.8091]
        ],
        "traffic_profile": {
            8: {"level": 3, "speed": 20, "status": "Yoğun Trafik (Balgat)", "color": "#ef4444", "glow": "#7f1d1d"},
            13: {"level": 2, "speed": 50, "status": "Orta Yoğunluk", "color": "#f59e0b", "glow": "#78350f"},
            18: {"level": 4, "speed": 15, "status": "Ağır Trafik (Gölbaşı Yönü)", "color": "#dc2626", "glow": "#450a0a"},
            2: {"level": 1, "speed": 75, "status": "Tamamen Açık", "color": "#10b981", "glow": "#064e3b"}
        }
    },
    {
        "id": "ROAD_SAMSUN",
        "name": "D200 Doğu (Samsun Yolu / Mamak ↔ Kayaş ↔ Elmadağ)",
        "base_speed": 65,
        "coords": [
            [39.9421, 32.8592], [39.9500, 32.8750], [39.9550, 32.8900],
            [39.9480, 32.9300], [39.9412, 32.9685], [39.9350, 33.0400],
            [39.9250, 33.1000], [39.9200, 33.1800], [39.9192, 33.2289]
        ],
        "traffic_profile": {
            8: {"level": 2, "speed": 35, "status": "Orta Yoğun", "color": "#f59e0b", "glow": "#78350f"},
            13: {"level": 1, "speed": 60, "status": "Akıcı", "color": "#10b981", "glow": "#064e3b"},
            18: {"level": 3, "speed": 26, "status": "Yoğun Trafik (Mamak)", "color": "#ef4444", "glow": "#7f1d1d"},
            2: {"level": 1, "speed": 75, "status": "Tamamen Açık", "color": "#10b981", "glow": "#064e3b"}
        }
    },
    {
        "id": "ROAD_CEVRE",
        "name": "O-20 Ankara Çevre Otoyolu (Çevre Çemberi)",
        "base_speed": 95,
        "coords": [
            [39.815, 32.780], [39.825, 32.710], [39.840, 32.650],
            [39.880, 32.600], [39.920, 32.570], [39.970, 32.590],
            [40.020, 32.650], [40.045, 32.740], [40.050, 32.820],
            [40.045, 32.900], [40.030, 32.960], [39.980, 32.985],
            [39.930, 32.980], [39.880, 32.950], [39.840, 32.900],
            [39.815, 32.780]
        ],
        "traffic_profile": {
            8: {"level": 2, "speed": 65, "status": "Orta Akıcı", "color": "#f59e0b", "glow": "#78350f"},
            13: {"level": 1, "speed": 95, "status": "Hızlı Akış", "color": "#10b981", "glow": "#064e3b"},
            18: {"level": 3, "speed": 40, "status": "Yoğun (Batıkent/İvedik Çıkışları)", "color": "#ef4444", "glow": "#7f1d1d"},
            2: {"level": 1, "speed": 100, "status": "Serbest Otoyol", "color": "#10b981", "glow": "#064e3b"}
        }
    },
    {
        "id": "ROAD_HAVALIMANI",
        "name": "Özal Bulvarı (Protokol Yolu / Pursaklar ↔ Esenboğa)",
        "base_speed": 75,
        "coords": [
            [39.9421, 32.8592], [39.9550, 32.8700], [39.9700, 32.8800],
            [40.0050, 32.8900], [40.0384, 32.9014], [40.0800, 32.9450],
            [40.1150, 32.9900], [40.1800, 33.0100], [40.2389, 33.0315]
        ],
        "traffic_profile": {
            8: {"level": 3, "speed": 30, "status": "Yoğun (Aydınlıkevler)", "color": "#ef4444", "glow": "#7f1d1d"},
            13: {"level": 1, "speed": 70, "status": "Akıcı", "color": "#10b981", "glow": "#064e3b"},
            18: {"level": 3, "speed": 28, "status": "Yoğun (Pursaklar)", "color": "#ef4444", "glow": "#7f1d1d"},
            2: {"level": 1, "speed": 85, "status": "Açık", "color": "#10b981", "glow": "#064e3b"}
        }
    },
    {
        "id": "ROAD_TURAN_GUNES",
        "name": "Turan Güneş Bulvarı (Çankaya Köşkü ↔ Oran ↔ İncek)",
        "base_speed": 55,
        "coords": [
            [39.8967, 32.8550], [39.8800, 32.8500], [39.8600, 32.8450],
            [39.8450, 32.8350], [39.8315, 32.7380]
        ],
        "traffic_profile": {
            8: {"level": 3, "speed": 18, "status": "Ağır Trafik (Çankaya İnişi)", "color": "#ef4444", "glow": "#7f1d1d"},
            13: {"level": 1, "speed": 50, "status": "Akıcı", "color": "#10b981", "glow": "#064e3b"},
            18: {"level": 4, "speed": 14, "status": "Kilitli (Oran Kavşağı)", "color": "#dc2626", "glow": "#450a0a"},
            2: {"level": 1, "speed": 65, "status": "Açık", "color": "#10b981", "glow": "#064e3b"}
        }
    }
]

# 6. SEYAHAT SÜRESİ VE TRAFİK MOTORU
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_traffic_multiplier(hour):
    if 7 <= hour <= 9:
        return 1.65
    elif 10 <= hour <= 15:
        return 1.10
    elif 17 <= hour <= 19:
        return 1.85
    elif 20 <= hour <= 23:
        return 1.20
    else:
        return 1.00

def calculate_travel_time_minutes(lat1, lon1, lat2, lon2, hour=13):
    crow_dist = haversine_km(lat1, lon1, lat2, lon2)
    road_dist_km = crow_dist * 1.32
    
    if road_dist_km < 6.0:
        base_speed = 34.0
    elif road_dist_km < 20.0:
        base_speed = 52.0
    else:
        base_speed = 76.0
        
    traffic_mult = get_traffic_multiplier(hour)
    effective_speed = max(14.0, base_speed / traffic_mult)
    
    travel_time_min = (road_dist_km / effective_speed) * 60.0
    return round(travel_time_min, 1), round(road_dist_km, 1)

def build_travel_matrix(hour=13):
    time_matrix = {}
    dist_matrix = {}
    
    for dem in DEMAND_POINTS:
        time_matrix[dem["id"]] = {}
        dist_matrix[dem["id"]] = {}
        for cand in CANDIDATE_SITES:
            t_min, d_km = calculate_travel_time_minutes(
                dem["lat"], dem["lon"],
                cand["lat"], cand["lon"],
                hour=hour
            )
            time_matrix[dem["id"]][cand["id"]] = t_min
            dist_matrix[dem["id"]][cand["id"]] = d_km
            
    return time_matrix, dist_matrix

def calculate_baseline_existing_performance(hour=13):
    total_pop = sum(d["population"] for d in DEMAND_POINTS)
    weighted_time = 0.0
    cov_15 = 0
    cov_25 = 0
    max_t = 0.0
    
    for d in DEMAND_POINTS:
        t1, _ = calculate_travel_time_minutes(d["lat"], d["lon"], EXISTING_HOSPITALS[0]["lat"], EXISTING_HOSPITALS[0]["lon"], hour=hour)
        t2, _ = calculate_travel_time_minutes(d["lat"], d["lon"], EXISTING_HOSPITALS[1]["lat"], EXISTING_HOSPITALS[1]["lon"], hour=hour)
        best_t = min(t1, t2)
        
        weighted_time += d["population"] * best_t
        if best_t <= 15.0:
            cov_15 += d["population"]
        if best_t <= 25.0:
            cov_25 += d["population"]
        if best_t > max_t:
            max_t = best_t
            
    return {
        "avg_travel_time_min": round(weighted_time / total_pop, 1),
        "coverage_15_pct": round((cov_15 / total_pop) * 100.0, 1),
        "coverage_25_pct": round((cov_25 / total_pop) * 100.0, 1),
        "max_travel_time_min": round(max_t, 1)
    }

def get_dataframes():
    return pd.DataFrame(DEMAND_POINTS), pd.DataFrame(CANDIDATE_SITES)
