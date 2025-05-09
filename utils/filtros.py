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
def aplicar_filtro_sku_y_fecha(df):
    df = df.copy()
    df['fecha'] = pd.to_datetime(df['fecha'])

    # Valores únicos y ordenados para SKUs
    skus = sorted(df['sku'].unique())
    skus.insert(0, "TODOS")

    # Inicializar estados si no existen
    if "sku_seleccionado" not in st.session_state:
        st.session_state["sku_seleccionado"] = "TODOS"

    # Definir el rango de fechas
    fecha_min = df['fecha'].min().date()
    fecha_max = df['fecha'].max().date()
    fecha_min_defecto = max(fecha_min, (fecha_max - relativedelta(months=24)))

    # Inicializar fechas si no existen
    if "fecha_inicio" not in st.session_state:
        st.session_state["fecha_inicio"] = fecha_min_defecto
    if "fecha_fin" not in st.session_state:
        st.session_state["fecha_fin"] = fecha_max

    # Filtros en la misma fila
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        st.session_state["sku_seleccionado"] = st.selectbox("🔎 Filtrar por SKU", options=skus, 
                                                            index=skus.index(st.session_state["sku_seleccionado"]))
    with col2:
        st.session_state["fecha_inicio"] = st.date_input("📅 Fecha de inicio", 
                                                         value=st.session_state["fecha_inicio"], 
                                                         min_value=fecha_min, max_value=fecha_max)
    with col3:
        st.session_state["fecha_fin"] = st.date_input("📅 Fecha de fin", 
                                                      value=st.session_state["fecha_fin"], 
                                                      min_value=fecha_min, max_value=fecha_max)

    # Aplicar filtros
    df_filtrado = df.copy()
    if st.session_state["sku_seleccionado"] != "TODOS":
        df_filtrado = df_filtrado[df_filtrado["sku"] == st.session_state["sku_seleccionado"]]

    fecha_inicio = pd.to_datetime(st.session_state["fecha_inicio"])
    fecha_fin = pd.to_datetime(st.session_state["fecha_fin"])
    df_filtrado = df_filtrado[(df_filtrado["fecha"] >= fecha_inicio) & (df_filtrado["fecha"] <= fecha_fin)]

    return df_filtrado, st.session_state["sku_seleccionado"], fecha_inicio, fecha_fin