import streamlit as st
import pandas as pd
from utils import render_logo_sidebar
from modules.inventory_managment import calcular_politicas_inventario
from modules.evaluar_compra_sku import evaluar_compra_sku
from dateutil.relativedelta import relativedelta
import io
import os

# --- Cargar estilos y logo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()
render_logo_sidebar()

st.markdown("<h1 style='font-size: 26px; font-weight: 500;'>📦 GESTIÓN DE INVENTARIOS</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 16px;'>Revisa políticas de inventario por SKU y un resumen general de compras sugeridas</p>", unsafe_allow_html=True)

# --- Función para cargar desde disco si no está en session_state ---
def cargar_si_existe(clave, ruta, tipo='csv'):
    if clave not in st.session_state or st.session_state[clave] is None:
        if os.path.exists(ruta):
            df = pd.read_excel(ruta) if tipo == 'excel' else pd.read_csv(ruta)
            if 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
            if 'cantidad' in df.columns:
                df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
            if 'stock' in df.columns:
                df['stock'] = pd.to_numeric(df['stock'], errors='coerce').fillna(0).astype(int)
            st.session_state[clave] = df
            return df
    return st.session_state.get(clave, pd.DataFrame())

# --- Bases de datos ---
df_forecast = cargar_si_existe('forecast', 'data/forecast.csv')
df_maestro = cargar_si_existe('maestro', 'data/maestro.csv')
df_demanda_limpia = cargar_si_existe('demanda_limpia', 'data/demanda_limpia.xlsx', tipo='excel')
df_stock = cargar_si_existe('stock_actual', 'data/stock_actual.csv')
df_repos = cargar_si_existe('reposiciones', 'data/reposiciones.csv')

if df_forecast.empty:
    st.warning("⚠️ No se ha generado el forecast aún.")
    st.stop()

df_forecast['mes'] = pd.to_datetime(df_forecast['mes'])

# --- Cálculo de resumen general + tabla por SKU ---
fecha_actual = pd.to_datetime("today").replace(day=1)
tabla_resumen = []
st.session_state['resultados_inventario'] = {}

for sku in df_forecast['sku'].unique():
    stock_actual = df_stock[df_stock['sku'] == sku]['stock'].iloc[0] if sku in df_stock['sku'].values else 0
    unidades_en_camino = df_repos[df_repos['sku'] == sku]['cantidad'].sum() if sku in df_repos['sku'].values else 0
    costo_fab = df_maestro[df_maestro['sku'] == sku]['costo_fabricacion'].iloc[0] if sku in df_maestro['sku'].values else 0

    df_sku_forecast = df_forecast[(df_forecast['sku'] == sku) & (df_forecast['tipo_mes'] == 'proyección')].sort_values('mes')
    forecast_4m = df_sku_forecast[df_sku_forecast['mes'] >= fecha_actual]['forecast'].head(4)
    demanda_mensual = int(round(forecast_4m.mean(), 0)) if not forecast_4m.empty else 0

    politicas = calcular_politicas_inventario(
        df_forecast,
        sku=sku,
        unidades_en_camino=unidades_en_camino,
        df_maestro=df_maestro,
        df_demanda_limpia=df_demanda_limpia
    )

    if politicas is None:
        continue

    resultado = evaluar_compra_sku(
        sku=sku,
        stock_inicial=stock_actual,
        fecha_actual=fecha_actual,
        demanda_mensual=demanda_mensual,
        safety_stock=politicas['safety_stock'],
        eoq=politicas['eoq'],
        df_repos=df_repos
    )

    tabla_resumen.append({
        "Demanda Mensual": demanda_mensual,
        "SKU": sku,
        "Stock Actual": int(stock_actual),
        "Reposiciones": int(unidades_en_camino),
        "Stock Proyectado (5M)": resultado["stock_final_simulado"],
        "ROP": politicas["rop_original"],
        "Safety Stock": politicas["safety_stock"],
        "EOQ": politicas["eoq"],
        "Costo Fabricación (€)": round(costo_fab, 2),
        "Acción": resultado["accion"]
    })

    st.session_state['resultados_inventario'][sku] = {
        "stock_actual": stock_actual,
        "unidades_en_camino": unidades_en_camino,
        "demanda_mensual": demanda_mensual,
        "politicas": politicas,
        "accion": resultado["accion"],
        "unidades_sugeridas": politicas['eoq'] if resultado["accion"] == "Comprar" else 0,
        "stock_final_simulado": resultado["stock_final_simulado"],
        "costo_fabricacion": costo_fab
    }

# --- Mostrar KPIs agregados con tarjetas ---
compras = [r for r in tabla_resumen if r["Acción"] == "Comprar"]
total_skus = len(compras)
total_unidades = sum(r["EOQ"] if r["EOQ"] else 0 for r in compras)
total_costo = sum(r["EOQ"] * r["Costo Fabricación (€)"] if r["EOQ"] else 0 for r in compras)

st.markdown("<div class='titulo-con-fondo'>📊 Resumen General de Compras</div>", unsafe_allow_html=True)

def tarjeta_resumen(label, value, unidad=""):
    return f"""
    <div style='
        background-color:#ffffff;
        padding:16px;
        border-radius:12px;
        text-align:center;
        height:90px;
        width:100%;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        margin: 10px;
        border: 1px solid #B0B0B0;
    '>
        <div style='font-size:14px; font-weight:500;'>{label}</div>
        <div style='font-size:26px;'>{value:,} {unidad}</div>
    </div>
    """

col1, col2, col3 = st.columns(3)
col1.markdown(tarjeta_resumen("Total SKUs a Comprar", total_skus), unsafe_allow_html=True)
col2.markdown(tarjeta_resumen("Total Unidades a Comprar", total_unidades, "unidades"), unsafe_allow_html=True)
col3.markdown(tarjeta_resumen("Costo Total de Fabricación", int(total_costo), "€"), unsafe_allow_html=True)

# --- Tabla detallada por SKU ---
st.markdown("<div class='titulo-con-fondo'>📋 Tabla Resumen por SKU</div>", unsafe_allow_html=True)

df_resumen = pd.DataFrame(tabla_resumen)
df_resumen = df_resumen[["SKU", "Demanda Mensual", "Stock Actual", "Reposiciones", "Stock Proyectado (5M)", "ROP", "Safety Stock", "EOQ", "Costo Fabricación (€)", "Acción"]]

# ✅ Guardar resumen en session_state para el planificador IA
st.session_state["politicas_inventario"] = df_resumen

st.dataframe(df_resumen, use_container_width=True)

# --- Botón para descargar Excel ---
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_resumen.to_excel(writer, index=False, sheet_name="Resumen Inventario")

st.download_button(
    label="📥 Descargar Excel",
    data=output.getvalue(),
    file_name="resumen_inventario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- Detalle por SKU con tarjetas ---
sku_sel = st.selectbox("Selecciona un SKU para ver el detalle", sorted(df_forecast['sku'].unique()))
sku_data = st.session_state['resultados_inventario'][sku_sel]

stock_actual = sku_data['stock_actual']
unidades_en_camino = sku_data['unidades_en_camino']
demanda_mensual_detalle = sku_data['demanda_mensual']
resultados = sku_data['politicas']
accion = "🛒 Comprar" if sku_data['accion'] == "Comprar" else "📦 No comprar"
unidades_sugeridas = sku_data['unidades_sugeridas']
stock_proyectado = sku_data['stock_final_simulado']

st.markdown("<div class='titulo-con-fondo'>📊 Políticas de Inventario para SKU Seleccionado</div>", unsafe_allow_html=True)

def tarjeta_kpi(label, value, unidad="unidades"):
    return f"""
    <div style='
        background-color:#ffffff;
        padding:16px;
        border-radius:12px;
        text-align:center;
        height:90px;
        width:100%;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        margin: 10px;
        border: 1px solid #B0B0B0;
    '>
        <div style='font-size:14px; font-weight:500;'>{label}</div>
        <div style='font-size:26px;'>{value if value is not None else "–"} {unidad if value is not None else ""}</div>
    </div>
    """

col1, col2, col3 = st.columns(3)
col1.markdown(tarjeta_kpi("Demanda Mensual", demanda_mensual_detalle), unsafe_allow_html=True)
col2.markdown(tarjeta_kpi("Safety Stock", resultados['safety_stock']), unsafe_allow_html=True)
col3.markdown(tarjeta_kpi("ROP Original", resultados['rop_original']), unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)
col4.markdown(tarjeta_kpi("Stock Proyectado (5M)", stock_proyectado), unsafe_allow_html=True)
col5.markdown(tarjeta_kpi("Unidades en Camino", unidades_en_camino), unsafe_allow_html=True)
col6.markdown(tarjeta_kpi("EOQ", resultados['eoq']), unsafe_allow_html=True)

col7, col8, col9 = st.columns(3)
col7.markdown(tarjeta_kpi("Stock Actual", stock_actual), unsafe_allow_html=True)
col8.markdown(tarjeta_kpi("Acción", accion, unidad=""), unsafe_allow_html=True)
col9.markdown(tarjeta_kpi("Unidades a Comprar", unidades_sugeridas), unsafe_allow_html=True)
