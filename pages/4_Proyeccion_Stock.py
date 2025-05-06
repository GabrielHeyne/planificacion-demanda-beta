import pandas as pd
import streamlit as st
from utils.utils import render_logo_sidebar 
import plotly.graph_objects as go
from modules.stock_projector import project_stock
import os

# --- Cargar estilo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
render_logo_sidebar()

st.markdown("<h1 style='font-size: 26px; font-weight: 500;'>📦 PROYECCIÓN DE STOCK MENSUAL</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 16px;'>Proyección de stock por SKU y análisis de pérdidas estimadas</p>", unsafe_allow_html=True)

# --- Cargar forecast desde disco si está vacío ---
if 'forecast' not in st.session_state:
    if os.path.exists("data/forecast.csv"):
        df_forecast = pd.read_csv("data/forecast.csv")
        df_forecast['mes'] = pd.to_datetime(df_forecast['mes'])
        st.session_state['forecast'] = df_forecast

# --- Validaciones ---
if 'forecast' not in st.session_state or st.session_state['forecast'] is None:
    st.warning("⚠️ No se ha generado el forecast aún. Ve al módulo correspondiente y vuelve a intentarlo.")
    st.stop()

if 'stock_actual' not in st.session_state or st.session_state['stock_actual'] is None:
    st.warning("⚠️ No se ha cargado el archivo de stock actual. Ve al módulo de carga y vuelve a intentarlo.")
    st.stop()

# --- Carga de datos ---
df_forecast = st.session_state['forecast'].copy()
df_stock = st.session_state['stock_actual'].copy()
df_repos = st.session_state.get('reposiciones', pd.DataFrame(columns=['sku', 'fecha', 'cantidad']))
df_maestro = st.session_state.get('maestro', pd.DataFrame())

# --- Selector de SKU ---
skus = sorted(df_forecast['sku'].unique())
sku_sel = st.selectbox("Selecciona un SKU", skus)

# --- Stock inicial automático (última fecha disponible) ---
stock_info = df_stock[df_stock['sku'] == sku_sel]
if stock_info.empty:
    st.warning("⚠️ No hay stock inicial cargado para este SKU.")
    st.stop()

fecha_inicio = stock_info['fecha'].max().to_period('M').to_timestamp()
fila_stock = stock_info[stock_info['fecha'].dt.to_period('M').dt.to_timestamp() == fecha_inicio].iloc[0]
stock_inicial = int(fila_stock['stock'])

# Precio de venta
precio_venta = None
if not df_maestro.empty and sku_sel in df_maestro['sku'].values:
    precio_venta = df_maestro[df_maestro['sku'] == sku_sel]['precio_venta'].iloc[0]

# --- Ejecutar proyección ---
df_resultado = project_stock(
    df_forecast=df_forecast,
    df_stock=df_stock,
    df_repos=df_repos,
    sku=sku_sel,
    fecha_inicio=fecha_inicio,
    precio_venta=precio_venta
)

if df_resultado.empty:
    st.warning("⚠️ No se pudo generar la proyección. Revisa si el forecast contiene datos desde la fecha seleccionada.")
    st.stop()

# ✅ Guardar la proyección para el planificador IA
st.session_state['stock_proyectado'] = df_resultado

# ✅ Guardar CSV de persistencia
df_resultado.to_csv(f"data/proyeccion_stock_{sku_sel}.csv", index=False)

# --- KPIs visuales ---
st.markdown("<div class='titulo-con-fondo'>📌 Información del Producto Seleccionado</div>", unsafe_allow_html=True)

unidades_perdidas = int(df_resultado['unidades_perdidas'].sum())
unidades_repos = int(df_resultado['repos_aplicadas'].sum())

def tarjeta_kpi(label, value):
    return f"""
    <div style="
        background-color:#ffffff;
        padding:16px;
        border-radius:12px;
        text-align:center;
        height:90px;
        width:100%;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        margin: 10px;
        border: 1px solid #B0B0B0;
    ">
        <div style="font-size:14px; font-weight:500;">{label}</div>
        <div style="font-size:26px;">{value}</div>
    </div>
    """

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(tarjeta_kpi("Stock Inicial", f"{stock_inicial} unidades"), unsafe_allow_html=True)
with col2:
    st.markdown(tarjeta_kpi("Unidades en Camino", f"{unidades_repos} unidades"), unsafe_allow_html=True)
with col3:
    st.markdown(tarjeta_kpi("Unidades Perdidas Proyectadas", f"{unidades_perdidas} unidades"), unsafe_allow_html=True)

# --- Tabla de proyección ---
st.markdown("<div class='titulo-con-fondo'>📊 Tabla de Proyección Detallada</div>", unsafe_allow_html=True)
st.dataframe(df_resultado, use_container_width=True)

# --- Gráficos en 2 columnas ---
colg1, colg2 = st.columns(2)

with colg1:
    st.markdown("<div class='titulo-con-fondo'>📉 Stock Proyectado por Mes</div>", unsafe_allow_html=True)
    fig_stock = go.Figure()
    fig_stock.add_trace(go.Scatter(
        x=df_resultado['mes'],
        y=df_resultado['stock_final_mes'],
        mode='lines+markers',
        name='Stock Final',
        line=dict(color='royalblue', width=3),
        marker=dict(size=7)
    ))
    fig_stock.update_layout(
        xaxis_title="Mes",
        yaxis_title="Unidades",
        height=420,
        margin=dict(t=50),
        xaxis=dict(tickformat="%b %Y", dtick="M1", tickangle=-45),
        yaxis=dict(range=[0, max(df_resultado['stock_final_mes'].max(), 10)])
    )
    st.plotly_chart(fig_stock, use_container_width=True)

with colg2:
    st.markdown("<div class='titulo-con-fondo'>💸 Pérdidas Estimadas por Quiebres (en €)</div>", unsafe_allow_html=True)
    fig_loss = go.Figure()
    fig_loss.add_trace(go.Bar(
        x=df_resultado['mes'],
        y=df_resultado['perdida_proyectada_euros'],
        name="Pérdida estimada (€)",
        marker_color='crimson'
    ))
    fig_loss.update_layout(
        xaxis_title="Mes",
        yaxis_title="Pérdida (€)",
        height=420,
        margin=dict(t=50),
        xaxis=dict(tickformat="%b %Y", dtick="M1", tickangle=-45),
        yaxis=dict(range=[0, max(df_resultado['perdida_proyectada_euros'].max(), 10)])
    )
    st.plotly_chart(fig_loss, use_container_width=True)

# --- Gráfico de stock histórico mensual ---
if 'stock_historico' in st.session_state and st.session_state['stock_historico'] is not None:
    df_hist = st.session_state['stock_historico'].copy()
    df_hist = df_hist[df_hist['sku'] == sku_sel].copy()

    if not df_hist.empty:
        df_hist['mes'] = pd.to_datetime(df_hist['fecha']).dt.to_period('M').dt.to_timestamp()
        df_hist = df_hist.groupby('mes')['stock'].sum().reset_index()

        st.markdown("<div class='titulo-con-fondo'>📚 Evolución Histórica del Stock</div>", unsafe_allow_html=True)

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=df_hist['mes'],
            y=df_hist['stock'],
            mode='lines+markers',
            name='Stock Histórico',
            line=dict(color='gray', width=3),
            marker=dict(size=7)
        ))
        fig_hist.update_layout(
            xaxis_title="Mes",
            yaxis_title="Stock Disponible",
            height=420,
            margin=dict(t=50),
            xaxis=dict(tickformat="%b %Y", dtick="M1", tickangle=-45)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# --- Descargar CSV ---
def generar_csv(df):
    df_export = df.copy()
    df_export.columns = [col.replace("_", " ").capitalize() for col in df_export.columns]
    return df_export.to_csv(index=False).encode('utf-8')

csv = generar_csv(df_resultado)

st.download_button(
    label="📥 Descargar archivo CSV",
    data=csv,
    file_name=f"proyeccion_stock_{sku_sel}.csv",
    mime="text/csv"
)
