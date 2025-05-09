import streamlit as st
import pandas as pd
from utils.render_logo_sidebar import render_logo_sidebar
from modules.inventory_managment import calcular_politicas_inventario
from modules.evaluar_compra_sku import evaluar_compra_sku
from dateutil.relativedelta import relativedelta
import io
from utils.filtros import aplicar_filtro_sku

# --- Estilos y logo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()
render_logo_sidebar()

st.markdown("<h1 style='font-size: 26px; font-weight: 500;'>📦 GESTIÓN DE INVENTARIOS</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 16px;'>Revisa políticas de inventario por SKU y un resumen general de compras sugeridas</p>", unsafe_allow_html=True)

# --- Validación de datos precargados ---
if any(k not in st.session_state for k in ["forecast", "maestro", "demanda_limpia", "stock_actual", "reposiciones"]):
    st.warning("⚠️ Los datos aún no se han cargado completamente. Vuelve a Inicio y presiona 'Comenzar planificación'.")
    st.stop()

# --- Obtener desde session_state ---
df_forecast = st.session_state["forecast"]
df_maestro = st.session_state["maestro"]
df_demanda_limpia = st.session_state["demanda_limpia"]
df_stock = st.session_state["stock_actual"]
df_repos = st.session_state["reposiciones"]

# --- Asegurar datetime en reposiciones ---
if 'fecha' in df_repos.columns:
    df_repos['fecha'] = pd.to_datetime(df_repos['fecha'], errors='coerce')
df_forecast['mes'] = pd.to_datetime(df_forecast['mes'])

# --- Cálculos de políticas y simulación de compras ---
fecha_actual = pd.to_datetime("today").replace(day=1)
tabla_resumen = []
st.session_state['resultados_inventario'] = {}

for sku in df_forecast['sku'].unique():
    stock_actual = df_stock[df_stock['sku'] == sku]['stock'].iloc[0] if sku in df_stock['sku'].values else 0
    unidades_en_camino = df_repos[df_repos['sku'] == sku]['cantidad'].sum() if sku in df_repos['sku'].values else 0
    costo_fab = df_maestro[df_maestro['sku'] == sku]['costo_fabricacion'].iloc[0] if sku in df_maestro['sku'].values else 0

    forecast_4m = df_forecast[(df_forecast['sku'] == sku) & 
                               (df_forecast['tipo_mes'] == 'proyección') & 
                               (df_forecast['mes'] >= fecha_actual)
                              ]['forecast'].head(4)
    demanda_mensual = int(round(forecast_4m.mean(), 0)) if not forecast_4m.empty else 0

    politicas = calcular_politicas_inventario(df_forecast, sku, unidades_en_camino, df_maestro, df_demanda_limpia)
    if politicas is None:
        continue

    resultado = evaluar_compra_sku(sku, stock_actual, fecha_actual, demanda_mensual,
                                   politicas["safety_stock"], politicas["eoq"], df_repos)

    tabla_resumen.append({
        "SKU": sku,
        "Demanda Mensual": demanda_mensual,
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

# --- KPIs generales ---
compras = [r for r in tabla_resumen if r["Acción"] == "Comprar"]
total_skus = len(compras)
total_unidades = sum(r["EOQ"] for r in compras)
total_costo = sum(r["EOQ"] * r["Costo Fabricación (€)"] for r in compras)

st.markdown("<div class='titulo-con-fondo'>📊 Resumen General de Compras</div>", unsafe_allow_html=True)

def tarjeta(label, valor, unidad=""):
    try:
        valor_formateado = f"{int(valor):,}" if isinstance(valor, (int, float)) else valor
    except:
        valor_formateado = valor
    return f"""
    <div style='background:#fff;padding:16px;border-radius:12px;text-align:center;
        height:90px;margin:10px;border:1px solid #B0B0B0;'>
        <div style='font-size:14px;font-weight:500;'>{label}</div>
        <div style='font-size:26px;'>{valor_formateado} {unidad if isinstance(valor, (int, float)) else ""}</div>
    </div>"""

col1, col2, col3 = st.columns(3)
col1.markdown(tarjeta("Total SKUs a Comprar", total_skus), unsafe_allow_html=True)
col2.markdown(tarjeta("Total Unidades a Comprar", total_unidades, "unidades"), unsafe_allow_html=True)
col3.markdown(tarjeta("Costo Total de Fabricación", int(total_costo), "€"), unsafe_allow_html=True)

# --- Filtro por acción sugerida ---
opcion_filtro = st.radio("Filtrar por acción sugerida:", ["Todos", "Sólo los que se deben comprar", "Sólo los que no se deben comprar"], horizontal=True)

df_resumen = pd.DataFrame(tabla_resumen)
if opcion_filtro == "Sólo los que se deben comprar":
    df_resumen = df_resumen[df_resumen["Acción"] == "Comprar"]
elif opcion_filtro == "Sólo los que no se deben comprar":
    df_resumen = df_resumen[df_resumen["Acción"] == "No comprar"]

# --- Guardar en session_state para Resumen General ---
st.session_state["politicas_inventario"] = df_resumen

# --- Tabla resumen ---
st.markdown("<div class='titulo-con-fondo'>📋 Tabla Resumen por SKU</div>", unsafe_allow_html=True)
st.dataframe(df_resumen, use_container_width=True)

# --- Botón de descarga ---
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    df_resumen.to_excel(writer, index=False, sheet_name="Resumen Inventario")
st.download_button(
    label="📥 Descargar Excel",
    data=output.getvalue(),
    file_name="resumen_inventario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- Detalle por SKU seleccionado ---
sku_sel = st.selectbox("Selecciona un SKU para ver el detalle", sorted(df_forecast['sku'].unique()))
sku_data = st.session_state['resultados_inventario'][sku_sel]

col1, col2, col3 = st.columns(3)
col1.markdown(tarjeta("Demanda Mensual", sku_data["demanda_mensual"]), unsafe_allow_html=True)
col2.markdown(tarjeta("Safety Stock", sku_data["politicas"]["safety_stock"]), unsafe_allow_html=True)
col3.markdown(tarjeta("ROP Original", sku_data["politicas"]["rop_original"]), unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)
col4.markdown(tarjeta("Stock Proyectado (5M)", sku_data["stock_final_simulado"]), unsafe_allow_html=True)
col5.markdown(tarjeta("Unidades en Camino", sku_data["unidades_en_camino"]), unsafe_allow_html=True)
col6.markdown(tarjeta("EOQ", sku_data["politicas"]["eoq"]), unsafe_allow_html=True)

col7, col8, col9 = st.columns(3)
col7.markdown(tarjeta("Stock Actual", sku_data["stock_actual"]), unsafe_allow_html=True)
col8.markdown(tarjeta("Acción", "🛒 Comprar" if sku_data["accion"] == "Comprar" else "📦 No comprar", unidad=""), unsafe_allow_html=True)
col9.markdown(tarjeta("Unidades a Comprar", sku_data["unidades_sugeridas"]), unsafe_allow_html=True)