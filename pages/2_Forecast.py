import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.render_logo_sidebar import render_logo_sidebar
from utils.filtros import aplicar_filtro_sku

# --- Configuración general ---
st.set_page_config(layout="wide")

# --- Cargar estilos y logo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()
render_logo_sidebar()

# --- Validación de datos ---
if "demanda_limpia" not in st.session_state or "forecast" not in st.session_state:
    st.warning("⚠️ Aún no se han cargado los datos necesarios. Vuelve a la página de Inicio y presiona 'Comenzar planificación'.")
    st.stop()

# --- Cargar datos desde session_state ---
df_demanda = st.session_state["demanda_limpia"]
df_forecast = st.session_state["forecast"]
df_comparativa = st.session_state.get("forecast_comparativa")

# --- Aplicar filtro por SKU ---
df_filtrado, sku_seleccionado = aplicar_filtro_sku(df_forecast, incluir_todos=False)
df_filtrado['mes'] = pd.to_datetime(df_filtrado['mes'])



# --- KPIs ---
ultimo_mes_con_demandas = df_filtrado[df_filtrado['demanda_limpia'] > 0]['mes'].max()
df_ultimos_6_meses = df_filtrado[df_filtrado['mes'] <= ultimo_mes_con_demandas].tail(6)
demanda_promedio_6 = int(round(df_ultimos_6_meses['demanda_limpia'].mean())) if len(df_ultimos_6_meses) > 0 else 0

df_forecast_futuro = df_filtrado[df_filtrado['tipo_mes'] == 'proyección']
forecast_proyectado = int(round(df_forecast_futuro['forecast'].mean())) if not df_forecast_futuro.empty else 0
forecast_con_margen = int(round(df_forecast_futuro['forecast_up'].mean())) if 'forecast_up' in df_forecast_futuro.columns and not df_forecast_futuro['forecast_up'].isna().all() else 0

df_backtest = df_filtrado[df_filtrado['tipo_mes'] == 'backtest'].sort_values('mes')
dpa_valores = df_backtest['dpa_movil'].dropna()
dpa_resumen = round(dpa_valores.iloc[-3:].mean(), 3) if not dpa_valores.empty else "–"

# --- KPIs visuales ---
kpi_template = """
<div style="background-color:#ffffff;padding:16px;border-radius:12px;text-align:center;
height:110px;display:flex;flex-direction:column;justify-content:space-between;
margin: 10px;border: 1px solid #B0B0B0;box-shadow: none;">
    <div style="font-size:14px; font-weight:500; margin-bottom:6px;">{label}</div>
    <div style="font-size:30px;">{value}</div>
</div>
"""

col1, col2, col3, col4 = st.columns(4)
col1.markdown(kpi_template.format(label="Demanda Limpia (Últ. 6 meses)", value=f"{demanda_promedio_6} unidades"), unsafe_allow_html=True)
col2.markdown(kpi_template.format(label="Forecast Proyectado", value=f"{forecast_proyectado} unidades"), unsafe_allow_html=True)
col3.markdown(kpi_template.format(label="Forecast con Margen", value=f"{forecast_con_margen} unidades"), unsafe_allow_html=True)
col4.markdown(kpi_template.format(label="DPA Móvil (Backtest)", value=f"{dpa_resumen:.1%}" if isinstance(dpa_resumen, float) else dpa_resumen), unsafe_allow_html=True)

# --- Gráfico de forecast ---
df_plot = df_filtrado.sort_values('mes').copy()
df_plot['mes_label'] = df_plot['mes'].dt.strftime('%b %Y')
df_forecast_line = df_plot[df_plot['tipo_mes'] != 'histórico'].tail(6)

fig = go.Figure()
fig.add_trace(go.Bar(
    x=df_plot['mes_label'],
    y=df_plot['demanda_limpia'],
    name='Demanda Limpia',
    marker_color='royalblue',
    text=df_plot['demanda_limpia'],
    textposition='outside',
    textangle=0,
    cliponaxis=False
))
fig.add_trace(go.Scatter(
    x=df_forecast_line['mes_label'],
    y=df_forecast_line['forecast'],
    name='Forecast proyectado',
    mode='lines+markers+text',
    line=dict(color='crimson', width=3),
    marker=dict(size=8),
    text=df_forecast_line['forecast'],
    textposition='top center'
))
df_forecast_margin = df_forecast_line[df_forecast_line['tipo_mes'] == 'proyección']
if not df_forecast_margin.empty:
    fig.add_trace(go.Scatter(
        x=df_forecast_margin['mes_label'],
        y=df_forecast_margin['forecast_up'],
        name='Forecast con Margen',
        mode='lines+markers+text',
        line=dict(color='orange', width=2, dash='dot'),
        marker=dict(size=8),
        text=df_forecast_margin['forecast_up'],
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

# --- Comparativa de métodos ---
st.markdown(
    f'<h1 style="font-size: 22px; margin-top: 40px; margin-bottom: 10px; font-weight: 500; text-align: center;">📊 Comparativa de Forecast por Método</h1>',
    unsafe_allow_html=True
)

if df_comparativa is not None:
    df_comp_sku = df_comparativa[df_comparativa['sku'] == sku_seleccionado]
    if df_comp_sku.empty:
        st.warning("No hay datos disponibles para este SKU en la tabla comparativa.")
    else:
        st.dataframe(df_comp_sku, use_container_width=True)
        csv_comparativa = df_comp_sku.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Comparativa por Método", data=csv_comparativa, file_name=f"comparativa_forecast_{sku_seleccionado}.csv", mime="text/csv")
else:
    st.warning("No se ha encontrado la tabla comparativa de forecast.")

# --- Tabla Detallada del Forecast ---
st.markdown(
    f'<h1 style="font-size: 22px; margin-top: 40px; margin-bottom: 10px; font-weight: 500; text-align: center;">📋 Detalle por Mes del Forecast</h1>',
    unsafe_allow_html=True
)

df_tabla = df_filtrado.copy()
df_tabla['dpa_movil'] = df_tabla.apply(
    lambda row: f"{row['dpa_movil']:.1%}" if pd.notnull(row['dpa_movil']) and row['tipo_mes'] == 'backtest' else "–",
    axis=1
)

columnas = ['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'forecast_up', 'tipo_mes', 'dpa_movil']
df_tabla = df_tabla[columnas]
df_tabla.columns = ['SKU', 'Mes', 'Demanda Real', 'Demanda Limpia', 'Forecast', 'Forecast con Margen', 'Tipo de Mes', 'DPA Móvil']
st.dataframe(df_tabla, use_container_width=True)

# --- Descargar forecast ---
def generar_csv_forecast(df):
    df_export = df[['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'forecast_up', 'dpa_movil', 'metodo_forecast']].copy()
    df_export.columns = ['SKU', 'Mes', 'Demanda Real', 'Demanda Limpia', 'Forecast', 'Forecast con Margen', 'DPA Móvil', 'Método Forecast']
    return df_export.to_csv(index=False).encode('utf-8')

csv_forecast = generar_csv_forecast(df_forecast)
st.download_button("📥 Descargar Forecast Calculado", data=csv_forecast, file_name="forecast.csv", mime="text/csv")
