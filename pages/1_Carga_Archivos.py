import pandas as pd
import streamlit as st
import os
from pandas import ExcelWriter
from modules.demand_cleaner import clean_demand

# Cargar CSS
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cargar el CSS
load_css()

# --- Inicializar session_state ---
if 'demanda_limpia' not in st.session_state:
    st.session_state['demanda_limpia'] = None
if 'stock_actual' not in st.session_state:
    st.session_state['stock_actual'] = None
if 'reposiciones' not in st.session_state:
    st.session_state['reposiciones'] = None
if 'maestro' not in st.session_state:
    st.session_state['maestro'] = None
if 'stock_historico' not in st.session_state:
    st.session_state['stock_historico'] = None

os.makedirs("data", exist_ok=True)

# --- CARGA DEMANDA ---
st.markdown("<div class='section-title'>📁 Carga de Archivos y Limpieza de Demanda</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Sube el archivo de demanda (CSV)</div>", unsafe_allow_html=True)

if st.session_state['demanda_limpia'] is None:
    archivo_demanda = st.file_uploader("", type="csv", key="uploader_demanda")

    if archivo_demanda is not None:
        demand_df = pd.read_csv(archivo_demanda)
        demand_df['fecha'] = pd.to_datetime(demand_df['fecha'])

        cleaned_demand_df = clean_demand(demand_df)
        st.session_state['demanda_limpia'] = cleaned_demand_df

        file_path = "data/demanda_limpia.xlsx"
        with ExcelWriter(file_path, engine='xlsxwriter') as writer:
            cleaned_demand_df.to_excel(writer, index=False, sheet_name='Demanda Limpia')

        st.session_state['demanda_limpia_path'] = file_path
        st.success("✅ Archivo cargado y demanda limpia generada correctamente.")
        st.rerun()
else:
    cleaned_demand_df = st.session_state['demanda_limpia']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa de la demanda limpia</b></div>", unsafe_allow_html=True)
    st.dataframe(cleaned_demand_df[['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier']])

    if 'demanda_limpia_path' in st.session_state:
        file_path = st.session_state['demanda_limpia_path']
        st.download_button(
            label="📥 Descargar Excel de Demanda Limpia",
            data=open(file_path, 'rb').read(),
            file_name="demanda_limpia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.info("ℹ️ Los datos ya fueron cargados y están disponibles para visualización o forecasting desde el menú 'Demanda Total'.")

# --- CARGA STOCK ACTUAL ---
st.markdown("<div class='section-title'>📦 Carga de Stock Actual por SKU (Opcional)</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Sube el archivo de stock actual (CSV)</div>", unsafe_allow_html=True)

if st.session_state['stock_actual'] is None:
    archivo_stock = st.file_uploader("", type="csv", key="uploader_stock")

    if archivo_stock is not None:
        stock_df = pd.read_csv(archivo_stock)
        columnas_esperadas = {'sku', 'descripcion', 'stock', 'fecha'}

        if columnas_esperadas.issubset(set(stock_df.columns)):
            stock_df['fecha'] = pd.to_datetime(stock_df['fecha'], errors='coerce')
            st.session_state['stock_actual'] = stock_df

            stock_df.to_csv("data/stock_actual.csv", index=False)
            st.session_state['stock_actual_path'] = "data/stock_actual.csv"

            st.success("✅ Archivo de stock actual cargado correctamente.")
            st.rerun()
        else:
            st.error("⚠️ El archivo debe tener las columnas: sku, descripcion, stock, fecha.")
else:
    stock_df = st.session_state['stock_actual']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa del stock actual</b></div>", unsafe_allow_html=True)
    st.dataframe(stock_df[['sku', 'descripcion', 'stock', 'fecha']])

# --- CARGA REPOSICIONES FUTURAS ---
st.markdown("<div class='section-title'>📦 Carga de Reposiciones Futuras (Opcional)</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Sube el archivo de reposiciones (CSV) con columnas: sku, fecha, cantidad</div>", unsafe_allow_html=True)

if st.session_state['reposiciones'] is None:
    archivo_reposiciones = st.file_uploader("", type="csv", key="uploader_reposiciones")

    if archivo_reposiciones is not None:
        repos_df = pd.read_csv(archivo_reposiciones)
        columnas_requeridas = {'sku', 'fecha', 'cantidad'}

        if columnas_requeridas.issubset(set(repos_df.columns)):
            repos_df['fecha'] = pd.to_datetime(repos_df['fecha'], errors='coerce')
            repos_df['cantidad'] = pd.to_numeric(repos_df['cantidad'], errors='coerce').fillna(0).astype(int)
            st.session_state['reposiciones'] = repos_df

            repos_df.to_csv("data/reposiciones.csv", index=False)
            st.session_state['reposiciones_path'] = "data/reposiciones.csv"

            st.success("✅ Archivo de reposiciones cargado correctamente.")
            st.rerun()
        else:
            st.error("⚠️ El archivo debe tener las columnas: sku, fecha, cantidad.")
else:
    repos_df = st.session_state['reposiciones']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa de las reposiciones futuras</b></div>", unsafe_allow_html=True)
    st.dataframe(repos_df)

# --- CARGA MAESTRO DE PRODUCTOS ---
st.markdown("<div class='section-title'>📘 Carga del Maestro de Productos</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Sube el archivo maestro (CSV) con columnas: sku, descripcion, costo_fabricacion, precio_venta, categoria</div>", unsafe_allow_html=True)

if st.session_state['maestro'] is None:
    archivo_maestro = st.file_uploader("", type="csv", key="uploader_maestro")

    if archivo_maestro is not None:
        maestro_df = pd.read_csv(archivo_maestro)
        columnas_requeridas = {'sku', 'descripcion', 'costo_fabricacion', 'precio_venta', 'categoria'}

        if columnas_requeridas.issubset(set(maestro_df.columns)):
            maestro_df = maestro_df.dropna(subset=['sku'])
            st.session_state['maestro'] = maestro_df

            maestro_df.to_csv("data/maestro.csv", index=False)
            st.session_state['maestro_path'] = "data/maestro.csv"

            st.success("✅ Archivo maestro cargado correctamente.")
            st.rerun()
        else:
            st.error("⚠️ El archivo debe tener las columnas: sku, descripcion, costo_fabricacion, precio_venta, categoria.")
else:
    maestro_df = st.session_state['maestro']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa del maestro de productos</b></div>", unsafe_allow_html=True)
    st.dataframe(maestro_df)

# --- CARGA DE STOCK HISTÓRICO ---
st.markdown("<div class='section-title'>📊 Carga de Stock Histórico</div>", unsafe_allow_html=True)
st.markdown("<div class='subtext'>Sube el archivo de stock histórico (CSV) con columnas: sku, fecha, stock</div>", unsafe_allow_html=True)

if st.session_state['stock_historico'] is None:
    archivo_stock_hist = st.file_uploader("", type="csv", key="uploader_stock_historico")

    if archivo_stock_hist is not None:
        stock_hist_df = pd.read_csv(archivo_stock_hist)
        columnas_requeridas = {'sku', 'fecha', 'stock'}

        if columnas_requeridas.issubset(set(stock_hist_df.columns)):
            stock_hist_df['fecha'] = pd.to_datetime(stock_hist_df['fecha'], errors='coerce')
            stock_hist_df['stock'] = pd.to_numeric(stock_hist_df['stock'], errors='coerce').fillna(0).astype(int)
            st.session_state['stock_historico'] = stock_hist_df

            stock_hist_df.to_csv("data/stock_historico.csv", index=False)
            st.session_state['stock_historico_path'] = "data/stock_historico.csv"

            st.success("✅ Archivo de stock histórico cargado correctamente.")
            st.rerun()
        else:
            st.error("⚠️ El archivo debe tener las columnas: sku, fecha, stock.")
else:
    stock_hist_df = st.session_state['stock_historico']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa del stock histórico</b></div>", unsafe_allow_html=True)
    st.dataframe(stock_hist_df)
