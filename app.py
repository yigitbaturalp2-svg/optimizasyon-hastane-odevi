"""
ANKARA SAĞLIKNET - Çok Katmanlı Sağlık Yerleşimi ve Acil Müdahale Karar Destek Sistemi
Web Uygulaması: Streamlit + Folium + PuLP CBC
"""

import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import pandas as pd
import numpy as np

from core.models import (
    DataStatus, FacilityType, CandidateSelectionMode, OptimizationScenario,
    is_eligible_for_hospital_optimization
)
from core.optimizer import solve_elastic_cflp
from core.routing import get_traffic_multiplier, RoutingMode
from core.metrics import compare_scenarios
from data import (
    get_verified_facilities, get_candidate_facilities, get_demand_zones,
    get_all_facilities, get_eligible_candidate_hospitals, get_candidate_emergency_posts
)

# ----------------- STREAMLIT KONFİGÜRASYONU -----------------
st.set_page_config(
    page_title="Ankara SağlıkNet | Karar Destek Sistemi",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- ÖZEL CSS STİLLERİ -----------------
st.markdown("""
<style>
    .main {
        background-color: #0b0f19;
        color: #f1f5f9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1e293b;
        padding: 8px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
    }
    .main-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #f8fafc;
        letter-spacing: -0.02em;
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
    .badge-post {
        background: #1e3a8a;
        color: #bfdbfe;
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
candidate_all = get_candidate_facilities()
candidate_hospitals = get_eligible_candidate_hospitals()       # 6 adet hastane adayı
candidate_emergency_posts = get_candidate_emergency_posts()   # 4 adet acil üssü adayı
all_facilities = get_all_facilities()
demand_zones = get_demand_zones()

# ----------------- YAN PANEL (KONTROL MERKEZİ) -----------------
with st.sidebar:
    st.markdown("""
        <div style='background:linear-gradient(135deg, #0f172a, #1e293b); border:1px solid #3b82f6; border-radius:10px; padding:14px; margin-bottom:14px; text-align:center;'>
            <div style='font-size:1.6rem;'>🏥 🚑 📊</div>
            <div style='font-size:1.15rem; font-weight:800; color:#60a5fa;'>ANKARA SAĞLIKNET</div>
            <div style='font-size:0.75rem; color:#94a3b8;'>Hastane Yerleşim ve Nakil Optimizasyonu</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. Senaryo Modu Seçimi
    st.markdown("### 🎯 Çalışma Senaryosu")
    scenario_mode = st.radio(
        "Senaryo Türü:",
        [
            "Senaryo B: Mevcut Ağ + Yeni Yatırım Adayları (Optimizasyon)",
            "Senaryo A: Yalnızca Mevcut Resmi Ağ (Baz Durum, p=0)"
        ],
        index=0
    )
    is_scenario_b = ("Senaryo B" in scenario_mode)

    st.markdown("---")
    st.markdown("### ⚙️ Optimizasyon Parametreleri")

    if is_scenario_b:
        # Aday Seçim ve Bütçe Kısıtı Modu (TEKNİK GÖREV 001.3)
        selection_mode_label = st.selectbox(
            "Aday Seçim / Bütçe Kısıtı Türü:",
            [
                "Tam p Adet Yeni Hastane (EXACT_COUNT)",
                "En Fazla p Adet Yeni Hastane (MAX_COUNT)",
                "Yatırım Bütçesi Sınırı (BUDGET_LIMIT)",
                "Kombine: En Fazla p Adet + Bütçe Sınırı (COMBINED)"
            ],
            index=0
        )
        if "EXACT_COUNT" in selection_mode_label:
            cand_mode = CandidateSelectionMode.EXACT_COUNT
        elif "MAX_COUNT" in selection_mode_label:
            cand_mode = CandidateSelectionMode.MAX_COUNT
        elif "BUDGET_LIMIT" in selection_mode_label:
            cand_mode = CandidateSelectionMode.BUDGET_LIMIT
        else:
            cand_mode = CandidateSelectionMode.COMBINED

        # Tesis sayısı ve bütçe girdileri
        if cand_mode in (CandidateSelectionMode.EXACT_COUNT, CandidateSelectionMode.MAX_COUNT, CandidateSelectionMode.COMBINED):
            p_candidates = st.slider(
                "Açılacak Yeni Hastane Sayısı (p):",
                min_value=1,
                max_value=len(candidate_hospitals),
                value=3,
                step=1,
                help=f"Genel hastane optimizasyonuna uygun {len(candidate_hospitals)} adet aday sağlık kampüsü bulunmaktadır."
            )
        else:
            p_candidates = len(candidate_hospitals)

        if cand_mode in (CandidateSelectionMode.BUDGET_LIMIT, CandidateSelectionMode.COMBINED):
            budget_limit = st.slider(
                "Maksimum Yatırım Bütçesi (Milyon TL):",
                min_value=500.0,
                max_value=4500.0,
                value=2000.0,
                step=100.0,
                help="Seçilen yeni tesislerin toplam yatırım maliyetinin üst sınırı."
            )
        else:
            budget_limit = None

        travel_weight = st.slider("Nakil Süresi Önceliği (%):", min_value=0, max_value=100, value=75, step=5)
        cost_weight = 100 - travel_weight
    else:
        cand_mode = CandidateSelectionMode.EXACT_COUNT
        p_candidates = 0
        budget_limit = None
        travel_weight = 100
        cost_weight = 0
        st.info("ℹ️ Senaryo A'da yeni tesis açılmaz (p=0). Mevcut 20 kamu hastanesinin performansı ölçülür.")

    enable_capacity = st.checkbox("Kapasite Kısıtlarını Uygula (CFLP)", value=True)
    use_lexico = st.checkbox("İki Aşamalı Lexicographic Çözücü", value=True, help="Önce açıkta kalan talebi minimize eder; ardından seyahat süresini optimize eder.")

    st.markdown("---")
    st.markdown("### 🚦 Ulaşım Yöntemi ve Trafik Modeli")
    
    routing_choice = st.radio(
        "Ulaşım Motoru Modu:",
        [
            "Tahmini Geometrik Mod (Haversine * 1.28x Yol Katsayısı)",
            "OSRM Yol Ağı Modu (Gerçek Karayolu Geometrisi)"
        ],
        index=0
    )
    is_osrm = ("OSRM" in routing_choice)
    active_routing_mode = RoutingMode.OSRM_NETWORK if is_osrm else RoutingMode.ESTIMATED_GEOMETRIC
    allow_fallback = st.checkbox("OSRM servis hatasında geometrik modele dön", value=True)

    selected_hour = st.slider("Günün Saati (00:00 - 23:00):", min_value=0, max_value=23, value=18, step=1)
    traffic_mult = get_traffic_multiplier(selected_hour)

    if traffic_mult >= 1.6:
        st.markdown(f"🔴 **Zirve Trafik Simülasyonu (+%{(traffic_mult-1)*100:.0f} Gecikme)**")
    elif traffic_mult >= 1.2:
        st.markdown(f"🟡 **Orta Düzey Trafik Simülasyonu (+%{(traffic_mult-1)*100:.0f} Gecikme)**")
    else:
        st.markdown("🟢 **Akıcı Trafik (Normal Süre)**")

    st.markdown("---")
    st.markdown("### 👁️ Harita Katman Kontrolleri")
    show_verified = st.checkbox("🏢 Doğrulanmış Mevcut Hastaneler (20 Tesis)", value=True)
    show_cand_hospitals = st.checkbox("🏥 Aday Sağlık Kampüsleri (6 Hastane)", value=True)
    show_cand_posts = st.checkbox("🚑 Aday Acil Müdahale Üsleri (4 Üs - Faz 002)", value=True)
    show_demands = st.checkbox("👥 TÜİK Nüfus Talep Merkezleri (32 Bölge)", value=True)
    show_assignment_lines = st.checkbox("🕸️ Hasta Sevk ve Tahsis Hatları", value=True)
    show_legend = st.checkbox("🧭 Açık Harita Lejandı", value=True)

# ----------------- OPTİMİZASYON SENARYOLARINI ÇALIŞTIR -----------------
# 1. Aktif Seçilen Senaryo
active_scenario = OptimizationScenario(
    name="Aktif Senaryo",
    description="Kullanıcı Parametreleriyle Çalıştırılan Senaryo",
    candidate_selection_mode=cand_mode,
    p_candidates=p_candidates,
    max_investment_budget_million_tl=budget_limit,
    weight_travel_time=travel_weight / 100.0,
    weight_investment_cost=cost_weight / 100.0,
    hour=selected_hour,
    enable_capacity_limits=enable_capacity,
    use_lexicographic=use_lexico
)

results_active = solve_elastic_cflp(
    demand_zones, all_facilities, active_scenario,
    routing_mode=active_routing_mode,
    allow_osrm_fallback_to_geometric=allow_fallback
)

# ----------------- ÇÖZÜCÜ BAŞARISIZLIK KONTROLÜ (ERKEN DENETİM) -----------------
# Metadata veya sonuç okunmadan önce başarısızlık kontrol edilir; çökme önlenir
if not results_active.get("success", False):
    st.error(f"""
        ⚠️ **Optimizasyon Başarısız Oldu:** {results_active.get('status')}  
        **Açıklama:** {results_active.get('message')}  
        Lütfen sol paneldeki parametreleri (aday tesis sayısı, bütçe tavanı veya kapasite ayarları) kontrol ediniz.
    """)
    st.stop()

# 2. Baz Senaryo A (Mevcut Durum p=0, Karşılaştırma için arka planda hesaplanır)
baseline_scenario = OptimizationScenario(
    name="Mevcut Durum",
    description="Sadece Doğrulanmış Mevcut Hastaneler (p=0)",
    candidate_selection_mode=CandidateSelectionMode.EXACT_COUNT,
    p_candidates=0,
    weight_travel_time=1.0,
    weight_investment_cost=0.0,
    hour=selected_hour,
    enable_capacity_limits=enable_capacity,
    use_lexicographic=use_lexico
)

results_baseline = solve_elastic_cflp(
    demand_zones, all_facilities, baseline_scenario,
    routing_mode=active_routing_mode,
    allow_osrm_fallback_to_geometric=allow_fallback
)

# Karşılaştırma Analitiği (Kesirli tahsis gruplamalı ve kapsama uyarı denetimli)
comparison_data = compare_scenarios(results_baseline, results_active)

# ----------------- ÜST BAŞLIK VE KÜNYE -----------------
st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid #1e293b; padding-bottom:8px;">
        <div>
            <h1 class="main-title">ANKARA SAĞLIKNET — ÇOK KATMANLI KARAR DESTEK SİSTEMİ</h1>
            <p class="subtitle">Ankara Metropolü Sağlık Tesis Yerleşimi ve Acil Müdahale Kapasite Optimizasyonu</p>
        </div>
        <div style="text-align:right;">
            <span class="badge-verified">20 Doğrulanmış Kamu Hastanesi</span>
            <span class="badge-simulation">6 Aday Sağlık Kampüsü</span>
            <span class="badge-post">4 Aday Acil Üssü (Faz 002)</span><br/>
            <span style="font-size:0.75rem; color:#64748b;">Model: Elastik CFLP / MILP (PuLP) &bull; Ulaşım: {results_active['routing_metadata']['source']}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# Başarısızlık kontrolü yukarıda erken denetim olarak yapıldı.

# ----------------- ÜST KPI KARTLARI (ÖLÇÜLEBİLİR METRİKLER) -----------------
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    avg_t = results_active.get('avg_travel_time_min')
    avg_t_str = f"{avg_t:.1f} <span style='font-size:0.9rem; color:#64748b;'>dk</span>" if avg_t is not None else "<span style='font-size:1.1rem; color:#94a3b8;'>Tanımsız</span>"
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#3b82f6;">
            <div class="kpi-label">Tahmini Nakil Süresi</div>
            <div class="kpi-val">{avg_t_str}</div>
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
            <div class="kpi-label">Karşılanamayan Yıllık Talep</div>
            <div class="kpi-val" style="color:{'#f87171' if unmet_pct>0 else '#34d399'};">%{unmet_pct:.2f}</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    n_active = len(results_active['active_facility_ids'])
    n_new = len(results_active['selected_candidate_ids'])
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#a855f7;">
            <div class="kpi-label">Açık Sağlık Tesisleri</div>
            <div class="kpi-val">{n_active} <span style="font-size:0.9rem; color:#a855f7;">(+{n_new} Yeni)</span></div>
        </div>
    """, unsafe_allow_html=True)

with c5:
    cost = results_active['total_investment_cost_million_tl']
    st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#f59e0b;">
            <div class="kpi-label">Yeni Yatırım Tahmini Maliyeti</div>
            <div class="kpi-val">{cost:.1f} <span style="font-size:0.9rem; color:#64748b;">M TL</span></div>
        </div>
    """, unsafe_allow_html=True)

# ----------------- SEKMELİ ANALİTİK PANELİ -----------------
tab_map, tab_comparison, tab_data, tab_capacity, tab_theory = st.tabs([
    "🗺️ Taktiksel CBS & Sevk Haritası",
    "📊 Senaryo Karşılaştırması & Hakkaniyet",
    "🔍 Veri Şeffaflığı & Provenance",
    "🚨 Kapasite & Açıkta Kalan Talep",
    "📝 Matematiksel Formülasyon"
])

# ===================== SEKME 1: HARİTA =====================
with tab_map:
    # Esri Dark Gray Canvas Haritası
    m = folium.Map(
        location=[39.9250, 32.8350],
        zoom_start=11,
        tiles=None,
        control_scale=True,
        prefer_canvas=True
    )

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Dark Gray",
        name="Karanlık Taktiksel Taban",
        overlay=False
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
        attr="Labels",
        name="Etiketler",
        overlay=True
    ).add_to(m)

    plugins.Fullscreen(position='topleft', title='Tam Ekran').add_to(m)
    plugins.MiniMap(position='bottomleft', width=140, height=100, toggle_display=True).add_to(m)
    plugins.MeasureControl(position='bottomleft', primary_length_unit='kilometers').add_to(m)

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
    .emergency-post-icon {
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 2px solid #facc15;
        background: #854d0e;
        font-size: 14px;
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
                    <span style='background:#065f46; color:#a7f3d0; font-size:9px; padding:2px 5px; border-radius:3px;'>DOĞRULANMIŞ GERÇEK TESİS</span><br/>
                    <b style='font-size:1.0rem;'>{h.name}</b>
                </div>
                <div style='padding:8px;'>
                    <b>Tür:</b> {h.facility_type.value}<br/>
                    <b>İlçe:</b> {h.district}<br/>
                    <b>Tescilli Yatak:</b> {h.bed_capacity:,}<br/>
                    <b>Acil Kabul Kapasitesi:</b> ~{h.annual_emergency_capacity:,} başvuru/yıl (Simülasyon Normu)<br/>
                    <hr style='margin:6px 0;'/>
                    <span style='font-size:0.75rem; color:#64748b;'><b>Tescil Kaynağı:</b> {h.source}</span>
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

    # 2. Aday Sağlık Kampüsleri Katmanı (6 Aday Hastane)
    if show_cand_hospitals:
        cand_fg = folium.FeatureGroup(name="🏥 Aday Sağlık Kampüsleri (6 Hastane)", show=True)
        selected_ids = set(results_active.get("selected_candidate_ids", []))

        for cand in candidate_hospitals:
            is_selected = cand.id in selected_ids
            if is_selected:
                icon_html = '<div class="pulse-candidate" style="width:36px; height:36px;">🏥</div>'
                badge_txt = "AÇILMASI ÖNERİLEN HASTANE"
                badge_bg = "#059669"
            else:
                icon_html = '<div style="background:#475569; border-radius:50%; width:26px; height:26px; display:flex; align-items:center; justify-content:center; color:#94a3b8; font-size:13px; border:1px solid #cbd5e1;">⚪</div>'
                badge_txt = "SEÇİLMEYEN ADAY HASTANE"
                badge_bg = "#475569"

            popup_html = f"""
            <div style='font-family:sans-serif; min-width:260px; color:#1e293b;'>
                <div style='background:{badge_bg}; color:white; padding:6px 10px; border-radius:6px 6px 0 0;'>
                    <span style='background:#854d0e; color:#fef08a; font-size:9px; padding:2px 5px; border-radius:3px;'>SİMÜLASYON ADAYI</span><br/>
                    <b style='font-size:1.0rem;'>{cand.name}</b>
                </div>
                <div style='padding:8px;'>
                    <b>Statü:</b> {badge_txt}<br/>
                    <b>İlçe:</b> {cand.district}<br/>
                    <b>Yatırım Maliyeti:</b> {cand.investment_cost_million_tl:.1f} Milyon TL<br/>
                    <b>Hedef Yatak:</b> {cand.bed_capacity} Yatak<br/>
                    <b>Simüle Kapasite:</b> ~{cand.annual_emergency_capacity:,} başvuru/yıl<br/>
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

    # 3. Aday Acil Müdahale Üsleri Katmanı (4 Üs - Faz 002 İçin Ayrılmış)
    if show_cand_posts:
        post_fg = folium.FeatureGroup(name="🚑 Aday Acil Müdahale Üsleri (4 Üs - Faz 002)", show=True)
        for post in candidate_emergency_posts:
            icon_html = '<div class="emergency-post-icon" style="width:30px; height:30px;">🚑</div>'
            popup_html = f"""
            <div style='font-family:sans-serif; min-width:260px; color:#1e293b;'>
                <div style='background:#854d0e; color:white; padding:6px 10px; border-radius:6px 6px 0 0;'>
                    <span style='background:#1e3a8a; color:#bfdbfe; font-size:9px; padding:2px 5px; border-radius:3px;'>FAZ 002 İÇİN AYRILMIŞ</span><br/>
                    <b style='font-size:1.0rem;'>{post.name}</b>
                </div>
                <div style='padding:8px;'>
                    <b>Tür:</b> {post.facility_type.value}<br/>
                    <b>İlçe:</b> {post.district}<br/>
                    <b>Rol:</b> İlk Müdahale / 112 Takviye İstasyonu (Genel Hastane Değildir)<br/>
                    <b>Yatak Sayısı:</b> 0 (Yataklı servis bulunmaz)<br/>
                    <b>Maliyet:</b> {post.investment_cost_million_tl:.1f} Milyon TL<br/>
                    <hr style='margin:6px 0;'/>
                    <span style='font-size:0.75rem; color:#64748b;'><b>Durum:</b> Genel hastane optimizasyonuna kapalıdır.</span>
                </div>
            </div>
            """
            folium.Marker(
                location=[post.lat, post.lon],
                icon=folium.DivIcon(html=icon_html, icon_size=(30, 30), icon_anchor=(15, 15)),
                tooltip=f"🚑 {post.name} (Acil Üssü - Faz 002)",
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(post_fg)
        post_fg.add_to(m)

    # 4. Talep Merkezleri Katmanı
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
                        <b>Yıllık Acil Servis Talebi:</b> ~{d.annual_emergency_demand:,} başvuru/yıl (0.35 normu)
                    </div>
                """, max_width=260)
            ).add_to(dem_fg)
        dem_fg.add_to(m)

    # 5. Hasta Tahsis Hatları
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
                tooltip=f"{a['demand_name']} ➡️ {a['facility_name']} ({a['travel_time_min']:.1f} dk)"
            ).add_to(assign_fg)
        assign_fg.add_to(m)

    # 6. Açık Harita Lejandı
    if show_legend:
        legend_html = """
        <div style="position:fixed; bottom:25px; right:25px; z-index:1000; background:rgba(15, 23, 42, 0.95); border:1px solid #334155; border-radius:8px; padding:12px; font-size:12px; color:#f8fafc; font-family:sans-serif; min-width:260px; box-shadow:0 4px 16px rgba(0,0,0,0.5);">
            <div style="font-weight:bold; color:#60a5fa; margin-bottom:6px; border-bottom:1px solid #334155; padding-bottom:4px;">ANKARA SAĞLIKNET LEJANDI</div>
            <div style="margin-bottom:4px;"><span style="color:#60a5fa;">🏢</span> <b>Doğrulanmış Mevcut Hastane</b> (20 Tesis)</div>
            <div style="margin-bottom:4px;"><span style="color:#10b981;">🏥</span> <b>Seçilen Yeni Sağlık Kampüsü</b> (Optimum)</div>
            <div style="margin-bottom:4px;"><span style="color:#94a3b8;">⚪</span> <b>Açılmayan Aday Sağlık Kampüsü</b></div>
            <div style="margin-bottom:4px;"><span style="color:#facc15;">🚑</span> <b>Aday Acil Üssü (Faz 002 İçin Ayrılmış)</b></div>
            <div style="margin-bottom:4px;"><span style="color:#38bdf8;">📍</span> <b>TÜİK Talep Bölgesi</b> (32 Odak, 5.57M Nüfus)</div>
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

    if comparison_data.get("has_coverage_difference"):
        st.warning(f"⚠️ {comparison_data['coverage_warning']}")

    cmp1, cmp2, cmp3 = st.columns(3)
    with cmp1:
        time_a_val = comparison_data['travel_time_a_min']
        time_b_val = comparison_data['travel_time_b_min']
        time_a_str = f"{time_a_val:.1f} dk" if time_a_val is not None else "Tanımsız"
        time_b_str = f"{time_b_val:.1f} dk" if time_b_val is not None else "Tanımsız"
        saved_str = f"⚡ -%{comparison_data['travel_time_saved_pct']:.1f} SÜRE KAZANCI" if comparison_data['travel_time_saved_min'] is not None else "Kapsama Farkı Var"

        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#3b82f6;">
                <div class="kpi-label">Tahmini Hastaneye Nakil Süresi</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Mevcut (A):</span><br/><span style="font-size:1.3rem; font-weight:700; color:#ef4444;">{time_a_str}</span></div>
                    <div style="font-size:1.4rem; color:#60a5fa;">➡️</div>
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Önerilen (B):</span><br/><span style="font-size:1.3rem; font-weight:700; color:#10b981;">{time_b_str}</span></div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">{saved_str}</span>
            </div>
        """, unsafe_allow_html=True)

    with cmp2:
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#10b981;">
                <div class="kpi-label">15 Dk Acil Servis Kapsama Oranı</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Mevcut (A):</span><br/><span style="font-size:1.3rem; font-weight:700; color:#ef4444;">%{comparison_data['coverage_15_a_pct']:.1f}</span></div>
                    <div style="font-size:1.4rem; color:#10b981;">➡️</div>
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Önerilen (B):</span><br/><span style="font-size:1.3rem; font-weight:700; color:#10b981;">%{comparison_data['coverage_15_b_pct']:.1f}</span></div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">📈 +%{comparison_data['coverage_15_gain_pct']:.1f} DAHA FAZLA NÜFUS</span>
            </div>
        """, unsafe_allow_html=True)

    with cmp3:
        st.markdown(f"""
            <div class="kpi-card" style="border-top-color:#ec4899;">
                <div class="kpi-label">Maksimum Nakil Süresi</div>
                <div style="display:flex; justify-content:space-around; align-items:center; margin:8px 0;">
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Mevcut (A):</span><br/><span style="font-size:1.3rem; font-weight:700; color:#ef4444;">{comparison_data['max_time_a_min']:.1f} dk</span></div>
                    <div style="font-size:1.4rem; color:#ec4899;">➡️</div>
                    <div><span style="font-size:0.8rem; color:#94a3b8;">Önerilen (B):</span><br/><span style="font-size:1.3rem; font-weight:700; color:#10b981;">{comparison_data['max_time_b_min']:.1f} dk</span></div>
                </div>
                <span style="color:#10b981; font-weight:bold; font-size:0.85rem;">🛡️ {comparison_data['max_time_gain_min']:.1f} DAKİKA KAZANÇ</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🏆 Bölge Bazında Gruplanmış Tahsis ve Süre Karşılaştırması (Kesirli Tahsis Kaybı Yok)")
    comparisons = comparison_data.get("all_district_comparisons", [])
    if comparisons:
        df_comp = pd.DataFrame(comparisons)[[
            "demand_name", "district", "population", "scenario_a_time_min", "scenario_b_time_min",
            "time_saved_min", "comparison_status", "assigned_facility"
        ]]
        df_comp.columns = [
            "Semt / Bölge", "İlçe", "Nüfus", "Mevcut Ağırlıklı Süre (dk)",
            "Önerilen Ağırlıklı Süre (dk)", "Zaman Kazancı (dk)", "Karşılaştırma Durumu", "Birincil Tesis"
        ]
        st.dataframe(df_comp, use_container_width=True)

# ===================== SEKME 3: VERİ ŞEFFAFLIĞI VE PROVENANCE =====================
with tab_data:
    st.markdown("### 📋 Veri Kaynakları, Provenance ve Güvenilirlik Kayıtları")
    st.markdown("""
    Bu sistemde **doğrulanmış resmi kamu verileri**, **kentsel planlama simülasyon varsayımları** ve **Faz 002 acil müdahale üsleri**
    birbirinden kesin çizgilerle ayrılmıştır.
    """)

    sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs([
        "🏢 Doğrulanmış Mevcut Hastaneler (20)",
        "🏥 Aday Sağlık Kampüsleri (6)",
        "🚑 Aday Acil Müdahale Üsleri (4 - Faz 002)",
        "👥 TÜİK Nüfus ve Talep Doğrulama (32)"
    ])

    with sub_t1:
        st.markdown("#### 🏢 T.C. Sağlık Bakanlığı Doğrulanmış Gerçek Kamu Hastaneleri")
        df_ver = pd.DataFrame([h.to_dict() for h in verified_hospitals])[[
            "name", "district", "facility_type", "bed_capacity", "annual_emergency_capacity",
            "capacity_is_simulated", "coordinate_source", "last_verified_date"
        ]]
        df_ver.columns = [
            "Hastane Adı", "İlçe", "Tür", "Tescilli Yatak", "Simüle Acil Kapasite (Kişi/Yıl)",
            "Kapasite Simüle mi?", "Koordinat Kaynağı", "Son Doğrulama"
        ]
        st.dataframe(df_ver, use_container_width=True)

    with sub_t2:
        st.markdown("#### 🏥 Genel Hastane Nakline Uygun Aday Sağlık Kampüsleri (6 Adet)")
        df_cand_h = pd.DataFrame([c.to_dict() for c in candidate_hospitals])[[
            "id", "name", "district", "investment_cost_million_tl", "bed_capacity", "annual_emergency_capacity", "source"
        ]]
        df_cand_h.columns = [
            "Kod", "Aday Kampüs Adı", "İlçe", "Maliyet (M TL)", "Hedef Yatak", "Hedef Acil Kapasite Kotası", "Simülasyon Dayanağı"
        ]
        st.dataframe(df_cand_h, use_container_width=True)

    with sub_t3:
        st.markdown("#### 🚑 Faz 002 İçin Ayrılmış Aday Acil Müdahale Üsleri (4 Adet)")
        st.info("ℹ️ Bu tesisler genel yataklı hastane değildir; Faz 002'de ambulans konuşlanma ve ilk müdahale üssü olarak kullanılmak üzere genel hastane nakil optimizasyonundan ayrılmıştır.")
        df_posts = pd.DataFrame([p.to_dict() for p in candidate_emergency_posts])[[
            "id", "name", "district", "investment_cost_million_tl", "operational_status", "source"
        ]]
        df_posts.columns = [
            "Kod", "Acil Üssü Adı", "İlçe", "Maliyet (M TL)", "Statü", "Planlama Dayanağı"
        ]
        st.dataframe(df_posts, use_container_width=True)

    with sub_t4:
        st.markdown("#### 👥 TÜİK ADNKS 2023 Nüfus ve Acil Talep Dağılımı")
        st.markdown("""
        - **TÜİK ADNKS 2023 Ankara İl Geneli Toplam Nüfus:** 5,803,482 kişi
        - **Modellenen 32 Kentsel / Metropol / Yakın Çeper Talep Bölgesi:** 5,570,000 kişi (%95.98 temsil oranı)
        - **Kapsam Dışı Uzak Kırsal Nüfus (Güdül, Ayaş, Beypazarı/Nallıhan çeperi vb.):** ~233,482 kişi (Faz 002/003 genişlemesine ayrılmıştır)
        - **Yıllık Acil Servis Başvuru Katsayısı:** 0.35 başvuru/kişi/yıl
        - **Modellenen Yıllık Acil Servis Başvuru Talebi:** 1,949,500 başvuru/yıl
        """)
        df_dem = pd.DataFrame([d.to_dict() for d in demand_zones])[[
            "id", "name", "district", "population", "annual_emergency_demand", "source"
        ]]
        df_dem.columns = ["Kod", "Bölge / Semt", "İlçe", "Nüfus", "Yıllık Acil Başvuru Talebi", "Kaynak"]
        st.dataframe(df_dem, use_container_width=True)

# ===================== SEKME 4: KAPASİTE VE AÇIKTA KALAN TALEP =====================
with tab_capacity:
    st.markdown("### 🚨 Kapasite Kısıtları ve Açıkta Kalan Talep Denetimi")
    st.caption("CFLP modelinde hiçbir talep bölgesi sessizce yok sayılmaz; karşılanamayan talep elastik gevşetme değişkeniyle (u_i) tam şeffaflıkla raporlanır:")

    if results_active.get("has_unmet_demand"):
        st.error(f"❌ Aktif senaryoda toplam {results_active['unmet_demand_total']:,} acil başvuru talebi (%{results_active['unmet_percentage']:.2f}) karşılanamamıştır!")
        st.markdown("#### Açıkta Kalan Talep Bölgeleri Dökümü:")
        df_unmet = pd.DataFrame(results_active["unmet_zones"])[[
            "zone_name", "district", "unmet_population", "unmet_annual_demand", "unmet_fraction"
        ]]
        df_unmet.columns = ["Bölge / Semt", "İlçe", "Açıkta Kalan Nüfus", "Açıkta Kalan Yıllık Acil Talep", "Karşılanamayan Oran"]
        st.dataframe(df_unmet, use_container_width=True)
    else:
        st.success(f"✅ **Tam Kapsama Sağlandı:** Aktif senaryoda modellenen 5.570.000 nüfusun tüm acil servis talebi açık tesislerin kapasite sınırları dahilinde karşılanmıştır (Açıkta kalan talep: %0.0).")

# ===================== SEKME 5: MATEMATİKSEL TEORİ =====================
with tab_theory:
    st.markdown("### 📝 İki Aşamalı Lexicographic Elastik CFLP Formülasyonu")
    st.markdown(r"""
    Model, insan hayatının ve sağlık hizmetine erişimin maliyet ve süreden üstün olduğu ilkesine dayanarak iki aşamalı öncelik hiyerarşisi uygular:

    #### Aşama 1: Karşılanamayan Talebin Doğrudan Minimizasyonu
    $$\min U = \sum_{i \in I} d_i \cdot u_i$$
    
    Aşama 1'in çözücü statüsü kontrol edilir. **Optimal statü doğrulanmadan Aşama 2 asla başlatılmaz**.
    Elde edilen küresel minimum açıkta kalan talep seviyesi $U^*$ olarak kaydedilir.

    #### Aşama 2: Nakil Süresi ve Yatırım Maliyetinin Minimizasyonu
    $$\sum_{i \in I} d_i \cdot u_i \le U^* + 10^{-3}$$
    $$\min Z_2 = w_1 \cdot \left(\frac{\sum_{(i,j) \in E_{\text{reach}}} d_i \cdot T_{ij}(t) \cdot x_{ij}}{\text{NormTime}}\right) + w_2 \cdot \left(\frac{\sum_{j \in J_{\text{cand}}} F_j \cdot y_j}{\text{NormCost}}\right)$$

    #### Temel Kısıtlar:
    1. **Elastik Talep Korunumu:** $\sum_{j : (i,j) \in E_{\text{reach}}} x_{ij} + u_i = 1 \quad \forall i \in I$
    2. **Açık Tesis Mantıksal Bağı:** $x_{ij} \le y_j \quad \forall (i,j) \in E_{\text{reach}}, \; j \in J_{\text{cand}}$
    3. **Kapasite Sınırı:** $\sum_{i : (i,j) \in E_{\text{reach}}} d_i \cdot x_{ij} \le C_j \cdot y_j \quad \forall j \in J$
    4. **Aday Seçim Kuralı:**
       - **EXACT_COUNT:** $\sum_{j \in J_{\text{cand}}} y_j = p$
       - **MAX_COUNT:** $\sum_{j \in J_{\text{cand}}} y_j \le p$
       - **BUDGET_LIMIT:** $\sum_{j \in J_{\text{cand}}} F_j \cdot y_j \le B$
       - **COMBINED:** $\sum y_j \le p \land \sum F_j \cdot y_j \le B$
    5. **Ulaşılamayan Bağlantılar:** $T_{ij} = \infty$ veya geçersiz süreler için $x_{ij}$ değişkeni oluşturulmaz.
    """)
