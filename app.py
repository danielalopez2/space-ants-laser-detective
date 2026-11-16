from datetime import datetime, timezone
import json
import os
import folium
import pandas as pd
from pipeline_datos import (
    construir_base_datos,
    consultar_poblacion_ciudad_viva,
    distancia_haversine_km,
)
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="LASER | Space Ants - NASA Space Apps",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');

    [data-testid="stSidebar"], [data-testid="collapsedControl"], header[data-testid="stHeader"] {
        display: none !important;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background-color: #08090c;
        color: #e4e4e7;
    }
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1400px;
    }

    @keyframes fadeSlideUp {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes radarPulse {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { box-shadow: 0 0 0 9px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    @keyframes borderGlow {
        0%, 100% { border-color: rgba(239, 68, 68, 0.45); }
        50% { border-color: rgba(239, 68, 68, 0.95); }
    }
    @keyframes liveDot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.3; transform: scale(0.8); }
    }
    @keyframes scanSweep {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(350%); }
    }

    [data-testid="stPlotlyChart"] {
        position: relative;
        overflow: hidden;
        border-radius: 8px;
    }
    [data-testid="stPlotlyChart"]::after {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 28%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 102, 0.055), transparent);
        pointer-events: none;
        animation: scanSweep 4.2s infinite linear;
    }

    .live-dot {
        display: inline-block;
        width: 7px;
        height: 7px;
        background-color: #00ff66;
        box-shadow: 0 0 8px #00ff66;
        border-radius: 50%;
        margin-right: 8px;
        animation: liveDot 1.4s infinite ease-in-out;
    }
    .live-dot-red {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #ef4444;
        border-radius: 50%;
        margin-right: 7px;
        animation: radarPulse 1.5s infinite;
    }

    .cinema-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-top: 0.6rem;
        margin-bottom: 1.1rem;
        padding-bottom: 0.85rem;
        border-bottom: 1px solid #1f2229;
        gap: 1rem;
    }
    .kicker-mono {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        letter-spacing: 0.13em;
        color: #9ca3af;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .main-headline {
        font-size: 1.65rem;
        font-weight: 800;
        color: #fafafa;
        letter-spacing: -0.025em;
        margin: 0;
        line-height: 1.2;
    }
    .sub-hint {
        font-size: 0.8rem;
        color: #9ca3af;
        text-align: right;
        line-height: 1.5;
    }
    .sync-badge {
        display: inline-flex;
        align-items: center;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.69rem;
        color: #00ff66;
        background: rgba(0, 255, 102, 0.07);
        border: 1px solid rgba(0, 255, 102, 0.25);
        padding: 2px 8px;
        border-radius: 999px;
        margin-bottom: 4px;
    }

    div.stButton > button {
        width: 100%;
        background: linear-gradient(180deg, #14171f 0%, #0f1117 100%);
        color: #a1a1aa;
        border: 1px solid #262932;
        border-radius: 8px;
        padding: 0.52rem 0.85rem;
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
        min-height: 40px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    }
    div.stButton > button:hover {
        background: linear-gradient(180deg, #1c202b 0%, #141720 100%);
        border-color: #52525b;
        color: #f4f4f5;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.45);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(180deg, #18231e 0%, #101714 100%);
        border: 1px solid #00ff66;
        color: #00ff66;
        box-shadow: 0 0 14px rgba(0, 255, 102, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(180deg, #1d2b25 0%, #131c18 100%);
        color: #ffffff;
    }

    .kpi-card, .kpi-card-alert {
        background-color: #12141b;
        border: 1px solid #252832;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        height: 124px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: transform 0.2s ease, border-color 0.2s ease;
        animation: fadeSlideUp 0.4s ease-out;
    }
    .kpi-card:hover {
        border-color: #3f3f46;
        transform: translateY(-2px);
    }
    .kpi-card-alert {
        background: linear-gradient(135deg, #1f1115 0%, #141013 100%);
        border: 1px solid #ef4444;
        animation: borderGlow 2s infinite ease-in-out;
    }
    .kpi-label {
        font-size: 0.74rem;
        font-weight: 500;
        color: #9ca3af;
        letter-spacing: 0.01em;
    }
    .kpi-val-terminal {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.04rem;
        font-weight: 700;
        color: #00ff66;
        text-shadow: 0 0 8px rgba(0, 255, 102, 0.2);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-val-amber {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.04rem;
        font-weight: 700;
        color: #fbbf24;
        white-space: nowrap;
    }
    .kpi-val-silver {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.04rem;
        font-weight: 700;
        color: #f4f4f5;
        white-space: nowrap;
    }
    .kpi-val-red {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.02rem;
        font-weight: 700;
        color: #f87171;
        white-space: nowrap;
    }
    .kpi-foot {
        font-size: 0.72rem;
        color: #71717a;
        line-height: 1.35;
    }

    .explain-banner {
        background-color: #111318;
        border: 1px solid #252832;
        border-left: 3px solid #00ff66;
        border-radius: 8px;
        padding: 0.85rem 1.05rem;
        margin-top: 0.9rem;
        font-size: 0.82rem;
        color: #d4d4d8;
        line-height: 1.5;
    }

    .live-alert-box {
        background: linear-gradient(135deg, #241014 0%, #140d10 100%);
        border: 1px solid #ef4444;
        border-left: 5px solid #ef4444;
        border-radius: 10px;
        padding: 1.1rem 1.2rem;
        margin-top: 0.8rem;
        animation: fadeSlideUp 0.3s ease-out;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.85rem;
            padding-right: 0.85rem;
            padding-top: 0.8rem;
        }
        .cinema-header {
            flex-direction: column;
            align-items: flex-start;
        }
        .sub-hint {
            text-align: left;
            margin-top: 0.35rem;
        }
        .main-headline {
            font-size: 1.32rem;
        }
        .kpi-card, .kpi-card-alert {
            height: auto;
            min-height: 105px;
            margin-bottom: 0.5rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=1800)
def cargar_datos():
    if not os.path.exists("laser_data.json"):
        return construir_base_datos()
    with open("laser_data.json", "r", encoding="utf-8") as f:
        return json.load(f)


def geocodificar_municipio_vivo(nombre_lugar):
    """Geocodifica coordenadas reales de cualquier municipio vía Nominatim (OpenStreetMap)."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": nombre_lugar, "format": "json", "limit": 1},
            headers={"User-Agent": "SpaceAnts-LASER-NASA-SpaceApps/1.0"},
            timeout=8,
        )
        if resp.status_code == 200 and resp.json():
            item = resp.json()[0]
            return {
                "nombre_completo": item.get("display_name", nombre_lugar),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
            }
    except Exception:
        pass
    return None


def formatear_ubicacion_sismo(lugar_en, idioma):
    """Traduce rumbos cardinales y conectores de USGS al español cuando el idioma es ES."""
    if idioma == "EN":
        return lugar_en
    rumbos = {
        "NNE": "NNE",
        "ENE": "ENE",
        "ESE": "ESE",
        "SSE": "SSE",
        "SSW": "SSO",
        "WSW": "OSO",
        "WNW": "ONO",
        "NNW": "NNO",
        "NE": "NE",
        "SE": "SE",
        "SW": "SO",
        "NW": "NO",
        "N": "N",
        "S": "S",
        "E": "E",
        "W": "O",
    }
    if " of " in lugar_en:
        izq, der = lugar_en.split(" of ", 1)
        tokens = izq.strip().split()
        if tokens and tokens[-1] in rumbos:
            tokens[-1] = rumbos[tokens[-1]]
        return f"{' '.join(tokens)} al {der.strip()}".replace(
            " al ", " al de ", 1
        )
    return lugar_en


data = cargar_datos()
nodos = data["nodos"]

if "nodo_seleccionado" not in st.session_state:
    st.session_state.nodo_seleccionado = "mesa_santos"
if "idioma" not in st.session_state:
    st.session_state.idioma = "ES"
if "vista_activa" not in st.session_state:
    st.session_state.vista_activa = "01"
if "var_nasa" not in st.session_state:
    st.session_state.var_nasa = "TS"
if "alerta_emitida" not in st.session_state:
    st.session_state.alerta_emitida = None

nodo_actual = nodos[st.session_state.nodo_seleccionado]
info = nodo_actual["info"]
est = nodo_actual["estadisticas"]
df_serie = pd.DataFrame(nodo_actual["serie"])

# Población exacta de la región/nodo seleccionado
pob_nodo_exacta = info["poblacion"]
estado_nodo_txt = (
    "EN ALERTA"
    if est["en_alerta_activa"]
    else ("VIGILANCIA" if st.session_state.idioma == "ES" else "MONITORED")
)
if st.session_state.idioma == "EN" and est["en_alerta_activa"]:
    estado_nodo_txt = "ACTIVE ALERT"

TXT = {
    "ES": {
        "kicker": "SPACE ANTS • SISTEMA LASER • TELEMETRÍA NASA & USGS EN VIVO",
        "title": "Monitor Sísmico y de Tendencias Terrestres",
        "auto_sync": "AUTO-SYNC (30m) • {ts} UTC",
        "pop_hdr": "Población Exacta en Zona ({zona} • {fuente}): <strong style='color:#e4e4e7;'>{pob:,} hab.</strong> &nbsp;|&nbsp; Estado: <strong style='color:{col_est};'>{est_txt}</strong>",
        "nav_1": "01 // Centro de Comando",
        "nav_2": "02 // Ventana de Oro (72h)",
        "nav_3": "03 // Sismos & Alerta Ciudadana",
        "sync": "↻ Sincronizar",
        "kpi1_lbl": "Tendencia Térmica (MERRA-2)",
        "kpi1_foot": "Mann-Kendall • Dato satelital: {f_nasa}",
        "kpi2_lbl": "Índice p (Z-Score Direccional)",
        "kpi2_norm": "Normal (-1.80 a +1.80) • Sin anomalía",
        "kpi2_dist": "Anomalía térmica/hídrica fuera de rango",
        "kpi3_lbl": "Humedad del Suelo (GLDAS)",
        "kpi3_foot": "Lluvia 72h: {lluvia} mm • Crítico > 72%",
        "kpi4_lbl": "Peligro Encadenado (Sismo + Lluvia)",
        "kpi4_foot": "Sismo a {dist} km • {pob:,} hab. ({fuente})",
        "graph_title": "Índice p (Anomalía del Terreno) — {zona}",
        "graph_leg": "--- Umbral (±1.8) &nbsp; • Curva Índice p",
        "map_title": "Radar Satelital (NASA GIBS + Sismos USGS)",
        "plain_explain": (
            "<strong style='color:#00ff66;'>Desglose Demográfico Exacto (Radio 50 km alrededor de {zona}):</strong> "
            "{munis} = <strong>{pob:,} habitantes verificados ({fuente})</strong>."
        ),
        "trends": {
            "increasing": "CRECIENTE",
            "decreasing": "DECRECIENTE",
            "no trend": "ESTABLE",
        },
        "hum_states": ("Saturado", "Húmedo", "Normal"),
        "risk_levels": {"ALTA": "ALTO", "MODERADA": "MODERADO", "BAJA": "BAJO"},
        "alert_active": "ALERTA DERRUMBE",
        "risk_prefix": "RIESGO",
        "in_range": "EN RANGO",
        "anomaly": "ANOMALÍA",
        "v2_title": "Ventana de Oro (72h) & Telemetría Satelital NASA — {zona}",
        "v2_cap": "{placa} | Población exacta en radio de 50 km ({fuente}): {pob:,} hab.",
        "v2_k1": ("Lluvia Acumulada 72h (GPM IMERG)", "Precipitación satelital últimas 72h"),
        "v2_k2": ("Saturación Máxima Suelo (GLDAS)", "Umbral crítico deslizamiento: 0.72"),
        "v2_k3": ("Cambio Térmico 72h (MERRA-2)", "Diferencial temperatura superficial"),
        "v2_k4": ("Tasa de Cambio Mann-Kendall", "Significancia estadística"),
        "vars": [
            ("TS", "Temperatura Superficial (°C) • MERRA-2"),
            ("GWETTOP", "Humedad del Suelo (0-1) • GLDAS"),
            ("PRECTOTCORR", "Precipitación Diaria (mm) • GPM IMERG"),
        ],
        "v3_quakes": "Registro Sísmico Regional (USGS FDSN • M ≥ 3.5)",
        "v3_th": ("UBICACIÓN", "MAGNITUD", "FECHA (UTC)", "DISTANCIA NODO"),
        "v3_cap": "Sistema de Alerta Ciudadana en Vivo (Web Push + Censo Exacto)",
        "v3_desc": "Geocodifica en tiempo real el municipio, consulta su población exacta oficial y dispara una alerta inmediata con datos satelitales.",
        "v3_input": "Municipio o ciudad a alertar:",
        "v3_btn": "🚨 EMITIR ALERTA CIUDADANA EN VIVO",
        "v3_dl": "⬇ Exportar Boletín Oficial CAP v1.2 (Autoridades)",
    },
    "EN": {
        "kicker": "SPACE ANTS • LASER SYSTEM • LIVE NASA & USGS TELEMETRY",
        "title": "Seismic & Earth System Trend Monitor",
        "auto_sync": "AUTO-SYNC (30m) • {ts} UTC",
        "pop_hdr": "Exact Zone Population ({zona} • {fuente}): <strong style='color:#e4e4e7;'>{pob:,} people</strong> &nbsp;|&nbsp; Status: <strong style='color:{col_est};'>{est_txt}</strong>",
        "nav_1": "01 // Command Center",
        "nav_2": "02 // Golden Window (72h)",
        "nav_3": "03 // Quakes & Citizen Alert",
        "sync": "↻ Sync Data",
        "kpi1_lbl": "Thermal Trend (MERRA-2)",
        "kpi1_foot": "Mann-Kendall • Satellite date: {f_nasa}",
        "kpi2_lbl": "Index p (Directional Z-Score)",
        "kpi2_norm": "Normal (-1.80 to +1.80) • Baseline stable",
        "kpi2_dist": "Thermal/moisture anomaly beyond baseline",
        "kpi3_lbl": "Soil Moisture (GLDAS)",
        "kpi3_foot": "72h Rain: {lluvia} mm • Critical > 72%",
        "kpi4_lbl": "Cascading Hazard (Quake + Rain)",
        "kpi4_foot": "Quake at {dist} km • {pob:,} people ({fuente})",
        "graph_title": "Index p Timeline (Terrain Anomaly) — {zona}",
        "graph_leg": "--- Threshold (±1.8) &nbsp; • Index p Curve",
        "map_title": "Satellite Radar (NASA GIBS + USGS Quakes)",
        "plain_explain": (
            "<strong style='color:#00ff66;'>Exact Demographic Breakdown (50 km radius around {zona}):</strong> "
            "{munis} = <strong>{pob:,} verified inhabitants ({fuente})</strong>."
        ),
        "trends": {
            "increasing": "INCREASING",
            "decreasing": "DECREASING",
            "no trend": "STABLE",
        },
        "hum_states": ("Saturated", "Wet", "Normal"),
        "risk_levels": {"ALTA": "HIGH", "MODERADA": "MODERATE", "BAJA": "LOW"},
        "alert_active": "LANDSLIDE ALERT",
        "risk_prefix": "RISK:",
        "in_range": "IN RANGE",
        "anomaly": "ANOMALY",
        "v2_title": "Golden Window (72h) & NASA Satellite Telemetry — {zona}",
        "v2_cap": "{placa} | Exact population within 50 km radius ({fuente}): {pob:,}",
        "v2_k1": ("72h Rainfall (GPM IMERG)", "Accumulated satellite precipitation"),
        "v2_k2": ("Max Soil Saturation (GLDAS)", "Critical landslide threshold: 0.72"),
        "v2_k3": ("72h Thermal Shift (MERRA-2)", "Surface temperature delta"),
        "v2_k4": ("Mann-Kendall Slope", "Statistical significance"),
        "vars": [
            ("TS", "Surface Temperature (°C) • MERRA-2"),
            ("GWETTOP", "Top Soil Moisture (0-1) • GLDAS"),
            ("PRECTOTCORR", "Daily Precipitation (mm) • GPM IMERG"),
        ],
        "v3_quakes": "Regional Seismic Log (USGS FDSN • M ≥ 3.5)",
        "v3_th": ("LOCATION", "MAGNITUDE", "DATE (UTC)", "DIST. TO NODE"),
        "v3_cap": "Live Citizen Early Warning Dispatch (Web Push + Exact Census)",
        "v3_desc": "Geocodes the target municipality in real time, retrieves its exact official population, and broadcasts a live citizen alert.",
        "v3_input": "Municipality or city to alert:",
        "v3_btn": "🚨 BROADCAST LIVE CITIZEN ALERT",
        "v3_dl": "⬇ Export Official CAP v1.2 Bulletin (Agencies)",
    },
}

t = TXT[st.session_state.idioma]

# --- BARRA DE NAVEGACIÓN ---
nav1, nav2, nav3, nav_sp, nav_lang, nav_sync = st.columns(
    [1.15, 1.15, 1.15, 0.35, 0.65, 0.75]
)

with nav1:
    if st.button(
        t["nav_1"],
        type="primary" if st.session_state.vista_activa == "01" else "secondary",
        width="stretch",
    ):
        st.session_state.vista_activa = "01"
        st.rerun()
with nav2:
    if st.button(
        t["nav_2"],
        type="primary" if st.session_state.vista_activa == "02" else "secondary",
        width="stretch",
    ):
        st.session_state.vista_activa = "02"
        st.rerun()
with nav3:
    if st.button(
        t["nav_3"],
        type="primary" if st.session_state.vista_activa == "03" else "secondary",
        width="stretch",
    ):
        st.session_state.vista_activa = "03"
        st.rerun()
with nav_lang:
    if st.button("🌐 ES / EN", width="stretch"):
        st.session_state.idioma = "EN" if st.session_state.idioma == "ES" else "ES"
        st.rerun()
with nav_sync:
    if st.button(t["sync"], width="stretch"):
        overlay = st.empty()
        msg_scan = (
            "SINCRONIZANDO TELEMETRÍA SATELITAL (NASA POWER + USGS)..."
            if st.session_state.idioma == "ES"
            else "SYNCING SATELLITE TELEMETRY (NASA POWER + USGS)..."
        )
        overlay.markdown(
            f"""
            <style>
            @keyframes orbitSpin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
            @keyframes waveExpand {{ 0% {{ transform: scale(0.6); opacity: 0.9; }} 100% {{ transform: scale(2.1); opacity: 0; }} }}
            .sat-overlay {{
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                background: rgba(8, 9, 12, 0.88); backdrop-filter: blur(6px);
                z-index: 999999; display: flex; flex-direction: column;
                justify-content: center; align-items: center;
            }}
            .radar-box {{
                position: relative; width: 105px; height: 105px;
                display: flex; justify-content: center; align-items: center; margin-bottom: 1.2rem;
            }}
            .radar-ring {{
                position: absolute; width: 100%; height: 100%;
                border: 2px solid #00ff66; border-radius: 50%;
                animation: waveExpand 1.8s infinite ease-out;
            }}
            .orbit-track {{
                position: absolute; width: 80px; height: 80px;
                border: 1px dashed #71717a; border-radius: 50%;
                animation: orbitSpin 3s linear infinite;
            }}
            .sat-dot {{
                position: absolute; top: -5px; left: 50%;
                width: 10px; height: 10px; background: #00ff66;
                box-shadow: 0 0 12px #00ff66; border-radius: 50%;
            }}
            .sat-text {{
                font-family: 'JetBrains Mono', monospace; color: #00ff66;
                font-size: 0.9rem; letter-spacing: 0.08em; text-align: center; padding: 0 1rem;
            }}
            </style>
            <div class="sat-overlay">
                <div class="radar-box">
                    <div class="radar-ring"></div>
                    <div class="orbit-track"><div class="sat-dot"></div></div>
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#f4f4f5" stroke-width="1.8">
                        <path d="M13 7L9 3 5 7l4 4m6 6l4 4 4-4-4-4M8 16l8-8M3 21l3-3m12-12l3-3"/>
                        <circle cx="12" cy="12" r="2" fill="#00ff66"/>
                    </svg>
                </div>
                <div class="sat-text">{msg_scan}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        construir_base_datos()
        st.cache_data.clear()
        overlay.empty()
        st.rerun()

zona_hdr = info["nombre"].split("(")[0].strip()
color_est_hdr = "#f87171" if est["en_alerta_activa"] else "#00ff66"

st.markdown(
    f"""
    <div class="cinema-header">
        <div>
            <div class="kicker-mono"><span class="live-dot"></span>{t['kicker']}</div>
            <h1 class="main-headline">{t['title']}</h1>
        </div>
        <div class="sub-hint">
            <div class="sync-badge"><span class="live-dot"></span>{t['auto_sync'].format(ts=data['ultima_actualizacion'])}</div><br>
            {t['pop_hdr'].format(zona=zona_hdr, fuente=info.get('fuente_demografica', 'DANE/INE'), pob=pob_nodo_exacta, col_est=color_est_hdr, est_txt=estado_nodo_txt)}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 4 Botones de Regiones
nodos_principales = [
    ("mesa_santos", "Mesa de los Santos", "Santander, COL"),
    ("bocono", "Falla de Boconó", "Mérida/Táchira, VEN"),
    ("pereira", "Pereira y Eje", "Risaralda, COL"),
    ("la_guaira", "La Guaira y Costa", "Vargas, VEN"),
]

cols_nodos = st.columns(4)
for idx, (key, titulo, subtitulo) in enumerate(nodos_principales):
    if key in nodos:
        es_activo = st.session_state.nodo_seleccionado == key
        indicador = " ●" if es_activo else ""
        with cols_nodos[idx]:
            if st.button(
                f"{titulo}{indicador}\n{subtitulo}",
                key=f"btn_{key}",
                type="primary" if es_activo else "secondary",
                width="stretch",
            ):
                st.session_state.nodo_seleccionado = key
                st.rerun()


def crear_grafica_viva(
    fechas, valores, colores_pts=None, tamanos_pts=None, con_umbrales=False
):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=fechas,
            y=valores,
            mode="lines+markers" if colores_pts else "lines",
            fill=None if colores_pts else "tozeroy",
            fillcolor=None if colores_pts else "rgba(0, 255, 102, 0.07)",
            line=dict(
                color="#a1a1aa" if colores_pts else "#e4e4e7", width=2.2
            ),
            marker=(
                dict(
                    size=tamanos_pts,
                    color=colores_pts,
                    line=dict(width=1, color="#090d16"),
                )
                if colores_pts
                else None
            ),
            hovertemplate="<b>Fecha:</b> %{x}<br><b>Valor:</b> %{y:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[fechas.iloc[-1]],
            y=[valores.iloc[-1]],
            mode="markers",
            marker=dict(
                size=16,
                color="rgba(0, 255, 102, 0.25)",
                line=dict(width=1.5, color="#00ff66"),
            ),
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[fechas.iloc[-1]],
            y=[valores.iloc[-1]],
            mode="markers",
            marker=dict(size=7, color="#00ff66"),
            hoverinfo="skip",
        )
    )

    if con_umbrales:
        fig.add_hline(
            y=1.8, line_dash="dash", line_color="#7f1d1d", line_width=1.2
        )
        fig.add_hline(
            y=-1.8, line_dash="dash", line_color="#7f1d1d", line_width=1.2
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111318",
        plot_bgcolor="#111318",
        height=335,
        margin=dict(l=12, r=12, t=14, b=18),
        xaxis=dict(showgrid=False, color="#71717a"),
        yaxis=dict(gridcolor="#1f2229", zerolinecolor="#27272a", color="#71717a"),
        showlegend=False,
    )
    return fig


# ==============================================================================
# PANTALLA 01: CENTRO DE COMANDO PRINCIPAL
# ==============================================================================
if st.session_state.vista_activa == "01":
    tend_txt = t["trends"].get(est["tendencia_ts"], est["tendencia_ts"].upper())
    pi_val = est["pi_actual"]
    en_distorsion = abs(pi_val) > 1.8
    humedad_pct = int(round(float(df_serie["GWETTOP"].iloc[-1]) * 100))
    riesgo_raw = est["alerta_derrumbe"]
    riesgo_txt = t["risk_levels"].get(riesgo_raw, riesgo_raw)
    es_critico = riesgo_raw == "ALTA" or en_distorsion
    fecha_nasa = est.get("fecha_ultimo_dato_nasa", df_serie["fecha"].iloc[-1])
    dist_sismo = est.get("sismo_mas_cercano_km", -1)
    fuente_demo = info.get("fuente_demografica", "DANE/INE")
    munis_lista = " + ".join(info.get("municipios_radio_50km", []))

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{t['kpi1_lbl']}</div>
                <div class="kpi-val-terminal">{tend_txt} (p={est['p_value_ts']})</div>
                <div class="kpi-foot">{t['kpi1_foot'].format(f_nasa=fecha_nasa)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        clase_pi = "kpi-val-amber" if en_distorsion else "kpi-val-silver"
        estado_pi = (
            f"⚡ {t['anomaly']}" if en_distorsion else f"● {t['in_range']}"
        )
        foot_pi = t["kpi2_dist"] if en_distorsion else t["kpi2_norm"]
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{t['kpi2_lbl']}</div>
                <div class="{clase_pi}">{pi_val:+.2f} {estado_pi}</div>
                <div class="kpi-foot">{foot_pi}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        estado_hum = (
            t["hum_states"][0]
            if humedad_pct >= 72
            else (
                t["hum_states"][1] if humedad_pct >= 60 else t["hum_states"][2]
            )
        )
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{t['kpi3_lbl']}</div>
                <div class="kpi-val-silver">{humedad_pct}% ({estado_hum})</div>
                <div class="kpi-foot">{t['kpi3_foot'].format(lluvia=est.get('lluvia_72h_mm', 0))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        card_class = "kpi-card-alert" if es_critico else "kpi-card"
        val_class = "kpi-val-red" if es_critico else "kpi-val-silver"
        dot_html = "<span class='live-dot-red'></span>" if es_critico else ""
        texto_alerta = (
            f"{t['alert_active']} ({riesgo_txt})"
            if es_critico
            else f"{t['risk_prefix']} {riesgo_txt}"
        )
        st.markdown(
            f"""
            <div class="{card_class}">
                <div class="kpi-label">{t['kpi4_lbl']}</div>
                <div class="{val_class}">{dot_html}{texto_alerta}</div>
                <div class="kpi-foot">{t['kpi4_foot'].format(dist=dist_sismo, pob=info['poblacion'], fuente=fuente_demo)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col_g, col_m = st.columns([1.32, 1])

    with col_g:
        st.markdown(
            f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; flex-wrap:wrap; gap:4px;'>"
            f"<strong style='color:#f4f4f5; font-size:0.9rem;'>{t['graph_title'].format(zona=zona_hdr)}</strong>"
            f"<span style='font-family:JetBrains Mono, monospace; font-size:0.7rem; color:#71717a;'>{t['graph_leg']}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        df_plot = df_serie.tail(45).reset_index(drop=True)
        colores_puntos = [
            "#ef4444" if abs(v) > 1.8 else "#d4d4d8"
            for v in df_plot["indice_pi"]
        ]
        tamanos_puntos = [
            8 if abs(v) > 1.8 else 4.5 for v in df_plot["indice_pi"]
        ]

        fig_pi = crear_grafica_viva(
            df_plot["fecha"],
            df_plot["indice_pi"],
            colores_pts=colores_puntos,
            tamanos_pts=tamanos_puntos,
            con_umbrales=True,
        )
        st.plotly_chart(
            fig_pi, width="stretch", config={"displayModeBar": False}
        )

    with col_m:
        st.markdown(
            f"<div style='margin-bottom:6px;'><strong style='color:#f4f4f5; font-size:0.9rem;'>{t['map_title']}</strong></div>",
            unsafe_allow_html=True,
        )
        mapa = folium.Map(
            location=[info["lat"], info["lon"]],
            zoom_start=6,
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Dark Gray Canvas",
        )
        folium.TileLayer(
            tiles="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/2026-11-12/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
            attr="NASA GIBS",
            name="Satélite NASA MODIS",
            overlay=True,
            opacity=0.32,
        ).add_to(mapa)

        for k, v in nodos.items():
            n_info = v["info"]
            n_est = v["estadisticas"]
            es_sel = k == st.session_state.nodo_seleccionado
            color_pin = (
                "red"
                if (n_est["en_alerta_activa"] or es_sel)
                else "lightgray"
            )
            folium.Marker(
                [n_info["lat"], n_info["lon"]],
                popup=f"<b>{n_info['nombre']}</b><br>Índice p: {n_est['pi_actual']}<br>Población Exacta (50km): {n_info['poblacion']:,}",
                tooltip=n_info["nombre"],
                icon=folium.Icon(color=color_pin),
            ).add_to(mapa)

        for s in data["sismos_recientes"][:18]:
            lugar_pop = formatear_ubicacion_sismo(
                s["lugar"], st.session_state.idioma
            )
            folium.CircleMarker(
                location=[s["lat"], s["lon"]],
                radius=s["magnitud"] * 2.1,
                color="#ef4444" if s["magnitud"] >= 4.2 else "#a1a1aa",
                fill=True,
                fill_opacity=0.6,
                popup=f"M{s['magnitud']} - {lugar_pop} ({s['fecha']})",
            ).add_to(mapa)

        components.html(mapa._repr_html_(), height=335)

    st.markdown(
        f"<div class='explain-banner'>{t['plain_explain'].format(zona=zona_hdr, munis=munis_lista, pob=info['poblacion'], fuente=fuente_demo)}</div>",
        unsafe_allow_html=True,
    )

# ==============================================================================
# PANTALLA 02: VENTANA DE ORO (72H) & VARIABLES NASA
# ==============================================================================
elif st.session_state.vista_activa == "02":
    st.markdown(f"#### {t['v2_title'].format(zona=info['nombre'])}")
    st.caption(
        t["v2_cap"].format(
            placa=info["placa"],
            pob=info["poblacion"],
            fuente=info.get("fuente_demografica", "DANE/INE"),
        )
    )

    v1, v2, v3, v4 = st.columns(4)
    with v1:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>{t['v2_k1'][0]}</div><div class='kpi-val-silver'>{est.get('lluvia_72h_mm', 0)} mm</div><div class='kpi-foot'>{t['v2_k1'][1]}</div></div>",
            unsafe_allow_html=True,
        )
    with v2:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>{t['v2_k2'][0]}</div><div class='kpi-val-silver'>{est.get('humedad_max_72h', 0)} / 1.00</div><div class='kpi-foot'>{t['v2_k2'][1]}</div></div>",
            unsafe_allow_html=True,
        )
    with v3:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>{t['v2_k3'][0]}</div><div class='kpi-val-amber'>{est.get('delta_temp_72h', 0):+} °C</div><div class='kpi-foot'>{t['v2_k3'][1]}</div></div>",
            unsafe_allow_html=True,
        )
    with v4:
        st.markdown(
            f"<div class='kpi-card'><div class='kpi-label'>{t['v2_k4'][0]}</div><div class='kpi-val-terminal'>{est['tasa_cambio_ts']} °C/d</div><div class='kpi-foot'>p-value = {est['p_value_ts']}</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    cols_var = st.columns(3)
    for i, (v_code, v_label) in enumerate(t["vars"]):
        with cols_var[i]:
            if st.button(
                v_label,
                key=f"var_{v_code}",
                type=(
                    "primary"
                    if st.session_state.var_nasa == v_code
                    else "secondary"
                ),
                width="stretch",
            ):
                st.session_state.var_nasa = v_code
                st.rerun()

    df_var_plot = df_serie.reset_index(drop=True)
    fig_var = crear_grafica_viva(
        df_var_plot["fecha"],
        df_var_plot[st.session_state.var_nasa],
        con_umbrales=False,
    )
    st.plotly_chart(
        fig_var, width="stretch", config={"displayModeBar": False}
    )

# ==============================================================================
# PANTALLA 03: SISMOS EN VIVO USGS & ALERTA CIUDADANA REAL
# ==============================================================================
else:
    c_izq, c_der = st.columns([1.25, 1])

    with c_izq:
        st.markdown(f"#### {t['v3_quakes']}")
        if data["sismos_recientes"]:
            sismos_con_dist = []
            for s in data["sismos_recientes"]:
                dist_km = distancia_haversine_km(
                    info["lat"], info["lon"], s["lat"], s["lon"]
                )
                sismos_con_dist.append((dist_km, s))
            sismos_con_dist.sort(key=lambda x: x[0])

            filas = ""
            for dist_km, s in sismos_con_dist[:12]:
                lugar_txt = formatear_ubicacion_sismo(
                    s["lugar"], st.session_state.idioma
                )
                color_mag = "#ef4444" if s["magnitud"] >= 4.2 else "#00ff66"
                color_dist = "#fbbf24" if dist_km <= 150 else "#e4e4e7"
                filas += (
                    f"<tr style='border-bottom:1px solid #1f2229;'>"
                    f"<td style='padding:8px;'>{lugar_txt}</td>"
                    f"<td style='padding:8px; color:{color_mag}; font-weight:700; font-family:JetBrains Mono;'>M {s['magnitud']}</td>"
                    f"<td style='padding:8px; font-family:JetBrains Mono; color:#a1a1aa;'>{s['fecha']}</td>"
                    f"<td style='padding:8px; font-family:JetBrains Mono; color:{color_dist}; font-weight:600;'>{dist_km} km</td>"
                    f"</tr>"
                )
            cols_th = t["v3_th"]
            st.markdown(
                f"""
                <div style="overflow-x:auto; background:#0d0f14; border:1px solid #22252e; border-radius:10px; padding:0.5rem;">
                <table style="width:100%; border-collapse:collapse; font-size:0.84rem; color:#e4e4e7;">
                    <thead>
                        <tr style="border-bottom:1px solid #3f3f46; color:#71717a; text-align:left; font-size:0.74rem;">
                            <th style="padding:8px;">{cols_th[0]}</th>
                            <th style="padding:8px;">{cols_th[1]}</th>
                            <th style="padding:8px;">{cols_th[2]}</th>
                            <th style="padding:8px;">{cols_th[3]}</th>
                        </tr>
                    </thead>
                    <tbody>{filas}</tbody>
                </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with c_der:
        st.markdown(f"#### {t['v3_cap']}")
        st.caption(t["v3_desc"])

        municipio_dest = st.text_input(
            t["v3_input"], value="Piedecuesta, Santander"
        )

        if st.button(t["v3_btn"], type="primary", width="stretch"):
            geo = geocodificar_municipio_vivo(municipio_dest)
            if geo:
                demo_ciudad = consultar_poblacion_ciudad_viva(
                    municipio_dest, geo["lat"], geo["lon"]
                )
                dist_nodo = distancia_haversine_km(
                    geo["lat"], geo["lon"], info["lat"], info["lon"]
                )
                sismos_ordenados = sorted(
                    data["sismos_recientes"],
                    key=lambda x: distancia_haversine_km(
                        geo["lat"], geo["lon"], x["lat"], x["lon"]
                    ),
                )
                sismo_cercano = (
                    sismos_ordenados[0] if sismos_ordenados else None
                )
                dist_sismo_vivo = (
                    distancia_haversine_km(
                        geo["lat"],
                        geo["lon"],
                        sismo_cercano["lat"],
                        sismo_cercano["lon"],
                    )
                    if sismo_cercano
                    else dist_nodo
                )
                st.session_state.alerta_emitida = {
                    "municipio": municipio_dest,
                    "ciudad_oficial": demo_ciudad["ciudad_oficial"],
                    "poblacion_exacta": demo_ciudad["poblacion_ciudad"],
                    "fuente_pob": demo_ciudad["fuente"],
                    "lat": round(geo["lat"], 4),
                    "lon": round(geo["lon"], 4),
                    "dist_nodo": dist_nodo,
                    "dist_sismo": dist_sismo_vivo,
                    "hora": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
                    "riesgo": est["alerta_derrumbe"],
                    "lluvia": est.get("lluvia_72h_mm", 0),
                    "humedad": int(
                        round(float(df_serie["GWETTOP"].iloc[-1]) * 100)
                    ),
                }
            else:
                st.error(
                    "No se encontraron coordenadas para ese municipio. Intenta con 'Ciudad, País'."
                    if st.session_state.idioma == "ES"
                    else "Coordinates not found for that municipality. Try 'City, Country'."
                )

        if st.session_state.alerta_emitida:
            al = st.session_state.alerta_emitida
            pob_txt_es = (
                f"<strong>{al['poblacion_exacta']:,} hab.</strong> ({al['fuente_pob']})"
                if al["poblacion_exacta"]
                else f"Área de influencia nodo: <strong>{info['poblacion']:,} hab.</strong>"
            )
            pob_txt_en = (
                f"<strong>{al['poblacion_exacta']:,} people</strong> ({al['fuente_pob']})"
                if al["poblacion_exacta"]
                else f"Node influence area: <strong>{info['poblacion']:,} people</strong>"
            )

            if st.session_state.idioma == "ES":
                titulo_al = f"ALERTA TEMPRANA ACTIVA • {al['hora']}"
                badge_al = f"RIESGO {al['riesgo']}"
                cuerpo_al = (
                    f"• Población exacta de <strong>{al['ciudad_oficial']}</strong>: {pob_txt_es}<br>"
                    f"• Distancia al nodo <strong>{zona_hdr}</strong>: <strong>{al['dist_nodo']} km</strong> | Sismo más cercano: <strong>{al['dist_sismo']} km</strong><br>"
                    f"• Humedad suelo (NASA GLDAS): <strong>{al['humedad']}%</strong> | Lluvia 72h (GPM IMERG): <strong>{al['lluvia']} mm</strong><br>"
                    f"• <strong>Acción recomendada:</strong> Monitorear taludes y vías de ladera durante las próximas 72 horas."
                )
            else:
                titulo_al = f"ACTIVE EARLY WARNING • {al['hora']}"
                badge_al = f"RISK: {al['riesgo']}"
                cuerpo_al = (
                    f"• Exact population of <strong>{al['ciudad_oficial']}</strong>: {pob_txt_en}<br>"
                    f"• Distance to node <strong>{zona_hdr}</strong>: <strong>{al['dist_nodo']} km</strong> | Nearest quake: <strong>{al['dist_sismo']} km</strong><br>"
                    f"• Soil moisture (NASA GLDAS): <strong>{al['humedad']}%</strong> | 72h Rain (GPM IMERG): <strong>{al['lluvia']} mm</strong><br>"
                    f"• <strong>Recommended action:</strong> Monitor slopes and hillside roads over the next 72 hours."
                )

            st.markdown(
                f"""
                <div class="live-alert-box">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
                        <span style="color:#f87171; font-weight:800; font-size:0.9rem; letter-spacing:0.04em;">
                            <span class="live-dot-red"></span>{titulo_al}
                        </span>
                        <span style="background:#ef4444; color:#fff; font-size:0.7rem; font-weight:700; padding:2px 8px; border-radius:4px;">
                            {badge_al}
                        </span>
                    </div>
                    <div style="font-size:0.95rem; font-weight:700; color:#fafafa; margin-bottom:4px;">
                        📍 {al['municipio']} ({al['lat']}, {al['lon']})
                    </div>
                    <div style="font-size:0.8rem; color:#d4d4d8; line-height:1.5;">
                        {cuerpo_al}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            components.html(
                f"""
                <script>
                if ("Notification" in window) {{
                    if (Notification.permission === "granted") {{
                        new Notification("🚨 LASER - {al['municipio']}", {{
                            body: "{badge_al} | NASA GLDAS: {al['humedad']}% | USGS: {al['dist_sismo']} km"
                        }});
                    }} else if (Notification.permission !== "denied") {{
                        Notification.requestPermission().then(function (permission) {{
                            if (permission === "granted") {{
                                new Notification("🚨 LASER - {al['municipio']}", {{
                                    body: "{badge_al} | NASA GLDAS: {al['humedad']}% | USGS: {al['dist_sismo']} km"
                                }});
                            }}
                        }});
                    }}
                }}
                </script>
                """,
                height=0,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        pob_cap = (
            st.session_state.alerta_emitida["poblacion_exacta"]
            if (
                st.session_state.alerta_emitida
                and st.session_state.alerta_emitida["poblacion_exacta"]
            )
            else info["poblacion"]
        )

        cap_payload = {
            "identifier": f"LASER-CAP-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
            "sender": "space-ants-laser@nasa-space-apps.org",
            "sent": datetime.now(timezone.utc).isoformat(),
            "status": "Actual",
            "msgType": "Alert",
            "scope": "Public",
            "info": {
                "category": "Geo",
                "event": "Cascading Seismic & Landslide Hazard Monitoring",
                "urgency": (
                    "Immediate" if est["en_alerta_activa"] else "Expected"
                ),
                "severity": (
                    "Severe" if est["alerta_derrumbe"] == "ALTA" else "Moderate"
                ),
                "certainty": "Observed",
                "area": {
                    "areaDesc": f"{municipio_dest} — Nodo {info['nombre']}",
                    "circle": f"{info['lat']},{info['lon']} 50.0",
                },
                "parameter": [
                    {"valueName": "Index_p_ZScore", "value": est["pi_actual"]},
                    {
                        "valueName": "NASA_GLDAS_SoilMoisture",
                        "value": est.get("humedad_max_72h", 0),
                    },
                    {
                        "valueName": "NASA_GPM_72h_Rain_mm",
                        "value": est.get("lluvia_72h_mm", 0),
                    },
                    {
                        "valueName": "Exact_Population",
                        "value": pob_cap,
                    },
                ],
            },
        }

        st.download_button(
            label=t["v3_dl"],
            data=json.dumps(cap_payload, indent=2),
            file_name=f"CAP_ALERTA_{st.session_state.nodo_seleccionado}.json",
            mime="application/json",
            width="stretch",
        )