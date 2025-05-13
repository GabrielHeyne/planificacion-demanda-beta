import streamlit as st
import pandas as pd
from dateutil.relativedelta import relativedelta

# 🔹 Filtro por SKU
def aplicar_filtro_sku(df, incluir_todos=True, key="sku_filtro"):
    df = df.copy()

    # Obtener lista de SKUs
    skus = sorted(df['sku'].unique())
    if incluir_todos:
        skus.insert(0, "TODOS")

    # Inicializar valor por defecto si aún no está seteado
    if key not in st.session_state:
        st.session_state[key] = skus[0]

    # Selector con key fijo (usa directamente session_state['sku_filtro'])
    sku = st.selectbox("🔎 Filtrar por SKU", options=skus, key=key, index=skus.index(st.session_state[key]))

    # Filtrar por SKU
    df_filtrado = df if sku == "TODOS" else df[df["sku"] == sku]
    return df_filtrado, sku

# 🔹 Filtro por SKU + Rango de Fechas
def aplicar_filtro_sku_y_fecha(df, key_prefix="filtro"):
    df = df.copy()
    df['fecha'] = pd.to_datetime(df['fecha'])

    skus = sorted(df['sku'].unique())
    skus.insert(0, "TODOS")

    fecha_min = df['fecha'].min().date()
    fecha_max = df['fecha'].max().date()
    fecha_min_default = max(fecha_min, fecha_max - relativedelta(months=24))

    key_sku = f"{key_prefix}_sku"
    key_inicio = f"{key_prefix}_fecha_inicio"
    key_fin = f"{key_prefix}_fecha_fin"

    sku_default = st.session_state.get(key_sku, "TODOS")
    fecha_inicio_default = st.session_state.get(key_inicio, fecha_min_default)
    fecha_fin_default = st.session_state.get(key_fin, fecha_max)

    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        sku = st.selectbox("🔎 Filtrar por SKU", options=skus, index=skus.index(sku_default), key=key_sku)
    with col2:
        fecha_inicio = st.date_input("📅 Fecha de inicio", value=fecha_inicio_default, min_value=fecha_min, max_value=fecha_max, key=key_inicio)
    with col3:
        fecha_fin = st.date_input("📅 Fecha de fin", value=fecha_fin_default, min_value=fecha_min, max_value=fecha_max, key=key_fin)

    df_filtrado = df.copy()
    if sku != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["sku"] == sku]
    df_filtrado = df_filtrado[(df_filtrado["fecha"] >= pd.to_datetime(fecha_inicio)) & (df_filtrado["fecha"] <= pd.to_datetime(fecha_fin))]

    return df_filtrado, sku, fecha_inicio, fecha_fin
