"""
Ankara İli Hastane Konumlandırma, Toplu Taşıma ve Dinamik Trafik Optimizasyon Sistemi
(Ankara Facility Location, Transit Networks, Emergency Dispatch & Live Traffic Simulation)

Ders: Optimizasyona Giriş
Model: Capacitated Facility Location Problem (CFLP) / Mixed Integer Linear Programming (MILP)
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium import plugins
from streamlit_folium import st_folium
from scipy.spatial import ConvexHull

from data import (
    DEMAND_POINTS, CANDIDATE_SITES, EXISTING_HOSPITALS, TRANSIT_LINES,
    METRO_STATIONS, TRANSIT_HUBS, ROAD_ARTERIES, get_traffic_multiplier,
    calculate_baseline_existing_performance, calculate_travel_time_minutes
)
from optimizer import solve_hospital_location

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Ankara Akıllı Sağlık & Ulaşım GIS",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS ile Modern Glassmorphism & Cyberpunk Dokunuşları
st.markdown("""
<style>
    .stApp {
        background-color: #0b0f19;
        color: #e2e8f0;
    }
    .header-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 20px 26px;
        margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.4);
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .subtitle {
        color: #94a3b8;
        font-size: 1.0rem;
        margin-top: 5px;
        margin-bottom: 0px;
    }
    .kpi-card {
        background: rgba(17, 24, 39, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 3px solid #38bdf8;
        border-radius: 12px;
        padding: 14px 18px;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.3);
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.45);
    }
    .kpi-val {
        font-size: 1.85rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 3px 0;
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 6px;
    }
    .badge-cflp { background: #059669; color: white; }
    .badge-pulp { background: #2563eb; color: white; }
    .badge-transit { background: #d97706; color: white; }
    .badge-live { background: #dc2626; color: white; }
    
    .dispatch-box {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        border: 1px solid #6366f1;
        border-radius: 12px;
        padding: 16px 22px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Helper: Hex to RGB string for CSS vars
def hex_to_rgb_str(hex_str):
    hex_str = hex_str.lstrip('#')
    return f"{int(hex_str[0:2], 16)}, {int(hex_str[2:4], 16)}, {int(hex_str[4:6], 16)}"

# Session State Hazırlığı
if "hour_val" not in st.session_state:
    st.session_state["hour_val"] = 18
if "p_val" not in st.session_state:
    st.session_state["p_val"] = 5
if "travel_weight_val" not in st.session_state:
    st.session_state["travel_weight_val"] = 65
if "model_choice" not in st.session_state:
    st.session_state["model_choice"] = 0

# ----------------- YAN PANEL (KONTROL VE PARAMETRELER) -----------------
with st.sidebar:
    st.markdown("""
        <div style='background:linear-gradient(135deg, #1e293b, #0f172a); border:1px solid #38bdf8; border-radius:12px; padding:16px; margin-bottom:18px; text-align:center;'>
            <div style='font-size:1.8rem;'>🏥 🚑 🚇</div>
            <div style='font-size:1.2rem; font-weight:800; color:#38bdf8;'>ANKARA SAĞLIK GIS</div>
            <div style='font-size:0.75rem; color:#94a3b8; margin-top:2px;'>Akıllı Şehir & Karar Destek</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. AKILLI TAHTA HIZLI SUNUM BUTONLARI (PRESETS)
    st.markdown("### 🎓 Akıllı Tahta Hızlı Sunum Butonları")
    col_pre1, col_pre2 = st.columns(2)
    with col_pre1:
        if st.button("🌟 Önerilen Model", help="5 Hastane, Dengeli Süre/Maliyet"):
            st.session_state["hour_val"] = 18
            st.session_state["p_val"] = 5
            st.session_state["travel_weight_val"] = 65
            st.session_state["model_choice"] = 0
            st.rerun()
    with col_pre2:
        if st.button("🚨 Akşam Zirvesi", help="18:30 Yoğun Trafik & 6 Hastane"):
            st.session_state["hour_val"] = 18
            st.session_state["p_val"] = 6
            st.session_state["travel_weight_val"] = 80
            st.session_state["model_choice"] = 0
            st.rerun()

    col_pre3, col_pre4 = st.columns(2)
    with col_pre3:
        if st.button("🌙 Gece Nöbeti", help="02:00 Boş Yol Hızlı Ulaşım"):
            st.session_state["hour_val"] = 2
            st.session_state["p_val"] = 4
            st.session_state["travel_weight_val"] = 50
            st.session_state["model_choice"] = 0
            st.rerun()
    with col_pre4:
        if st.button("💰 Düşük Bütçe", help="3 Hastane, Minimum Harcama"):
            st.session_state["hour_val"] = 13
            st.session_state["p_val"] = 3
            st.session_state["travel_weight_val"] = 30
            st.session_state["model_choice"] = 0
            st.rerun()
            
    st.markdown("---")
    
    # 2. DİNAMİK TRAFİK SENARYOLARI
    st.markdown("### 🚦 Saat ve Canlı Trafik Senaryosu")
    
    col_sc1, col_sc2 = st.columns(2)
    with col_sc1:
        if st.button("🌅 08:30 Sabah"):
            st.session_state["hour_val"] = 8
            st.rerun()
    with col_sc2:
        if st.button("🌇 18:30 Akşam"):
            st.session_state["hour_val"] = 18
            st.rerun()
            
    col_sc3, col_sc4 = st.columns(2)
    with col_sc3:
        if st.button("☀️ 13:30 Öğle"):
            st.session_state["hour_val"] = 13
            st.rerun()
    with col_sc4:
        if st.button("🌙 02:00 Gece"):
            st.session_state["hour_val"] = 2
            st.rerun()
            
    selected_hour = st.slider(
        "Günün Saati (00:00 - 23:00):",
        min_value=0,
        max_value=23,
        value=st.session_state["hour_val"],
        step=1
    )
    st.session_state["hour_val"] = selected_hour
    
    traffic_mult = get_traffic_multiplier(selected_hour)
    if traffic_mult >= 1.6:
        st.markdown(f"🔴 **Ağır Zirve Trafiği (+%{(traffic_mult-1)*100:.0f} Gecikme)**")
    elif traffic_mult >= 1.2:
        st.markdown(f"🟡 **Orta Seviye Trafik (+%{(traffic_mult-1)*100:.0f} Gecikme)**")
    else:
        st.markdown("🟢 **Akıcı / Gece Açık Yol (Normal Süre)**")
        
    # 24 Saatlik Trafik Eğrisi Mini-Grafiği
    st.caption("📈 Ankara 24 Saatlik Trafik Sıkışıklık Eğrisi:")
    df_traffic_curve = pd.DataFrame({
        "Saat": [f"{h:02d}:00" for h in range(24)],
        "Trafik Çarpanı": [get_traffic_multiplier(h) for h in range(24)]
    }).set_index("Saat")
    st.line_chart(df_traffic_curve, height=120)
        
    st.markdown("---")
    
    # 3. OPTİMİZASYON MODELİ
    st.markdown("### ⚙️ Optimizasyon Kısıtları")
    model_type = st.radio(
        "Modelleme Türü:",
        ["CFLP (Kapasiteli Tesis Yeri)", "UFLP (Kapasitesiz Model)"],
        index=st.session_state["model_choice"]
    )
    is_capacitated = ("CFLP" in model_type)
    
    p_hospitals = st.slider(
        "Açılacak Hastane Sayısı (p):",
        min_value=3,
        max_value=10,
        value=st.session_state["p_val"],
        step=1
    )
    st.session_state["p_val"] = p_hospitals
    
    travel_weight = st.slider(
        "Ulaşım Süresi Önceliği (%):",
        min_value=0,
        max_value=100,
        value=st.session_state["travel_weight_val"],
        step=5
    )
    st.session_state["travel_weight_val"] = travel_weight
    cost_weight = 100 - travel_weight
    
    st.markdown("---")
    st.markdown("### 🎨 Harita Altlığı")
    map_theme = st.selectbox(
        "Zemin Stili:",
        [
            "🌙 Dark Mode (Gece Komuta Modu)",
            "📍 Canlı Sokak & Yol Haritası",
            "🛰️ Gerçek Uydu Fotoğrafı (Satellite)"
        ],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 👁️ Katman Aç / Kapat")
    show_catchments = st.checkbox("🗺️ Bölgesel Hizmet Havzaları (Hinterlant)", value=True)
    show_traffic = st.checkbox("🚦 Canlı Karayolu Trafik Akışı (Çift Katmanlı)", value=True)
    show_transit_lines = st.checkbox("🚇 Metro, Ankaray ve Başkentray Hatları", value=True)
    show_transit_stations = st.checkbox("⚪ Metro Ara İstasyon Noktaları", value=True)
    show_transit_hubs = st.checkbox("🚌 AŞTİ, YHT Garı ve Ana EGO Durakları", value=True)
    show_existing = st.checkbox("🏢 Mevcut Şehir Hastaneleri (Bilkent & Etlik)", value=True)
    show_spider = st.checkbox("🕸️ Semt - Hastane Tahsis Hatları", value=True)
    show_isochrone = st.checkbox("⭕ 10 & 15 Dk Acil Servis Çemberleri", value=True)
    show_heatmap = st.checkbox("🔥 Nüfus Yoğunluğu Isı Haritası", value=False)
    show_unselected = st.checkbox("⚪ Seçilmeyen Aday Konumlar", value=True)

# ----------------- ÇÖZÜCÜYÜ ÇALIŞTIR -----------------
results = solve_hospital_location(
    p_hospitals=p_hospitals,
    weight_travel_time=travel_weight / 100.0,
    weight_cost=cost_weight / 100.0,
    enable_capacity=is_capacitated,
    hour=selected_hour
)

baseline_perf = calculate_baseline_existing_performance(hour=selected_hour)

# ----------------- ÜST BAŞLIK VE KÜNYE -----------------
st.markdown(f"""
<div class="header-box">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1 class="main-title">ANKARA AKILLI SAĞLIK, TRAFİK & ULAŞIM GIS</h1>
            <p class="subtitle">Saat <b>{selected_hour:02d}:00 Trafik Simülasyonu</b> | Metro, AŞTİ/Gar Durakları & Çok Amaçlı CFLP Optimizasyonu</p>
        </div>
        <div>
            <span class="badge badge-cflp">CFLP Modeli</span>
            <span class="badge badge-transit">Metro & Otobüs Entegre</span>
            <span class="badge badge-live">Canlı Trafik Motoru</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if not results["success"]:
    st.error(f"❌ {results['message']}")
    st.stop()

# ----------------- ÜST KPI METRİK KARTLARI -----------------
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#38bdf8;">
            <div class="kpi-label">Toplam Yatırım Maliyeti</div>
            <div class="kpi-val">{results['total_cost_million_tl']:,.0f} <span style="font-size:0.9rem; color:#64748b;">M TL</span></div>
        </div>
    """, unsafe_allow_html=True)
with k2:
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#f59e0b;">
            <div class="kpi-label">Trafikte Ort. Seyahat</div>
            <div class="kpi-val">{results['avg_travel_time_min']:.1f} <span style="font-size:0.9rem; color:#64748b;">dk</span></div>
        </div>
    """, unsafe_allow_html=True)
with k3:
    traffic_pct = (traffic_mult - 1.0) * 100.0
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#ef4444;">
            <div class="kpi-label">Trafik Gecikme Etkisi</div>
            <div class="kpi-val" style="color:{'#ef4444' if traffic_pct>30 else '#10b981'};">+{traffic_pct:.0f}%</div>
        </div>
    """, unsafe_allow_html=True)
with k4:
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#10b981;">
            <div class="kpi-label">15 Dk Kapsama Oranı</div>
            <div class="kpi-val" style="color:{'#34d399' if results['coverage_under_15_min_pct']>50 else '#f59e0b'};">%{results['coverage_under_15_min_pct']:.1f}</div>
        </div>
    """, unsafe_allow_html=True)
with k5:
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#ec4899;">
            <div class="kpi-label">Maks. Ulaşım (En Uzak)</div>
            <div class="kpi-val" style="color:#fb7185;">{results['max_travel_time_min']:.1f} <span style="font-size:0.9rem; color:#64748b;">dk</span></div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# Renk Paleti (Canlı Tonlar)
VIBRANT_HEX = ["#0284c7", "#e11d48", "#059669", "#d97706", "#7c3aed", "#db2777", "#0891b2", "#ea580c", "#4f46e5", "#0d9488"]
hosp_color_map = {}
for idx, hosp in enumerate(results["selected_hospitals"]):
    hosp_color_map[hosp["id"]] = VIBRANT_HEX[idx % len(VIBRANT_HEX)]

# ----------------- SEKMELER -----------------
tab_map, tab_comparison, tab_transit, tab_analysis, tab_theory = st.tabs([
    "🗺️ AKILLI SAĞLIK GIS & CANLI TRAFİK HARİTASI",
    "⚖️ MEVCUT DURUM VS OPTİMİZE MODEL (KIYASLAMA)",
    "🚇 METRO, AŞTİ VE EGO AKTARMA ANALİZİ",
    "📊 HASTANE DOLULUK VE MALİYET GRAFİKLERİ",
    "📝 MATEMATİKSEL TEORİ (CFLP & DİNAMİK MODEL)"
])

# ===================== SEKME 1: HARİTA GÖRÜNÜMÜ =====================
with tab_map:
    # 🚑 İNTERAKTİF ACİL AMBULANS SEVK SİMÜLATÖRÜ
    with st.expander("🚑 **Canlı Ambulans Sevk Simülatörü (Acil Çağrı Deneyimi)**", expanded=True):
        col_disp1, col_disp2 = st.columns([1, 2])
        demand_names = [f"{d['id']} - {d['name']} ({d['district']})" for d in DEMAND_POINTS]
        default_sincan_idx = next((i for i, d in enumerate(demand_names) if "Sincan" in d), 0)
        with col_disp1:
            selected_dem_str = st.selectbox(
                "Acil Çağrı Gelen Semt / Bölge Seçin:",
                demand_names,
                index=default_sincan_idx
            )
            selected_dem_id = selected_dem_str.split(" - ")[0]
            
        matched_assign = next(a for a in results["assignments"] if a["demand_id"] == selected_dem_id)
        
        # Mevcut 2 şehir hastanesine gitseydi ne kadar sürerdi?
        t1_base, d1_base = calculate_travel_time_minutes(
            matched_assign["demand_lat"], matched_assign["demand_lon"],
            EXISTING_HOSPITALS[0]["lat"], EXISTING_HOSPITALS[0]["lon"],
            hour=selected_hour
        )
        t2_base, d2_base = calculate_travel_time_minutes(
            matched_assign["demand_lat"], matched_assign["demand_lon"],
            EXISTING_HOSPITALS[1]["lat"], EXISTING_HOSPITALS[1]["lon"],
            hour=selected_hour
        )
        best_existing_time = min(t1_base, t2_base)
        best_existing_name = EXISTING_HOSPITALS[0]["name"] if t1_base <= t2_base else EXISTING_HOSPITALS[1]["name"]
        time_saved = best_existing_time - matched_assign['travel_time_min']
        
        with col_disp2:
            st.markdown(f"""
                <div class="dispatch-box">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div style="font-size:1.05rem; font-weight:800; color:#38bdf8;">
                            🚨 112 ACİL SEVK PROTOKOLÜ: <span style="color:#ffffff;">{matched_assign['demand_name']} ➡️ {matched_assign['hospital_name']}</span>
                        </div>
                        <span style="background:#ef4444; color:white; font-size:0.75rem; font-weight:bold; padding:3px 10px; border-radius:6px; box-shadow:0 0 10px #ef4444;">KOD KIRMIZI</span>
                    </div>
                    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; margin-top:10px; font-size:0.88rem; background:rgba(0,0,0,0.35); padding:10px 14px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
                        <div>⏱️ <b>Optimize Süre:</b> <br/><span style="color:#10b981; font-size:1.25rem; font-weight:bold;">{matched_assign['travel_time_min']} dk</span></div>
                        <div>🏢 <b>Mevcut Durum:</b> <br/><span style="color:#ef4444; font-size:1.25rem; font-weight:bold;">{best_existing_time:.1f} dk</span></div>
                        <div>⚡ <b>Kazanılan Süre:</b> <br/><span style="color:#38bdf8; font-size:1.25rem; font-weight:bold;">{'+' if time_saved>0 else ''}{time_saved:.1f} dk</span></div>
                        <div>🛣️ <b>Yol Mesafesi:</b> <br/><span style="color:#f8fafc; font-size:1.25rem; font-weight:bold;">{matched_assign['distance_km']} km</span></div>
                    </div>
                    <div style="margin-top:8px; font-size:0.8rem; color:#94a3b8;">
                        ℹ️ <i>Eğer yeni optimize hastaneler açılmasaydı, bu vaka mecburen <b>{best_existing_name.split(' (')[0]}</b>'ne sevk edilecek ve <b>{best_existing_time:.1f} dakika</b> sürecekti.</i>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # Folium Haritası Başlat
    m = folium.Map(
        location=[39.92, 32.75],
        zoom_start=10,
        tiles=None
    )
    
    # Harita Altlığı
    if "Karanlık" in map_theme or "Dark" in map_theme:
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Dark Gray",
            name="Dark Canvas",
            overlay=False
        ).add_to(m)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            attr="Labels",
            name="Etiketler",
            overlay=True
        ).add_to(m)
    elif "Uydu" in map_theme:
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
            name="Gerçek Uydu Fotoğrafı",
            overlay=False
        ).add_to(m)
    else:
        folium.TileLayer(
            tiles="OpenStreetMap",
            name="Canlı Sokak & Yol Haritası",
            overlay=False
        ).add_to(m)

    # Taktiksel Harita Eklentileri (Fullscreen, MiniMap, MeasureControl)
    plugins.Fullscreen(
        position='topleft',
        title='Tam Ekran Görünümü (Akıllı Tahta / Projeksiyon)',
        title_cancel='Tam Ekrandan Çık',
        force_separate_button=True
    ).add_to(m)
    
    plugins.MiniMap(
        tile_layer="OpenStreetMap",
        position='bottomleft',
        width=150,
        height=110,
        toggle_display=True
    ).add_to(m)
    
    plugins.MeasureControl(
        position='bottomleft',
        primary_length_unit='kilometers',
        secondary_length_unit='meters'
    ).add_to(m)

    # Leaflet Özel Radar Dalgaları ve Siren Animasyonu CSS Enjeksiyonu
    leaflet_custom_css = """
    <style>
    @keyframes pulseGlow {
        0% {
            box-shadow: 0 0 0 0 rgba(var(--rgb), 0.85), 0 0 12px rgba(var(--rgb), 0.6);
            transform: scale(0.96);
        }
        70% {
            box-shadow: 0 0 0 20px rgba(var(--rgb), 0), 0 0 25px rgba(var(--rgb), 0.8);
            transform: scale(1.06);
        }
        100% {
            box-shadow: 0 0 0 0 rgba(var(--rgb), 0), 0 0 12px rgba(var(--rgb), 0.6);
            transform: scale(0.96);
        }
    }
    .pulse-hospital {
        border-radius: 50%;
        animation: pulseGlow 2.2s infinite ease-out;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    @keyframes sirenFlash {
        0%, 100% { 
            background: #ef4444; 
            box-shadow: 0 0 18px #ef4444, 0 0 35px rgba(239, 68, 68, 0.7); 
        }
        50% { 
            background: #3b82f6; 
            box-shadow: 0 0 18px #3b82f6, 0 0 35px rgba(59, 130, 246, 0.7); 
        }
    }
    .ambulance-beacon {
        border-radius: 50%;
        animation: sirenFlash 0.9s infinite alternate;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 3px solid #ffffff;
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(leaflet_custom_css))

    # 1. NÜFUS YOĞUNLUĞU ISI HARİTASI (HEATMAP)
    if show_heatmap:
        heat_data = [[d["lat"], d["lon"], float(d["population"]) / 1000.0] for d in DEMAND_POINTS]
        plugins.HeatMap(
            heat_data,
            name="🔥 Nüfus Yoğunluğu Isı Haritası",
            min_opacity=0.35,
            max_zoom=14,
            radius=30,
            blur=20,
            gradient={0.2: '#06b6d4', 0.4: '#10b981', 0.6: '#f59e0b', 0.8: '#f97316', 1.0: '#ef4444'}
        ).add_to(m)

    # 2. BÖLGESEL HİZMET HAVZALARI (CONVEX HULL HINTERLAND POLİGONLARI)
    if show_catchments:
        catchment_fg = folium.FeatureGroup(name="🗺️ Bölgesel Hizmet Havzaları (Hinterlant)", show=True)
        hosp_demands = {}
        for ass in results["assignments"]:
            h_id = ass["hospital_id"]
            if h_id not in hosp_demands:
                hosp_demands[h_id] = []
            hosp_demands[h_id].append([ass["demand_lat"], ass["demand_lon"]])
            
        for hosp in results["selected_hospitals"]:
            h_id = hosp["id"]
            h_color = hosp_color_map[h_id]
            pts = hosp_demands.get(h_id, [])
            all_pts = pts + [[hosp["lat"], hosp["lon"]]]
            if len(all_pts) >= 3:
                try:
                    hull = ConvexHull(np.array(all_pts))
                    hull_coords = [all_pts[v] for v in hull.vertices]
                    folium.Polygon(
                        locations=hull_coords,
                        color=h_color,
                        weight=2,
                        fill=True,
                        fill_color=h_color,
                        fill_opacity=0.09,
                        dash_array="5, 5",
                        tooltip=f"🏥 <b>{hosp['name']} Hizmet Havzası</b><br/>Bağlanan Nüfus: {hosp['allocated_population']:,}"
                    ).add_to(catchment_fg)
                except Exception:
                    pass
        catchment_fg.add_to(m)

    # 3. CANLI KARAYOLU TRAFİK AKIŞI (ÇİFT KATMANLI HD TRAFİK PARLAMASI)
    if show_traffic:
        traffic_fg = folium.FeatureGroup(name="🚦 Canlı Trafik Yoğunluğu (Saat Bazlı)", show=True)
        ref_h = 18 if 16 <= selected_hour <= 20 else (8 if 7 <= selected_hour <= 10 else (2 if selected_hour <= 5 else 13))
        
        for artery in ROAD_ARTERIES:
            t_info = artery["traffic_profile"].get(ref_h, artery["traffic_profile"][13])
            color = t_info["color"]
            glow = t_info["glow"]
            speed = t_info["speed"]
            status = t_info["status"]
            
            # Dış Katman (Glow Efekti)
            folium.PolyLine(
                locations=artery["coords"],
                color=glow,
                weight=8,
                opacity=0.5
            ).add_to(traffic_fg)
            
            # İç Katman (Canlı Çekirdek Renk)
            folium.PolyLine(
                locations=artery["coords"],
                color=color,
                weight=4.5,
                opacity=0.95,
                tooltip=f"🚦 <b>{artery['name']}</b><br/>Durum: <b>{status}</b><br/>Ortalama Hız: <b>{speed} km/s</b>"
            ).add_to(traffic_fg)
        traffic_fg.add_to(m)

    # 4. METRO VE RAYLI SİSTEMLER
    if show_transit_lines:
        transit_fg = folium.FeatureGroup(name="🚇 Ankara Raylı Sistem Hatları", show=True)
        for line in TRANSIT_LINES:
            folium.PolyLine(
                locations=line["coords"],
                color=line["color"],
                weight=line["weight"],
                opacity=0.95,
                tooltip=f"{line['name']} ({line['type']})"
            ).add_to(transit_fg)
        transit_fg.add_to(m)

    # 5. METRO ARA İSTASYONLARI
    if show_transit_stations:
        stations_fg = folium.FeatureGroup(name="⚪ Metro Ara İstasyonları", show=True)
        for stn in METRO_STATIONS:
            folium.CircleMarker(
                location=[stn["lat"], stn["lon"]],
                radius=4,
                color="#ffffff",
                weight=1.5,
                fill=True,
                fill_color="#6366f1",
                fill_opacity=0.9,
                tooltip=f"🚇 {stn['name']}"
            ).add_to(stations_fg)
        stations_fg.add_to(m)

    # 6. AKTARMA MERKEZLERİ & DURAKLAR
    if show_transit_hubs:
        hubs_fg = folium.FeatureGroup(name="🚌 AŞTİ, YHT Garı ve Ana EGO Durakları", show=True)
        for hub in TRANSIT_HUBS:
            folium.Marker(
                location=[hub["lat"], hub["lon"]],
                icon=folium.Icon(color="blue", icon="bus", prefix="fa"),
                tooltip=f"🚏 {hub['name']} ({hub['daily_passengers']:,} yolcu/gün)",
                popup=folium.Popup(f"""
                    <div style='font-family:sans-serif; min-width:220px;'>
                        <h4 style='margin:0; color:#1d4ed8;'>🚏 {hub['name']}</h4>
                        <b>Tür:</b> {hub['type']}<br/>
                        <b>Günlük Yolcu Hacmi:</b> ~{hub['daily_passengers']:,} kişi<br/>
                        <hr style='margin:6px 0;'/>
                        <span style='font-size:0.85rem; color:#475569;'>{hub['desc']}</span>
                    </div>
                """, max_width=280)
            ).add_to(hubs_fg)
        hubs_fg.add_to(m)

    # 7. MEVCUT ŞEHİR HASTANELERİ (BİLKENT & ETLİK)
    if show_existing:
        exist_fg = folium.FeatureGroup(name="🏢 Mevcut Şehir Hastaneleri (Bilkent & Etlik)", show=True)
        for exh in EXISTING_HOSPITALS:
            ex_icon_html = """
            <div style="
                background: #334155;
                border: 3px solid #f8fafc;
                border-radius: 50%;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 18px;
                color: white;
                box-shadow: 0 0 14px rgba(0,0,0,0.5);
            ">🏢</div>
            """
            folium.Marker(
                location=[exh["lat"], exh["lon"]],
                icon=folium.DivIcon(html=ex_icon_html, icon_size=(36, 36), icon_anchor=(18, 18)),
                tooltip=f"🏢 {exh['name']} ({exh['beds']:,} Yatak)",
                popup=folium.Popup(f"""
                    <div style='font-family:sans-serif;'>
                        <h4>🏢 {exh['name']}</h4>
                        <b>İlçe:</b> {exh['district']}<br/>
                        <b>Yatak Sayısı:</b> {exh['beds']:,}<br/>
                        <b>Kapasite:</b> {exh['capacity']:,} kişi<br/>
                        <p style='font-size:0.85rem; color:#64748b;'>{exh['desc']}</p>
                    </div>
                """, max_width=280)
            ).add_to(exist_fg)
        exist_fg.add_to(m)

    # 8. HASTA ULAŞIM HATLARI & CANLI AMBULANS SEVK ROTASI (AntPath)
    if show_spider:
        spider_fg = folium.FeatureGroup(name="🕸️ Hasta Akış Güzergahları", show=True)
        for ass in results["assignments"]:
            h_color = hosp_color_map[ass["hospital_id"]]
            is_active_sim = (ass["demand_id"] == selected_dem_id)
            
            if is_active_sim:
                # Canlı Hareket Eden Neon AntPath
                plugins.AntPath(
                    locations=[
                        [ass["demand_lat"], ass["demand_lon"]],
                        [ass["hospital_lat"], ass["hospital_lon"]]
                    ],
                    color="#00ffff",
                    pulse_color="#ffffff",
                    weight=5.5,
                    opacity=1.0,
                    delay=500,
                    dash_array=[12, 20],
                    tooltip=f"🚨 <b>CANLI AMBULANS SEVK ROTASI:</b> {ass['travel_time_min']} dk ({ass['distance_km']} km)"
                ).add_to(spider_fg)
            else:
                folium.PolyLine(
                    locations=[
                        [ass["demand_lat"], ass["demand_lon"]],
                        [ass["hospital_lat"], ass["hospital_lon"]]
                    ],
                    color=h_color,
                    weight=1.6,
                    opacity=0.55,
                    dash_array="5, 5",
                    tooltip=f"{ass['demand_name']} ➡️ {ass['hospital_name']} ({ass['travel_time_min']} dk)"
                ).add_to(spider_fg)
        spider_fg.add_to(m)

    # 9. ERİŞİM ÇEMBERLERİ (DİNAMİK İZO-KRONLAR)
    if show_isochrone:
        iso_fg = folium.FeatureGroup(name="⭕ 10 & 15 Dk Erişim Çemberleri", show=True)
        eff_radius_10min = int(8000 / traffic_mult)
        eff_radius_15min = int(14000 / traffic_mult)
        
        for hosp in results["selected_hospitals"]:
            h_color = hosp_color_map[hosp["id"]]
            
            folium.Circle(
                location=[hosp["lat"], hosp["lon"]],
                radius=eff_radius_10min,
                color=h_color,
                weight=1.5,
                fill=True,
                fill_color=h_color,
                fill_opacity=0.12,
                tooltip=f"{hosp['name']} - 10 Dk Acil Servis Alanı ({eff_radius_10min/1000:.1f} km)"
            ).add_to(iso_fg)
            
            folium.Circle(
                location=[hosp["lat"], hosp["lon"]],
                radius=eff_radius_15min,
                color=h_color,
                weight=1.0,
                dash_array="6, 6",
                fill=False,
                tooltip=f"{hosp['name']} - 15 Dk Genişletilmiş Alan ({eff_radius_15min/1000:.1f} km)"
            ).add_to(iso_fg)
        iso_fg.add_to(m)

    # 10. SEÇİLMEYEN ADAY KONUMLAR
    if show_unselected:
        selected_ids = {h["id"] for h in results["selected_hospitals"]}
        unselected_fg = folium.FeatureGroup(name="⚪ Seçilmeyen Aday Konumlar", show=True)
        for cand in CANDIDATE_SITES:
            if cand["id"] not in selected_ids:
                folium.CircleMarker(
                    location=[cand["lat"], cand["lon"]],
                    radius=5.5,
                    color="#64748b",
                    weight=1,
                    fill=True,
                    fill_color="#334155",
                    fill_opacity=0.7,
                    tooltip=f"❌ {cand['name']} (Açılmadı - {cand['cost_million_tl']}M TL)"
                ).add_to(unselected_fg)
        unselected_fg.add_to(m)

    # 11. TALEP MERKEZLERİ
    demands_fg = folium.FeatureGroup(name="👥 Semt Nüfus Noktaları", show=True)
    for ass in results["assignments"]:
        h_color = hosp_color_map[ass["hospital_id"]]
        is_active_sim = (ass["demand_id"] == selected_dem_id)
        
        if is_active_sim:
            amb_html = """
            <div class="ambulance-beacon" style="
                width: 38px;
                height: 38px;
                font-size: 19px;
                position: relative;
            ">
                🚑
                <span style="
                    position: absolute;
                    bottom: -16px;
                    background: #dc2626;
                    color: white;
                    border: 1px solid #fca5a5;
                    border-radius: 4px;
                    font-size: 8px;
                    font-weight: 800;
                    padding: 0px 4px;
                    white-space: nowrap;
                ">ACİL ÇAĞRI</span>
            </div>
            """
            folium.Marker(
                location=[ass["demand_lat"], ass["demand_lon"]],
                icon=folium.DivIcon(html=amb_html, icon_size=(38, 38), icon_anchor=(19, 19)),
                tooltip=f"🚨 ACİL ÇAĞRI: {ass['demand_name']} ➡️ {ass['travel_time_min']} dk"
            ).add_to(demands_fg)
        else:
            pop_radius = 5 + (ass["population"] / 60000)
            folium.CircleMarker(
                location=[ass["demand_lat"], ass["demand_lon"]],
                radius=pop_radius,
                color="#ffffff",
                weight=1.5,
                fill=True,
                fill_color=h_color,
                fill_opacity=0.92,
                tooltip=f"📍 {ass['demand_name']} ({ass['population']:,} kişi) ➡️ {ass['travel_time_min']} dk",
                popup=folium.Popup(f"""
                    <div style='font-family:sans-serif;'>
                        <b>{ass['demand_name']}</b> ({ass['district']})<br/>
                        <b>Nüfus:</b> {ass['population']:,}<br/>
                        <b>Atanan:</b> {ass['hospital_name']}<br/>
                        <b>Trafikli Süre:</b> <span style='color:#ef4444; font-weight:bold;'>{ass['travel_time_min']} dk</span><br/>
                        <b>Mesafe:</b> {ass['distance_km']} km
                    </div>
                """, max_width=250)
            ).add_to(demands_fg)
    demands_fg.add_to(m)

    # 12. SEÇİLEN HASTANELER (RADAR DALGALI GLOW İKONLARI)
    hosp_fg = folium.FeatureGroup(name="🏥 Açılan Optimal Hastaneler", show=True)
    for idx, hosp in enumerate(results["selected_hospitals"]):
        h_color = hosp_color_map[hosp["id"]]
        rgb_str = hex_to_rgb_str(h_color)
        
        html_marker = f"""
        <div class="pulse-hospital" style="
            --rgb: {rgb_str};
            background: {h_color};
            border: 3px solid #ffffff;
            width: 38px;
            height: 38px;
            font-size: 19px;
            color: white;
            cursor: pointer;
            position: relative;
        ">
            🏥
            <span style="
                position: absolute;
                bottom: -15px;
                background: rgba(15, 23, 42, 0.95);
                color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 4px;
                font-size: 8px;
                font-weight: 800;
                padding: 0px 4px;
                white-space: nowrap;
                letter-spacing: 0.5px;
            ">AÇIK #{idx+1}</span>
        </div>
        """
        icon = folium.DivIcon(html=html_marker, icon_size=(38, 38), icon_anchor=(19, 19))
        
        popup_html = f"""
        <div style='font-family:system-ui, -apple-system, sans-serif; min-width:260px; color:#1e293b;'>
            <div style='background:{h_color}; color:white; padding:8px 12px; border-radius:8px 8px 0 0; margin:-1px -1px 8px -1px;'>
                <div style='font-size:0.75rem; text-transform:uppercase; letter-spacing:0.05em; opacity:0.9;'>Optimal Sağlık Kampüsü</div>
                <b style='font-size:1.1rem;'>🏥 {hosp['name']}</b>
            </div>
            <div style='padding:0 4px;'>
                <div style='display:flex; justify-content:space-between; margin-bottom:4px;'>
                    <span style='color:#64748b;'>İlçe / Bölge:</span>
                    <b>{hosp['district']}</b>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:4px;'>
                    <span style='color:#64748b;'>Yatırım Maliyeti:</span>
                    <b style='color:#0284c7;'>{hosp['cost_million_tl']} Milyon TL</b>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:4px;'>
                    <span style='color:#64748b;'>Yatak Kapasitesi:</span>
                    <b>{hosp['capacity']:,} kişi</b>
                </div>
                <div style='display:flex; justify-content:space-between; margin-bottom:4px;'>
                    <span style='color:#64748b;'>Yoğun Bakım & Filo:</span>
                    <b>{hosp.get('icu_beds', 120)} Yatak | {hosp.get('ambulances', 12)} Araç</b>
                </div>
                <hr style='border:none; border-top:1px solid #e2e8f0; margin:6px 0;'/>
                <div style='display:flex; justify-content:space-between; margin-bottom:4px;'>
                    <span style='color:#64748b;'>Hizmet Verilen Nüfus:</span>
                    <b>{hosp['allocated_population']:,} kişi</b>
                </div>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='color:#64748b;'>Kapasite Doluluk:</span>
                    <span style='background:#f1f5f9; padding:2px 6px; border-radius:4px; font-weight:700; color:{'#10b981' if hosp['utilization_pct']<=90 else '#f59e0b'};'>
                        %{hosp['utilization_pct']}
                    </span>
                </div>
            </div>
        </div>
        """
        
        folium.Marker(
            location=[hosp["lat"], hosp["lon"]],
            icon=icon,
            tooltip=f"🏥 {hosp['name']} (%{hosp['utilization_pct']} Dolu)",
            popup=folium.Popup(popup_html, max_width=320)
        ).add_to(hosp_fg)
    hosp_fg.add_to(m)

    # 13. HARİTA ÜZERİNDE SABİT GLASSMORPHISM LEJANT
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 1000;
        background: rgba(15, 23, 42, 0.92);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 10px;
        padding: 12px 16px;
        color: #f8fafc;
        font-family: sans-serif;
        font-size: 12px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        max-width: 250px;
    ">
        <div style="font-weight:bold; font-size:13px; color:#38bdf8; margin-bottom:8px; border-bottom:1px solid #334155; padding-bottom:4px;">
            🧭 ANKARA SAĞLIK GIS LEJANDI
        </div>
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="display:inline-block; width:12px; height:12px; background:#ef4444; border-radius:50%; margin-right:8px;"></span>
            Ağır Zirve Trafiği (15-25 km/s)
        </div>
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="display:inline-block; width:12px; height:12px; background:#f59e0b; border-radius:50%; margin-right:8px;"></span>
            Orta Seviye Trafik (40-50 km/s)
        </div>
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="display:inline-block; width:12px; height:12px; background:#10b981; border-radius:50%; margin-right:8px;"></span>
            Akıcı Trafik (65-85 km/s)
        </div>
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="margin-right:6px;">🏥</span> Optimal Açılan Hastaneler
        </div>
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="margin-right:6px;">🏢</span> Mevcut Şehir Hastaneleri
        </div>
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="margin-right:6px;">🚇</span> Ankara Metro & Banliyö Hatları
        </div>
        <div style="display:flex; align-items:center; margin-bottom:4px;">
            <span style="margin-right:6px;">🚌</span> AŞTİ, Gar & EGO Aktarma
        </div>
        <div style="display:flex; align-items:center;">
            <span style="margin-right:6px;">⭕</span> 10 ve 15 Dk Erişim Çemberleri
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Haritayı Render Et
    st_folium(m, width="100%", height=760)

# ===================== SEKME 2: MEVCUT DURUM VS OPTİMİZE MODEL =====================
with tab_comparison:
    st.markdown("### ⚖️ Mevcut Durum (Sadece 2 Şehir Hastanesi) vs Önerilen Çok Merkezli Model")
    st.caption("Bilkent ve Etlik Şehir Hastanelerine mahkûm kalındığında yaşanan gecikmeler ile yeni dağıtık modelin farkı:")
    
    col_cmp1, col_cmp2, col_cmp3 = st.columns(3)
    
    with col_cmp1:
        time_diff = baseline_perf['avg_travel_time_min'] - results['avg_travel_time_min']
        time_pct = (time_diff / baseline_perf['avg_travel_time_min']) * 100.0
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#38bdf8;">
                <div class="kpi-label">Ortalama Ambulans Süresi</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div>
                        <span style="font-size:0.8rem; color:#94a3b8;">Mevcut:</span><br/>
                        <span style="font-size:1.3rem; font-weight:700; color:#ef4444;">{baseline_perf['avg_travel_time_min']:.1f} dk</span>
                    </div>
                    <div style="font-size:1.5rem; color:#38bdf8;">➡️</div>
                    <div>
                        <span style="font-size:0.8rem; color:#94a3b8;">Önerilen:</span><br/>
                        <span style="font-size:1.3rem; font-weight:700; color:#10b981;">{results['avg_travel_time_min']:.1f} dk</span>
                    </div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">⚡ -%{time_pct:.1f} DAHA HIZLI ERİŞİM</span>
            </div>
        """, unsafe_allow_html=True)

    with col_cmp2:
        cov_gain = results['coverage_under_15_min_pct'] - baseline_perf['coverage_15_pct']
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#10b981;">
                <div class="kpi-label">15 Dk Acil Servis Kapsama Oranı</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div>
                        <span style="font-size:0.8rem; color:#94a3b8;">Mevcut:</span><br/>
                        <span style="font-size:1.3rem; font-weight:700; color:#ef4444;">%{baseline_perf['coverage_15_pct']:.1f}</span>
                    </div>
                    <div style="font-size:1.5rem; color:#10b981;">➡️</div>
                    <div>
                        <span style="font-size:0.8rem; color:#94a3b8;">Önerilen:</span><br/>
                        <span style="font-size:1.3rem; font-weight:700; color:#10b981;">%{results['coverage_under_15_min_pct']:.1f}</span>
                    </div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">📈 +%{cov_gain:.1f} DAHA FAZLA NÜFUS</span>
            </div>
        """, unsafe_allow_html=True)

    with col_cmp3:
        max_diff = baseline_perf['max_travel_time_min'] - results['max_travel_time_min']
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#ec4899;">
                <div class="kpi-label">En Uç İlçe Maksimum Ulaşım</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div>
                        <span style="font-size:0.8rem; color:#94a3b8;">Mevcut:</span><br/>
                        <span style="font-size:1.3rem; font-weight:700; color:#ef4444;">{baseline_perf['max_travel_time_min']:.1f} dk</span>
                    </div>
                    <div style="font-size:1.5rem; color:#ec4899;">➡️</div>
                    <div>
                        <span style="font-size:0.8rem; color:#94a3b8;">Önerilen:</span><br/>
                        <span style="font-size:1.3rem; font-weight:700; color:#10b981;">{results['max_travel_time_min']:.1f} dk</span>
                    </div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">🛡️ {max_diff:.1f} DAKİKA KAZANÇ</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    st.markdown("#### 📊 Performans Karşılaştırma Grafiği")
    cmp_chart_df = pd.DataFrame({
        "Metrik": ["Ortalama Seyahat Süresi (dk)", "15 Dk Kapsama Oranı (%)", "25 Dk Kapsama Oranı (%)"],
        "Mevcut Durum (Sadece Şehir Hastaneleri)": [baseline_perf["avg_travel_time_min"], baseline_perf["coverage_15_pct"], baseline_perf["coverage_25_pct"]],
        "Önerilen Çok Merkezli CFLP Modeli": [results["avg_travel_time_min"], results["coverage_under_15_min_pct"], results["coverage_under_25_min_pct"]]
    }).set_index("Metrik")
    st.bar_chart(cmp_chart_df)
    
    st.markdown("#### 🏆 En Yüksek Zaman Tasarrufu Sağlanan Çeper Semtler & İlçeler")
    gain_rows = []
    for ass in results["assignments"]:
        t1_b, _ = calculate_travel_time_minutes(ass["demand_lat"], ass["demand_lon"], EXISTING_HOSPITALS[0]["lat"], EXISTING_HOSPITALS[0]["lon"], hour=selected_hour)
        t2_b, _ = calculate_travel_time_minutes(ass["demand_lat"], ass["demand_lon"], EXISTING_HOSPITALS[1]["lat"], EXISTING_HOSPITALS[1]["lon"], hour=selected_hour)
        b_time = min(t1_b, t2_b)
        diff = b_time - ass["travel_time_min"]
        gain_rows.append({
            "Semt / İlçe": f"{ass['demand_name']} ({ass['district']})",
            "Nüfus": ass["population"],
            "Mevcut Şehir Hastanesi Süresi": f"{b_time:.1f} dk",
            "Önerilen Yeni Hastane Süresi": f"{ass['travel_time_min']:.1f} dk",
            "Kazanılan Hayat Kurtaran Süre": f"+{diff:.1f} dk",
            "diff_num": diff
        })
    df_gain = pd.DataFrame(gain_rows).sort_values(by="diff_num", ascending=False).drop(columns=["diff_num"]).head(8)
    st.dataframe(df_gain, width="stretch")
    
    st.success(
        "🎯 **Sunum Argümanı:** 'Hocam, mevcut durumda tüm Ankara nüfusunu Bilkent ve Etlik gibi 2 devasa kampüse yığmak, "
        "Polatlı, Elmadağ, Sincan ve Pursaklar gibi çeper ilçelerdeki acil vakaların ölüm riskini artırmaktadır. "
        "Matematiksel optimizasyon modelimiz bütçeyi eşit büyüklükte 5-6 stratejik merkeze paylaştırarak ortalama ambulans "
        f"süresini {baseline_perf['avg_travel_time_min']:.1f} dakikadan {results['avg_travel_time_min']:.1f} dakikaya indirmektedir.'"
    )

# ===================== SEKME 3: TOPLU TAŞIMA ANALİZİ =====================
with tab_transit:
    st.markdown("### 🚇 Ankara Raylı Sistemleri & EGO Ana Aktarma Merkezleri")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### 🚉 Kritik Aktarma Merkezleri ve Yolcu Kapasiteleri")
        df_hubs = pd.DataFrame(TRANSIT_HUBS)[["name", "type", "daily_passengers", "desc"]]
        df_hubs.columns = ["İstasyon / Aktarma Merkezi", "Tür", "Günlük Yolcu Hacmi", "Açıklama"]
        st.dataframe(df_hubs, width="stretch")
        
    with col_t2:
        st.markdown("#### 🚇 Ankara Raylı Sistem Hatları Listesi")
        lines_summary = []
        for line in TRANSIT_LINES:
            lines_summary.append({
                "Hat Adı": line["name"].split(" (")[0],
                "Tür": line["type"],
                "Güzergah": line["name"].split(" (")[1].replace(")", "") if "(" in line["name"] else "Ankara İçi"
            })
        st.dataframe(pd.DataFrame(lines_summary), width="stretch")

# ===================== SEKME 4: GRAFİKLER & TABLO =====================
with tab_analysis:
    st.markdown("### 📊 Hastane Yükü ve İlçe Bazlı Erişim Performansı")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("#### Hastane Yüklenen Nüfus vs Kapasite (Kişi)")
        chart_df = pd.DataFrame([{
            "Hastane": h["name"].split(" - ")[0],
            "Yüklenen Nüfus": h["allocated_population"],
            "Kapasite Limiti": h["capacity"]
        } for h in results["selected_hospitals"]]).set_index("Hastane")
        st.bar_chart(chart_df)
        
    with col_a2:
        st.markdown("#### Yapım ve Arsa Maliyeti (Milyon TL)")
        cost_df = pd.DataFrame([{
            "Hastane": h["name"].split(" - ")[0],
            "Maliyet (M TL)": h["cost_million_tl"]
        } for h in results["selected_hospitals"]]).set_index("Hastane")
        st.bar_chart(cost_df)
        
    st.markdown("---")
    st.markdown("#### 📋 Detaylı Semt ve Talep Tahsis Dökümü")
    df_ass = pd.DataFrame(results["assignments"])[[
        "demand_name", "district", "population", "hospital_name", "travel_time_min", "distance_km"
    ]]
    df_ass.columns = ["Semt/Bölge", "İlçe", "Nüfus", "Atanan Hastane", "Trafikli Ulaşım Süresi (dk)", "Mesafe (km)"]
    st.dataframe(df_ass.sort_values(by="Trafikli Ulaşım Süresi (dk)", ascending=False), width="stretch")

# ===================== SEKME 5: MATEMATİKSEL TEORİ =====================
with tab_theory:
    st.markdown("### 🎓 Dinamik Trafik Entegreli CFLP Matematiksel Modeli")
    st.markdown(r"""
    Bu projede standart CFLP formülasyonu, **zamana bağlı dinamik trafik katsayısı $K(t)$** ve **toplu taşıma erişilebilirliği** ile genişletilmiştir:
    
    #### 1. Dinamik Amaç Fonksiyonu:
    $$\min Z = w_1 \cdot \left(\frac{\sum_{i \in I} \sum_{j \in J} h_i \cdot T_{ij}(t) \cdot x_{ij}}{\text{NormTime}}\right) + w_2 \cdot \left(\frac{\sum_{j \in J} F_j \cdot y_j}{\text{NormCost}}\right)$$
    
    Burada:
    - $T_{ij}(t) = T_{ij}^{\text{baz}} \times K(t)$: $t$ saatindeki trafik sıkışıklık çarpanına bağlı gerçek sürüş süresi.
    - $t = 18$ (Akşam zirvesi) iken $K(18) = 1.85$ (Seyahat süreleri %85 artar).
    - $t = 02$ (Gece) iken $K(2) = 1.00$ (Serbest akış).
    - $h_i$: $i$ bölgesinin nüfusu (sağlık talebi ağırlığı).
    - $F_j$: $j$ aday hastanesinin inşaat ve arsa kamulaştırma maliyeti (Milyon TL).
    - $w_1, w_2$: Karar vericinin belirlediği seyahat süresi ve maliyet ağırlıkları ($w_1 + w_2 = 1.0$).
    
    #### 2. Kısıtlar:
    1. $\sum_{j \in J} x_{ij} = 1 \quad \forall i \in I$: Her semtin sağlık talebi eksiksiz bir hastaneye bağlanmalıdır.
    2. $x_{ij} \le y_j \quad \forall i, j$: Talep yalnızca fiziksel olarak açılmış ($y_j = 1$) bir hastaneye atanabilir.
    3. $\sum_{i \in I} h_i x_{ij} \le C_j y_j \quad \forall j \in J$: Hastaneye bağlanan nüfus, tesisin yatak/hizmet kapasitesini ($C_j$) aşamaz (CFLP kısıtı).
    4. $\sum_{j \in J} y_j = p$: Açılacak toplam hastane sayısı bütçe ve planlama gereği tam olarak $p$ adettir.
    5. $y_j \in \{0, 1\} \quad \forall j \in J$: Tesis açma karar değişkeni ikili (binary).
    6. $0 \le x_{ij} \le 1 \quad \forall i \in I, j \in J$: Hizmet tahsis oranı.
    """)
