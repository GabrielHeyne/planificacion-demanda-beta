import pandas as pd
import streamlit as st
from modules.demand_cleaner import clean_demand
from utils.utils import render_logo_sidebar
from utils.file_operations import upload_file_to_supabase, get_file_from_supabase, list_available_files

# --- Estilos y logo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()
render_logo_sidebar()

# --- Inicializar estructuras ---
for clave in ['demanda_limpia', 'stock_actual', 'reposiciones', 'maestro', 'stock_historico']:
    if clave not in st.session_state:
        st.session_state[clave] = None

# --- Carga de DEMANDA ---
st.markdown("<div class='section-title'>📁 Carga de Archivos y Limpieza de Demanda</div>", unsafe_allow_html=True)

if st.session_state['demanda_limpia'] is None:
    # Show available files
    available_files = list_available_files('demanda')
    if available_files:
        st.markdown("### Archivos disponibles")
        for file in available_files:
            if st.button(f"📄 {file['file_name']} ({file['upload_date']})"):
                df = get_file_from_supabase('demanda', file['file_name'])
                if df is not None:
                    df['fecha'] = pd.to_datetime(df['fecha'])
                    df = clean_demand(df)
                    st.session_state['demanda_limpia'] = df
                    st.success("✅ Archivo cargado y demanda limpia generada.")
                    st.rerun()
    
    # File uploader
    archivo = st.file_uploader("Sube el archivo de demanda (CSV)", type="csv", key="uploader_demanda")
    if archivo:
        # Upload to Supabase
        success, file_name = upload_file_to_supabase(archivo, 'demanda')
        if success:
            st.success(f"✅ Archivo guardado en Supabase como: {file_name}")
        
        # Process the file
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
st.markdown("<div class='section-title'>📦 Carga de Stock Actual por SKU (Opcional)</div>", unsafe_allow_html=True)

if st.session_state['stock_actual'] is None:
    # Show available files
    available_files = list_available_files('stock_actual')
    if available_files:
        st.markdown("### Archivos disponibles")
        for file in available_files:
            if st.button(f"📄 {file['file_name']} ({file['upload_date']})"):
                df = get_file_from_supabase('stock_actual', file['file_name'])
                if df is not None:
                    st.session_state['stock_actual'] = df
                    st.success("✅ Archivo cargado correctamente.")
                    st.rerun()
    
    # File uploader
    archivo = st.file_uploader("Sube el archivo de stock actual (CSV)", type="csv", key="uploader_stock")
    if archivo:
        # Upload to Supabase
        success, file_name = upload_file_to_supabase(archivo, 'stock_actual')
        if success:
            st.success(f"✅ Archivo guardado en Supabase como: {file_name}")
        
        # Process the file
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
st.markdown("<div class='section-title'>📦 Carga de Reposiciones Futuras</div>", unsafe_allow_html=True)

if st.session_state['reposiciones'] is None:
    # Show available files
    available_files = list_available_files('reposiciones')
    if available_files:
        st.markdown("### Archivos disponibles")
        for file in available_files:
            if st.button(f"📄 {file['file_name']} ({file['upload_date']})"):
                df = get_file_from_supabase('reposiciones', file['file_name'])
                if df is not None:
                    st.session_state['reposiciones'] = df
                    st.success("✅ Reposiciones cargadas.")
                    st.rerun()
    
    # File uploader
    archivo = st.file_uploader("Sube el archivo de reposiciones (CSV)", type="csv", key="uploader_reposiciones")
    if archivo:
        # Upload to Supabase
        success, file_name = upload_file_to_supabase(archivo, 'reposiciones')
        if success:
            st.success(f"✅ Archivo guardado en Supabase como: {file_name}")
        
        # Process the file
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
st.markdown("<div class='section-title'>📘 Carga del Maestro de Productos</div>", unsafe_allow_html=True)

if st.session_state['maestro'] is None:
    # Show available files
    available_files = list_available_files('maestro')
    if available_files:
        st.markdown("### Archivos disponibles")
        for file in available_files:
            if st.button(f"📄 {file['file_name']} ({file['upload_date']})"):
                df = get_file_from_supabase('maestro', file['file_name'])
                if df is not None:
                    st.session_state['maestro'] = df
                    st.success("✅ Maestro cargado.")
                    st.rerun()
    
    # File uploader
    archivo = st.file_uploader("Sube el archivo maestro (CSV)", type="csv", key="uploader_maestro")
    if archivo:
        # Upload to Supabase
        success, file_name = upload_file_to_supabase(archivo, 'maestro')
        if success:
            st.success(f"✅ Archivo guardado en Supabase como: {file_name}")
        
        # Process the file
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


# --- STOCK HISTÓRICO ---
st.markdown("<div class='section-title'>📊 Carga de Stock Histórico</div>", unsafe_allow_html=True)

if st.session_state['stock_historico'] is None:
    # Show available files
    available_files = list_available_files('stock_historico')
    if available_files:
        st.markdown("### Archivos disponibles")
        for file in available_files:
            if st.button(f"📄 {file['file_name']} ({file['upload_date']})"):
                df = get_file_from_supabase('stock_historico', file['file_name'])
                if df is not None:
                    st.session_state['stock_historico'] = df
                    st.success("✅ Stock histórico cargado.")
                    st.rerun()
    
    # File uploader
    archivo = st.file_uploader("Sube el archivo de stock histórico (CSV)", type="csv", key="uploader_stock_historico")
    if archivo:
        # Upload to Supabase
        success, file_name = upload_file_to_supabase(archivo, 'stock_historico')
        if success:
            st.success(f"✅ Archivo guardado en Supabase como: {file_name}")
        
        # Process the file
        df = pd.read_csv(archivo)
        expected = {'sku', 'fecha', 'stock'}
        if expected.issubset(df.columns):
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            df['stock'] = pd.to_numeric(df['stock'], errors='coerce').fillna(0).astype(int)
            st.session_state['stock_historico'] = df
            st.success("✅ Stock histórico cargado.")
            st.rerun()
        else:
            st.error(f"⚠️ Faltan columnas: {expected - set(df.columns)}")
else:
    historico_df = st.session_state['stock_historico']
    st.markdown("<div style='font-size:16px;'>✅ <b>Vista previa del stock histórico</b></div>", unsafe_allow_html=True)
    st.dataframe(historico_df)

