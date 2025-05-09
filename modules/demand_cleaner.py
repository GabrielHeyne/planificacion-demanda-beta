import streamlit as st
import pandas as pd
import numpy as np

st.title("Limpieza de demanda histórica")

archivo_demanda = st.file_uploader("Sube el archivo de demanda (CSV)", type=["csv"])

@st.cache_data
def clean_demand(demand_df_raw):
    demand_df = demand_df_raw.copy()

    # Procesar estructura
    demand_df['fecha'] = pd.to_datetime(demand_df['fecha'])
    demand_df = demand_df.sort_values(by=['sku', 'fecha']).reset_index(drop=True)
    demand_df['demanda_sin_stockout'] = np.nan
    demand_df['demanda_sin_outlier'] = np.nan

    df_stock = st.session_state.get("stock_historico")
    usar_stock = isinstance(df_stock, pd.DataFrame) and not df_stock.empty

    skus_obsoletos = []
    skus_con_quiebres = set()
    ultimos_3_meses = []

    if usar_stock:
        df_stock = df_stock.copy()
        df_stock['stock'] = pd.to_numeric(df_stock['stock'], errors='coerce').fillna(0).astype(int)
        df_stock['fecha'] = pd.to_datetime(df_stock['fecha'], errors='coerce')
        df_stock['mes'] = df_stock['fecha'].dt.to_period('M').dt.to_timestamp()

        fecha_max = df_stock['mes'].max()
        fecha_inicio = fecha_max - pd.DateOffset(months=11)
        ultimos_12 = df_stock[df_stock['mes'].between(fecha_inicio, fecha_max)]

        resumen = ultimos_12.groupby(['sku', 'mes'])['stock'].sum().reset_index()
        resumen['sin_stock'] = resumen['stock'] == 0
        conteo_sin_stock = resumen.groupby('sku')['sin_stock'].sum()
        skus_obsoletos = conteo_sin_stock[conteo_sin_stock == 12].index.tolist()

        def contar_quiebres_stock(s):
            quiebres = 0
            en_quiebre = False
            for val in s:
                if val == 0 and not en_quiebre:
                    quiebres += 1
                    en_quiebre = True
                elif val > 0:
                    en_quiebre = False
            return quiebres

        quiebres_df = (
            ultimos_12.sort_values(['sku', 'mes'])
            .groupby('sku')['stock']
            .apply(contar_quiebres_stock)
        )
        skus_con_quiebres = set(quiebres_df[quiebres_df >= 2].index)
        ultimos_3_meses = sorted(df_stock['mes'].unique())[-3:]

    demand_df['es_obsoleto'] = demand_df['sku'].isin(skus_obsoletos)

    for sku, grupo in demand_df.groupby('sku'):
        grupo = grupo.sort_values('fecha').reset_index(drop=True)
        demanda_sin_stockout = []

        if sku in skus_obsoletos:
            demand_df.loc[demand_df['sku'] == sku, 'demanda_sin_stockout'] = grupo['demanda'].values
            demand_df.loc[demand_df['sku'] == sku, 'demanda_sin_outlier'] = grupo['demanda'].values
            continue

        for i in range(len(grupo)):
            demanda_actual = grupo.loc[i, 'demanda']
            fecha_semana = grupo.loc[i, 'fecha']
            ultimas_24 = grupo.iloc[max(0, i - 24):i]
            demanda_valida = ultimas_24[ultimas_24['demanda'] > 0]['demanda']

            aplicar_limpieza = False
            imputar = False

            if usar_stock:
                mes_actual = fecha_semana.to_period('M').to_timestamp()
                mes_anterior = (fecha_semana - pd.DateOffset(months=1)).to_period('M').to_timestamp()

                stock_actual = df_stock[(df_stock['sku'] == sku) & (df_stock['mes'] == mes_actual)]['stock'].sum()
                stock_anterior = df_stock[(df_stock['sku'] == sku) & (df_stock['mes'] == mes_anterior)]['stock'].sum()
                meses_futuros = [(mes_actual + pd.DateOffset(months=m)).to_period('M').to_timestamp() for m in range(1, 7)]
                stock_futuro = df_stock[(df_stock['sku'] == sku) & (df_stock['mes'].isin(meses_futuros))]['stock'].sum()

                # Criterios combinados
                if (stock_actual == 0 or stock_anterior == 0) and (stock_futuro > 0 or mes_actual in ultimos_3_meses):
                    aplicar_limpieza = True
                    imputar = True

                # Criterio adicional: stock 0 en meses adyacentes (anterior, actual o posterior)
                meses_revisar = [
                    (fecha_semana - pd.DateOffset(months=1)).to_period('M').to_timestamp(),
                    fecha_semana.to_period('M').to_timestamp(),
                    (fecha_semana + pd.DateOffset(months=1)).to_period('M').to_timestamp()
                ]
                stock_meses = df_stock[(df_stock['sku'] == sku) & (df_stock['mes'].isin(meses_revisar))]
                if not stock_meses.empty and (stock_meses['stock'] == 0).any():
                    aplicar_limpieza = True
                    imputar = True

                # Criterio adicional: SKU con historial de quiebres frecuentes
                if sku in skus_con_quiebres:
                    aplicar_limpieza = True
                    imputar = True

            else:
                ultimas_48 = grupo.tail(48)['demanda'].values
                quiebres = 0
                en_quiebre = False
                for val in ultimas_48:
                    if val == 0 and not en_quiebre:
                        quiebres += 1
                        en_quiebre = True
                    elif val > 0:
                        en_quiebre = False
                aplicar_limpieza = quiebres >= 2
                imputar = aplicar_limpieza

            if not aplicar_limpieza:
                demanda_sin_stockout.append(demanda_actual)
                continue

            if demanda_valida.empty:
                demanda_sin_stockout.append(0)
                continue

            if imputar and demanda_actual < np.percentile(demanda_valida, 15):
                p60 = np.percentile(demanda_valida, 60)
                demanda_sin_stockout.append(round(p60))
            else:
                demanda_sin_stockout.append(demanda_actual)

        demand_df.loc[demand_df['sku'] == sku, 'demanda_sin_stockout'] = demanda_sin_stockout

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

    demand_df['demanda_sin_stockout'] = demand_df['demanda_sin_stockout'].apply(lambda x: round(x) if pd.notnull(x) else 0)
    demand_df['demanda_sin_outlier'] = demand_df['demanda_sin_outlier'].apply(lambda x: round(x) if pd.notnull(x) else 0)

    return demand_df



# Ejecutar limpieza
if archivo_demanda is not None:
    demand_df = pd.read_csv(archivo_demanda)
    df_limpio = clean_demand(demand_df)
    st.session_state['demanda_limpia'] = df_limpio

    st.subheader("Demanda limpia")
    st.dataframe(df_limpio[['sku', 'fecha', 'demanda', 'demanda_sin_stockout', 'demanda_sin_outlier']])
