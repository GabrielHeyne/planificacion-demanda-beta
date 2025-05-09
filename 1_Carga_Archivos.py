import pandas as pd
import streamlit as st
from modules.demand_cleaner import clean_demand
from utils import render_logo_sidebar

# --- Estilos y logo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()
render_logo_sidebar()

# --- Inicializar session_state ---
for clave in ['demanda_limpia', 'stock_actual', 'reposiciones', 'maestro', 'stock_historico']:
    if clave not in st.session_state:
        st.session_state[clave] = None

st.markdown("""
<div style='font-size:25px; font-weight:400; margin-top:10px; margin-bottom:10px;'>
📁 Carga de Archivos
</div>
""", unsafe_allow_html=True)

# --- STOCK HISTÓRICO (Primero) ---
st.markdown("<div class='section-subtitle'>📊 Carga de Stock Histórico</div>", unsafe_allow_html=True)
if st.session_state['stock_historico'] is None:
    archivo = st.file_uploader("1️⃣ Sube el archivo de stock histórico (CSV)", type="csv", key="uploader_stock_historico")
    if archivo:
        df = pd.read_csv(archivo)
        expected = {'sku', 'fecha', 'stock'}
        if expected.issubset(df.columns):
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['stock'] = pd.to_numeric(df['stock'], errors='coerce').fillna(0).astype(int)
            st.session_state['stock_historico'] = df
            st.success("✅ Stock histórico cargado correctamente.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    historico_df = st.session_state['stock_historico']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa del stock histórico</b></div>", unsafe_allow_html=True)
    st.dataframe(historico_df)

# --- DEMANDA (Permitir siempre, con advertencia si no hay stock) ---
st.markdown("<div class='section-subtitle'>📈 Carga de Demanda y Limpieza</div>", unsafe_allow_html=True)

if st.session_state['stock_historico'] is None:
    st.warning("⚠️ Para limpiar la demanda correctamente, se recomienda subir primero el archivo de stock histórico. Aun así, puedes continuar.")

if st.session_state['demanda_limpia'] is None:
    archivo = st.file_uploader("2️⃣ Sube el archivo de demanda (CSV)", type="csv", key="uploader_demanda")
    if archivo:
        df = pd.read_csv(archivo)
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = clean_demand(df)
        st.session_state['demanda_limpia'] = df
        st.success("✅ Archivo cargado y demanda limpia generada.")
        st.rerun()
else:
    cleaned_demand_df = st.session_state['demanda_limpia']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa de la demanda limpia</b></div>", unsafe_allow_html=True)
    cols = [c for c in ['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier'] if c in cleaned_demand_df.columns]
    st.dataframe(cleaned_demand_df[cols])
    st.download_button("📥 Descargar Excel de Demanda Limpia", cleaned_demand_df.to_csv(index=False).encode(), "demanda_limpia.csv")


# --- STOCK ACTUAL ---
st.markdown("<div class='section-subtitle'>📦 Carga de Stock Actual por SKU (Opcional)</div>", unsafe_allow_html=True)
if st.session_state['stock_actual'] is None:
    archivo = st.file_uploader("Sube el archivo de stock actual (CSV)", type="csv", key="uploader_stock")
    if archivo:
        df = pd.read_csv(archivo)
        expected = {'sku', 'descripcion', 'stock', 'fecha'}
        if expected.issubset(df.columns):
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            st.session_state['stock_actual'] = df
            st.success("✅ Archivo cargado correctamente.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    stock_df = st.session_state['stock_actual']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa del stock actual</b></div>", unsafe_allow_html=True)
    st.dataframe(stock_df)

# --- REPOSICIONES ---
st.markdown("<div class='section-subtitle'>📦 Carga de Reposiciones Futuras</div>", unsafe_allow_html=True)
if st.session_state['reposiciones'] is None:
    archivo = st.file_uploader("Sube el archivo de reposiciones (CSV)", type="csv", key="uploader_reposiciones")
    if archivo:
        df = pd.read_csv(archivo)
        expected = {'sku', 'fecha', 'cantidad'}
        if expected.issubset(df.columns):
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
            st.session_state['reposiciones'] = df
            st.success("✅ Reposiciones cargadas.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    repos_df = st.session_state['reposiciones']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa de las reposiciones futuras</b></div>", unsafe_allow_html=True)
    st.dataframe(repos_df)

# --- MAESTRO ---
st.markdown("<div class='section-subtitle'>📘 Carga del Maestro de Productos</div>", unsafe_allow_html=True)
if st.session_state['maestro'] is None:
    archivo = st.file_uploader("Sube el archivo maestro (CSV)", type="csv", key="uploader_maestro")
    if archivo:
        df = pd.read_csv(archivo)
        expected = {'sku', 'descripcion', 'costo_fabricacion', 'precio_venta', 'categoria'}
        if expected.issubset(df.columns):
            df = df.dropna(subset=['sku'])
            st.session_state['maestro'] = df
            st.success("✅ Maestro cargado.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    maestro_df = st.session_state['maestro']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa del maestro de productos</b></div>", unsafe_allow_html=True)
    st.dataframe(maestro_df)


