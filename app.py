"""
ANKARA SAĞLIKNET — Çok Katmanlı Sağlık Yerleşimi ve Acil Müdahale Karar Destek Sistemi
Mimari: Modüler Katmanlı Yapı (Core / Data / UI)
Model: Elastik Kapasiteli Tesis Yeri Seçimi (Elastic CFLP / MILP)
"""

import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium import plugins
from streamlit_folium import st_folium

from core.models import DataStatus, FacilityType, OptimizationScenario
from core.optimizer import solve_elastic_cflp
from core.metrics import compare_scenarios
from core.routing import get_traffic_multiplier, calculate_travel_time
from data import get_verified_facilities, get_candidate_facilities, get_all_facilities, get_demand_zones

# ----------------- SAYFA YAPILANDIRMASI -----------------
st.set_page_config(
    page_title="ANKARA SAĞLIKNET — Karar Destek GIS",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Koyu Lacivert / Kurumsal Komuta Merkezi CSS
st.markdown("""
<style>
    .stApp {
        background-color: #070c18;
        color: #e2e8f0;
    }
    .header-box {
        background: linear-gradient(135deg, #0b1329 0%, #172554 100%);
        border: 1px solid #1e3a8a;
        border-radius: 12px;
        padding: 18px 24px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }
    .main-title {
        font-size: 1.95rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #60a5fa 0%, #a78bfa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .subtitle {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-top: 4px;
        margin-bottom: 0px;
    }
    .kpi-card {
        background: rgba(15, 23, 42, 0.9);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-top: 3px solid #3b82f6;
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3);
    }
    .kpi-val {
        font-size: 1.7rem;
        font-weight: 700;
        color: #f8fafc;
        margin: 2px 0;
    }
    .kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .badge-verified {
        background: #065f46;
        color: #a7f3d0;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-simulation {
        background: #854d0e;
        color: #fef08a;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .alert-box {
        background: rgba(127, 29, 29, 0.3);
        border: 1px solid #ef4444;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- VERİLERİ YÜKLE -----------------
verified_hospitals = get_verified_facilities()
candidate_hospitals = get_candidate_facilities()
all_facilities = get_all_facilities()
demand_zones = get_demand_zones()

# ----------------- YAN PANEL (KONTROL MERKEZİ) -----------------
with st.sidebar:
    st.markdown("""
        <div style='background:linear-gradient(135deg, #0f172a, #1e293b); border:1px solid #3b82f6; border-radius:10px; padding:14px; margin-bottom:14px; text-align:center;'>
            <div style='font-size:1.6rem;'>🏥 🚑 📊</div>
            <div style='font-size:1.15rem; font-weight:800; color:#60a5fa;'>ANKARA SAĞLIKNET</div>
            <div style='font-size:0.75rem; color:#94a3b8;'>Çok Katmanlı Karar Destek & CFLP</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. Senaryo Seçimi
    st.markdown("### 🎯 Çalışma Senaryosu")
    scenario_mode = st.radio(
        "Senaryo Türü:",
        [
            "Senaryo B: Mevcut Kamu Ağı + Yeni Yatırımlar (Önerilen)",
            "Senaryo A: Yalnızca Mevcut Kamu Ağı (Baz Durum, p=0)"
        ],
        index=0
    )
    is_scenario_b = ("Senaryo B" in scenario_mode)

    st.markdown("---")
    st.markdown("### ⚙️ Optimizasyon Parametreleri")
    
    if is_scenario_b:
        p_candidates = st.slider("Açılacak Yeni Aday Tesis Sayısı (p):", min_value=1, max_value=8, value=4, step=1)
        travel_weight = st.slider("Ulaşım Süresi Önceliği (%):", min_value=0, max_value=100, value=70, step=5)
        cost_weight = 100 - travel_weight
    else:
        p_candidates = 0
        travel_weight = 100
        cost_weight = 0
        st.info("ℹ️ Senaryo A'da yeni tesis açılmaz (p=0). Yalnızca mevcut 20 kamu hastanesinin performansı ölçülür.")

    enable_capacity = st.checkbox("Kapasite Kısıtlarını Uygula (CFLP)", value=True)

    st.markdown("---")
    st.markdown("### 🚦 Simülasyon Saat ve Trafik Profili")
    selected_hour = st.slider("Günün Saati (00:00 - 23:00):", min_value=0, max_value=23, value=18, step=1)
    traffic_mult = get_traffic_multiplier(selected_hour)
    
    if traffic_mult >= 1.6:
        st.markdown(f"🔴 **Yoğun Zirve Trafiği (+%{(traffic_mult-1)*100:.0f} Gecikme)**")
    elif traffic_mult >= 1.2:
        st.markdown(f"🟡 **Orta Düzey Trafik (+%{(traffic_mult-1)*100:.0f} Gecikme)**")
    else:
        st.markdown("🟢 **Akıcı Trafik (Normal Süre)**")

    st.markdown("---")
    st.markdown("### 👁️ Harita Katman Kontrolleri")
    show_verified = st.checkbox("🏢 Doğrulanmış Mevcut Hastaneler (20 Tesis)", value=True)
    show_candidates = st.checkbox("🏥 Yeni Yatırım Adayları (10 Tesis)", value=True)
    show_demands = st.checkbox("👥 TÜİK Nüfus Talep Merkezleri (32 Bölge)", value=True)
    show_assignment_lines = st.checkbox("🕸️ Hasta Tahsis Çizgileri", value=True)
    show_legend = st.checkbox("🧭 Açık Harita Lejandı", value=True)

# ----------------- OPTİMİZASYON SENARYOLARINI ÇALIŞTIR -----------------
# 1. Aktif Seçilen Senaryo
active_scenario = OptimizationScenario(
    name="Aktif Senaryo",
    description="Kullanıcı Parametreleriyle Çalıştırılan Senaryo",
    p_candidates=p_candidates,
    weight_travel_time=travel_weight / 100.0,
    weight_investment_cost=cost_weight / 100.0,
    hour=selected_hour,
    enable_capacity_limits=enable_capacity
)
results_active = solve_elastic_cflp(demand_zones, all_facilities, active_scenario)

# 2. Baz Senaryo A (Mevcut Durum p=0, Karşılaştırma için arka planda hesaplanır)
baseline_scenario = OptimizationScenario(
    name="Mevcut Durum",
    description="Sadece Doğrulanmış Mevcut Hastaneler (p=0)",
    p_candidates=0,
    weight_travel_time=1.0,
    weight_investment_cost=0.0,
    hour=selected_hour,
    enable_capacity_limits=enable_capacity
)
results_baseline = solve_elastic_cflp(demand_zones, all_facilities, baseline_scenario)

# Karşılaştırma Analitiği
comparison_data = compare_scenarios(results_baseline, results_active)

# ----------------- ÜST BAŞLIK VE KÜNYE -----------------
st.markdown(f"""
<div class="header-box">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h1 class="main-title">ANKARA SAĞLIKNET — KARAR DESTEK VE SİMÜLASYON SİSTEMİ</h1>
            <p class="subtitle">Saat <b>{selected_hour:02d}:00 Simülasyonu</b> | Doğrulanmış Kamu Hastaneleri vs Aday Yatırımlar | Elastik CFLP Modeli</p>
        </div>
        <div>
            <span class="badge-verified">20 Doğrulanmış Hastane</span>
            <span class="badge-simulation">10 Aday Lokasyon</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- AÇIKTA KALAN TALEP UYARISI -----------------
if results_active.get("has_unmet_demand"):
    st.markdown(f"""
    <div class="alert-box">
        <h4 style="margin:0; color:#f87171;">⚠️ KAPASİTE YETERSİZLİĞİ: TALEBİ KARŞILANAMAYAN NÜFUS TESPİT EDİLDİ!</h4>
        <p style="margin:5px 0 0 0; font-size:0.9rem; color:#fca5a5;">
            Toplam acil servis talebinin <b>%{results_active['unmet_percentage']:.2f}'si</b> ({results_active['unmet_demand_total']:,} başvuru/yıl) kapasite sınırları nedeniyle karşılanamamıştır.
            Aşağıdaki <b>'Kapasite & Açıkta Kalan Talep'</b> sekmesinden etkilenen ilçeleri inceleyiniz.
        </p>
    </div>
    """, unsafe_allow_html=True)

# ----------------- ÜST KPI KARTLARI -----------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#3b82f6;">
            <div class="kpi-label">Ort. Ulaşım Süresi</div>
            <div class="kpi-val">{results_active['avg_travel_time_min']:.1f} <span style="font-size:0.9rem; color:#64748b;">dk</span></div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    cov15 = results_active['coverage_under_15_min_pct']
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#10b981;">
            <div class="kpi-label">15 Dk Kapsama Oranı</div>
            <div class="kpi-val" style="color:{'#34d399' if cov15>60 else '#f59e0b'};">%{cov15:.1f}</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    unmet_pct = results_active['unmet_percentage']
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:{'#ef4444' if unmet_pct>0 else '#10b981'};">
            <div class="kpi-label">Açıkta Kalan Talep</div>
            <div class="kpi-val" style="color:{'#ef4444' if unmet_pct>0 else '#10b981'};">%{unmet_pct:.1f}</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    cost_val = results_active['total_investment_cost_million_tl']
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#8b5cf6;">
            <div class="kpi-label">Toplam Yatırım Bütçesi</div>
            <div class="kpi-val">{cost_val:,.0f} <span style="font-size:0.9rem; color:#64748b;">M TL</span></div>
        </div>
    """, unsafe_allow_html=True)

with c5:
    max_t = results_active['max_travel_time_min']
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#ec4899;">
            <div class="kpi-label">En Uzak İlçe Erişimi</div>
            <div class="kpi-val" style="color:#fb7185;">{max_t:.1f} <span style="font-size:0.9rem; color:#64748b;">dk</span></div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# ----------------- SEKMELER -----------------
tab_map, tab_comparison, tab_data, tab_capacity, tab_theory = st.tabs([
    "🗺️ TAKTİKSEL GIS HARİTASI",
    "⚖️ MEVCUT DURUM VS YENİ YATIRIMLAR (KIYASLAMA)",
    "📋 VERİ ŞEFFAFLIĞI VE PROVENANCE",
    "🚨 KAPASİTE VE AÇIKTA KALAN TALEP DENETİMİ",
    "📝 MATEMATİKSEL MODEL SPESİFİKASYONU"
])

# ===================== SEKME 1: HARİTA GÖRÜNÜMÜ =====================
with tab_map:
    # Folium Haritası
    m = folium.Map(
        location=[39.93, 32.78],
        zoom_start=10,
        tiles=None
    )
    
    # Esri Dark Gray Altlık (Sıfır filigran, profesyonel GIS)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri Dark Gray",
        name="Karanlık Komuta Modu",
        overlay=False
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
        attr="Labels",
        name="Etiketler",
        overlay=True
    ).add_to(m)

    # Taktiksel Araçlar
    plugins.Fullscreen(position='topleft', title='Tam Ekran').add_to(m)
    plugins.MiniMap(position='bottomleft', width=140, height=100, toggle_display=True).add_to(m)
    plugins.MeasureControl(position='bottomleft', primary_length_unit='kilometers').add_to(m)

    # Leaflet Özel CSS (Pulsing ve rozetler)
    leaflet_css = """
    <style>
    @keyframes pulseAday {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.8); transform: scale(0.96); }
        70% { box-shadow: 0 0 0 16px rgba(16, 185, 129, 0); transform: scale(1.05); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); transform: scale(0.96); }
    }
    .pulse-candidate {
        border-radius: 50%;
        animation: pulseAday 2.0s infinite ease-out;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #ffffff;
        background: #059669;
        font-size: 17px;
        color: white;
    }
    .existing-icon {
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #93c5fd;
        background: #1e40af;
        font-size: 15px;
        color: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    }
    </style>
    """
    m.get_root().html.add_child(folium.Element(leaflet_css))

    # 1. Doğrulanmış Mevcut Hastaneler Katmanı
    if show_verified:
        verified_fg = folium.FeatureGroup(name="🏢 Doğrulanmış Mevcut Hastaneler", show=True)
        for h in verified_hospitals:
            icon_html = '<div class="existing-icon" style="width:32px; height:32px;">🏢</div>'
            popup_html = f"""
            <div style='font-family:sans-serif; min-width:260px; color:#1e293b;'>
                <div style='background:#1e40af; color:white; padding:6px 10px; border-radius:6px 6px 0 0;'>
                    <span style='background:#065f46; color:#a7f3d0; font-size:9px; padding:2px 5px; border-radius:3px;'>DOĞRULANMIŞ GERÇEK VERİ</span><br/>
                    <b style='font-size:1.0rem;'>{h.name}</b>
                </div>
                <div style='padding:8px;'>
                    <b>Tür:</b> {h.facility_type.value}<br/>
                    <b>İlçe:</b> {h.district}<br/>
                    <b>Tescilli Yatak:</b> {h.bed_capacity:,}<br/>
                    <b>Acil Kabul Kapasitesi:</b> ~{h.annual_emergency_capacity:,} başvuru/yıl<br/>
                    <hr style='margin:6px 0;'/>
                    <span style='font-size:0.75rem; color:#64748b;'><b>Kaynak:</b> {h.source}</span>
                </div>
            </div>
            """
            folium.Marker(
                location=[h.lat, h.lon],
                icon=folium.DivIcon(html=icon_html, icon_size=(32, 32), icon_anchor=(16, 16)),
                tooltip=f"🏢 {h.name} ({h.bed_capacity} Yatak)",
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(verified_fg)
        verified_fg.add_to(m)

    # 2. Yeni Yatırım Adayları Katmanı
    if show_candidates:
        cand_fg = folium.FeatureGroup(name="🏥 Yeni Yatırım Adayları", show=True)
        selected_ids = set(results_active.get("selected_candidate_ids", []))
        
        for cand in candidate_hospitals:
            is_selected = cand.id in selected_ids
            if is_selected:
                icon_html = '<div class="pulse-candidate" style="width:36px; height:36px;">🏥</div>'
                badge_txt = "AÇILMASI ÖNERİLEN YATIRIM"
                badge_bg = "#059669"
            else:
                icon_html = '<div style="background:#475569; border-radius:50%; width:26px; height:26px; display:flex; align-items:center; justify-content:center; color:#94a3b8; font-size:13px; border:1px solid #cbd5e1;">⚪</div>'
                badge_txt = "SEÇİLMEYEN ADAY LOKASYON"
                badge_bg = "#475569"

            popup_html = f"""
            <div style='font-family:sans-serif; min-width:260px; color:#1e293b;'>
                <div style='background:{badge_bg}; color:white; padding:6px 10px; border-radius:6px 6px 0 0;'>
                    <span style='background:#854d0e; color:#fef08a; font-size:9px; padding:2px 5px; border-radius:3px;'>SİMÜLASYON VARSAYIMI</span><br/>
                    <b style='font-size:1.0rem;'>{cand.name}</b>
                </div>
                <div style='padding:8px;'>
                    <b>Statü:</b> {badge_txt}<br/>
                    <b>İlçe:</b> {cand.district}<br/>
                    <b>Yatırım Maliyeti:</b> {cand.investment_cost_million_tl:.1f} Milyon TL<br/>
                    <b>Hedef Yatak:</b> {cand.bed_capacity} Yatak<br/>
                    <b>Acil Kapasite Kotası:</b> ~{cand.annual_emergency_capacity:,} kişi/yıl<br/>
                    <hr style='margin:6px 0;'/>
                    <span style='font-size:0.75rem; color:#64748b;'><b>Dayanak:</b> {cand.source}</span>
                </div>
            </div>
            """
            folium.Marker(
                location=[cand.lat, cand.lon],
                icon=folium.DivIcon(html=icon_html, icon_size=(36, 36), icon_anchor=(18, 18)),
                tooltip=f"{'🏥 [SEÇİLDİ]' if is_selected else '⚪ [AÇILMADI]'} {cand.name}",
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(cand_fg)
        cand_fg.add_to(m)

    # 3. Talep Merkezleri Katmanı
    if show_demands:
        dem_fg = folium.FeatureGroup(name="👥 TÜİK Talep Merkezleri", show=True)
        for d in demand_zones:
            rad = 4 + (d.population / 60000)
            folium.CircleMarker(
                location=[d.lat, d.lon],
                radius=rad,
                color="#ffffff",
                weight=1.5,
                fill=True,
                fill_color="#38bdf8",
                fill_opacity=0.85,
                tooltip=f"📍 {d.name} ({d.population:,} Nüfus)",
                popup=folium.Popup(f"""
                    <div style='font-family:sans-serif; min-width:220px;'>
                        <span style='background:#0284c7; color:white; font-size:9px; padding:2px 5px; border-radius:3px;'>TÜİK 2023 ADNKS</span><br/>
                        <b>{d.name}</b> ({d.district})<br/>
                        <b>Nüfus:</b> {d.population:,} kişi<br/>
                        <b>Yıllık Acil Talep:</b> ~{d.annual_emergency_demand:,} başvuru/yıl
                    </div>
                """, max_width=260)
            ).add_to(dem_fg)
        dem_fg.add_to(m)

    # 4. Tahsis Hatları
    if show_assignment_lines:
        assign_fg = folium.FeatureGroup(name="🕸️ Hasta Sevk Hatları", show=True)
        for a in results_active.get("assignments", []):
            color = "#10b981" if not a["is_existing"] else "#3b82f6"
            folium.PolyLine(
                locations=[[a["demand_lat"], a["demand_lon"]], [a["facility_lat"], a["facility_lon"]]],
                color=color,
                weight=1.8,
                opacity=0.55,
                dash_array="4, 4" if a["is_existing"] else None,
                tooltip=f"{a['demand_name']} ➡️ {a['facility_name']} ({a['travel_time_min']} dk)"
            ).add_to(assign_fg)
        assign_fg.add_to(m)

    # 5. Açık Harita Lejandı
    if show_legend:
        legend_html = """
        <div style="position:fixed; bottom:25px; right:25px; z-index:1000; background:rgba(15, 23, 42, 0.95); border:1px solid #334155; border-radius:8px; padding:12px; font-size:12px; color:#f8fafc; font-family:sans-serif; min-width:240px; box-shadow:0 4px 16px rgba(0,0,0,0.5);">
            <div style="font-weight:bold; color:#60a5fa; margin-bottom:6px; border-bottom:1px solid #334155; padding-bottom:4px;">ANKARA SAĞLIKNET LEJANDI</div>
            <div style="margin-bottom:4px;"><span style="color:#60a5fa;">🏢</span> <b>Doğrulanmış Mevcut Hastane</b> (20 Tesis)</div>
            <div style="margin-bottom:4px;"><span style="color:#10b981;">🏥</span> <b>Seçilen Yeni Yatırım</b> (CFLP Optimum)</div>
            <div style="margin-bottom:4px;"><span style="color:#94a3b8;">⚪</span> <b>Açılmayan Aday Lokasyon</b></div>
            <div style="margin-bottom:4px;"><span style="color:#38bdf8;">📍</span> <b>TÜİK Talep Bölgesi</b> (Nüfus Odağı)</div>
            <div style="margin-bottom:4px;"><span style="display:inline-block; width:14px; height:3px; background:#10b981; margin-right:4px;"></span> Yeni Tesise Tahsis Hattı</div>
            <div><span style="display:inline-block; width:14px; height:3px; background:#3b82f6; margin-right:4px;"></span> Mevcut Hastaneye Tahsis Hattı</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

    st_folium(m, width="100%", height=720)

# ===================== SEKME 2: KARŞILAŞTIRMA =====================
with tab_comparison:
    st.markdown("### ⚖️ Senaryo A (Mevcut Durum) vs Senaryo B (Optimize Yeni Yatırımlar)")
    st.caption("Aynı talep bölgeleri, aynı nüfus katsayıları ve aynı saatlik trafik profiliyle birebir nesnel karşılaştırma:")

    cmp1, cmp2, cmp3 = st.columns(3)
    with cmp1:
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#3b82f6;">
                <div class="kpi-label">Ortalama Ambulans Süresi</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Mevcut:</span><br/><span style="font-size:1.3rem; font-weight:700; color:#ef4444;">{comparison_data['travel_time_a_min']:.1f} dk</span></div>
                    <div style="font-size:1.4rem; color:#60a5fa;">➡️</div>
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Önerilen:</span><br/><span style="font-size:1.3rem; font-weight:700; color:#10b981;">{comparison_data['travel_time_b_min']:.1f} dk</span></div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">⚡ -%{comparison_data['travel_time_saved_pct']:.1f} SÜRE KAZANCI</span>
            </div>
        """, unsafe_allow_html=True)

    with cmp2:
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#10b981;">
                <div class="kpi-label">15 Dk Acil Servis Kapsama Oranı</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Mevcut:</span><br/><span style="font-size:1.3rem; font-weight:700; color:#ef4444;">%{comparison_data['coverage_15_a_pct']:.1f}</span></div>
                    <div style="font-size:1.4rem; color:#10b981;">➡️</div>
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Önerilen:</span><br/><span style="font-size:1.3rem; font-weight:700; color:#10b981;">%{comparison_data['coverage_15_b_pct']:.1f}</span></div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">📈 +%{comparison_data['coverage_15_gain_pct']:.1f} DAHA FAZLA NÜFUS</span>
            </div>
        """, unsafe_allow_html=True)

    with cmp3:
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#ec4899;">
                <div class="kpi-label">En Uç İlçe Maksimum Seyahat</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Mevcut:</span><br/><span style="font-size:1.3rem; font-weight:700; color:#ef4444;">{comparison_data['max_time_a_min']:.1f} dk</span></div>
                    <div style="font-size:1.4rem; color:#ec4899;">➡️</div>
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Önerilen:</span><br/><span style="font-size:1.3rem; font-weight:700; color:#10b981;">{comparison_data['max_time_b_min']:.1f} dk</span></div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">🛡️ {comparison_data['max_time_gain_min']:.1f} DAKİKA KAZANÇ</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🏆 Yeni Yatırımlardan En Fazla Hayat Kurtaran Kazanım Sağlayan İlk 8 Semt")
    df_gains = pd.DataFrame(comparison_data["top_gaining_districts"])[[
        "demand_name", "district", "population", "scenario_a_time_min", "scenario_b_time_min", "time_saved_min", "assigned_facility"
    ]]
    df_gains.columns = ["Semt / Bölge", "İlçe", "Nüfus", "Mevcut Süre (dk)", "Önerilen Süre (dk)", "Zaman Kazancı (dk)", "Hizmet Veren Tesis"]
    st.dataframe(df_gains, use_container_width=True)

# ===================== SEKME 3: VERİ ŞEFFAFLIĞI =====================
with tab_data:
    st.markdown("### 📋 Veri Kaynakları ve Doğruluk Derecesi (Provenance)")
    st.markdown("""
    Bu sistemde **doğrulanmış resmi kamu verileri** ile **senaryo simülasyon varsayımları** birbirinden kesin çizgilerle ayrılmıştır.
    """)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("#### 🏢 Doğrulanmış Resmi Kamu Hastaneleri (20 Tesis)")
        df_ver = pd.DataFrame([h.to_dict() for h in verified_hospitals])[[
            "name", "district", "facility_type", "bed_capacity", "annual_emergency_capacity", "source"
        ]]
        df_ver.columns = ["Hastane Adı", "İlçe", "Tür", "Yatak", "Yıllık Kapasite", "Resmi Kaynak"]
        st.dataframe(df_ver, use_container_width=True)

    with col_d2:
        st.markdown("#### 🏥 Yeni Yatırım Aday Lokasyonları (Simülasyon - 10 Tesis)")
        df_cand = pd.DataFrame([c.to_dict() for c in candidate_hospitals])[[
            "name", "district", "investment_cost_million_tl", "bed_capacity", "annual_emergency_capacity", "source"
        ]]
        df_cand.columns = ["Aday Tesis Adı", "İlçe", "Maliyet (M TL)", "Hedef Yatak", "Yıllık Kapasite Kotası", "Simülasyon Dayanağı"]
        st.dataframe(df_cand, use_container_width=True)

# ===================== SEKME 4: KAPASİTE VE AÇIKTA KALAN TALEP =====================
with tab_capacity:
    st.markdown("### 🚨 Kapasite Kısıtları ve Açıkta Kalan Talep Denetimi")
    st.caption("CFLP modelinde hiçbir talep bölgesi sessizce yok sayılmaz; karşılanamayan talep elastik slack değişkeniyle (u_i) raporlanır:")

    if results_active.get("has_unmet_demand"):
        st.error(f"❌ Aktif senaryoda toplam {results_active['unmet_demand_total']:,} acil başvuru talebi (%{results_active['unmet_percentage']:.2f}) karşılanamamıştır!")
        st.markdown("#### Açıkta Kalan Talep Bölgeleri Dökümü:")
        df_unmet = pd.DataFrame(results_active["unmet_zones"])[[
            "zone_name", "district", "unmet_population", "unmet_annual_demand", "unmet_fraction"
        ]]
        df_unmet.columns = ["Bölge / Semt", "İlçe", "Açıkta Kalan Nüfus", "Açıkta Kalan Yıllık Acil Talep", "Karşılanamayan Oran"]
        st.dataframe(df_unmet, use_container_width=True)
    else:
        st.success("✅ **Tam Kapsama Sağlandı:** Aktif senaryoda Ankara'nın 5.8 milyonluk nüfusunun tüm acil servis talebi açık tesislerin kapasite sınırları dahilinde karşılanmıştır (Açıkta kalan talep: %0.0).")

# ===================== SEKME 5: MATEMATİKSEL TEORİ =====================
with tab_theory:
    st.markdown("### 📝 Elastik CFLP Matematiksel Formülasyonu")
    st.markdown(r"""
    $$\min Z = w_1 \cdot \left(\frac{\sum_{i \in I} \sum_{j \in J} d_i \cdot T_{ij}(t) \cdot x_{ij}}{\text{NormTime}}\right) + w_2 \cdot \left(\frac{\sum_{j \in J_{\text{cand}}} F_j \cdot y_j}{\text{NormCost}}\right) + M \cdot \sum_{i \in I} u_i$$
    
    #### Kısıtlar:
    1. **Elastik Talep Korunumu:** $\sum_{j \in J} x_{ij} + u_i = 1 \quad \forall i \in I$
    2. **Açık Tesis Mantıksal Bağı:** $x_{ij} \le y_j \quad \forall i \in I, \; \forall j \in J_{\text{cand}}$
    3. **Kapasite Sınırı:** $\sum_{i \in I} d_i \cdot x_{ij} \le C_j \cdot y_j \quad \forall j \in J$
    4. **Bütçe / Tesis Sayısı:** $\sum_{j \in J_{\text{cand}}} y_j = p$
    5. **Değişkenler:** $y_j \in \{0, 1\}, \quad x_{ij} \ge 0, \quad u_i \ge 0$
    
    *Burada $u_i$ açıkta kalan talep fraksiyonunu, $M = 1000$ ise karşılanamayan talep ceza katsayısını temsil eder.*
    """)
