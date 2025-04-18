import streamlit as st
import pandas as pd
import numpy as np

st.title("Limpieza de demanda histórica")

# Subir archivo de demanda
archivo_demanda = st.file_uploader("Sube el archivo de demanda (CSV)", type=["csv"])

# Función de limpieza
def clean_demand(demand_df):
    # Convertir a datetime
    demand_df['fecha'] = pd.to_datetime(demand_df['fecha'])

    # Ordenar
    demand_df = demand_df.sort_values(by=['sku', 'fecha']).reset_index(drop=True)

    # Crear columnas vacías
    demand_df['demanda_sin_stockout'] = np.nan
    demand_df['demanda_sin_outlier'] = np.nan

    for sku, grupo in demand_df.groupby('sku'):
        grupo = grupo.sort_values('fecha').reset_index()

        demanda_sin_stockout = []

        for i in range(len(grupo)):
            demanda_actual = grupo.loc[i, 'demanda']
            ultimas_24 = grupo.loc[max(0, i - 24):i - 1]
            demanda_valida = ultimas_24[ultimas_24['demanda'] > 0]['demanda']

            if demanda_actual == 0:
                if not demanda_valida.empty:
                    p60 = np.percentile(demanda_valida, 60)
                    demanda_sin_stockout.append(p60)
                else:
                    demanda_sin_stockout.append(None)
            else:
                demanda_sin_stockout.append(demanda_actual)

        # Asignar columna de demanda sin stockout
        demand_df.loc[demand_df['sku'] == sku, 'demanda_sin_stockout'] = demanda_sin_stockout

        # Calcular outliers sobre demanda_sin_stockout
        grupo['demanda_sin_stockout'] = demanda_sin_stockout
        demanda_limpia = grupo[grupo['demanda_sin_stockout'] > 0]['demanda_sin_stockout']

        if not demanda_limpia.empty:
            p85 = np.percentile(demanda_limpia, 85)
            p95 = np.percentile(demanda_limpia, 95)
        else:
            p85 = p95 = None

        demanda_sin_outlier = []
        for val in grupo['demanda_sin_stockout']:
            if p95 is not None and val is not None and val > p95:
                demanda_sin_outlier.append(p95)
            else:
                demanda_sin_outlier.append(val)

        demand_df.loc[demand_df['sku'] == sku, 'demanda_sin_outlier'] = demanda_sin_outlier

    # Redondear los valores de demanda sin outlier y demanda sin stockout
    demand_df['demanda_sin_stockout'] = demand_df['demanda_sin_stockout'].apply(lambda x: round(x) if pd.notnull(x) else 0)
    demand_df['demanda_sin_outlier'] = demand_df['demanda_sin_outlier'].apply(lambda x: round(x) if pd.notnull(x) else 0)

    return demand_df

# Ejecutar limpieza cuando se suba archivo
if archivo_demanda is not None:
    demand_df = pd.read_csv(archivo_demanda)
    df_limpio = clean_demand(demand_df)

    # 👇 Esta línea es clave para que funcione el resto de la app
    st.session_state['demanda_limpia'] = df_limpio

    st.subheader("Demanda limpia")
    st.dataframe(df_limpio[['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier']])



