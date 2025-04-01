import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Herramienta de Planificación",
    page_icon="📊",
    layout="wide"
)

# Estilos
def set_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'Montserrat', sans-serif !important;
        }

        .block-container {
            padding-top: 2.5rem;
            padding-left: 3rem;
            padding-right: 3rem;
        }

        h1, h2, h3, h4, h5, h6, p, li, span, div {
            font-family: 'Montserrat', sans-serif !important;
        }

        /* Mostrar logo en la parte superior del sidebar */
        [data-testid="stSidebar"]::before {
            content: "";
            display: block;
            background-image: url('https://raw.githubusercontent.com/GabrielHeyne/planning-logo/main/logogh.png');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: top center;
            height: 250px;  /* Aumentado el tamaño */
            margin-bottom: 0px;
        }

        /* Ocultar flecha de colapso del sidebar */
        button[title="Collapse sidebar"] {
            display: none;
        }

        /* Aumentar el espacio entre el logo y el menú lateral */
        [data-testid="stSidebarNav"] {
            margin-top: 0px;
        }
    </style>
    """, unsafe_allow_html=True)

set_custom_css()

# Título principal y subtítulo
st.markdown('<h2 style="text-transform: uppercase;">Herramienta de Planificación</h2>', unsafe_allow_html=True)
st.markdown("#### Lleva tu negocio al siguiente nivel")
st.markdown("Esta aplicación te ayudará a:")

# Sección de funciones con íconos alineados verticalmente
def render_icon_text(icon_path, text):
    cols = st.columns([0.05, 0.95])
    with cols[0]:
        st.image(icon_path, width=40)
    with cols[1]:
        st.markdown(
            f'<div style="display: flex; align-items: center; height: 42px;"><strong>{text}</strong></div>',
            unsafe_allow_html=True
        )

render_icon_text("1_clean.png", "Limpiar la demanda de forma automática.")
render_icon_text("2_cargar.png", "Cargar y visualizar tus datos.")
render_icon_text("3_forecast.png", "Generar forecast por producto.")
render_icon_text("4_analizar.png", "Analizar patrones y detectar quiebres futuros.")

# Cierre
st.markdown("Usa el menú lateral para navegar entre las secciones disponibles.")
st.markdown("---")
st.markdown("Desarrollado por [Tu Consultora]. Versión MVP 1.0 🚀")


