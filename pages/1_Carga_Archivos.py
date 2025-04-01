import pandas as pd
import streamlit as st
import os
from pandas import ExcelWriter
from modules.demand_cleaner import clean_demand

# Aplicar la misma fuente Montserrat globalmente
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap');
        html, body, [class*="css"] {
            font-family: 'Montserrat', sans-serif !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📂 Carga de Archivos y Limpieza de Demanda")

# --- Inicializar variable si no existe ---
if 'demanda_limpia' not in st.session_state:
    st.session_state['demanda_limpia'] = None

# --- Upload y limpieza solo si aún no se ha procesado ---
if st.session_state['demanda_limpia'] is None:
    archivo_demanda = st.file_uploader("Sube el archivo de demanda (CSV)", type="csv")

    if archivo_demanda is not None:
        # Leer archivo
        demand_df = pd.read_csv(archivo_demanda)
        demand_df['fecha'] = pd.to_datetime(demand_df['fecha'])

        # Aplicar limpieza
        cleaned_demand_df = clean_demand(demand_df)

        # Guardar en session_state
        st.session_state['demanda_limpia'] = cleaned_demand_df

        os.makedirs("data", exist_ok=True)
        file_path = "data/demanda_limpia.xlsx"
        with ExcelWriter(file_path, engine='xlsxwriter') as writer:
            cleaned_demand_df.to_excel(writer, index=False, sheet_name='Demanda Limpia')

        # Mensaje y refrescar app
        st.success("✅ Archivo cargado y demanda limpia generada correctamente.")
        st.session_state['demanda_limpia_path'] = file_path  # Almacenar la ruta del archivo limpio
        st.rerun()

else:
    # Mostrar vista previa
    cleaned_demand_df = st.session_state['demanda_limpia']
    st.subheader("✅ Vista previa de la demanda limpia")
    st.dataframe(cleaned_demand_df[['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier']])

    # Botón de descarga
    if 'demanda_limpia_path' in st.session_state:
        file_path = st.session_state['demanda_limpia_path']
        st.download_button(
            label="📥 Descargar Excel de Demanda Limpia",
            data=open(file_path, 'rb').read(),
            file_name="demanda_limpia.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Mensaje adicional (sin visualizaciones)
    st.info("ℹ️ Los datos ya fueron cargados y están disponibles para visualización o forecasting desde el menú 'Demanda Total'.")

