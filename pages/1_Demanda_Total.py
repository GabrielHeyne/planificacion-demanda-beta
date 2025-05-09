import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from utils.filtros import aplicar_filtro_sku_y_fecha

# ✅ Configuración inicial
st.set_page_config(layout="wide")

# ✅ Logo y estilos
from utils.render_logo_sidebar import render_logo_sidebar

def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
render_logo_sidebar()

# ✅ Título
st.markdown('<h1 style="font-size: 24px; margin-bottom: 2px; font-weight: 500;">📊 DEMANDA TOTAL Y QUIEBRES</h1>', unsafe_allow_html=True)

# ✅ Validación de datos
if "demanda_limpia" not in st.session_state or st.session_state["demanda_limpia"] is None or st.session_state["demanda_limpia"].empty:
    st.warning("⚠️ Aún no se han cargado los datos de demanda limpia. Por favor, vuelve a la página de Inicio y presiona 'Comenzar planificación'.")
    st.stop()

# ✅ Cargar datos
df = st.session_state["demanda_limpia"].copy()
df['fecha'] = pd.to_datetime(df['fecha'])
df['semana'] = df['fecha'].dt.to_period('W').apply(lambda r: r.start_time)

# (Aquí continúa el resto de tu lógica de filtros, gráficos, KPIs, etc.)


df_filtrado, sku_seleccionado, fecha_inicio, fecha_fin = aplicar_filtro_sku_y_fecha(df)


# --- KPIs y quiebres ---
df_quiebre = df_filtrado.copy()
df_quiebre['quiebre_stock'] = (df_quiebre['demanda'] == 0) & (df_quiebre['demanda_sin_outlier'] > 0)

# Calcular unidades perdidas
df_quiebre['unidades_perdidas'] = df_quiebre.apply(
    lambda row: row['demanda_sin_stockout'] - row['demanda'] if row['demanda_sin_stockout'] > row['demanda'] else 0,
    axis=1
)
df_quiebre['unidades_perdidas'] = df_quiebre['unidades_perdidas'].fillna(0).round(0).astype(int)

# ✅ Cálculo universal del % de quiebre (para TODOS o un SKU)
total_unidades_perdidas = df_quiebre['unidades_perdidas'].sum()
demanda_real_total = df_quiebre['demanda'].sum()
porcentaje_quiebre = round(
    (total_unidades_perdidas / (demanda_real_total + total_unidades_perdidas)) * 100,
    1
) if (demanda_real_total + total_unidades_perdidas) > 0 else 0


# Redondeo de columnas generales
df_filtrado['demanda'] = df_filtrado['demanda'].fillna(0).round(0).astype(int)
df_filtrado['demanda_sin_outlier'] = df_filtrado['demanda_sin_outlier'].fillna(0).round(0).astype(int)

# Cálculo adicional por fila (para gráficos y rankings)
df_quiebre['porcentaje_quiebre'] = (df_quiebre['unidades_perdidas'] / (df_quiebre['demanda'] + df_quiebre['unidades_perdidas'])) * 100
df_quiebre['porcentaje_quiebre'] = df_quiebre['porcentaje_quiebre'].fillna(0).round().astype(int)

# Totales para KPIs visuales
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
    import numpy as np  # asegúrate de tener esta importación si no la tienes arriba

    df_quiebre = df.copy()
    df_quiebre['mes'] = df_quiebre['fecha'].dt.to_period('M').dt.to_timestamp()
    df_quiebre_mensual = df_quiebre.groupby('mes').apply(
        lambda x: (x['unidades_perdidas'].sum() / x['demanda_sin_outlier'].sum()) * 100
        if x['demanda_sin_outlier'].sum() > 0 else 0
    ).reset_index(name='porcentaje_quiebre')

    # Manejar posibles NaN o infinitos al convertir a texto
    if df_quiebre_mensual['porcentaje_quiebre'].isnull().any() or np.isinf(df_quiebre_mensual['porcentaje_quiebre']).any():
        texto_quiebre = (
            df_quiebre_mensual['porcentaje_quiebre']
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0)
            .round(0)
            .astype(int)
            .astype(str) + '%'
        )
    else:
        texto_quiebre = df_quiebre_mensual['porcentaje_quiebre'].round(0).astype(int).astype(str) + '%'

    # Gráfico
    fig_quiebre = go.Figure()
    fig_quiebre.add_trace(go.Scatter(
        x=df_quiebre_mensual['mes'],
        y=df_quiebre_mensual['porcentaje_quiebre'],
        mode='lines+markers+text',
        name='% Quiebre de Stock',
        text=texto_quiebre,
        textposition='top center',
        line=dict(color='lightcoral', width=2),
        marker=dict(size=6, color='red', symbol='circle')
    ))

    fig_quiebre.update_layout(
        xaxis_title="Mes",
        yaxis_title="% Quiebre de Stock",
        template="plotly_white",
        margin=dict(t=4)
    )

    return fig_quiebre



# --- Mostrar gráficos ---
st.markdown(titulo_con_fondo(f"🔍 Demanda Semanal - {sku_seleccionado}"), unsafe_allow_html=True)
st.plotly_chart(procesar_demanda_semanal(df_filtrado), use_container_width=True)

# --- Descargable de demanda limpia semanal ---
df_export_semanal = df_filtrado[['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier']].copy()
df_export_semanal.columns = ['SKU', 'Fecha', 'Demanda Real', 'Demanda sin Stockout', 'Demanda Limpia']
csv_semanal = df_export_semanal.to_csv(index=False).encode('utf-8')

st.download_button("📥 Descargar Detalle Semanal", data=csv_semanal, file_name="demanda_limpia_semanal.csv", mime='text/csv', key="descarga_semanal")


st.markdown(titulo_con_fondo(f"📆 Demanda Mensual - {sku_seleccionado}"), unsafe_allow_html=True)
st.plotly_chart(procesar_demanda_mensual(df_filtrado), use_container_width=True)

# --- Descargable de demanda limpia mensual ---
df_export_semanal['Mes'] = pd.to_datetime(df_export_semanal['Fecha']).dt.to_period('M').dt.to_timestamp()
df_mensual = df_export_semanal.groupby(['SKU', 'Mes'], as_index=False)[['Demanda Real', 'Demanda sin Stockout', 'Demanda Limpia']].sum()
csv_mensual = df_mensual.to_csv(index=False).encode('utf-8')

st.download_button("📥 Descargar Resumen Mensual", data=csv_mensual, file_name="demanda_limpia_mensual.csv", mime='text/csv', key="descarga_mensual")


# Gráficos de Unidades Perdidas y % Quiebre
col1, col2 = st.columns(2)

with col1:
    st.markdown(titulo_con_fondo(f"⚠️ Unidades Perdidas Mensuales - {sku_seleccionado}"), unsafe_allow_html=True)
    st.plotly_chart(graficar_unidades_perdidas(df_quiebre), use_container_width=True)

with col2:
    st.markdown(titulo_con_fondo(f"📉 % de Quiebre de Stock Mensual - {sku_seleccionado}"), unsafe_allow_html=True)
    st.plotly_chart(graficar_quiebre(df_quiebre), use_container_width=True)


# Calcular el porcentaje de quiebre por SKU
df_quiebre['porcentaje_quiebre'] = (df_quiebre['unidades_perdidas'] / (df_quiebre['demanda'] + df_quiebre['unidades_perdidas'])) * 100


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
    df_quiebre['porcentaje_quiebre'] = (df_quiebre['unidades_perdidas'] / (df_quiebre['demanda'] + df_quiebre['unidades_perdidas'])) * 100
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


# =====================================
# 🔎 ANÁLISIS ABC DE DEMANDA
# =====================================

# Paso 1: filtrar últimos 12 meses
fecha_max = df['fecha'].max()
fecha_min = fecha_max - pd.DateOffset(months=12)
df_12m = df[df['fecha'] >= fecha_min]

# Paso 2: agrupar demanda limpia por SKU
df_abc = df_12m.groupby('sku')['demanda_sin_outlier'].sum().reset_index()
df_abc = df_abc.sort_values('demanda_sin_outlier', ascending=False)
df_abc['participacion'] = df_abc['demanda_sin_outlier'] / df_abc['demanda_sin_outlier'].sum()
df_abc['acumulado'] = df_abc['participacion'].cumsum()

# Paso 3: clasificar ABC
def clasificar(row):
    if row['acumulado'] <= 0.7:
        return 'A'
    elif row['acumulado'] <= 0.9:
        return 'B'
    else:
        return 'C'
df_abc['Clase ABC'] = df_abc.apply(clasificar, axis=1)

# Paso 4: agregar descripción si existe maestro
if 'maestro' in st.session_state and st.session_state['maestro'] is not None:
    df_abc = df_abc.merge(st.session_state['maestro'][['sku', 'descripcion']], on='sku', how='left')

# Paso 5: tabla formateada
df_tabla_abc = df_abc[['sku', 'descripcion', 'demanda_sin_outlier', 'acumulado', 'Clase ABC']].copy()
df_tabla_abc.columns = ['SKU', 'Descripción', 'Demanda Total', '% Acumulado', 'Clase ABC']
df_tabla_abc['% Acumulado'] = (df_tabla_abc['% Acumulado'] * 100).round(0).astype(int).astype(str) + '%'
# Guardar clasificación ABC en session_state
st.session_state["clase_abc"] = df_abc.set_index("sku")["Clase ABC"].to_dict()


# Conteo para gráfico
conteo_clases = df_tabla_abc['Clase ABC'].value_counts().reset_index()
conteo_clases.columns = ['Clase', 'Cantidad']
conteo_clases = conteo_clases.sort_values('Clase')

# Ajustar eje Y automáticamente (10% extra)
max_cantidad = conteo_clases['Cantidad'].max()
fig_clases = px.bar(
    conteo_clases,
    x='Clase',
    y='Cantidad',
    color='Clase',
    text='Cantidad',
    color_discrete_sequence=['#2a9d8f', '#f4a261', '#e76f51']
)
fig_clases.update_traces(
    textposition='outside',
    textfont=dict(size=14, color='black')
)
fig_clases.update_layout(
    height=370,
    margin=dict(t=10),
    yaxis=dict(range=[0, max_cantidad * 1.1])
)

# Layout: gráfico a la izquierda, tabla a la derecha
with st.container():
    col_grafico, col_tabla = st.columns([1, 2])

    with col_grafico:
        st.markdown("""
        <div class="titulo-con-fondo" style="margin-bottom: 5px; text-align: center;">
            <h4 style="margin: 0; font-weight: 400; font-size: 18px;">
                📊 Cantidad de SKUs en cada Clase ABC
            </h4>
        </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(fig_clases, use_container_width=True)

        # Botón alineado a la izquierda debajo del gráfico
        csv_abc = df_tabla_abc.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Descargar Análisis ABC", data=csv_abc, file_name="analisis_abc.csv", mime="text/csv")

    with col_tabla:
        st.markdown("""
        <div class="titulo-con-fondo" style="margin-bottom: 5px; text-align: center;">
            <h4 style="margin: 0; font-weight: 400; font-size: 18px;">
                📊 Análisis ABC de Demanda (últimos 12 meses)
            </h4>
        </div>
        """, unsafe_allow_html=True)
        st.dataframe(df_tabla_abc, use_container_width=True, height=300)