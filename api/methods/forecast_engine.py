import pandas as pd
import numpy as np

class ForecastEngine:
    def __init__(self):
        self.lead_time_meses = 3  # Default lead time

    def generate_forecast(self, df, product_id, forecast_horizon, seasonality=None):
        """
        Generate forecast for a specific product.
        
        Args:
            df (pd.DataFrame): Historical data
            product_id (str): Product/SKU identifier
            forecast_horizon (int): Number of periods to forecast
            seasonality (int, optional): Seasonality period. Defaults to None.
            
        Returns:
            tuple: (forecast_df, metrics)
        """
        # Filter data for the specific product
        df_product = df[df['sku'] == product_id].copy()
        
        # Generate forecast
        forecast_df = self.forecast_simple(df_product, lead_time_meses=self.lead_time_meses)
        
        # Calculate metrics
        metrics = self._calculate_metrics(forecast_df)
        
        return forecast_df, metrics
    
    def _calculate_metrics(self, forecast_df):
        """
        Calculate forecast accuracy metrics.
        """
        backtest_data = forecast_df[forecast_df['tipo_mes'] == 'backtest']
        
        if backtest_data.empty:
            return {
                'mape': None,
                'rmse': None,
                'dpa_movil': None
            }
        
        # Calculate MAPE
        actual = backtest_data['demanda_limpia']
        forecast = backtest_data['forecast']
        mape = np.mean(np.abs((actual - forecast) / actual)) * 100 if not actual.empty else None
        
        # Calculate RMSE
        rmse = np.sqrt(np.mean((actual - forecast) ** 2)) if not actual.empty else None
        
        # Get latest DPA móvil
        latest_dpa = backtest_data['dpa_movil'].iloc[-1] if not backtest_data.empty else None
        
        return {
            'mape': float(mape) if mape is not None else None,
            'rmse': float(rmse) if rmse is not None else None,
            'dpa_movil': float(latest_dpa) if latest_dpa is not None else None
        }

def forecast_simple(df, lead_time_meses=3):
    """
    Calcula el forecast mensual para cada SKU usando un promedio móvil con lead time,
    y genera un DPA móvil por mes basado en una bolsa de 3 meses anteriores.
    """

    # Preprocesamiento inicial
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

        # Agregar histórico puro
        for _, row in df_sku.iterrows():
            resultados.append({
                'sku': sku,
                'mes': row['mes'],
                'demanda': row['demanda'],
                'demanda_limpia': row['demanda_limpia'],
                'forecast': np.nan,
                'tipo_mes': 'histórico'
            })

        all_months = sorted(df_sku['mes'].unique())

        # -------- BACKTEST --------
        for mes_objetivo in all_months:
            mes_forecast = mes_objetivo - pd.DateOffset(months=lead_time_meses)
            fecha_limite = mes_forecast - pd.DateOffset(months=1)

            if fecha_limite < df_sku['mes'].min():
                continue

            historial = df_sku[df_sku['mes'] <= fecha_limite].sort_values('mes', ascending=False).head(4)
            ultimos_validos = historial[historial['demanda_limpia'] > 0]

            if not ultimos_validos.empty:
                promedio = round(ultimos_validos['demanda_limpia'].mean())
                demanda_real = df_sku[df_sku['mes'] == mes_objetivo]['demanda_limpia'].values[0]
                demanda_original = df_sku[df_sku['mes'] == mes_objetivo]['demanda'].values[0]

                resultados.append({
                    'sku': sku,
                    'mes': mes_objetivo,
                    'demanda': demanda_original,
                    'demanda_limpia': demanda_real,
                    'forecast': promedio,
                    'tipo_mes': 'backtest'
                })

        # -------- FORECAST FUTURO --------
        for mes_forecast in forecast_horizon:
            fecha_limite = mes_forecast - pd.DateOffset(months=1)
            historial = df_sku[df_sku['mes'] <= fecha_limite].sort_values('mes', ascending=False).head(4)
            ultimos_validos = historial[historial['demanda_limpia'] > 0]
            promedio = round(ultimos_validos['demanda_limpia'].mean()) if not ultimos_validos.empty else 0

            resultados.append({
                'sku': sku,
                'mes': mes_forecast,
                'demanda': np.nan,
                'demanda_limpia': np.nan,
                'forecast': promedio,
                'tipo_mes': 'proyección'
            })

    # -------- UNIFICAR RESULTADOS --------
    df_final = pd.DataFrame(resultados)
    df_final['mes'] = pd.to_datetime(df_final['mes'])
    df_final['forecast'] = df_final['forecast'].fillna(0).astype(int)
    df_final['demanda'] = df_final['demanda'].fillna(0).astype(int)
    df_final['demanda_limpia'] = df_final['demanda_limpia'].fillna(0).astype(int)

    # -------- DPA MÓVIL --------
    df_final['dpa_movil'] = np.nan
    for sku in df_final['sku'].unique():
        df_sku = df_final[(df_final['sku'] == sku) & (df_final['tipo_mes'] == 'backtest')].sort_values('mes')
        for i in range(2, len(df_sku)):
            ventana = df_sku.iloc[i-2:i+1]  # Bolsa de 3 meses
            suma_real = ventana['demanda_limpia'].sum()
            suma_forecast = ventana['forecast'].sum()
            if suma_real > 0:
                dpa = 1 - abs(suma_real - suma_forecast) / suma_real
                dpa = max(dpa, 0)
                idx = df_final[(df_final['sku'] == sku) & (df_final['mes'] == df_sku.iloc[i]['mes'])].index
                df_final.loc[idx, 'dpa_movil'] = round(dpa, 4)

    df_final['mes'] = df_final['mes'].dt.strftime('%Y-%m')
    return df_final
