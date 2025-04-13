import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

# --- Fuentes modernas Inter + Manrope ---
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

st.title("📈 DEMANDA TOTAL Y QUIEBRES")
st.subheader("Demanda Real y Limpia por SKU")

# --- Cargar demanda limpia desde session_state ---
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
df_quiebre['quiebre_stock'] = (df_quiebre['demanda'] == 0) & (df_quiebre['demanda_sin_outlier'] > 0)
df_quiebre['semana'] = df_quiebre['fecha'].dt.to_period('W').dt.start_time
total_semanas = df_quiebre['semana'].nunique()
quiebre_semanas = df_quiebre[df_quiebre['quiebre_stock']].groupby('semana').ngroup().nunique()
porcentaje_quiebre = round((quiebre_semanas / total_semanas) * 100, 1) if total_semanas > 0 else 0
df_quiebre['unidades_perdidas'] = df_quiebre.apply(lambda row: row['demanda_sin_outlier'] if row['quiebre_stock'] else 0, axis=1)
total_unidades_perdidas = int(df_quiebre['unidades_perdidas'].sum())
demanda_real_total = int(df_filtrado['demanda'].sum())
demanda_limpia_total = int(df_filtrado['demanda_sin_outlier'].sum())

# --- KPIs con nuevo diseño ---
kpi_template = """
<div style="
    background-color:#FAFAFA;
    padding:16px;
    border-radius:20px;
    text-align:center;
    height:120px;
    display:flex;
    flex-direction:column;
    justify-content:center;
    margin: 4px;
    box-shadow: 0px 2px 6px rgba(0,0,0,0.04);
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
        <h4 style="margin: 0; line-height: 1.5; font-weight: 700; font-size: 22px;">{texto}</h4>
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
    df_tmp['mes'] = df_tmp['fecha'].dt.to_period('M').dt.to_timestamp()
    df_tmp['semana'] = df_tmp['fecha'].dt.to_period('W').dt.start_time
    semanas_por_mes = df_tmp.groupby('mes')['semana'].nunique().reset_index()
    meses_completos = semanas_por_mes[semanas_por_mes['semana'] >= 2]['mes']
    df_mensual = df_mensual[df_mensual['mes'].isin(meses_completos)]
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

# --- Top 10 pérdidas --- 
df_quiebre_top = df_quiebre.copy()
df_quiebre_top['unidades_perdidas'] = df_quiebre_top.apply(lambda row: row['demanda_sin_outlier'] if row['quiebre_stock'] else 0, axis=1)
resumen_quiebres = df_quiebre_top.groupby('sku').agg(semanas_quiebre=('quiebre_stock', 'sum'), semanas_totales=('semana', 'nunique'), unidades_perdidas=('unidades_perdidas', 'sum')).reset_index()
resumen_quiebres['porcentaje_quiebre'] = (100 * resumen_quiebres['semanas_quiebre'] / resumen_quiebres['semanas_totales']).round(1)
resumen_quiebres['porcentaje_quiebre'] = resumen_quiebres['porcentaje_quiebre'].astype(str) + ' %'
resumen_quiebres['unidades_perdidas'] = resumen_quiebres['unidades_perdidas'].astype(int)
top10_quiebres = resumen_quiebres.sort_values(by='unidades_perdidas', ascending=False).head(10)

# --- Tabla HTML personalizada ---
tabla_html = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
.table-container { font-family: 'Inter', sans-serif; margin-top: 10px; }
.table-title { font-size: 16px; font-weight: normal; margin-bottom: 10px; }
.custom-table { width: 100%; border-collapse: collapse; font-size: 12px; text-align: center; }
.custom-table th { background-color: #f3f3f3; padding: 6px; }
.custom-table td { padding: 6px; }
</style>
<div class="table-container">
  <div class="table-title">🔔 Top 10 SKUs con mayor número de unidades perdidas por quiebre de stock</div>
  <table class="custom-table">
    <thead>
      <tr><th>SKU</th><th>% Quiebre</th><th>Unidades Perdidas</th></tr>
    </thead>
    <tbody>
"""
for _, row in top10_quiebres.iterrows():
    tabla_html += f"<tr><td>{row['sku']}</td><td>{row['porcentaje_quiebre']}</td><td>{row['unidades_perdidas']:,}</td></tr>"
tabla_html += "</tbody></table></div>"

# --- Mostrar sección Top 10 con tabla --- 
colA, colB = st.columns([1, 1.5])
with colA:
    components.html(tabla_html, height=380, scrolling=True)

