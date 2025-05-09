import os
import tempfile
import pandas as pd
import streamlit as st
import gdown
from modules.demand_cleaner import clean_demand
from modules.forecast_engine import forecast_engine, generar_comparativa_forecasts
from modules.stock_projector import project_stock
from modules.resumen_utils import (
    consolidar_historico_stock,
    consolidar_proyeccion_futura,
    generar_contexto_negocio
)

@st.cache_data(ttl=3600)
def descargar_csv_drive(file_id, nombre_archivo):
    url = f"https://drive.google.com/uc?id={file_id}"
    ruta_local = os.path.join(tempfile.gettempdir(), nombre_archivo)
    gdown.download(url, ruta_local, quiet=True)
    return pd.read_csv(ruta_local)

def init_session(pasos=None, progress=None):
    def marcar_paso(i, texto):
        if pasos:
            pasos[i].markdown(texto)
        if progress:
            progress.progress((i + 1) / 6)

    # Paso 1: Descarga de archivos
    marcar_paso(0, "📁 1) Descargando archivos desde Google Drive...")
    if "demanda_cruda" not in st.session_state:
        st.session_state["demanda_cruda"] = descargar_csv_drive("1OXm_cHTP9Si4CtBInQZqQro0QR-pCWaQ", "demanda.csv")
    if "stock_historico" not in st.session_state:
        st.session_state["stock_historico"] = descargar_csv_drive("1GgjD8bL4QwHQo76pRv2bW2RGE71d4s9r", "stock_hist.csv")
    if "maestro" not in st.session_state:
        st.session_state["maestro"] = descargar_csv_drive("1ueW0mjB9aVUcDh4e8ywEIikJAvm-530h", "maestro.csv")
    if "stock_actual" not in st.session_state:
        st.session_state["stock_actual"] = descargar_csv_drive("1q5LfbrjT5dxlfMZQ-WvWqdKWz4fg7JBh", "stock_actual.csv")
    if "reposiciones" not in st.session_state:
        st.session_state["reposiciones"] = descargar_csv_drive("1v1tSpWkmR6Y4h39nD3uDG99JOx_qgLIk", "repos.csv")
    marcar_paso(0, "✅ 1) Archivos descargados correctamente")

    if st.session_state["stock_historico"] is None or st.session_state["stock_historico"].empty:
        st.error("❌ No se ha cargado correctamente el archivo de stock histórico.")
        st.stop()

    # Paso 2: Limpieza de demanda
    marcar_paso(1, "🧹 2) Limpiando demanda histórica...")
    if "demanda_limpia" not in st.session_state:
        st.session_state["demanda_limpia"] = clean_demand(st.session_state["demanda_cruda"])
    marcar_paso(1, "✅ 2) Demanda limpia generada")

    # Paso 3: Forecast
    marcar_paso(2, "📊 3) Generando forecast por SKU...")
    if "forecast" not in st.session_state:
        st.session_state["forecast"] = forecast_engine(st.session_state["demanda_limpia"])
    if "forecast_comparativa" not in st.session_state:
        st.session_state["forecast_comparativa"] = generar_comparativa_forecasts(st.session_state["demanda_limpia"], horizonte_meses=6)
    marcar_paso(2, "✅ 3) Forecast por SKU generado")

    # Paso 4: Proyección de stock
    marcar_paso(3, "📉 4) Proyectando stock futuro...")
    if "proyeccion_stock" not in st.session_state:
        st.session_state["proyeccion_stock"] = consolidar_proyeccion_futura(
            st.session_state["forecast"],
            st.session_state["stock_actual"],
            st.session_state["reposiciones"],
            st.session_state["maestro"]
        )
    marcar_paso(3, "✅ 4) Stock proyectado")

    # Paso 5: Pérdidas históricas
    marcar_paso(4, "📦 5) Calculando pérdidas y resumen histórico...")
    if "resumen_historico" not in st.session_state:
        st.session_state["resumen_historico"] = consolidar_historico_stock(
            st.session_state["demanda_limpia"],
            st.session_state["maestro"]
        )
    marcar_paso(4, "✅ 5) Resumen histórico generado")

    # Paso 6: Contexto IA
    marcar_paso(5, "🧠 6) Generando contexto de negocio para IA...")
    if ("contexto_negocio" not in st.session_state or
        "contexto_negocio_general" not in st.session_state):
        contexto = generar_contexto_negocio(
            st.session_state["forecast"],
            st.session_state["proyeccion_stock"],
            st.session_state["resumen_historico"]
        )
        st.session_state["contexto_negocio"] = contexto
        st.session_state["contexto_negocio_general"] = contexto
    marcar_paso(5, "✅ 6) Contexto de negocio listo")

    st.session_state["datos_cargados"] = True
