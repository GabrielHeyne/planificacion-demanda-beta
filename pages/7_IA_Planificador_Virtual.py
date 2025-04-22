import streamlit as st
import pandas as pd
from utils import render_logo_sidebar
from openai import OpenAI
from modules.resumen_utils import generar_contexto_negocio

# --- Configuración general ---
st.set_page_config(page_title="Planificador Virtual", layout="wide")
render_logo_sidebar()

# --- Cargar estilos ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

# --- Cliente OpenAI actualizado ---
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# --- Validar datos requeridos ---
requisitos = ["forecast", "stock_proyectado", "resumen_historico"]
faltantes = [r for r in requisitos if r not in st.session_state]
if faltantes:
    st.warning(f"⚠️ Faltan datos clave: {faltantes}")
    st.stop()

# --- Generar contexto del negocio ---
try:
    texto = generar_contexto_negocio(
        st.session_state["forecast"],
        st.session_state["stock_proyectado"],
        st.session_state["resumen_historico"]
    )
    st.session_state["contexto_negocio"] = texto
except Exception as e:
    st.error(f"❌ Error al generar el contexto del negocio: {e}")
    st.stop()

# --- Mostrar contexto ---
if "contexto_negocio" in st.session_state:
    with st.expander("📄 Ver resumen del contexto cargado", expanded=False):
        st.code(st.session_state["contexto_negocio"], language="markdown")

# --- Inicializar historial ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "system", "content": st.session_state["contexto_negocio"]}]

# --- Mostrar historial previo ---
for msg in st.session_state.chat_history[1:]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# --- Funciones para descargables ---
def generar_excel_compras():
    df = st.session_state.get("contexto_negocio_por_sku", pd.DataFrame())
    return df[df["Unidades a Comprar"] > 0][["SKU", "Unidades a Comprar"]]

def generar_excel_demanda_historica():
    df = st.session_state.get("demanda_limpia", pd.DataFrame())
    return df[["sku", "fecha", "demanda", "demanda_sin_outlier"]]

def generar_excel_politicas():
    df = st.session_state.get("contexto_negocio_por_sku", pd.DataFrame())
    return df[["SKU", "ROP", "EOQ", "Safety Stock"]]

def generar_excel_demanda_forecast():
    df = st.session_state.get("forecast", pd.DataFrame())
    return df[["sku", "mes", "demanda", "demanda_limpia", "forecast", "tipo_mes"]]

# --- Respuesta por SKU ---
def responder_con_sku(sku, pregunta):
    st.session_state["último_sku_utilizado"] = sku
    df = st.session_state["contexto_negocio_por_sku"]
    row = df[df["SKU"] == sku].iloc[0]

    forecast = row['Forecast Promedio Mensual']
    stock_proj = row['Stock Proyectado']
    perdidas = int(row['Unidades Perdidas'])
    perdidas_eur = int(row['Pérdida Hist. (€)'])
    unidades_comprar = int(row['Unidades a Comprar']) if row['Unidades a Comprar'] > 0 else 0
    tasa_quiebre = row['Tasa de Quiebre (%)']
    rop = int(row.get("ROP", 0))
    eoq = int(row.get("EOQ", 0))
    safety = int(row.get("Safety Stock", 0))

    pregunta_limpia = pregunta.lower()

    if any(p in pregunta_limpia for p in ["cuánto", "cuantas", "comprar", "reponer", "necesito"]):
        return f"🛒 Deberías comprar aproximadamente **{unidades_comprar} unidades** del SKU {sku}."
    if any(p in pregunta_limpia for p in ["stock", "inventario", "existencias", "disponible"]):
        return f"📦 El stock proyectado del SKU {sku} es de **{stock_proj} unidades**."
    if any(p in pregunta_limpia for p in ["forecast", "demanda", "pronóstico", "previsión"]):
        return f"📈 El forecast mensual promedio del SKU {sku} es de **{forecast} unidades**."
    if any(p in pregunta_limpia for p in ["pérdida", "quiebre", "se perdieron"]):
        return f"💸 El SKU {sku} ha tenido **{perdidas} unidades perdidas**, equivalente a €{perdidas_eur}, con una tasa de quiebre de **{tasa_quiebre:.1f}%**."
    if any(p in pregunta_limpia for p in ["rop", "punto de reposición"]):
        return f"🔁 El Punto de Reposición (ROP) del SKU {sku} es **{rop} unidades**."
    if "eoq" in pregunta_limpia or "cantidad óptima" in pregunta_limpia:
        return f"📦 La cantidad óptima de pedido (EOQ) del SKU {sku} es **{eoq} unidades**."
    if "inventario de seguridad" in pregunta_limpia or "safety stock" in pregunta_limpia:
        return f"🛡️ El inventario de seguridad (safety stock) del SKU {sku} es **{safety} unidades**."

    return (
        f"🔍 Información del SKU {sku}:\n"
        f"• Forecast mensual promedio: {forecast} unidades\n"
        f"• Stock proyectado: {stock_proj} unidades\n"
        f"• Unidades perdidas históricas: {perdidas} unidades\n"
        f"• Pérdida histórica: €{perdidas_eur}\n"
        f"• Tasa de quiebre: {tasa_quiebre:.1f}%\n"
        f"• Unidades a comprar: {unidades_comprar} unidades\n"
        f"• ROP: {rop}, EOQ: {eoq}, Safety Stock: {safety}"
    )

# --- Respuesta general ---
def responder_general(pregunta):
    contexto = st.session_state.get("contexto_negocio_general", {})
    pregunta_limpia = pregunta.lower()

    if "comprar" in pregunta_limpia and "excel" not in pregunta_limpia and "tabla" not in pregunta_limpia and "descargar" not in pregunta_limpia:
        return (
            f"🛒 En total, deberías comprar **{contexto.get('Total Unidades a Comprar', 0):,} unidades** "
            f"distribuidas en **{contexto.get('Total SKUs a Comprar', 0):,} SKUs**."
        )
    if "costo" in pregunta_limpia:
        return f"💰 El costo total estimado de fabricación para la compra es de **€{contexto.get('Costo Total Compra (€)', 0):,}**."
    if "camino" in pregunta_limpia or "llegan" in pregunta_limpia:
        return f"🚚 Actualmente hay **{contexto.get('Total Unidades en Camino', 0):,} unidades en camino**."
    if "stock" in pregunta_limpia and ("total" in pregunta_limpia or "todos" in pregunta_limpia):
        df_stock = st.session_state.get("stock_actual", pd.DataFrame())
        total = int(df_stock['stock'].sum()) if not df_stock.empty else 0
        return f"📦 El stock actual total es de **{total:,} unidades**."

    # --- Descargables ---
    if "excel" in pregunta_limpia or "descargar" in pregunta_limpia or "tabla" in pregunta_limpia:
        if "comprar" in pregunta_limpia:
            df = generar_excel_compras()
            st.markdown("### 📋 Vista previa: Productos a Comprar")
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Descargar productos a comprar", df.to_csv(index=False).encode("utf-8"), "productos_a_comprar.csv", "text/csv")
            return "📄 Aquí tienes los productos que necesitas comprar."

        elif "histórica" in pregunta_limpia or "pasada" in pregunta_limpia:
            df = generar_excel_demanda_historica()
            st.markdown("### 📋 Vista previa: Demanda Histórica")
            st.dataframe(df.head(50), use_container_width=True)
            st.download_button("📥 Descargar demanda histórica", df.to_csv(index=False).encode("utf-8"), "demanda_historica.csv", "text/csv")
            return "📄 Aquí tienes la demanda histórica de todos los SKUs."

        elif "política" in pregunta_limpia or "inventario" in pregunta_limpia:
            df = generar_excel_politicas()
            st.markdown("### 📋 Vista previa: Políticas de Inventario")
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Descargar políticas de inventario", df.to_csv(index=False).encode("utf-8"), "politicas_inventario.csv", "text/csv")
            return "📄 Aquí tienes las políticas de inventario por SKU."

        elif "forecast" in pregunta_limpia or "proyección" in pregunta_limpia:
            df = generar_excel_demanda_forecast()
            st.markdown("### 📋 Vista previa: Demanda y Forecast")
            st.dataframe(df.head(50), use_container_width=True)
            st.download_button("📥 Descargar demanda y forecast", df.to_csv(index=False).encode("utf-8"), "forecast_y_demanda.csv", "text/csv")
            return "📄 Aquí tienes la demanda y forecast por SKU."

    return None  # dejar que OpenAI responda


# --- Chat input ---
user_input = st.chat_input("Escribe tu pregunta...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Detectar SKU
    sku_detectado = None
    df_context = st.session_state.get("contexto_negocio_por_sku", pd.DataFrame())
    if not df_context.empty:
        posibles_skus = df_context["SKU"].astype(str).str.upper().tolist()
        mensaje = user_input.upper().replace("-", "").replace(",", "").replace(":", "")
        for sku in posibles_skus:
            if sku.replace("-", "") in mensaje:
                sku_detectado = sku
                break

    st.session_state.chat_history[0] = {"role": "system", "content": st.session_state["contexto_negocio"]}

    if sku_detectado:
        respuesta = responder_con_sku(sku_detectado, pregunta=user_input)
    elif "último_sku_utilizado" in st.session_state:
        respuesta = responder_con_sku(st.session_state["último_sku_utilizado"], pregunta=user_input)
    else:
        respuesta = responder_general(user_input)
        if respuesta is None:
            with st.spinner("Pensando..."):
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=st.session_state.chat_history
                )
                respuesta = response.choices[0].message.content

    st.session_state.chat_history.append({"role": "assistant", "content": respuesta})
    st.chat_message("assistant").write(respuesta)

# --- Botón de reinicio ---
st.markdown("<hr style='margin-top: 30px;'>", unsafe_allow_html=True)
if st.button("🔄 Reiniciar conversación"):
    st.session_state.pop("chat_history", None)
    st.session_state.pop("último_sku_utilizado", None)
    st.rerun()
