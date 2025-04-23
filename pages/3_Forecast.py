import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from modules.forecast_engine import forecast_engine, generar_comparativa_forecasts
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

# --- Forecast principal ---
if 'forecast' not in st.session_state:
    if os.path.exists("data/forecast.csv"):
        os.remove("data/forecast.csv")
    df_forecast = forecast_engine(df_demanda, lead_time_meses=4)
    df_forecast.to_csv("data/forecast.csv", index=False)
    st.session_state['forecast'] = df_forecast
else:
    df_forecast = st.session_state['forecast']

# --- Comparativa por métodos ---
if 'forecast_comparativa' not in st.session_state:
    df_comparativa = generar_comparativa_forecasts(df_demanda, horizonte_meses=6)
    st.session_state['forecast_comparativa'] = df_comparativa
else:
    df_comparativa = st.session_state['forecast_comparativa']

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

# --- Demanda Limpia (barras) con texto horizontal fuera de la barra ---
fig.add_trace(go.Bar(
    x=df_plot['mes_label'],
    y=df_plot['demanda_limpia'],
    name='Demanda Limpia',
    marker_color='royalblue',
    text=df_plot['demanda_limpia'],
    textposition='outside',     # Coloca los textos fuera de la barra
    textangle=0,                # Fuerza orientación horizontal
    cliponaxis=False
))

# --- Forecast proyectado (línea roja) ---
df_forecast_total = df_plot[df_plot['tipo_mes'] != 'histórico']
fig.add_trace(go.Scatter(
    x=df_forecast_total['mes_label'],
    y=df_forecast_total['forecast'],
    name='Forecast proyectado',
    mode='lines+markers+text',
    line=dict(color='crimson', width=3),
    marker=dict(size=8),
    text=df_forecast_total['forecast'],
    textposition='top center'
))

fig.update_layout(
    barmode='overlay',
    xaxis_title='Mes',
    yaxis_title='Unidades',
    yaxis=dict(rangemode='tozero'),
    font_family='Poppins, sans-serif',
    xaxis_tickangle=45,
    height=500,
    margin=dict(l=40, r=40, t=60, b=80),
    legend_title='Tipo',
    legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='center', x=0.5)
)

st.markdown(
    f'<h1 style="font-size: 22px; margin-bottom: 2px; font-weight: 400; text-align: center;">📊 Gráfico: Demanda Limpia y Forecast para SKU: {sku_seleccionado}</h1>',
    unsafe_allow_html=True
)
st.plotly_chart(fig, use_container_width=True)


# --- Comparativa de métodos en columnas ---

st.markdown(
    f'<h1 style="font-size: 22px; margin-top: 40px; margin-bottom: 10px; font-weight: 500; text-align: center;">📊 Comparativa de Forecast por Método</h1>',
    unsafe_allow_html=True
)

# Asegurarse de que forecast_comparativa esté disponible
if 'forecast_comparativa' not in st.session_state:
    st.error("No se encontró la tabla comparativa. Asegúrate de ejecutar el forecast nuevamente.")
else:
    df_comparativa = st.session_state['forecast_comparativa']
    
    # Filtrar solo para el SKU seleccionado
    df_comp_sku = df_comparativa[df_comparativa['sku'] == sku_seleccionado].copy()

    if df_comp_sku.empty:
        st.warning("No hay datos disponibles para este SKU en la tabla comparativa.")
    else:
        st.dataframe(df_comp_sku, use_container_width=True)

        # --- Descargar tabla comparativa ---
        csv_comparativa = df_comp_sku.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Comparativa por Método", data=csv_comparativa, file_name=f"comparativa_forecast_{sku_seleccionado}.csv", mime="text/csv")


# --- Descargar CSV ---
def generar_csv_forecast(df):
    df_export = df[['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'dpa_movil', 'metodo_forecast']].copy()
    df_export.columns = ['SKU', 'Mes', 'Demanda Real', 'Demanda Limpia', 'Forecast', 'DPA Móvil', 'Método Forecast']
    return df_export.to_csv(index=False).encode('utf-8')

csv_forecast = generar_csv_forecast(df_forecast)
st.download_button("📥 Descargar Forecast Calculado", data=csv_forecast, file_name="forecast.csv", mime="text/csv")
