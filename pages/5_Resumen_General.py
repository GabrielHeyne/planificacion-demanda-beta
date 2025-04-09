import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from modules.resumen_utils import consolidar_historico_stock, consolidar_proyeccion_futura

# --- Estilos personalizados ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Manrope:wght@600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 700 !important;
    }

    .stSelectbox label, .stDownloadButton > button, .stMetricLabel, .stMetricValue {
        font-family: 'Inter', sans-serif !important;
    }

    .stButton > button {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 600;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    .element-container h3 {
        font-size: 16px !important;
        text-align: center !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("## Resumen General de Indicadores")

# --- Validaciones ---
requisitos = ['forecast', 'demanda_limpia', 'stock_historico', 'stock_actual']
for r in requisitos:
    if r not in st.session_state or st.session_state[r] is None:
        st.warning(f"⚠️ Faltan datos requeridos: {r}. Ve al módulo correspondiente.")
        st.stop()

# --- Carga de datos ---
df_demand = st.session_state['demanda_limpia'].copy()
df_forecast = st.session_state['forecast'].copy()
df_stock_hist = st.session_state['stock_historico'].copy()
df_stock_actual = st.session_state['stock_actual'].copy()
df_repos = st.session_state.get('reposiciones', pd.DataFrame(columns=['sku', 'fecha', 'cantidad']))
df_maestro = st.session_state.get('maestro', pd.DataFrame())

# --- Filtro SKU ---
sku_options = sorted(set(df_demand['sku'].unique()) | set(df_forecast['sku'].unique()))
sku_select = st.selectbox("🔍 Filtrar por SKU", options=['Todos'] + sku_options)

# --- Consolidar datos ---
@st.cache_data
def calcular_resumen(df_demand, df_forecast, df_stock_actual, df_repos, df_maestro):
    df_hist = consolidar_historico_stock(df_demand, df_maestro)
    df_futuro = consolidar_proyeccion_futura(df_forecast, df_stock_actual, df_repos, df_maestro)
    return df_hist, df_futuro

df_hist, df_futuro = calcular_resumen(df_demand, df_forecast, df_stock_actual, df_repos, df_maestro)
st.session_state['proyeccion_stock'] = df_futuro

# --- Filtrar por SKU ---
if sku_select != 'Todos':
    df_hist = df_hist[df_hist['sku'] == sku_select]
    df_futuro = df_futuro[df_futuro['sku'] == sku_select]
    df_demand = df_demand[df_demand['sku'] == sku_select]
    df_stock_hist = df_stock_hist[df_stock_hist['sku'] == sku_select]
    df_forecast = df_forecast[df_forecast['sku'] == sku_select]
    df_stock_actual = df_stock_actual[df_stock_actual['sku'] == sku_select]
    df_repos = df_repos[df_repos['sku'] == sku_select]

# --- Detectar último mes completo con al menos 4 semanas ---
df_demand['fecha'] = pd.to_datetime(df_demand['fecha'])
df_demand['mes'] = df_demand['fecha'].dt.to_period('M').dt.to_timestamp()
df_demand['semana'] = df_demand['fecha'].dt.isocalendar().week

conteo_semanas = df_demand.groupby('mes')['semana'].nunique().reset_index(name='num_semanas')
meses_completos = conteo_semanas[conteo_semanas['num_semanas'] >= 4]['mes']
if meses_completos.empty:
    st.warning("⚠️ No se encontraron meses completos con al menos 4 semanas de demanda.")
    st.stop()
ultimo_mes_completo = meses_completos.max()
mes_siguiente = ultimo_mes_completo + pd.DateOffset(months=1)

# --- Filtrar datos históricos últimos 12 meses hasta el último mes completo ---
fecha_max_hist = ultimo_mes_completo
fecha_min_hist = fecha_max_hist - pd.DateOffset(months=12)

df_hist['mes'] = pd.to_datetime(df_hist['mes'])
df_hist = df_hist[(df_hist['mes'] >= fecha_min_hist) & (df_hist['mes'] <= fecha_max_hist)]

df_demand = df_demand[(df_demand['mes'] >= fecha_min_hist) & (df_demand['mes'] <= fecha_max_hist)]

df_stock_hist['fecha'] = pd.to_datetime(df_stock_hist['fecha'])
df_stock_hist['mes'] = df_stock_hist['fecha'].dt.to_period('M').dt.to_timestamp()
df_stock_hist = df_stock_hist[(df_stock_hist['mes'] >= fecha_min_hist) & (df_stock_hist['mes'] <= fecha_max_hist)]

# --- KPIs ---
total_stock = int(df_stock_actual['stock'].sum())
unidades_vendidas_12m = int(df_demand['demanda'].sum())
unidades_en_camino = int(df_repos['cantidad'].sum())

df_demand_ventas = df_demand.merge(df_maestro[['sku', 'precio_venta']], on='sku', how='left')
df_demand_ventas['venta_real_euros'] = df_demand_ventas['demanda'] * df_demand_ventas['precio_venta']
facturacion_12m = int(df_demand_ventas['venta_real_euros'].sum())

unidades_perdidas_hist = int(df_hist['unidades_perdidas'].sum())
perdidas_hist_euros = int(df_hist['valor_perdido_euros'].sum())

# --- Tasa de quiebre ---
tasa_quiebre = 0
if (unidades_perdidas_hist + unidades_vendidas_12m) > 0:
    tasa_quiebre = (unidades_perdidas_hist / (unidades_perdidas_hist + unidades_vendidas_12m)) * 100

# --- Demanda promedio mensual últimos 3 meses completos ---
meses_validos = meses_completos.sort_values().iloc[-3:]
df_demand_3m = df_demand[df_demand['mes'].isin(meses_validos)]
demanda_promedio_mensual = int(df_demand_3m.groupby('mes')['demanda'].sum().mean())

# --- KPIs visuales (alineados) ---
col1, col2, col3, col4 = st.columns(4)
col6, col7, col8, col9 = st.columns(4)

col1.metric("Existencias Totales", f"{total_stock:,}")
col2.metric("Unidades Vendidas (12M)", f"{unidades_vendidas_12m:,}")
col3.metric("Facturación (12M)", f"€ {facturacion_12m:,}")
col4.metric("Unidades en Camino", f"{unidades_en_camino:,}")

col6.metric("Unidades Perdidas (Histórico)", f"{unidades_perdidas_hist:,}")
col7.metric("Venta Perdida (Histórico)", f"€ {perdidas_hist_euros:,}")
col8.metric("Demanda Prom. Mensual (3M)", f"{demanda_promedio_mensual:,}")
col9.metric("Tasa de Quiebre", f"{tasa_quiebre:.1f}%")

# --- Gráfico 1: Demanda real vs limpia ---
df_mensual = df_demand.groupby('mes').agg(
    demanda=('demanda', 'sum'),
    demanda_limpia=('demanda_sin_outlier', 'sum')
).reset_index()

fig_demand = go.Figure()
fig_demand.add_trace(go.Scatter(x=df_mensual['mes'], y=df_mensual['demanda'], name="Demanda Real", mode="lines+markers"))
fig_demand.add_trace(go.Scatter(x=df_mensual['mes'], y=df_mensual['demanda_limpia'], name="Demanda Limpia", mode="lines+markers"))
fig_demand.update_layout(
    height=400,
    xaxis_title="Mes",
    yaxis_title="Unidades",
    xaxis_tickangle=-45,
    yaxis=dict(rangemode="tozero"),
    legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="center", x=0.5),
    margin=dict(t=80, b=40)
)

# --- Gráfico 2: Demanda histórica vs forecast ---
df_demanda_hist = df_mensual[df_mensual['mes'] <= ultimo_mes_completo][['mes', 'demanda_limpia']]
df_forecast['mes'] = pd.to_datetime(df_forecast['mes'])
df_forecast_mes = df_forecast[df_forecast['mes'] >= mes_siguiente].groupby('mes').agg(forecast=('forecast', 'sum')).reset_index()

df_mix = pd.concat([
    df_demanda_hist.rename(columns={'demanda_limpia': 'valor'}).assign(tipo='Demanda'),
    df_forecast_mes.rename(columns={'forecast': 'valor'}).assign(tipo='Previsión')
])

fig_mix = px.line(df_mix, x='mes', y='valor', color='tipo', markers=True, labels={'valor': 'Unidades', 'mes': 'Mes', 'tipo': ''})
fig_mix.update_layout(
    height=400,
    yaxis=dict(rangemode="tozero"),
    xaxis_tickangle=-45,
    legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="center", x=0.5),
    margin=dict(t=80, b=40)
)

# --- Gráfico 3: Stock histórico mensual ---
df_stock_mes = df_stock_hist.groupby('mes')['stock'].sum().reset_index()
fig_stock = px.line(df_stock_mes, x='mes', y='stock', markers=True)
fig_stock.update_layout(
    height=420,
    xaxis_title="Mes",
    yaxis_title="Unidades",
    yaxis=dict(rangemode="tozero"),
    xaxis_tickangle=-45,
    margin=dict(t=80, b=40)
)

# --- Gráfico 4: Stock Proyectado vs Pérdida Estimada (€) ---
df_stock_plot = df_futuro.groupby('mes').agg(
    stock_final=('stock_final_mes', 'sum'),
    perdida_euros=('perdida_proyectada_euros', 'sum')
).reset_index()

fig_stock_loss = go.Figure()
fig_stock_loss.add_trace(go.Bar(
    x=df_stock_plot['mes'],
    y=df_stock_plot['perdida_euros'],
    name="Pérdida Estimada (€)",
    marker_color='crimson',
    yaxis='y2',
    opacity=0.85
))
fig_stock_loss.add_trace(go.Scatter(
    x=df_stock_plot['mes'],
    y=df_stock_plot['stock_final'],
    name="Stock Final Proyectado",
    mode="lines+markers",
    line=dict(color='royalblue', width=3),
    yaxis='y'
))
fig_stock_loss.update_layout(
    height=420,
    xaxis_title="Mes",
    xaxis_tickangle=-45,
    yaxis=dict(title="Unidades", rangemode="tozero"),
    yaxis2=dict(title="Pérdida (€)", overlaying="y", side="right", rangemode="tozero"),
    legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="center", x=0.5),
    margin=dict(t=80, b=40)
)

# --- Gráfico 5: Pérdidas Históricas Mensuales (€) ---
df_perdidas_hist = df_hist.groupby('mes')['valor_perdido_euros'].sum().reset_index()
fig_perdidas_hist = px.bar(df_perdidas_hist, x='mes', y='valor_perdido_euros', labels={'mes': 'Mes', 'valor_perdido_euros': '€ Pérdidos'})
fig_perdidas_hist.update_layout(
    height=420,
    xaxis_tickangle=-45,
    yaxis=dict(rangemode="tozero"),
    margin=dict(t=80, b=40)
)

# --- Mostrar gráficos ---
colg1, colg2 = st.columns(2)
with colg1:
    st.subheader("📈 Demanda Real vs Limpia")
    st.plotly_chart(fig_demand, use_container_width=True)
with colg2:
    st.subheader("📉 Demanda Histórica vs Pronóstico")
    st.plotly_chart(fig_mix, use_container_width=True)
colg3, colg4 = st.columns(2)
with colg3:
    st.subheader("📦 Stock Histórico Mensual")
    st.plotly_chart(fig_stock, use_container_width=True)
with colg4:
    st.subheader("📦 Stock Proyectado vs Pérdida Estimada (€)")
    st.plotly_chart(fig_stock_loss, use_container_width=True)

st.subheader("💸 Pérdidas Históricas Mensuales (€)")
st.plotly_chart(fig_perdidas_hist, use_container_width=True)

# --- Descargas ---
st.markdown("### 📥 Descargar reportes consolidados")
col1, col2 = st.columns(2)
with col1:
    st.download_button(
        label="📄 Descargar Histórico Consolidado",
        data=df_hist.to_csv(index=False).encode('utf-8'),
        file_name="resumen_historico.csv",
        mime="text/csv"
    )
with col2:
    st.download_button(
        label="📄 Descargar Proyección Futura",
        data=df_futuro.to_csv(index=False).encode('utf-8'),
        file_name="proyeccion_futura.csv",
        mime="text/csv"
    )

