import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from modules.forecast_engine import forecast_simple
from utils import render_logo_sidebar
import os

# --- Configuración inicial ---
st.set_page_config(layout="wide")

# --- Cargar estilos ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
render_logo_sidebar()

# --- Título ---
st.markdown('<h1 style="font-size: 26px; margin-bottom: 2px; font-weight: 500;">FORECAST DE DEMANDA POR SKU</h1>', unsafe_allow_html=True)

# --- Validación de datos ---
if 'demanda_limpia' not in st.session_state:
    st.error("⚠️ No se ha cargado la demanda limpia. Por favor, ve a 'Carga Archivos' y vuelve a intentarlo.")
    st.stop()

st.success("📈 Demanda limpia cargada correctamente.")
df_demanda = st.session_state['demanda_limpia']

# --- Cargar forecast desde disco si está disponible ---
if 'forecast' not in st.session_state:
    if os.path.exists("data/forecast.csv"):
        df_forecast = pd.read_csv("data/forecast.csv")
        df_forecast['mes'] = pd.to_datetime(df_forecast['mes'])
        st.session_state['forecast'] = df_forecast
    else:
        df_forecast = forecast_simple(df_demanda, lead_time_meses=4)
        df_forecast.to_csv("data/forecast.csv", index=False)
        st.session_state['forecast'] = df_forecast
else:
    df_forecast = st.session_state['forecast']

# --- Selección de SKU ---
sku_seleccionado = st.selectbox("Selecciona un SKU", df_forecast['sku'].unique())
df_filtrado = df_forecast[df_forecast['sku'] == sku_seleccionado].copy()
df_filtrado['mes'] = pd.to_datetime(df_filtrado['mes'])

# --- KPIs ---
ultimo_mes_con_demandas = df_filtrado[df_filtrado['demanda_limpia'] > 0]['mes'].max()
df_ultimos_6_meses = df_filtrado[df_filtrado['mes'] <= ultimo_mes_con_demandas].tail(6)
demanda_promedio_6 = int(round(df_ultimos_6_meses['demanda_limpia'].mean())) if len(df_ultimos_6_meses) > 0 else 0

df_forecast_futuro = df_filtrado[df_filtrado['tipo_mes'] == 'proyección']
forecast_proyectado = int(round(df_forecast_futuro['forecast'].mean())) if not df_forecast_futuro.empty else 0

df_backtest = df_filtrado[df_filtrado['tipo_mes'] == 'backtest'].sort_values('mes')
dpa_valores = df_backtest['dpa_movil'].dropna()
dpa_resumen = round(dpa_valores.iloc[-3:].mean(), 3) if not dpa_valores.empty else "–"

# --- KPIs visuales ---
kpi_template = """
<div style="
        background-color:#ffffff;
        padding:16px;
        border-radius:12px;
        text-align:center;
        height:110px;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        margin: 10px;
        border: 1px solid #B0B0B0;
        box-shadow: none;
    ">
    <div style="font-size:14px; font-weight:500; margin-bottom:6px;">{label}</div>
    <div style="font-size:30px;">{value}</div>
</div>
"""

col1, col2, col3 = st.columns(3)
col1.markdown(kpi_template.format(label="Demanda Limpia (Últ. 6 meses)", value=f"{demanda_promedio_6} unidades"), unsafe_allow_html=True)
col2.markdown(kpi_template.format(label="Forecast Proyectado", value=f"{forecast_proyectado} unidades"), unsafe_allow_html=True)
col3.markdown(kpi_template.format(label="DPA Móvil (Backtest)", value=f"{dpa_resumen:.1%}" if isinstance(dpa_resumen, float) else dpa_resumen), unsafe_allow_html=True)

# --- Gráfico de forecast ---
df_plot = df_filtrado.sort_values('mes')
df_plot['mes_label'] = df_plot['mes'].dt.strftime('%b %Y')

fig = go.Figure()
fig.add_trace(go.Bar(x=df_plot['mes_label'], y=df_plot['demanda_limpia'], name='Demanda Limpia', marker_color='royalblue', text=df_plot['demanda_limpia'], textposition='outside'))

df_forecast_total = df_plot[df_plot['tipo_mes'] != 'histórico'].sort_values('mes')
fig.add_trace(go.Scatter(
    x=df_forecast_total['mes_label'], y=df_forecast_total['forecast'],
    name='Forecast proyectado', mode='lines+markers+text',
    line=dict(color='crimson', width=3), marker=dict(size=8),
    text=df_forecast_total['forecast'], textposition='top center'
))

fig.update_layout(
    xaxis_title='Mes', yaxis_title='Unidades', legend_title='Tipo',
    font_family='Poppins, sans-serif', xaxis_tickangle=45,
    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5)
)

st.markdown(f'<h1 style="font-size: 22px; margin-bottom: 2px; font-weight: 400; text-align: center;">📊 Gráfico: Demanda Limpia y Forecast para SKU: {sku_seleccionado}</h1>', unsafe_allow_html=True)
st.plotly_chart(fig, use_container_width=True)

# --- Tabla de detalle ---
df_tabla = df_filtrado.copy()
df_tabla['dpa_movil'] = df_tabla.apply(lambda row: f"{row['dpa_movil']:.2%}" if pd.notnull(row['dpa_movil']) and row['tipo_mes'] == 'backtest' else "–", axis=1)
columnas_ordenadas = ['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'tipo_mes', 'dpa_movil']
df_tabla = df_tabla[columnas_ordenadas]

st.markdown(f'<h1 style="font-size: 20px; margin-top: 25px; margin-bottom: 10px; font-weight: 400; text-align: center;">📋 Detalle del Forecast para SKU: {sku_seleccionado}</h1>', unsafe_allow_html=True)
st.dataframe(df_tabla)

# --- Descargar CSV ---
def generar_csv_forecast(df):
    df_export = df[['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'dpa_movil']].copy()
    df_export.columns = ['SKU', 'Mes', 'Demanda Real', 'Demanda Limpia', 'Forecast', 'DPA Móvil']
    return df_export.to_csv(index=False).encode('utf-8')

csv_forecast = generar_csv_forecast(df_forecast)
st.download_button("📥 Descargar Forecast Calculado", data=csv_forecast, file_name="forecast.csv", mime="text/csv")
