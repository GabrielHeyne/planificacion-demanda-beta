import streamlit as st
import pandas as pd

# Configuración de la página
st.set_page_config(page_title="Forecast", layout="wide")
st.title("📈 Forecast de Demanda")

st.info("Este módulo se encarga de realizar el forecast de demanda.")

# Verificar si los datos están cargados
if 'df_demanda' in st.session_state:
    df_demanda = st.session_state['df_demanda']
    df_demanda['fecha'] = pd.to_datetime(df_demanda['fecha'])
    df_demanda['mes'] = df_demanda['fecha'].dt.to_period('M')

    # Calcular el forecast: Promedio de los últimos 4 meses
    df_demanda = df_demanda.groupby('sku').apply(lambda x: x.sort_values('fecha').tail(4))
    forecast = df_demanda.groupby('sku')['demanda'].mean().reset_index()
    
    st.write("Forecast calculado:")
    st.dataframe(forecast)
else:
    st.warning("No se ha cargado el archivo de demanda. Ve a la sección de carga de archivos primero.")



