import pandas as pd
import numpy as np
import streamlit as st  # ✅ Esto es lo que faltaba


def consolidar_historico_stock(df_demanda, df_maestro):
    """
    Consolida datos históricos por SKU y mes:
    - Demanda real y limpia
    - Unidades perdidas por quiebre de stock
    - Valor perdido en euros (si hay precio_venta en maestro)
    """

    # Preprocesamiento
    df = df_demanda.copy()
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['mes'] = df['fecha'].dt.to_period('M').dt.to_timestamp()
    df['unidades_perdidas'] = df.apply(
        lambda row: row['demanda_sin_outlier'] if row['demanda'] == 0 and row['demanda_sin_outlier'] > 0 else 0,
        axis=1
    )

    resumen = df.groupby(['sku', 'mes']).agg(
        demanda_real=('demanda', 'sum'),
        demanda_limpia=('demanda_sin_outlier', 'sum'),
        unidades_perdidas=('unidades_perdidas', 'sum')
    ).reset_index()

    # Agregar info del maestro
    if not df_maestro.empty:
        resumen = resumen.merge(df_maestro, on='sku', how='left')
        resumen['valor_perdido_euros'] = resumen['unidades_perdidas'] * resumen['precio_venta']
    else:
        resumen['valor_perdido_euros'] = 0

    return resumen


def consolidar_proyeccion_futura(df_forecast, df_stock, df_repos, df_maestro):
    """
    Consolida la proyección futura por SKU usando la función project_stock.
    Devuelve un dataframe con:
    - Forecast, stock inicial, final, reposiciones
    - Unidades perdidas proyectadas
    - Pérdida proyectada en euros
    - Enriquecido con info del maestro
    """

    from modules.stock_projector import project_stock

    resumen_futuro = []

    for sku in df_forecast['sku'].unique():
        # Filtrar stock inicial para cada SKU
        stock_info = df_stock[df_stock['sku'] == sku]
        if stock_info.empty:
            continue

        fechas_stock = pd.to_datetime(stock_info['fecha']).dt.to_period('M').dt.to_timestamp()
        fecha_inicio = fechas_stock.min()

        precio_venta = None
        info_maestro = df_maestro[df_maestro['sku'] == sku]
        if not info_maestro.empty:
            precio_venta = info_maestro.iloc[0]['precio_venta']

        df_resultado = project_stock(
            df_forecast=df_forecast,
            df_stock=df_stock,
            df_repos=df_repos,
            sku=sku,
            fecha_inicio=fecha_inicio,
            precio_venta=precio_venta
        )

        if not df_resultado.empty:
            df_resultado['sku'] = sku
            resumen_futuro.append(df_resultado)

    df_final = pd.concat(resumen_futuro, ignore_index=True)

    # Agregar info del maestro
    if not df_maestro.empty:
        df_final = df_final.merge(df_maestro, on='sku', how='left')

    st.session_state['stock_proyectado'] = df_final  # ✅ agregamos esto

    return df_final
