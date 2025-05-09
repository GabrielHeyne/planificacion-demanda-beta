import streamlit as st
from PIL import Image
import os

# --- Configuración de página ---
st.set_page_config(page_title="Planity", layout="wide")

# --- Cargar estilos ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()

# --- Logo lateral ---
def render_logo_sidebar():
    logo_path = os.path.join("planity_logo.png")
    image = Image.open(logo_path)
    st.sidebar.image(image, use_container_width=True)
render_logo_sidebar()

# --- Banner + Descripción ---
banner_path = os.path.join("banner1.png")
st.image(banner_path, use_container_width=True)

st.markdown("""
    <div class='main-title' style='margin-top: 10px;'>
        <p>Planity es una plataforma inteligente para la planificación de demanda e inventarios. Diseñada para ayudarte a tomar decisiones estratégicas basadas en datos reales, Planity automatiza procesos clave y entrega insights accionables para optimizar tus operaciones.</p>
    </div>
""", unsafe_allow_html=True)

# --- Funcionalidades destacadas ---
col1, col2 = st.columns(2)
with col1:
    st.markdown("<div class='card-module'>✅ Limpieza de Demanda</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-module'>📦 Políticas de Inventario eficientes</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-module'>🧪 Simulación de escenarios</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-module'>📈 Paneles interactivos con KPIs</div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='card-module'>📊 Forecast automático por SKU</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-module'>📉 Proyección de stock y pérdidas</div>", unsafe_allow_html=True)
    st.markdown("<div class='card-module'>🛒 Definición de compras</div>", unsafe_allow_html=True)

# --- Botón de carga ---
st.markdown("<br><br>", unsafe_allow_html=True)
if st.button("🚀 Comenzar planificación"):
    with st.spinner("Inicializando aplicación..."):
        progress = st.progress(0)
        paso1 = st.empty()
        paso2 = st.empty()
        paso3 = st.empty()
        paso4 = st.empty()
        paso5 = st.empty()
        paso6 = st.empty()

        # Llamar a la función centralizada de carga
        from utils.init_session import init_session
        init_session(pasos=[paso1, paso2, paso3, paso4, paso5, paso6], progress=progress)

        st.success("🎯 Aplicación cargada correctamente")

# --- Nota final ---
st.markdown("<p style='text-align:center; margin-top:2rem;'>Usa el menú lateral izquierdo para navegar por los módulos.</p>", unsafe_allow_html=True)
