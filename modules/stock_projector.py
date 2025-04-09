import pandas as pd

def project_stock(df_forecast, df_stock, df_repos, sku, fecha_inicio, precio_venta=None):
    """
    Proyecta el stock mensual para un SKU, considerando forecast, reposiciones y precio de venta.

    Parámetros:
    - df_forecast: DataFrame con columnas ['sku', 'mes', 'forecast']
    - df_stock: DataFrame con columnas ['sku', 'descripcion', 'stock', 'fecha']
    - df_repos: DataFrame con columnas ['sku', 'fecha', 'cantidad']
    - sku: SKU a proyectar
    - fecha_inicio: fecha (datetime) desde la cual comenzar la proyección
    - precio_venta: (opcional) precio unitario del producto

    Retorna:
    - DataFrame con columnas:
      ['mes', 'forecast', 'repos_aplicadas', 'stock_inicial_mes', 'stock_final_mes',
       'unidades_perdidas', 'perdida_proyectada_euros']
    """
    # Preparar forecast
    df_sku = df_forecast[df_forecast['sku'] == sku].copy()
    df_sku['mes'] = pd.to_datetime(df_sku['mes'], errors='coerce')
    fecha_inicio = pd.to_datetime(fecha_inicio)
    df_sku = df_sku[df_sku['mes'] >= fecha_inicio].sort_values('mes').copy()

    # Obtener stock inicial
    stock_info = df_stock[
        (df_stock['sku'] == sku) &
        (pd.to_datetime(df_stock['fecha']).dt.to_period('M').dt.to_timestamp() == fecha_inicio)
    ]
    if stock_info.empty:
        return pd.DataFrame()

    stock_actual = int(stock_info.iloc[0]['stock'])

    # Reposiciones del SKU
    reposiciones = df_repos[df_repos['sku'] == sku].copy()
    reposiciones['mes'] = pd.to_datetime(reposiciones['fecha'], errors='coerce').dt.to_period('M').dt.to_timestamp()

    # Inicializar columnas
    df_sku['repos_aplicadas'] = 0
    df_sku['stock_inicial_mes'] = 0
    df_sku['stock_final_mes'] = 0
    df_sku['unidades_perdidas'] = 0
    df_sku['perdida_proyectada_euros'] = 0

    for i, row in df_sku.iterrows():
        mes = row['mes']
        forecast = row['forecast']
        stock_inicial = stock_actual

        # Reposiciones del mes
        repos_mes = reposiciones[reposiciones['mes'] == mes]['cantidad'].sum()
        stock_con_repos = stock_inicial + repos_mes

        # Calcular pérdidas
        unidades_perdidas = max(forecast - stock_con_repos, 0)
        perdida_euros = unidades_perdidas * precio_venta if precio_venta else 0

        # Actualizar stock
        stock_final = max(stock_con_repos - forecast, 0)

        # Guardar en DataFrame
        df_sku.at[i, 'repos_aplicadas'] = repos_mes
        df_sku.at[i, 'stock_inicial_mes'] = stock_inicial
        df_sku.at[i, 'stock_final_mes'] = stock_final
        df_sku.at[i, 'unidades_perdidas'] = unidades_perdidas
        df_sku.at[i, 'perdida_proyectada_euros'] = perdida_euros

        # Actualizar para el próximo mes
        stock_actual = stock_final

    return df_sku[['mes', 'forecast', 'repos_aplicadas', 'stock_inicial_mes', 'stock_final_mes',
                   'unidades_perdidas', 'perdida_proyectada_euros']]




