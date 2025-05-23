import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt, SimpleExpSmoothing

# --- Métodos de forecast ---
def forecast_promedio_movil(serie, ventana=4):
    forecast = serie.rolling(window=ventana, min_periods=1).mean()
    return forecast, None

def forecast_promedio_6m(serie):
    forecast = serie.rolling(window=6, min_periods=1).mean()
    return forecast, None

def forecast_ponderado_4m(serie):
    pesos = np.array([1, 2, 3, 4])
    pesos = pesos / pesos.sum()
    forecast = serie.rolling(window=4).apply(lambda x: np.dot(x, pesos), raw=True)
    return forecast, None

def forecast_ponderado_6m(serie):
    pesos = np.array([1, 1, 2, 3, 4, 5])
    pesos = pesos / pesos.sum()
    forecast = serie.rolling(window=6).apply(lambda x: np.dot(x, pesos), raw=True)
    return forecast, None

def forecast_ses(serie):
    model = SimpleExpSmoothing(serie, initialization_method="estimated").fit()
    return model.fittedvalues, model

def forecast_holt(serie):
    model = Holt(serie, initialization_method="estimated").fit(optimized=True)
    return model.fittedvalues, model

def forecast_holt_winters(serie):
    model = ExponentialSmoothing(
        serie,
        trend='add',
        seasonal='add',
        seasonal_periods=12,
        initialization_method="estimated"
    ).fit()
    return model.fittedvalues, model

# --- MAPE y selección de modelo ---
def calcular_mape(df_mes, metodo_fn):
    errores = []
    fechas = sorted(df_mes['mes'].unique())
    for i in range(5, len(fechas)):
        corte = df_mes[df_mes['mes'] < fechas[i - 3]]
        if len(corte) < 3:
            continue
        serie = corte.set_index('mes')['demanda_limpia']
        try:
            forecast, _ = metodo_fn(serie)
            pred = forecast.iloc[-1]
            real = df_mes[df_mes['mes'] == fechas[i]]['demanda'].values[0]
            if real > 0:
                errores.append(abs(real - pred) / real)
        except:
            continue
    return np.mean(errores) if errores else np.inf

def seleccionar_mejor_modelo(mapes):
    mapes_validos = {k: v for k, v in mapes.items() if v != np.inf}
    if not mapes_validos:
        return 'promedio_movil'
    min_error = min(mapes_validos.values())
    candidatos = [k for k, v in mapes_validos.items() if v == min_error]
    prioridad = ['holt_winters', 'holt_linear', 'ses', 'pmp_6m', 'pmp_4m', 'promedio_6m', 'promedio_movil']
    for metodo in prioridad:
        if metodo in candidatos:
            return metodo
    return candidatos[0]

def safe_forecast(serie, metodo_forecast):
    try:
        forecast_serie, modelo = metodo_forecast(serie)

        if modelo is not None:  # SES, Holt, Holt-Winters
            pred = modelo.forecast(1)[0]
        else:
            # rolling / ponderados: buscamos último valor no nulo de la serie de forecast
            forecast_serie = forecast_serie.dropna()
            pred = forecast_serie.iloc[-1] if len(forecast_serie) > 0 else serie.tail(4).mean()

    except Exception as e:
        pred = serie.tail(4).mean()

    if pd.isna(pred) or pred < 0:
        pred = serie.tail(3).mean()
    if pd.isna(pred) or pred < 0:
        pred = 0

    return round(pred)

# --- Forecast principal ---
def forecast_engine(df, lead_time_meses=3):
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['mes'] = df['fecha'].dt.to_period('M')
    df_mensual = df.groupby(['sku', 'mes']).agg({
        'demanda': 'sum',
        'demanda_sin_outlier': 'sum'
    }).reset_index()
    df_mensual.rename(columns={'demanda_sin_outlier': 'demanda_limpia'}, inplace=True)
    df_mensual['mes'] = df_mensual['mes'].dt.to_timestamp()

    last_month = df_mensual['mes'].max()
    forecast_horizon = pd.date_range(start=last_month + pd.DateOffset(months=1), periods=6, freq='MS')

    resultados = []

    for sku in df_mensual['sku'].unique():
        df_sku = df_mensual[df_mensual['sku'] == sku].copy()
        df_valid = df_sku[df_sku['demanda_limpia'] > 0]
        if len(df_valid) < 1:
            continue
        serie = df_valid.set_index('mes')['demanda_limpia']

        if len(serie) < 12:
            mejor_modelo = 'promedio_movil'
            metodo_forecast = lambda s: forecast_promedio_movil(s, ventana=4)
        else:
            modelos = {
                'promedio_movil': lambda s: forecast_promedio_movil(s, 4),
                'promedio_6m': forecast_promedio_6m,
                'pmp_4m': forecast_ponderado_4m,
                'pmp_6m': forecast_ponderado_6m,
                'ses': forecast_ses,
                'holt_linear': forecast_holt,
                'holt_winters': forecast_holt_winters
            }
            mapes = {name: calcular_mape(df_valid, model) for name, model in modelos.items()}
            mejor_modelo = seleccionar_mejor_modelo(mapes)
            metodo_forecast = modelos.get(mejor_modelo, lambda s: forecast_promedio_movil(s, 4))

        for _, row in df_sku.iterrows():
            resultados.append({
                'sku': sku,
                'mes': row['mes'],
                'demanda': row['demanda'],
                'demanda_limpia': row['demanda_limpia'],
                'forecast': np.nan,
                'forecast_up': np.nan,
                'tipo_mes': 'histórico',
                'metodo_forecast': mejor_modelo
            })

        all_months = sorted(df_valid['mes'].unique())
        for mes_objetivo in all_months:
            mes_forecast = mes_objetivo - pd.DateOffset(months=lead_time_meses)
            fecha_limite = mes_forecast - pd.DateOffset(months=1)
            if fecha_limite < df_valid['mes'].min():
                continue
            corte = df_valid[df_valid['mes'] <= fecha_limite]
            if len(corte) < 1:
                continue
            serie_bt = corte.set_index('mes')['demanda_limpia']
            pred = safe_forecast(serie_bt, metodo_forecast)

            demanda_real = df_valid[df_valid['mes'] == mes_objetivo]['demanda_limpia'].values[0]
            demanda_original = df_valid[df_valid['mes'] == mes_objetivo]['demanda'].values[0]
            resultados.append({
                'sku': sku,
                'mes': mes_objetivo,
                'demanda': demanda_original,
                'demanda_limpia': demanda_real,
                'forecast': pred,
                'forecast_up': np.nan,
                'tipo_mes': 'backtest',
                'metodo_forecast': mejor_modelo
            })

        std_forecast = df_valid.sort_values('mes')['demanda_limpia'].tail(6).std()
        for mes_forecast in forecast_horizon:
            fecha_limite = mes_forecast - pd.DateOffset(months=1)
            corte = df_valid[df_valid['mes'] <= fecha_limite]
            if len(corte) < 1:
                pred = 0
            else:
                serie_fut = corte.set_index('mes')['demanda_limpia']
                pred = safe_forecast(serie_fut, metodo_forecast)

            forecast_up = round(pred + 1 * std_forecast) if pd.notnull(std_forecast) else round(pred)

            resultados.append({
                'sku': sku,
                'mes': mes_forecast,
                'demanda': np.nan,
                'demanda_limpia': np.nan,
                'forecast': pred,
                'forecast_up': forecast_up,
                'tipo_mes': 'proyección',
                'metodo_forecast': mejor_modelo
            })

    df_final = pd.DataFrame(resultados)
    df_final['mes'] = pd.to_datetime(df_final['mes'])
    df_final['forecast'] = df_final['forecast'].fillna(0).astype(int)
    df_final['forecast_up'] = df_final['forecast_up'].fillna(np.nan).astype('Int64')
    df_final['demanda'] = df_final['demanda'].fillna(0).astype(int)
    df_final['demanda_limpia'] = df_final['demanda_limpia'].fillna(0).astype(int)

    df_final['dpa_movil'] = np.nan
    for sku in df_final['sku'].unique():
        df_sku_bt = df_final[(df_final['sku'] == sku) & (df_final['tipo_mes'] == 'backtest')].sort_values('mes')
        for i in range(2, len(df_sku_bt)):
            ventana = df_sku_bt.iloc[i-2:i+1]
            suma_real = ventana['demanda_limpia'].sum()
            suma_forecast = ventana['forecast'].sum()
            if suma_real > 0:
                dpa = 1 - abs(suma_real - suma_forecast) / suma_real
                dpa = max(dpa, 0)
                idx = df_sku_bt.iloc[i].name
                df_final.loc[idx, 'dpa_movil'] = round(dpa, 4)

    df_final['mes'] = df_final['mes'].dt.strftime('%Y-%m')
    return df_final



def generar_comparativa_forecasts(df, horizonte_meses=6):
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['mes'] = df['fecha'].dt.to_period('M')
    df_mensual = df.groupby(['sku', 'mes']).agg({
        'demanda': 'sum',
        'demanda_sin_outlier': 'sum'
    }).reset_index()

    df_mensual.rename(columns={'demanda_sin_outlier': 'demanda_limpia'}, inplace=True)
    df_mensual['mes'] = df_mensual['mes'].dt.to_timestamp()

    last_month = df_mensual['mes'].max()
    forecast_horizon = pd.date_range(start=last_month + pd.DateOffset(months=1), periods=horizonte_meses, freq='MS')

    resultados = []

    for sku in df_mensual['sku'].unique():
        df_valid = df_mensual[(df_mensual['sku'] == sku) & (df_mensual['demanda_limpia'] > 0)]
        if len(df_valid) < 1:
            continue

        serie = df_valid.set_index('mes')['demanda_limpia']
        modelos = {
            'promedio_movil': lambda s: forecast_promedio_movil(s, 4),
            'promedio_6m': forecast_promedio_6m,
            'pmp_4m': forecast_ponderado_4m,
            'pmp_6m': forecast_ponderado_6m,
            'ses': forecast_ses,
            'holt_linear': forecast_holt,
            'holt_winters': forecast_holt_winters
        }

        for nombre, modelo_func in modelos.items():
            for mes_forecast in forecast_horizon:
                fecha_limite = mes_forecast - pd.DateOffset(months=1)
                corte = df_valid[df_valid['mes'] <= fecha_limite]

                if len(corte) < 1:
                    pred = 0
                else:
                    try:
                        serie_corte = corte.set_index('mes')['demanda_limpia']
                        if len(serie_corte) < 4:
                            pred = serie_corte.mean()  # usa lo que haya
                        else:
                            pred = safe_forecast(serie_corte, modelo_func)
                    except:
                        pred = serie_corte.mean() if len(serie_corte) > 0 else 0

                resultados.append({
                    'sku': sku,
                    'mes': mes_forecast,
                    'metodo': nombre,
                    'forecast': round(pred)
                })

    df_resultado = pd.DataFrame(resultados)
    df_resultado['mes'] = df_resultado['mes'].dt.strftime('%Y-%m')

    df_pivot = df_resultado.pivot_table(
        index=['sku', 'mes'],
        columns='metodo',
        values='forecast'
    ).reset_index()

    return df_pivot
