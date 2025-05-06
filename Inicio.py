import streamlit as st
from PIL import Image
import os
from utils.utils import render_logo_sidebar

# --- Configuración de página ---
st.set_page_config(page_title="Planity", layout="wide", initial_sidebar_state="expanded")

# --- Función para cargar CSS personalizado ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cargar los estilos
load_css()
render_logo_sidebar()

# --- Banner superior ---
banner_path = os.path.join("banner1.png")  # Ruta del banner
st.image(banner_path, use_container_width=True)

# --- Título y descripción ---
st.markdown("""
     <div class='main-title' style='margin-top: 10px;'>
        <p>Planity es una plataforma inteligente para la planificación de demanda e inventarios. Diseñada para ayudarte a tomar decisiones estratégicas basadas en datos reales, Planity automatiza procesos clave y entrega insights accionables para optimizar tus operaciones.</p>
    </div>
""", unsafe_allow_html=True)

# --- Módulos / Funcionalidades en 2 columnas reales ---
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

# --- Nota de navegación ---
st.markdown("<p style='text-align:center; margin-top:2rem;'>Usa el menú lateral izquierdo para navegar por los módulos.</p>", unsafe_allow_html=True) 

