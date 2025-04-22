import pandas as pd
import streamlit as st
import os
from pandas import ExcelWriter
from modules.demand_cleaner import clean_demand
from utils import render_logo_sidebar

# --- Cargar estilos y logo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()
render_logo_sidebar()

os.makedirs("data", exist_ok=True)

# --- Recargar desde disco si session_state está vacío ---
def cargar_si_existe(clave, ruta, tipo='csv'):
    if clave not in st.session_state or st.session_state[clave] is None:
        if os.path.exists(ruta):
            df = pd.read_excel(ruta) if tipo == 'excel' else pd.read_csv(ruta)
            st.session_state[clave] = df
            return df
    return st.session_state.get(clave)

# --- DEMANDA ---
st.markdown("<div class='section-title'>📁 Carga de Archivos y Limpieza de Demanda</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Sube el archivo de demanda (CSV)</div>", unsafe_allow_html=True)

demanda_df = cargar_si_existe('demanda_limpia', "data/demanda_limpia.xlsx", tipo='excel')

if demanda_df is None:
    archivo_demanda = st.file_uploader("", type="csv", key="uploader_demanda")
    if archivo_demanda is not None:
        raw = pd.read_csv(archivo_demanda)
        raw['fecha'] = pd.to_datetime(raw['fecha'])
        clean_df = clean_demand(raw)
        st.session_state['demanda_limpia'] = clean_df
        with ExcelWriter("data/demanda_limpia.xlsx", engine='xlsxwriter') as writer:
            clean_df.to_excel(writer, index=False)
        st.success("✅ Archivo cargado y demanda limpia generada.")
        st.rerun()
else:
    st.subheader("✅ Vista previa de la demanda limpia")
    cols = [c for c in ['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier'] if c in demanda_df.columns]
    st.dataframe(demanda_df[cols])
    with open("data/demanda_limpia.xlsx", "rb") as f:
        st.download_button("📥 Descargar Excel de Demanda Limpia", f.read(), "demanda_limpia.xlsx")
    st.info("ℹ️ Los datos ya están disponibles para análisis.")

# --- STOCK ACTUAL ---
st.markdown("<div class='section-title'>📦 Carga de Stock Actual por SKU (Opcional)</div>", unsafe_allow_html=True)
stock_df = cargar_si_existe("stock_actual", "data/stock_actual.csv")

if stock_df is None:
    archivo_stock = st.file_uploader("", type="csv", key="uploader_stock")
    if archivo_stock:
        df = pd.read_csv(archivo_stock)
        expected = {'sku', 'descripcion', 'stock', 'fecha'}
        if expected.issubset(df.columns):
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            st.session_state["stock_actual"] = df
            df.to_csv("data/stock_actual.csv", index=False)
            st.success("✅ Archivo cargado.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    st.subheader("✅ Vista previa del stock actual")
    st.dataframe(stock_df[['sku', 'descripcion', 'stock', 'fecha']])

# --- REPOSICIONES ---
st.markdown("<div class='section-title'>📦 Carga de Reposiciones Futuras (Opcional)</div>", unsafe_allow_html=True)
repos_df = cargar_si_existe("reposiciones", "data/reposiciones.csv")

if repos_df is None:
    archivo_repos = st.file_uploader("", type="csv", key="uploader_reposiciones")
    if archivo_repos:
        df = pd.read_csv(archivo_repos)
        expected = {'sku', 'fecha', 'cantidad'}
        if expected.issubset(df.columns):
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
            st.session_state["reposiciones"] = df
            df.to_csv("data/reposiciones.csv", index=False)
            st.success("✅ Reposiciones cargadas.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    st.subheader("✅ Vista previa de las reposiciones futuras")
    st.dataframe(repos_df)

# --- MAESTRO ---
st.markdown("<div class='section-title'>📘 Carga del Maestro de Productos</div>", unsafe_allow_html=True)
maestro_df = cargar_si_existe("maestro", "data/maestro.csv")

if maestro_df is None:
    archivo_maestro = st.file_uploader("", type="csv", key="uploader_maestro")
    if archivo_maestro:
        df = pd.read_csv(archivo_maestro)
        expected = {'sku', 'descripcion', 'costo_fabricacion', 'precio_venta', 'categoria'}
        if expected.issubset(df.columns):
            df = df.dropna(subset=['sku'])
            st.session_state['maestro'] = df
            df.to_csv("data/maestro.csv", index=False)
            st.success("✅ Maestro cargado.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    st.subheader("✅ Vista previa del maestro de productos")
    st.dataframe(maestro_df)

# --- STOCK HISTÓRICO ---
st.markdown("<div class='section-title'>📊 Carga de Stock Histórico</div>", unsafe_allow_html=True)
stock_hist_df = cargar_si_existe("stock_historico", "data/stock_historico.csv")

if stock_hist_df is None:
    archivo_stock_hist = st.file_uploader("", type="csv", key="uploader_stock_historico")
    if archivo_stock_hist:
        df = pd.read_csv(archivo_stock_hist)
        expected = {'sku', 'fecha', 'stock'}
        if expected.issubset(df.columns):
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['stock'] = pd.to_numeric(df['stock'], errors='coerce').fillna(0).astype(int)
            st.session_state["stock_historico"] = df
            df.to_csv("data/stock_historico.csv", index=False)
            st.success("✅ Stock histórico cargado.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    st.subheader("✅ Vista previa del stock histórico")
    st.dataframe(stock_hist_df)
