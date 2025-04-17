import streamlit as st
from utils import render_logo_sidebar  # Importa la función desde utils.py
import pandas as pd
import plotly.express as px
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

# Cargar CSS
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cargar el CSS
load_css()

# Llamar a la función para renderizar el logo en la barra lateral
render_logo_sidebar()  # Este es el cambio para mostrar el logo

# Usar las clases CSS para los títulos
st.markdown('<h1 class="titulo-principal">📈 DEMANDA TOTAL Y QUIEBRES</h1>', unsafe_allow_html=True)
st.markdown('<h2 class="subtitulo">Demanda Real y Limpia por SKU</h2>', unsafe_allow_html=True)

# --- Cargar demanda limpia desde session_state ---
@st.cache_data
def cargar_demanda():
    return st.session_state.get('demanda_limpia', pd.DataFrame())

df = cargar_demanda()

if df.empty:
    st.warning("⚠️ No se han cargado los datos limpios. Ve al menú 'Carga Archivos' para hacerlo.")
    st.stop()

# --- Preprocesamiento básico ---
df['fecha'] = pd.to_datetime(df['fecha'])
df['semana'] = df['fecha'].dt.to_period('W').apply(lambda r: r.start_time)

# --- Filtro por SKU ---
skus = sorted(df['sku'].unique())
skus.insert(0, "TODOS")
sku_seleccionado = st.selectbox("Selecciona un SKU", skus)
df_filtrado = df if sku_seleccionado == "TODOS" else df[df['sku'] == sku_seleccionado]

# --- Filtro de fechas ---
fecha_min = df_filtrado['fecha'].min().date()
fecha_max = df_filtrado['fecha'].max().date()
fecha_min_defecto = max(fecha_min, (fecha_max - relativedelta(months=12)))
rango_fecha = st.date_input("Selecciona el rango de fechas", value=(fecha_min_defecto, fecha_max), min_value=fecha_min, max_value=fecha_max)
fecha_inicio = pd.to_datetime(rango_fecha[0])
fecha_fin = pd.to_datetime(rango_fecha[1])
df_filtrado = df_filtrado[(df_filtrado['fecha'] >= fecha_inicio) & (df_filtrado['fecha'] <= fecha_fin)]

# --- KPIs y quiebres --- 
df_quiebre = df_filtrado.copy()

# Calcular el quiebre de stock por cada SKU
df_quiebre['quiebre_stock'] = (df_quiebre['demanda'] == 0) & (df_quiebre['demanda_sin_outlier'] > 0)

# Si el filtro es "TODOS", calculamos el porcentaje promedio de quiebre de todos los SKUs
if sku_seleccionado == "TODOS":
    # Para cada SKU, calculamos el porcentaje de quiebre
    quiebre_por_sku = df_quiebre.groupby('sku').apply(lambda x: (x['quiebre_stock'].sum() / len(x)) * 100)
    # Promediamos el porcentaje de quiebre de todos los SKUs y limitamos a un decimal
    porcentaje_quiebre = round(quiebre_por_sku.mean(), 1)
else:
    # Cuando no se selecciona "TODOS", calculamos el porcentaje de quiebre solo para el SKU seleccionado
    total_semanas = df_quiebre['semana'].nunique()
    quiebre_semanas = df_quiebre[df_quiebre['quiebre_stock']].groupby('semana').ngroup().nunique()
    porcentaje_quiebre = round((quiebre_semanas / total_semanas) * 100, 1) if total_semanas > 0 else 0

# Calcular unidades perdidas
df_quiebre['unidades_perdidas'] = df_quiebre.apply(lambda row: row['demanda_sin_outlier'] if row['quiebre_stock'] else 0, axis=1)
total_unidades_perdidas = int(df_quiebre['unidades_perdidas'].sum())
demanda_real_total = int(df_filtrado['demanda'].sum())
demanda_limpia_total = int(df_filtrado['demanda_sin_outlier'].sum())

# --- KPIs con nuevo diseño ---
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
        box-shadow: none; /* Sin sombra */
    ">
    <div style="font-size:14px; font-weight:500; margin-bottom:6px;">{label}</div>
    <div style="font-size:30px;">{value}</div>
</div>
"""

col1, col2, col3, col4 = st.columns(4)
col1.markdown(kpi_template.format(label="Demanda Real Total", value=f"{demanda_real_total:,} un."), unsafe_allow_html=True)
col2.markdown(kpi_template.format(label="Demanda Limpia Total", value=f"{demanda_limpia_total:,} un."), unsafe_allow_html=True)
col3.markdown(kpi_template.format(label="% Quiebre de Stock", value=f"{porcentaje_quiebre} %"), unsafe_allow_html=True)
col4.markdown(kpi_template.format(label="Unidades Perdidas", value=f"{total_unidades_perdidas:,} un."), unsafe_allow_html=True)
st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)

# --- Función para títulos con fondo ---
def titulo_con_fondo(texto):
    return f"""
    <div style="background-color:#F7F7F7; padding:0px 0px; border-radius:16px; width:100%; text-align:center;">
        <h4 style="margin: 0; line-height: 1.5; font-weight: 400; font-size: 22px;">{texto}</h4>
    </div>
    """

# --- Procesamiento de demanda ---
@st.cache_data
def procesar_demanda(df_filtrado):
    df_semanal = df_filtrado.groupby('semana').agg({'demanda': 'sum','demanda_sin_outlier': 'sum'}).reset_index()
    fig_semanal = px.line(df_semanal, x='semana', y=['demanda', 'demanda_sin_outlier'], labels={'value': 'Unidades', 'variable': 'Tipo de Demanda'})
    fig_semanal.for_each_trace(lambda t: t.update(name='Demanda Real') if t.name == 'demanda' else t.update(name='Demanda Limpia'))
    df_tmp = df_filtrado.copy()
    df_tmp['fecha_fin'] = df_tmp['fecha'] + timedelta(days=6)
    rows = []
    for _, row in df_tmp.iterrows():
        dias = pd.date_range(start=row['fecha'], end=row['fecha_fin'])
        meses = dias.to_series().dt.to_period('M').value_counts().sort_index()
        for periodo, cantidad_dias in meses.items():
            fraccion = cantidad_dias / len(dias)
            rows.append({'mes': periodo.to_timestamp(),'demanda': row['demanda'] * fraccion,'demanda_sin_outlier': row['demanda_sin_outlier'] * fraccion})
    df_mensual = pd.DataFrame(rows).groupby('mes')[['demanda', 'demanda_sin_outlier']].sum().reset_index()
    fig_mensual = px.line(df_mensual, x='mes', y=['demanda', 'demanda_sin_outlier'], labels={'value': 'Unidades', 'variable': 'Tipo de Demanda'})
    fig_mensual.for_each_trace(lambda t: t.update(name='Demanda Real') if t.name == 'demanda' else t.update(name='Demanda Limpia'))
    return fig_semanal, fig_mensual

fig_semanal, fig_mensual = procesar_demanda(df_filtrado)

# --- Mostrar gráficos en filas ---
st.markdown(titulo_con_fondo(f"📅 Demanda Semanal - {sku_seleccionado}"), unsafe_allow_html=True)
st.plotly_chart(fig_semanal, use_container_width=True)
st.markdown("<div style='margin-top: 32px;'></div>", unsafe_allow_html=True)

st.markdown(titulo_con_fondo(f"📆 Demanda Mensual - {sku_seleccionado}"), unsafe_allow_html=True)
st.plotly_chart(fig_mensual, use_container_width=True)
