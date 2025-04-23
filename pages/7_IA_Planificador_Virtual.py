import streamlit as st
import pandas as pd
import os
from utils import render_logo_sidebar
from openai import OpenAI
from modules.resumen_utils import generar_contexto_negocio
from modules.ia_utils import responder_general

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
MODELO_OPENAI = "gpt-3.5-turbo"  # Cambiar a "gpt-4" si lo necesitas

# --- Cargar desde disco si no está en session_state ---
def cargar_si_existe(clave, ruta, tipo='csv'):
    if clave not in st.session_state or st.session_state[clave] is None:
        if os.path.exists(ruta):
            df = pd.read_excel(ruta) if tipo == 'excel' else pd.read_csv(ruta)
            st.session_state[clave] = df
    return st.session_state.get(clave, pd.DataFrame())

# --- Cargar datos clave ---
df_forecast = cargar_si_existe("forecast", "data/forecast.csv")
df_stock_proyectado = cargar_si_existe("stock_proyectado", "data/proyeccion_futura.csv")
df_resumen_historico = cargar_si_existe("resumen_historico", "data/resumen_historico.csv")

faltantes = []
if df_forecast.empty: faltantes.append("forecast")
if df_stock_proyectado.empty: faltantes.append("stock_proyectado")
if df_resumen_historico.empty: faltantes.append("resumen_historico")
if faltantes:
    st.warning(f"⚠️ Faltan datos clave: {faltantes}")
    st.stop()

# --- Generar contexto del negocio ---
try:
    texto = generar_contexto_negocio(df_forecast, df_stock_proyectado, df_resumen_historico)
    st.session_state["contexto_negocio"] = texto
except Exception as e:
    st.error(f"❌ Error al generar el contexto del negocio: {e}")
    st.stop()

df_context = st.session_state.get("contexto_negocio_por_sku", pd.DataFrame())
contexto_general = st.session_state.get("contexto_negocio_general", {})

if df_context.empty or not contexto_general:
    st.error("❌ No se pudo cargar completamente el contexto del negocio. Asegúrate de haber ejecutado 'Gestión de Inventarios'.")
    st.stop()

# --- Mostrar contexto ---
with st.expander("📄 Ver resumen del contexto cargado", expanded=False):
    st.code(st.session_state["contexto_negocio"], language="markdown")

# --- Inicializar historial de chat ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "system", "content": st.session_state["contexto_negocio"]}]

for msg in st.session_state.chat_history[1:]:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "assistant":
        st.chat_message("assistant").write(msg["content"])

# --- Responder por SKU ---
def responder_con_sku(sku, pregunta):
    st.session_state["ultimo_sku_utilizado"] = sku
    df = st.session_state["contexto_negocio_por_sku"]
    fila = df[df["SKU"] == sku]
    if fila.empty:
        return f"❌ El SKU {sku} no se encuentra en el contexto cargado."
    row = fila.iloc[0]

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
        return f"🍚 Deberías comprar aproximadamente **{unidades_comprar} unidades** del SKU {sku}."
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
        f"🔍 Información del SKU {sku}:"
        f"• Forecast mensual promedio: {forecast} unidades\n"
        f"• Stock proyectado: {stock_proj} unidades\n"
        f"• Unidades perdidas históricas: {perdidas} unidades\n"
        f"• Pérdida histórica: €{perdidas_eur}\n"
        f"• Tasa de quiebre: {tasa_quiebre:.1f}%\n"
        f"• Unidades a comprar: {unidades_comprar} unidades\n"
        f"• ROP: {rop}, EOQ: {eoq}, Safety Stock: {safety}"
    )

# --- Entrada del usuario ---
user_input = st.chat_input("Escribe tu pregunta...")

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    sku_detectado = None
    posibles_skus = df_context["SKU"].astype(str).str.upper().tolist()
    mensaje = user_input.upper().replace("-", "").replace(",", "").replace(":", "")
    for sku in posibles_skus:
        if sku.replace("-", "") in mensaje:
            sku_detectado = sku
            break

    st.session_state.chat_history[0] = {"role": "system", "content": st.session_state["contexto_negocio"]}

    if sku_detectado:
        respuesta = responder_con_sku(sku_detectado, user_input)
    elif "ultimo_sku_utilizado" in st.session_state:
        respuesta = responder_con_sku(st.session_state["ultimo_sku_utilizado"], user_input)
    else:
        respuesta = responder_general(user_input)
        if respuesta is None:
            with st.spinner("Pensando..."):
                try:
                    if user_input.strip().lower() in ["gracias", "ok", "vale", "perfecto"]:
                        respuesta = "✨ Con gusto! 😊"
                    else:
                        response = client.chat.completions.create(
                            model=MODELO_OPENAI,
                            messages=st.session_state.chat_history[-20:]
                        )
                        respuesta = response.choices[0].message.content
                except Exception as e:
                    respuesta = f"❌ Error inesperado: {str(e)}"

    st.session_state.chat_history.append({"role": "assistant", "content": respuesta})
    st.chat_message("assistant").write(respuesta)

# --- Reiniciar conversación ---
st.markdown("<hr style='margin-top: 30px;'>", unsafe_allow_html=True)
if st.button("🔄 Reiniciar conversación"):
    st.session_state.pop("chat_history", None)
    st.session_state.pop("ultimo_sku_utilizado", None)
    st.rerun()