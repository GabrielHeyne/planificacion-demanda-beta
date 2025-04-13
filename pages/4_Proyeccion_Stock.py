import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from modules.stock_projector import project_stock

# --- Estilos globales ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Manrope:wght@600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, .stTitle {
            font-family: 'Manrope', sans-serif !important;
            font-size: 28px !important;
            font-weight: 700 !important;
            margin-bottom: 0.5rem !important;
        }

        h2, .stSubtitle {
            font-family: 'Manrope', sans-serif !important;
            font-size: 18px !important;
            font-weight: 600 !important;
            margin-bottom: 0.5rem !important;
        }

        h3, h4, h5, h6 {
            font-family: 'Manrope', sans-serif !important;
            font-weight: 600 !important;
            font-size: 16px !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📦 PROYECCIÓN DE STOCK MENSUAL")
st.subheader("Proyección de Stock por SKU y Análisis de Disponibilidad")

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

# --- Datos del SKU seleccionado ---
stock_info = df_stock[df_stock['sku'] == sku_sel]
if stock_info.empty:
    st.warning("⚠️ No hay stock inicial cargado para este SKU.")
    st.stop()

fechas_disponibles = stock_info['fecha'].sort_values().dt.to_period('M').dt.to_timestamp().unique()
fecha_inicio = st.selectbox("Selecciona la fecha de stock inicial", fechas_disponibles)

fila_stock = stock_info[stock_info['fecha'].dt.to_period('M').dt.to_timestamp() == fecha_inicio].iloc[0]
descripcion = fila_stock.get('descripcion', 'N/A')
stock_inicial = fila_stock['stock']

# Obtener precio de venta desde el maestro
precio_venta = None
if not df_maestro.empty and sku_sel in df_maestro['sku'].values:
    precio_venta = df_maestro[df_maestro['sku'] == sku_sel]['precio_venta'].iloc[0]

# --- Mostrar información inicial ---
st.markdown(f"<h4 style='font-family: Montserrat;'>🛒 Descripción: {descripcion}</h4>", unsafe_allow_html=True)
st.markdown("#### 📦 Stock Inicial")
st.markdown(f"<h2 style='font-family: Montserrat; color: #333;'>{stock_inicial} unidades</h2>", unsafe_allow_html=True)

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

# --- Función para títulos con fondo --- 
def titulo_con_fondo(texto):
    return f"""
    <div style="background-color:#F7F7F7; padding:0px 0px; border-radius:16px; width:100%; text-align:center;">
        <h4 style="margin: 0; line-height: 1.5; font-weight: 700; font-size: 22px;">{texto}</h4>
    </div>
    """

# --- Mostrar tabla completa ---
st.markdown(titulo_con_fondo("📊 Tabla de proyección detallada"), unsafe_allow_html=True)
st.dataframe(df_resultado, use_container_width=True)

# --- Gráfico de stock final del mes ---
st.markdown(titulo_con_fondo("📉 Stock Proyectado al Final de Cada Mes"), unsafe_allow_html=True)
fig_stock = go.Figure()
fig_stock.add_trace(go.Scatter(
    x=df_resultado['mes'],
    y=df_resultado['stock_final_mes'],
    mode='lines+markers',
    name='Stock Final'
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

# --- Gráfico de pérdidas proyectadas en euros ---
st.markdown(titulo_con_fondo("💸 Pérdida Proyectada por Quiebres de Stock (en €)"), unsafe_allow_html=True)
fig_loss = go.Figure()
fig_loss.add_trace(go.Bar(
    x=df_resultado['mes'],
    y=df_resultado['perdida_proyectada_euros'],
    name="Pérdida proyectada (€)"
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
