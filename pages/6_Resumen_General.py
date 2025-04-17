import streamlit as st
from utils import render_logo_sidebar  # Importa la función desde utils.py
from PIL import Image
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
from modules.resumen_utils import consolidar_historico_stock, consolidar_proyeccion_futura



# --- Configuración de página ---
st.set_page_config(page_title="Resumen General", layout="wide")

# --- Cargar CSS ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cargar los estilos
load_css()

# Llamar a la función para renderizar el logo en la barra lateral
render_logo_sidebar()  # Este es el cambio para mostrar el logo

# --- Validaciones para asegurarse que los datos requeridos estén disponibles ---
requisitos = ['forecast', 'demanda_limpia', 'stock_historico', 'stock_actual']
for r in requisitos:
    if r not in st.session_state or st.session_state[r] is None:
        st.warning(f"⚠️ Faltan datos requeridos: {r}. Ve al módulo correspondiente.")
        st.stop()

# --- Carga de los datos desde session_state ---
df_demand = st.session_state['demanda_limpia'].copy()
df_forecast = st.session_state['forecast'].copy()
df_stock_hist = st.session_state['stock_historico'].copy()
df_stock_actual = st.session_state['stock_actual'].copy()
df_repos = st.session_state.get('reposiciones', pd.DataFrame(columns=['sku', 'fecha', 'cantidad']))
df_maestro = st.session_state.get('maestro', pd.DataFrame())

# --- Filtro de SKU ---
sku_options = sorted(set(df_demand['sku'].unique()) | set(df_forecast['sku'].unique()))
sku_select = st.selectbox("🔍 Filtrar por SKU", options=['Todos'] + sku_options)

# --- Consolidación de los datos ---
@st.cache_data
def calcular_resumen(df_demand, df_forecast, df_stock_actual, df_repos, df_maestro):
    # Consolida el historial de stock y la proyección futura
    df_hist = consolidar_historico_stock(df_demand, df_maestro)
    df_futuro = consolidar_proyeccion_futura(df_forecast, df_stock_actual, df_repos, df_maestro)
    return df_hist, df_futuro

# Calcular los datos consolidados
df_hist, df_futuro = calcular_resumen(df_demand, df_forecast, df_stock_actual, df_repos, df_maestro)
st.session_state['proyeccion_stock'] = df_futuro

# --- Filtrar los datos por SKU si se ha seleccionado uno ---
if sku_select != 'Todos':
    df_hist = df_hist[df_hist['sku'] == sku_select]
    df_futuro = df_futuro[df_futuro['sku'] == sku_select]
    df_demand = df_demand[df_demand['sku'] == sku_select]
    df_stock_hist = df_stock_hist[df_stock_hist['sku'] == sku_select]
    df_forecast = df_forecast[df_forecast['sku'] == sku_select]
    df_stock_actual = df_stock_actual[df_stock_actual['sku'] == sku_select]
    df_repos = df_repos[df_repos['sku'] == sku_select]

# --- Detectar el último mes completo con al menos 4 semanas ---
df_demand['fecha'] = pd.to_datetime(df_demand['fecha'])
df_demand['mes'] = df_demand['fecha'].dt.to_period('M').dt.to_timestamp()
df_demand['semana'] = df_demand['fecha'].dt.isocalendar().week

# Contar las semanas por mes
conteo_semanas = df_demand.groupby('mes')['semana'].nunique().reset_index(name='num_semanas')
meses_completos = conteo_semanas[conteo_semanas['num_semanas'] >= 4]['mes']
if meses_completos.empty:
    st.warning("⚠️ No se encontraron meses completos con al menos 4 semanas de demanda.")
    st.stop()
ultimo_mes_completo = meses_completos.max()
mes_siguiente = ultimo_mes_completo + pd.DateOffset(months=1)

# --- Filtrar datos históricos para los últimos 12 meses hasta el último mes completo ---
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

# Merge para obtener ventas en euros
df_demand_ventas = df_demand.merge(df_maestro[['sku', 'precio_venta']], on='sku', how='left')
df_demand_ventas['venta_real_euros'] = df_demand_ventas['demanda'] * df_demand_ventas['precio_venta']
facturacion_12m = int(df_demand_ventas['venta_real_euros'].sum())

# Unidades perdidas históricas y pérdidas en euros
unidades_perdidas_hist = int(df_hist['unidades_perdidas'].sum())
perdidas_hist_euros = int(df_hist['valor_perdido_euros'].sum())

# --- Cálculo de la tasa de quiebre ---
tasa_quiebre = 0
if (unidades_perdidas_hist + unidades_vendidas_12m) > 0:
    tasa_quiebre = (unidades_perdidas_hist / (unidades_perdidas_hist + unidades_vendidas_12m)) * 100

# --- Demanda promedio mensual últimos 3 meses completos ---
meses_validos = meses_completos.sort_values().iloc[-3:]
df_demand_3m = df_demand[df_demand['mes'].isin(meses_validos)]
demanda_promedio_mensual = int(df_demand_3m.groupby('mes')['demanda'].sum().mean())

# --- KPIs visuales (alineados) ---
kpi_style = """
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
        box-shadow: none; /* Sin sombra */
    ">
        <div style="font-size:18px; font-weight:500; height:36px; display:flex; align-items:center; justify-content:center; gap:6px;">
            {label}
        </div>
        <div style="font-size:36px; font-weight:400;">{value}</div>  <!-- Aumentar tamaño de letra y quitar negritas en el valor -->
    </div>
"""

# Fila 1 de KPIs
col1, col2, col3, col4 = st.columns(4)
col1.markdown(kpi_style.format(icon="📦", label="Stock Actual", value=f"{total_stock:,}"), unsafe_allow_html=True)
col2.markdown(kpi_style.format(icon="🛒", label="Unidades Vendidas (12M)", value=f"{unidades_vendidas_12m:,}"), unsafe_allow_html=True)
col3.markdown(kpi_style.format(icon="💰", label="Facturación (12M)", value=f"€ {facturacion_12m:,}"), unsafe_allow_html=True)
col4.markdown(kpi_style.format(icon="🚚", label="Unidades en Camino", value=f"{unidades_en_camino:,}"), unsafe_allow_html=True)

# Separación
st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

# Fila 2 de KPIs
col5, col6, col7, col8 = st.columns(4)
col5.markdown(kpi_style.format(icon="❌", label="Unidades Perdidas (12M)", value=f"{unidades_perdidas_hist:,}"), unsafe_allow_html=True)
col6.markdown(kpi_style.format(icon="📉", label="Venta Perdida (12M)", value=f"€ {perdidas_hist_euros:,}"), unsafe_allow_html=True)
col7.markdown(kpi_style.format(icon="📊", label="Demanda Mensual (3M)", value=f"{demanda_promedio_mensual:,}"), unsafe_allow_html=True)
col8.markdown(kpi_style.format(icon="⚠️", label="Tasa de Quiebre", value=f"{tasa_quiebre:.1f}%"), unsafe_allow_html=True)

# --- Espacio visual entre KPIs y gráficos ---
st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)


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
    margin=dict(t=30, b=40)
)

# --- Mostrar gráficos ---
colg1, colg2 = st.columns(2)

with colg1:
    with st.container():
        st.markdown("""<div style="background-color:#F7F7F7; padding:0px 0px; border-radius:16px; width:100%; text-align:center;">
                        <h4>📈 Demanda Real vs Limpia</h4></div>""", unsafe_allow_html=True)
        st.plotly_chart(fig_demand, use_container_width=True)

with colg2:
    with st.container():
        st.markdown("""<div style="background-color:#F7F7F7; padding:0px 0px; border-radius:16px; width:100%; text-align:center;">
                        <h4>📈 Demanda vs Forecast</h4></div>""", unsafe_allow_html=True)
        st.plotly_chart(fig_mix, use_container_width=True)

colg3, colg4 = st.columns(2)

with colg3:
    with st.container():
        st.markdown("""<div style="background-color:#F7F7F7; padding:0px 0px; border-radius:16px; width:100%; text-align:center;">
                        <h4>📦 Stock Histórico Mensual</h4></div>""", unsafe_allow_html=True)
        st.plotly_chart(fig_stock, use_container_width=True)

with colg4:
    with st.container():
        st.markdown("""<div style="background-color:#F7F7F7; padding:0px 0px; border-radius:16px; width:100%; text-align:center;">
                        <h4>📦 Stock Proyectado vs Pérdida Estimada (€)</h4></div>""", unsafe_allow_html=True)
        st.plotly_chart(fig_stock_loss, use_container_width=True)

with st.container():
    st.markdown("""<div style="background-color:#F7F7F7; padding:0px 0px; border-radius:16px; width:100%; text-align:center;">
                    <h4>💸 Pérdidas Históricas Mensuales (€)</h4></div>""", unsafe_allow_html=True)
    st.plotly_chart(fig_perdidas_hist, use_container_width=True)


# --- Rankings corregidos --- 
# Calcular promedio mensual real
df_demand_ventas['mes'] = pd.to_datetime(df_demand_ventas['fecha']).dt.to_period('M').dt.to_timestamp()
df_demand_ventas_mensual = df_demand_ventas.groupby(['sku', 'mes']).agg(
    demanda=('demanda', 'sum'),
    pxq=('venta_real_euros', 'sum')
).reset_index()

# Agrupación para rankings
df_top = df_demand_ventas_mensual.groupby('sku').agg(
    demanda_mensual=('demanda', 'mean'),
    pxq=('pxq', 'sum')
).reset_index()

# Pérdidas por SKU
perdidas_por_sku = df_hist.groupby('sku').agg(
    unidades_perdidas=('unidades_perdidas', 'sum'),
    perdida_euros=('valor_perdido_euros', 'sum')
).reset_index()

# --- Rankings finales y merge ---
df_rank_loss = perdidas_por_sku.merge(df_top[['sku', 'demanda_mensual']], on='sku', how='left')
df_rank_loss = df_rank_loss.sort_values(by='perdida_euros', ascending=False).head(10).reset_index(drop=True)
df_rank_loss.insert(0, 'Ranking', range(1, len(df_rank_loss) + 1))

df_rank_sales = df_top.sort_values(by='pxq', ascending=False).head(10).reset_index(drop=True)
df_rank_sales.insert(0, 'Ranking', range(1, len(df_rank_sales) + 1))

# --- Mostrar tablas con estilo centrado y sin decimales --- 
colA, colB = st.columns(2)

with colA:
    st.markdown("<h4 style='text-align: center;'>🔻 Top 10 SKUs con más pérdidas<br>(últimos 12 meses)</h4>", unsafe_allow_html=True)
    st.dataframe(
        df_rank_loss[['Ranking', 'sku', 'unidades_perdidas', 'perdida_euros']].rename(columns={
            'sku': 'SKU', 'unidades_perdidas': 'Unidades Perdidas', 'perdida_euros': 'Pérdida (€)'
        }).astype({'Unidades Perdidas': int, 'Pérdida (€)': int}),
        use_container_width=True,
        hide_index=True
    )

with colB:
    st.markdown("<h4 style='text-align: center;'>🏆 Top 10 SKUs con más ventas<br>&nbsp;</h4>", unsafe_allow_html=True)
    st.dataframe(
        df_rank_sales[['Ranking', 'sku', 'demanda_mensual', 'pxq']].rename(columns={
            'sku': 'SKU', 'demanda_mensual': 'Demanda Mensual', 'pxq': 'PxQ (€)'
        }).astype({'Demanda Mensual': int, 'PxQ (€)': int}),
        use_container_width=True,
        hide_index=True
    )

# --- Descargar reportes centrado con columnas --- 
st.markdown("""
    <div style="text-align: center;">
        <h4 style="margin-bottom: 1.5rem;">📥 Descargar reportes consolidados</h4>
    </div>
""", unsafe_allow_html=True)

# Crear columnas con espacio vacío a los lados para centrar
col_empty1, col_btn1, col_btn2, col_empty2 = st.columns([1, 2, 2, 1])

with col_btn1:
    st.download_button(
        label="📄 Descargar Histórico Consolidado",
        data=df_hist.to_csv(index=False).encode('utf-8'),
        file_name="resumen_historico.csv",
        mime="text/csv",
        key="btn_descarga_hist"
    )

with col_btn2:
    st.download_button(
        label="📄 Descargar Proyección Futura",
        data=df_futuro.to_csv(index=False).encode('utf-8'),
        file_name="proyeccion_futura.csv",
        mime="text/csv",
        key="btn_descarga_fut"
    )
