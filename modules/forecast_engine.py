import pandas as pd
import numpy as np

def forecast_simple(df):
    """
    Calcula el forecast mensual para cada SKU usando un promedio móvil de hasta 4 meses previos
    (sin considerar el mes actual), basado en la demanda limpia (sin outliers ni stockouts).
    """

    # Asegurar tipo fecha
    df['fecha'] = pd.to_datetime(df['fecha'])

    # Crear columna de mes (periodo)
    df['mes'] = df['fecha'].dt.to_period('M')

    # Agrupar por SKU y mes
    df_mensual = df.groupby(['sku', 'mes']).agg({
        'demanda': 'sum',
        'demanda_sin_outlier': 'sum'
    }).reset_index()

    df_mensual.rename(columns={'demanda_sin_outlier': 'demanda_limpia'}, inplace=True)

    # Convertir 'mes' a datetime para facilitar operaciones
    df_mensual['mes'] = df_mensual['mes'].dt.to_timestamp()

    # Obtener último mes con datos reales
    last_month = df_mensual['mes'].max()
    forecast_horizon = pd.date_range(start=last_month + pd.DateOffset(months=1), periods=6, freq='MS')

    # Crear DataFrame de resultados
    resultados = []

    for sku in df_mensual['sku'].unique():
        df_sku = df_mensual[df_mensual['sku'] == sku].copy()

        # Agregar datos históricos
        for _, row in df_sku.iterrows():
            resultados.append({
                'sku': sku,
                'mes': row['mes'],
                'demanda': row['demanda'],
                'demanda_limpia': row['demanda_limpia'],
                'forecast': np.nan
            })

        # Proyección mes a mes
        for mes_forecast in forecast_horizon:
            # Buscar los 4 meses previos a este mes
            fecha_limite = mes_forecast - pd.DateOffset(months=1)
            mask = (df_sku['mes'] <= fecha_limite)
            ultimos_meses = df_sku.loc[mask].sort_values('mes', ascending=False).head(4)

            # Considerar sólo los meses con demanda limpia > 0
            ultimos_validos = ultimos_meses[ultimos_meses['demanda_limpia'] > 0]

            if not ultimos_validos.empty:
                promedio = round(ultimos_validos['demanda_limpia'].mean())
            else:
                promedio = 0  # o podrías dejarlo como None si prefieres

            resultados.append({
                'sku': sku,
                'mes': mes_forecast,
                'demanda': np.nan,
                'demanda_limpia': np.nan,
                'forecast': promedio
            })

    # Convertir a DataFrame final
    df_final = pd.DataFrame(resultados)

    # Convertir columna 'mes' a string tipo YYYY-MM
    df_final['mes'] = df_final['mes'].dt.strftime('%Y-%m')

    # Redondear y asegurar enteros donde corresponda
    df_final['forecast'] = df_final['forecast'].fillna(0).astype(int)
    df_final['demanda'] = df_final['demanda'].fillna(0).astype(int)
    df_final['demanda_limpia'] = df_final['demanda_limpia'].fillna(0).astype(int)

    return df_final

