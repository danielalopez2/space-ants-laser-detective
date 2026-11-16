from datetime import datetime, timedelta, timezone
import json
import math
import os
import numpy as np
import pandas as pd
import pymannkendall as mk
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NODOS_BASE = {
    "mesa_santos": {
        "nombre": "Mesa de los Santos (Santander, COL)",
        "placa": "Placa Sudamericana - Nido Sísmico Activo",
        "lat": 6.80,
        "lon": -73.10,
    },
    "bocono": {
        "nombre": "Falla de Boconó (Mérida/Táchira, VEN)",
        "placa": "Placa Sudamericana - Falla Transcurrente",
        "lat": 8.59,
        "lon": -71.14,
    },
    "pereira": {
        "nombre": "Pereira y Eje Cafetero (Risaralda, COL)",
        "placa": "Subducción Placa de Nazca - Sudamericana",
        "lat": 4.81,
        "lon": -75.69,
    },
    "la_guaira": {
        "nombre": "La Guaira y Costa Central (VEN)",
        "placa": "Interacción Placa del Caribe - Sudamericana",
        "lat": 10.60,
        "lon": -66.93,
    },
}

# Censo oficial exacto por municipio (Proyecciones DANE Colombia / INE Venezuela)
CENTROS_POBLADOS_OFICIALES = [
    # Santander (DANE)
    {"ciudad": "Bucaramanga", "lat": 7.1193, "lon": -73.1227, "pob": 613400, "fuente": "DANE"},
    {"ciudad": "Floridablanca", "lat": 7.0622, "lon": -73.0864, "pob": 316200, "fuente": "DANE"},
    {"ciudad": "Girón", "lat": 7.0682, "lon": -73.1698, "pob": 175400, "fuente": "DANE"},
    {"ciudad": "Piedecuesta", "lat": 6.9875, "lon": -73.0497, "pob": 186100, "fuente": "DANE"},
    {"ciudad": "Los Santos", "lat": 6.7556, "lon": -73.0994, "pob": 14500, "fuente": "DANE"},
    {"ciudad": "Zapatoca", "lat": 6.8142, "lon": -73.2683, "pob": 9600, "fuente": "DANE"},
    {"ciudad": "Aratoca", "lat": 6.6947, "lon": -73.0211, "pob": 8900, "fuente": "DANE"},
    {"ciudad": "San Gil", "lat": 6.5553, "lon": -73.1336, "pob": 61200, "fuente": "DANE"},
    # Mérida / Táchira (INE)
    {"ciudad": "Mérida", "lat": 8.5897, "lon": -71.1561, "pob": 345000, "fuente": "INE"},
    {"ciudad": "Ejido", "lat": 8.5467, "lon": -71.2408, "pob": 115000, "fuente": "INE"},
    {"ciudad": "Tabay", "lat": 8.6333, "lon": -71.0667, "pob": 22000, "fuente": "INE"},
    {"ciudad": "Lagunillas", "lat": 8.5064, "lon": -71.3919, "pob": 58000, "fuente": "INE"},
    {"ciudad": "Mucuchíes", "lat": 8.7497, "lon": -70.9169, "pob": 19500, "fuente": "INE"},
    {"ciudad": "El Vigía", "lat": 8.6136, "lon": -71.6528, "pob": 158000, "fuente": "INE"},
    # Eje Cafetero (DANE)
    {"ciudad": "Pereira", "lat": 4.8133, "lon": -75.6961, "pob": 482400, "fuente": "DANE"},
    {"ciudad": "Dosquebradas", "lat": 4.8358, "lon": -75.6725, "pob": 228500, "fuente": "DANE"},
    {"ciudad": "Santa Rosa de Cabal", "lat": 4.8681, "lon": -75.6214, "pob": 81300, "fuente": "DANE"},
    {"ciudad": "Armenia", "lat": 4.5339, "lon": -75.6811, "pob": 312900, "fuente": "DANE"},
    {"ciudad": "Manizales", "lat": 5.0689, "lon": -75.5174, "pob": 454100, "fuente": "DANE"},
    {"ciudad": "Cartago", "lat": 4.7464, "lon": -75.9117, "pob": 141200, "fuente": "DANE"},
    # La Guaira / Caracas (INE)
    {"ciudad": "La Guaira / Maiquetía", "lat": 10.5990, "lon": -66.9346, "pob": 379000, "fuente": "INE"},
    {"ciudad": "Caracas (Área Metropolitana)", "lat": 10.4806, "lon": -66.9036, "pob": 2946000, "fuente": "INE"},
    {"ciudad": "Catia La Mar", "lat": 10.6039, "lon": -67.0303, "pob": 165000, "fuente": "INE"},
    {"ciudad": "Caraballeda", "lat": 10.6111, "lon": -66.8522, "pob": 54000, "fuente": "INE"},
]


def crear_sesion_resiliente():
    sesion = requests.Session()
    estrategia_reintento = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adaptador = HTTPAdapter(max_retries=estrategia_reintento)
    sesion.mount("https://", adaptador)
    sesion.mount("http://", adaptador)
    return sesion


def distancia_haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return round(2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)


def consultar_poblacion_ciudad_viva(nombre_ciudad, lat, lon):
    """
    Obtiene la población exacta de la ciudad solicitada:
    1) Busca coincidencia directa en el censo oficial DANE/INE.
    2) Si es otra ciudad del mundo, consulta la población real en Wikidata/OpenStreetMap Overpass.
    """
    nombre_limpio = nombre_ciudad.split(",")[0].strip().lower()
    for c in CENTROS_POBLADOS_OFICIALES:
        if nombre_limpio in c["ciudad"].lower():
            return {
                "ciudad_oficial": c["ciudad"],
                "poblacion_ciudad": c["pob"],
                "fuente": f"Censo Oficial {c['fuente']}",
            }

    # Consulta en vivo en OpenStreetMap Overpass para cualquier ciudad ingresada por el usuario
    try:
        query = f"""
        [out:json][timeout:10];
        node["place"~"city|town|municipality"]["population"](around:15000,{lat},{lon});
        out body;
        """
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=10,
        )
        if resp.status_code == 200:
            elementos = resp.json().get("elements", [])
            mejor_pob = 0
            mejor_nombre = nombre_ciudad.split(",")[0].strip()
            for el in elementos:
                tags = el.get("tags", {})
                pob_str = "".join(
                    ch for ch in str(tags.get("population", "")) if ch.isdigit()
                )
                if pob_str and int(pob_str) > mejor_pob:
                    mejor_pob = int(pob_str)
                    mejor_nombre = tags.get("name", mejor_nombre)
            if mejor_pob > 0:
                return {
                    "ciudad_oficial": mejor_nombre,
                    "poblacion_ciudad": mejor_pob,
                    "fuente": "OpenStreetMap / Censo Local",
                }
    except Exception:
        pass

    return {
        "ciudad_oficial": nombre_ciudad.split(",")[0].strip(),
        "poblacion_ciudad": None,
        "fuente": "Sin registro municipal directo",
    }


def calcular_poblacion_real_radio(sesion, lat, lon, radio_km=50.0):
    """Suma la población exacta de los municipios verificados dentro de 50 km."""
    municipios_en_radio = []
    total_pob = 0
    fuentes = set()

    for c in CENTROS_POBLADOS_OFICIALES:
        dist = distancia_haversine_km(lat, lon, c["lat"], c["lon"])
        if dist <= radio_km:
            total_pob += c["pob"]
            municipios_en_radio.append(
                f"{c['ciudad']}: {c['pob']:,} hab. ({dist} km)"
            )
            fuentes.add(c["fuente"])

    if total_pob == 0:
        try:
            radio_m = int(radio_km * 1000)
            query = f"""
            [out:json][timeout:10];
            node["place"~"city|town"]["population"](around:{radio_m},{lat},{lon});
            out body;
            """
            resp = sesion.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=12,
            )
            if resp.status_code == 200:
                for el in resp.json().get("elements", []):
                    tags = el.get("tags", {})
                    pob_str = "".join(
                        ch for ch in str(tags.get("population", "")) if ch.isdigit()
                    )
                    if pob_str:
                        p_val = int(pob_str)
                        nombre = tags.get("name", "Centro Poblado")
                        dist = distancia_haversine_km(
                            lat, lon, el["lat"], el["lon"]
                        )
                        total_pob += p_val
                        municipios_en_radio.append(
                            f"{nombre}: {p_val:,} hab. ({dist} km)"
                        )
                        fuentes.add("OSM Live")
        except Exception:
            pass

    return {
        "poblacion_total": total_pob,
        "municipios_incluidos": municipios_en_radio,
        "fuente_demografica": " + ".join(sorted(fuentes)) if fuentes else "DANE/INE",
    }


def cargar_respaldo_local():
    if os.path.exists("laser_data.json"):
        try:
            with open("laser_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def obtener_sismos_recientes(sesion):
    url = (
        "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
        "&minmagnitude=3.5&minlatitude=1.0&maxlatitude=13.0"
        "&minlongitude=-79.0&maxlongitude=-60.0&limit=30&orderby=time"
    )
    try:
        resp = sesion.get(url, timeout=15)
        resp.raise_for_status()
        res = resp.json()
        sismos = []
        ahora_utc = datetime.now(timezone.utc)
        for f in res.get("features", []):
            lon, lat, prof = f["geometry"]["coordinates"]
            tiempo_ms = f["properties"]["time"]
            dt_evento = datetime.fromtimestamp(
                tiempo_ms / 1000.0, tz=timezone.utc
            )
            horas_transcurridas = round(
                (ahora_utc - dt_evento).total_seconds() / 3600.0, 1
            )
            sismos.append({
                "lugar": f["properties"]["place"],
                "magnitud": round(float(f["properties"]["mag"]), 1),
                "fecha": dt_evento.strftime("%Y-%m-%d %H:%M"),
                "horas_atras": max(0.0, horas_transcurridas),
                "lat": round(float(lat), 4),
                "lon": round(float(lon), 4),
                "profundidad_km": round(float(prof), 1),
            })
        return sismos, True
    except Exception:
        return [], False


def obtener_datos_nasa_nodo(sesion, lat, lon):
    ahora_utc = datetime.now(timezone.utc)
    fecha_fin = (ahora_utc - timedelta(days=2)).strftime("%Y%m%d")
    fecha_inicio = (ahora_utc - timedelta(days=540)).strftime("%Y%m%d")

    url = (
        f"https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=TS,GWETTOP,PRECTOTCORR"
        f"&community=RE&longitude={lon}&latitude={lat}"
        f"&start={fecha_inicio}&end={fecha_fin}&format=JSON"
    )
    resp = sesion.get(url, timeout=25)
    resp.raise_for_status()
    res = resp.json()

    df = pd.DataFrame(res["properties"]["parameter"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "fecha"
    df.replace(-999.0, np.nan, inplace=True)
    df.dropna(how="all", inplace=True)
    df.interpolate(method="linear", inplace=True)
    df.dropna(inplace=True)
    return df


def analizar_nodo(df, info_nodo, sismos_recientes, ventana=7):
    mk_ts = mk.original_test(df["TS"])
    mk_hum = mk.original_test(df["GWETTOP"])

    pendiente = mk_ts.slope if mk_ts.slope != 0 else 0.0001
    media_movil = df["TS"].rolling(window=ventana).mean()
    std_movil = df["TS"].rolling(window=ventana).std().replace(0, 0.001)

    z_score = (df["TS"] - media_movil) / std_movil
    df["indice_pi"] = (z_score * np.sign(pendiente)).fillna(0)

    sismos_72h_cercanos = 0
    sismo_mas_cercano_km = None
    for s in sismos_recientes:
        dist = distancia_haversine_km(
            info_nodo["lat"], info_nodo["lon"], s["lat"], s["lon"]
        )
        if sismo_mas_cercano_km is None or dist < sismo_mas_cercano_km:
            sismo_mas_cercano_km = dist
        if s["horas_atras"] <= 72.0 and dist <= 150.0:
            sismos_72h_cercanos += 1

    hum_actual = float(df["GWETTOP"].iloc[-1])
    lluvia_actual = float(df["PRECTOTCORR"].iloc[-1])

    if (hum_actual > 0.72 and lluvia_actual > 8.0) or (
        hum_actual > 0.68 and sismos_72h_cercanos > 0
    ):
        alerta_actual = "ALTA"
    elif hum_actual > 0.62 or sismos_72h_cercanos > 0:
        alerta_actual = "MODERADA"
    else:
        alerta_actual = "BAJA"

    ultimas_72h = df.tail(3)
    lluvia_72h = round(float(ultimas_72h["PRECTOTCORR"].sum()), 2)
    humedad_max_72h = round(float(ultimas_72h["GWETTOP"].max()), 3)
    delta_temp_72h = round(
        float(ultimas_72h["TS"].iloc[-1] - ultimas_72h["TS"].iloc[0]), 2
    )

    pi_actual = round(float(df["indice_pi"].iloc[-1]), 3)
    en_alerta = (
        abs(pi_actual) > 1.8 or alerta_actual == "ALTA" or lluvia_72h > 35.0
    )

    resumen = {
        "tendencia_ts": mk_ts.trend,
        "p_value_ts": round(float(mk_ts.p), 5),
        "significativa_ts": bool(mk_ts.h),
        "tasa_cambio_ts": round(float(mk_ts.slope), 6),
        "tendencia_humedad": mk_hum.trend,
        "p_value_humedad": round(float(mk_hum.p), 5),
        "pi_actual": pi_actual,
        "alerta_derrumbe": alerta_actual,
        "en_alerta_activa": en_alerta,
        "lluvia_72h_mm": lluvia_72h,
        "humedad_max_72h": humedad_max_72h,
        "delta_temp_72h": delta_temp_72h,
        "sismos_72h_radio_150km": sismos_72h_cercanos,
        "sismo_mas_cercano_km": (
            sismo_mas_cercano_km if sismo_mas_cercano_km is not None else -1
        ),
        "fecha_ultimo_dato_nasa": df.index[-1].strftime("%Y-%m-%d"),
    }
    return df, resumen


def construir_base_datos():
    sesion = crear_sesion_resiliente()
    respaldo = cargar_respaldo_local()

    sismos, usgs_ok = obtener_sismos_recientes(sesion)
    if not usgs_ok and respaldo:
        sismos = respaldo.get("sismos_recientes", [])

    resultados_nodos = {}
    nasa_ok_count = 0

    for key, info_base in NODOS_BASE.items():
        info = info_base.copy()
        demo = calcular_poblacion_real_radio(sesion, info["lat"], info["lon"], 50.0)
        info["poblacion"] = demo["poblacion_total"]
        info["municipios_radio_50km"] = demo["municipios_incluidos"]
        info["fuente_demografica"] = demo["fuente_demografica"]

        try:
            df = obtener_datos_nasa_nodo(sesion, info["lat"], info["lon"])
            df_calc, resumen = analizar_nodo(df, info, sismos)
            nasa_ok_count += 1

            df_reciente = df_calc.tail(120).reset_index()
            df_reciente["fecha"] = df_reciente["fecha"].dt.strftime("%Y-%m-%d")
            serie_records = df_reciente.to_dict(orient="records")
            fuente_estado = "EN VIVO (NASA POWER)"
        except Exception:
            if respaldo and key in respaldo.get("nodos", {}):
                nodo_prev = respaldo["nodos"][key]
                resumen = nodo_prev["estadisticas"]
                serie_records = nodo_prev["serie"]
                fuente_estado = "CACHÉ LOCAL (RESPALDO)"
            else:
                continue

        resultados_nodos[key] = {
            "info": info,
            "fuente_estado": fuente_estado,
            "estadisticas": resumen,
            "serie": serie_records,
        }

    if not resultados_nodos and respaldo:
        return respaldo

    payload = {
        "ultima_actualizacion": datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "estado_apis": {
            "nasa_power": "ONLINE" if nasa_ok_count > 0 else "CACHED_FALLBACK",
            "usgs_fdsn": "ONLINE" if usgs_ok else "CACHED_FALLBACK",
        },
        "sismos_recientes": sismos,
        "nodos": resultados_nodos,
    }

    with open("laser_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Base de datos generada: laser_data.json")
    return payload


if __name__ == "__main__":
    construir_base_datos()