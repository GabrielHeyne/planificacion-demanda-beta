import pandas as pd
import streamlit as st
from modules.inventory_management import calcular_politicas_inventario

# Título de la página
st.title("📦 Gestión de Inventarios y Compras")
st.subheader("Cálculo de Políticas de Inventario, ROP y Ajustes")

# Verificamos si los datos están cargados
if 'forecast' not in st.session_state or st.session_state['forecast'] is None:
    st.warning("⚠️ No se ha generado el forecast aún. Ve al módulo correspondiente y vuelve a intentarlo.")
    st.stop()

if 'stock_actual' not in st.session_state or st.session_state['stock_actual'] is None:
    st.warning("⚠️ No se ha cargado el archivo de stock actual. Ve al módulo de carga y vuelve a intentarlo.")
    st.stop()

if 'reposiciones' not in st.session_state or st.session_state['reposiciones'] is None:
    st.warning("⚠️ No se han cargado las reposiciones futuras. Ve al módulo correspondiente y vuelve a intentarlo.")
    st.stop()

# Carga de datos
df_forecast = st.session_state['forecast']
df_stock = st.session_state['stock_actual']
df_repos = st.session_state['reposiciones']
df_maestro = st.session_state['maestro']

# Filtro para SKU
skus = sorted(df_forecast['sku'].unique())
sku_sel = st.selectbox("Selecciona un SKU", skus)

# Mostrar información relacionada con el SKU seleccionado
stock_info = df_stock[df_stock['sku'] == sku_sel]
if stock_info.empty:
    st.warning("⚠️ No hay stock inicial cargado para este SKU.")
    st.stop()

# Selección de fecha de stock inicial
fechas_disponibles = stock_info['fecha'].sort_values().dt.to_period('M').dt.to_timestamp().unique()
fecha_inicio = st.selectbox("Selecciona la fecha de stock inicial", fechas_disponibles)

fila_stock = stock_info[stock_info['fecha'].dt.to_period('M').dt.to_timestamp() == fecha_inicio].iloc[0]
descripcion = fila_stock.get('descripcion', 'N/A')
stock_inicial = fila_stock['stock']

# Obtener precio de venta desde el maestro
precio_venta = None
if not df_maestro.empty and sku_sel in df_maestro['sku'].values:
    precio_venta = df_maestro[df_maestro['sku'] == sku_sel]['precio_venta'].iloc[0]

# Mostrar la información del SKU seleccionado
st.markdown(f"<h4>🛒 Descripción: {descripcion}</h4>", unsafe_allow_html=True)
st.markdown(f"📦 **Stock Inicial**: {stock_inicial} unidades")

# Ejecutar el cálculo de políticas de inventario
df_politicas = calcular_politicas_inventario(
    df_forecast=df_forecast,
    df_stock=df_stock,
    df_repos=df_repos,
    sku=sku_sel,
    fecha_inicio=fecha_inicio,
    precio_venta=precio_venta
)

# Mostrar tabla con las políticas de inventario
st.subheader("📊 Políticas de Inventario y Recomendaciones")
st.dataframe(df_politicas, use_container_width=True)

# Mostrar ROP y Safety Stock
rop = df_politicas['ROP'].iloc[0]
safety_stock = df_politicas['Safety Stock'].iloc[0]

st.markdown(f"**ROP calculado**: {rop:.2f} unidades")
st.markdown(f"**Safety Stock calculado**: {safety_stock:.2f} unidades")

# Ajustes por unidades en camino (en este caso ya tenemos los datos de las reposiciones)
unidades_en_camino = df_repos[df_repos['sku'] == sku_sel]['cantidad'].sum()
st.markdown(f"**Unidades en camino**: {unidades_en_camino} unidades")

# Ajuste del ROP según unidades en camino
rop_ajustado = rop - unidades_en_camino if unidades_en_camino > 0 else rop
st.markdown(f"**ROP ajustado por unidades en camino**: {rop_ajustado:.2f} unidades")

# Mostrar alertas de productos con bajo stock
st.subheader("⚠️ Alerta de Productos Bajo Stock")
df_alertas = df_politicas[df_politicas['Stock Disponible'] < df_politicas['ROP']]
if not df_alertas.empty:
    st.dataframe(df_alertas[['SKU', 'Stock Disponible', 'ROP', 'Safety Stock']], use_container_width=True)
else:
    st.success("No hay productos con bajo stock.")

