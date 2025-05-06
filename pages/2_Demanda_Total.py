import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from utils.utils import render_logo_sidebar  
import os

st.set_page_config(layout="wide")

# Cargar CSS
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

# Logo lateral
render_logo_sidebar()

st.markdown('<h1 style="font-size: 24px; margin-bottom: 2px; font-weight: 500;">DEMANDA TOTAL Y QUIEBRES</h1>', unsafe_allow_html=True)

# --- Cargar demanda limpia desde session_state o desde disco ---
def cargar_demanda():
    if "demanda_limpia" not in st.session_state or st.session_state["demanda_limpia"] is None:
        if os.path.exists("data/demanda_limpia.xlsx"):
            df = pd.read_excel("data/demanda_limpia.xlsx")
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            st.session_state["demanda_limpia"] = df
    return st.session_state.get("demanda_limpia", pd.DataFrame())

df = cargar_demanda()

if df.empty:
    st.warning("⚠️ No se han cargado los datos limpios. Ve al menú 'Carga Archivos' para hacerlo.")
    st.stop()

# --- Continuación de tu código original ---
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
fecha_min_defecto = max(fecha_min, (fecha_max - relativedelta(months=24)))
rango_fecha = st.date_input("Selecciona el rango de fechas", value=(fecha_min_defecto, fecha_max), min_value=fecha_min, max_value=fecha_max)
fecha_inicio = pd.to_datetime(rango_fecha[0])
fecha_fin = pd.to_datetime(rango_fecha[1])
df_filtrado = df_filtrado[(df_filtrado['fecha'] >= fecha_inicio) & (df_filtrado['fecha'] <= fecha_fin)]

# --- KPIs y quiebres ---
df_quiebre = df_filtrado.copy()
df_quiebre['quiebre_stock'] = (df_quiebre['demanda'] == 0) & (df_quiebre['demanda_sin_outlier'] > 0)

if sku_seleccionado == "TODOS":
    quiebre_por_sku = df_quiebre.groupby('sku').apply(lambda x: (x['quiebre_stock'].sum() / len(x)) * 100)
    porcentaje_quiebre = round(quiebre_por_sku.mean(), 1)
else:
    total_semanas = df_quiebre['semana'].nunique()
    quiebre_semanas = df_quiebre[df_quiebre['quiebre_stock']].groupby('semana').ngroup().nunique()
    porcentaje_quiebre = round((quiebre_semanas / total_semanas) * 100, 1) if total_semanas > 0 else 0

# NUEVA DEFINICIÓN: Unidades perdidas
df_quiebre['unidades_perdidas'] = df_quiebre.apply(
    lambda row: row['demanda_sin_outlier'] - row['demanda'] if row['demanda_sin_outlier'] > row['demanda'] else 0,
    axis=1
)

# Redondear valores y manejar NaN/infinitos
df_quiebre['unidades_perdidas'] = df_quiebre['unidades_perdidas'].fillna(0).round(0).astype(int)
df_filtrado['demanda'] = df_filtrado['demanda'].fillna(0).round(0).astype(int)
df_filtrado['demanda_sin_outlier'] = df_filtrado['demanda_sin_outlier'].fillna(0).round(0).astype(int)

# Asegurando que no haya NaN en porcentaje_quiebre y que se redondee correctamente
df_quiebre['porcentaje_quiebre'] = (df_quiebre['unidades_perdidas'] / df_quiebre['demanda_sin_outlier']) * 100
df_quiebre['porcentaje_quiebre'] = df_quiebre['porcentaje_quiebre'].fillna(0).round(0).astype(int)

total_unidades_perdidas = int(df_quiebre['unidades_perdidas'].sum())
demanda_real_total = int(df_filtrado['demanda'].sum())
demanda_limpia_total = int(df_filtrado['demanda_sin_outlier'].sum())

# --- KPIs ---
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

col1, col2, col3, col4 = st.columns(4)
col1.markdown(kpi_template.format(label="Demanda Real Total", value=f"{demanda_real_total:,} un."), unsafe_allow_html=True)
col2.markdown(kpi_template.format(label="Demanda Limpia Total", value=f"{demanda_limpia_total:,} un."), unsafe_allow_html=True)
col3.markdown(kpi_template.format(label="% Quiebre de Stock", value=f"{porcentaje_quiebre} %"), unsafe_allow_html=True)
col4.markdown(kpi_template.format(label="Unidades Perdidas", value=f"{total_unidades_perdidas:,} un."), unsafe_allow_html=True)
st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)

# --- Títulos con fondo blanco --- 
def titulo_con_fondo(texto):
    return f"""
    <div class="titulo-con-fondo" style="margin-bottom: 5px;">
        <h4 style="margin: 0; padding: 0; line-height: 1; font-weight: 400; font-size: 18px;">{texto}</h4>
    </div>
    """


# --- Gráficos ---
@st.cache_data
def procesar_demanda_semanal(df_filtrado):
    df_semanal = df_filtrado.groupby('semana').agg({
        'demanda': 'sum',
        'demanda_sin_outlier': 'sum'
    }).reset_index()

    fig_semanal = px.line(df_semanal, x='semana', y=['demanda', 'demanda_sin_outlier'], labels={'value': 'Unidades', 'variable': 'Tipo de Demanda'})
    fig_semanal.for_each_trace(lambda t: t.update(name='Demanda Real') if t.name == 'demanda' else t.update(name='Demanda Limpia'))

    # Añadir la configuración para reducir el espacio
    fig_semanal.update_layout(margin=dict(t=4))  # Reducir el margen superior a 0

    return fig_semanal


@st.cache_data
def procesar_demanda_mensual(df_filtrado):
    df_tmp = df_filtrado.copy()
    df_tmp['fecha_fin'] = df_tmp['fecha'] + timedelta(days=6)
    rows = []

    for _, row in df_tmp.iterrows():
        dias = pd.date_range(start=row['fecha'], end=row['fecha_fin'])
        meses = dias.to_series().dt.to_period('M').value_counts().sort_index()
        for periodo, cantidad_dias in meses.items():
            if cantidad_dias >= 7:  # Verificamos que el mes tenga al menos 7 días
                fraccion = cantidad_dias / len(dias)
                rows.append({
                    'mes': periodo.to_timestamp(),
                    'demanda': row['demanda'] * fraccion,
                    'demanda_sin_outlier': row['demanda_sin_outlier'] * fraccion
                })

    df_mensual = pd.DataFrame(rows).groupby('mes')[['demanda', 'demanda_sin_outlier']].sum().reset_index()

    fig_mensual = px.line(df_mensual, x='mes', y=['demanda', 'demanda_sin_outlier'], labels={'value': 'Unidades', 'variable': 'Tipo de Demanda'})
    fig_mensual.for_each_trace(lambda t: t.update(name='Demanda Real') if t.name == 'demanda' else t.update(name='Demanda Limpia'))

    # Añadir la configuración para reducir el espacio
    fig_mensual.update_layout(margin=dict(t=4))  # Reducir el margen superior a 0

    return fig_mensual


# --- Gráfico de Unidades Perdidas Mensuales ---
@st.cache_data
def graficar_unidades_perdidas(df):
    df_perdidas = df.copy()
    df_perdidas['mes'] = df_perdidas['fecha'].dt.to_period('M').dt.to_timestamp()
    df_perdidas_mensual = df_perdidas.groupby('mes')['unidades_perdidas'].sum().reset_index()

    # Gráfico de barras de Unidades Perdidas
    fig_perdidas = px.bar(df_perdidas_mensual, x='mes', y='unidades_perdidas', labels={'unidades_perdidas': 'Unidades Perdidas', 'mes': 'Mes'})
    fig_perdidas.update_traces(marker_color='indianred')

    # Añadir etiquetas a las barras
    fig_perdidas.update_traces(text=df_perdidas_mensual['unidades_perdidas'], textposition='outside', texttemplate='%{text}')

    fig_perdidas.update_layout(margin=dict(t=4))  # Reducir el margen superior a 0

    return fig_perdidas


# --- Gráfico de % Quiebre de Stock Mensual ---
@st.cache_data
def graficar_quiebre(df):
    df_quiebre = df.copy()
    df_quiebre['mes'] = df_quiebre['fecha'].dt.to_period('M').dt.to_timestamp()
    df_quiebre_mensual = df_quiebre.groupby('mes').apply(
        lambda x: (x['unidades_perdidas'].sum() / x['demanda_sin_outlier'].sum()) * 100
    ).reset_index(name='porcentaje_quiebre')

    # Gráfico de líneas de % Quiebre de Stock
    fig_quiebre = go.Figure()

    # Añadir la línea para el % Quiebre de Stock
    fig_quiebre.add_trace(go.Scatter(
        x=df_quiebre_mensual['mes'], 
        y=df_quiebre_mensual['porcentaje_quiebre'],
        mode='lines+markers+text',  # Usamos 'text' para mostrar las etiquetas
        name='% Quiebre de Stock',
        text=df_quiebre_mensual['porcentaje_quiebre'].round(0).astype(int).astype(str) + '%',  # Eliminar decimales y mostrar solo el % entero
        textposition='top center',  # Coloca las etiquetas sobre la línea
        line=dict(color='lightcoral', width=2),
        marker=dict(size=6, color='red', symbol='circle')
    ))

    # Añadir títulos a los ejes y gráfico
    fig_quiebre.update_layout(
        xaxis_title="Mes",
        yaxis_title="% Quiebre de Stock",
        template="plotly_white"
    )

  # Añadir la configuración para reducir el espacio
    fig_quiebre.update_layout(margin=dict(t=4))  # Reducir el margen superior a 0

    return fig_quiebre


# --- Mostrar gráficos ---
st.markdown(titulo_con_fondo(f"🔍 Demanda Semanal - {sku_seleccionado}"), unsafe_allow_html=True)
st.plotly_chart(procesar_demanda_semanal(df_filtrado), use_container_width=True)

st.markdown(titulo_con_fondo(f"📆 Demanda Mensual - {sku_seleccionado}"), unsafe_allow_html=True)
st.plotly_chart(procesar_demanda_mensual(df_filtrado), use_container_width=True)

# Gráficos de Unidades Perdidas y % Quiebre
col1, col2 = st.columns(2)

with col1:
    st.markdown(titulo_con_fondo(f"⚠️ Unidades Perdidas Mensuales - {sku_seleccionado}"), unsafe_allow_html=True)
    st.plotly_chart(graficar_unidades_perdidas(df_quiebre), use_container_width=True)

with col2:
    st.markdown(titulo_con_fondo(f"📉 % de Quiebre de Stock Mensual - {sku_seleccionado}"), unsafe_allow_html=True)
    st.plotly_chart(graficar_quiebre(df_quiebre), use_container_width=True)


# Calcular el porcentaje de quiebre por SKU
df_quiebre['porcentaje_quiebre'] = (df_quiebre['unidades_perdidas'] / df_quiebre['demanda_sin_outlier']) * 100

# --- Ranking de SKUs con más quiebre ---
df_ranking_quiebre = df_quiebre.groupby('sku').agg({
    'unidades_perdidas': 'sum',
    'porcentaje_quiebre': 'mean'
}).reset_index()

# Redondeamos el porcentaje de quiebre a enteros
df_ranking_quiebre['porcentaje_quiebre'] = df_ranking_quiebre['porcentaje_quiebre'].fillna(0).round(0).astype(int)

# Ordenamos el DataFrame por unidades perdidas de manera descendente y seleccionamos los 10 primeros
df_ranking_quiebre = df_ranking_quiebre.sort_values(by='unidades_perdidas', ascending=False).head(10)

# Restablecer el índice y numerarlo desde 1 (en lugar de 0)
df_ranking_quiebre_reset = df_ranking_quiebre.reset_index(drop=True)  # Eliminar la columna de índice original
df_ranking_quiebre_reset.index = df_ranking_quiebre_reset.index + 1  # Ajustar el índice a partir de 1

# --- Top 10 SKUs Más Demandados ---
df_ranking_demandados = df_quiebre.groupby('sku').agg({
    'demanda_sin_outlier': 'sum'
}).reset_index()

# Ordenamos por demanda sin outlier y seleccionamos los 10 primeros
df_ranking_demandados = df_ranking_demandados.sort_values(by='demanda_sin_outlier', ascending=False).head(10)

# Redondeamos la demanda sin outlier para asegurarnos de que no haya decimales
df_ranking_demandados['demanda_sin_outlier'] = df_ranking_demandados['demanda_sin_outlier'].round(0).astype(int)

# Restablecer el índice y numerarlo desde 1 (en lugar de 0)
df_ranking_demandados_reset = df_ranking_demandados.reset_index(drop=True)
df_ranking_demandados_reset.index = df_ranking_demandados_reset.index + 1

# Mostrar las tablas de ranking de quiebre y ranking de demanda
col1, col2 = st.columns(2)

with col1:
    st.markdown(titulo_con_fondo(f"🚨 Top 10 SKUs con más Quiebre de Stock"), unsafe_allow_html=True)
    st.dataframe(df_ranking_quiebre_reset[['sku', 'unidades_perdidas', 'porcentaje_quiebre']].rename(columns={
        'sku': 'SKU',
        'unidades_perdidas': 'Unidades Perdidas',
        'porcentaje_quiebre': '% Quiebre de Stock'
    }), use_container_width=True)

with col2:
    st.markdown(titulo_con_fondo(f"🏆 Top 10 SKUs más Demandados"), unsafe_allow_html=True)
    st.dataframe(df_ranking_demandados_reset[['sku', 'demanda_sin_outlier']].rename(columns={
        'sku': 'SKU',
        'demanda_sin_outlier': 'Demanda Limpia'
    }), use_container_width=True)


# --- Crear archivo CSV para descarga ---
def generar_csv(df_quiebre):
    # Redondear la columna demanda_sin_outlier para asegurarnos de que no haya decimales
    df_quiebre['demanda_sin_outlier'] = df_quiebre['demanda_sin_outlier'].round(0)
    
    # Añadir columnas de interés: SKU, demanda real, demanda limpia, unidades perdidas, % de quiebre, fecha
    df_quiebre['porcentaje_quiebre'] = (df_quiebre['unidades_perdidas'] / df_quiebre['demanda_sin_outlier']) * 100
    df_quiebre['porcentaje_quiebre'] = df_quiebre['porcentaje_quiebre'].round(0)
    
    # Selección de las columnas relevantes
    df_export = df_quiebre[['sku', 'fecha', 'demanda', 'demanda_sin_outlier', 'unidades_perdidas', 'porcentaje_quiebre']]
    df_export.columns = ['SKU', 'Fecha', 'Demanda Real', 'Demanda Limpia', 'Unidades Perdidas', '% Quiebre de Stock']
    
    # Convertir el dataframe a un archivo CSV
    csv = df_export.to_csv(index=False).encode('utf-8')
    return csv

# --- Botón para descargar el CSV ---
csv = generar_csv(df_quiebre)
st.download_button(
    label="📥 Descargar Datos",
    data=csv,
    file_name="datos_quiebre_stock.csv",
    mime="text/csv",
    key="btn_descarga_quiebre"
)
