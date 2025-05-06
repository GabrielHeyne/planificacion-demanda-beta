import streamlit as st
import pandas as pd
import numpy as np

st.title("Limpieza de demanda histórica")

# Subir archivo de demanda
archivo_demanda = st.file_uploader("Sube el archivo de demanda (CSV)", type=["csv"])

# --- Función de limpieza adaptativa con validación de stock e imputación mínima ---
@st.cache_data
def clean_demand(demand_df_raw):
    demand_df = demand_df_raw.copy()

    # Procesar demanda
    demand_df['fecha'] = pd.to_datetime(demand_df['fecha'])
    demand_df = demand_df.sort_values(by=['sku', 'fecha']).reset_index(drop=True)
    demand_df['demanda_sin_stockout'] = np.nan
    demand_df['demanda_sin_outlier'] = np.nan

    # Cargar stock desde session_state (puede no existir)
    df_stock = st.session_state.get("stock_historico")
    usar_stock = isinstance(df_stock, pd.DataFrame) and not df_stock.empty

    if usar_stock:
        df_stock = df_stock.copy()
        df_stock['stock'] = pd.to_numeric(df_stock['stock'], errors='coerce').fillna(0).astype(int)
        df_stock['fecha'] = pd.to_datetime(df_stock['fecha'], errors='coerce')
        df_stock['mes'] = df_stock['fecha'].dt.to_period('M').dt.to_timestamp()

    for sku, grupo in demand_df.groupby('sku'):
        grupo = grupo.sort_values('fecha').reset_index()
        demanda_sin_stockout = []

        # Obtener percentil 20 para demanda válida de ese SKU
        demanda_valida_total = grupo[grupo['demanda'] > 0]['demanda']
        p20 = np.percentile(demanda_valida_total, 20) if not demanda_valida_total.empty else 0

        for i in range(len(grupo)):
            demanda_actual = grupo.loc[i, 'demanda']
            fecha_semana = grupo.loc[i, 'fecha']
            ultimas_24 = grupo.loc[max(0, i - 24):i - 1]
            demanda_valida = ultimas_24[ultimas_24['demanda'] > 0]['demanda']

            imputar = False

            if demanda_actual == 0 or demanda_actual <= p20:
                if usar_stock:
                    meses_revisar = [
                        (fecha_semana - pd.DateOffset(months=1)).to_period('M').to_timestamp(),
                        fecha_semana.to_period('M').to_timestamp(),
                        (fecha_semana + pd.DateOffset(months=1)).to_period('M').to_timestamp()
                    ]

                    stock_meses = df_stock[
                        (df_stock['sku'] == sku) &
                        (df_stock['mes'].isin(meses_revisar))
                    ]

                    if not stock_meses.empty and (stock_meses['stock'] == 0).any():
                        imputar = True
                else:
                    imputar = True

            if imputar and not demanda_valida.empty:
                p60 = np.percentile(demanda_valida, 60)
                demanda_sin_stockout.append(p60)
            else:
                demanda_sin_stockout.append(demanda_actual)

        demand_df.loc[demand_df['sku'] == sku, 'demanda_sin_stockout'] = demanda_sin_stockout

        # Calcular outliers
        grupo['demanda_sin_stockout'] = demanda_sin_stockout
        demanda_limpia = grupo[grupo['demanda_sin_stockout'] > 0]['demanda_sin_stockout']
        p95 = np.percentile(demanda_limpia, 95) if not demanda_limpia.empty else None

        demanda_sin_outlier = []
        for val in grupo['demanda_sin_stockout']:
            if p95 is not None and val is not None and val > p95:
                demanda_sin_outlier.append(p95)
            else:
                demanda_sin_outlier.append(val)

        demand_df.loc[demand_df['sku'] == sku, 'demanda_sin_outlier'] = demanda_sin_outlier

    # Redondear
    demand_df['demanda_sin_stockout'] = demand_df['demanda_sin_stockout'].apply(lambda x: round(x) if pd.notnull(x) else 0)
    demand_df['demanda_sin_outlier'] = demand_df['demanda_sin_outlier'].apply(lambda x: round(x) if pd.notnull(x) else 0)

    return demand_df

# --- Ejecutar limpieza cuando se sube archivo ---
if archivo_demanda is not None:
    demand_df = pd.read_csv(archivo_demanda)
    df_limpio = clean_demand(demand_df)

    # Guardar en session_state para el resto de la app
    st.session_state['demanda_limpia'] = df_limpio

    st.subheader("Demanda limpia")
    st.dataframe(df_limpio[['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier']])
