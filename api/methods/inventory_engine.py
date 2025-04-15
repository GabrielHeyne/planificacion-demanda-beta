import pandas as pd
import numpy as np

class InventoryEngine:
    def __init__(self, lead_time=4, service_level=1.65):
        """
        Initialize the InventoryEngine with default parameters.
        
        Args:
            lead_time (int): Lead time in months. Default is 4.
            service_level (float): Z-score for service level. Default is 1.65 (95% service level).
        """
        self.lead_time = lead_time
        self.service_level = service_level

    def inventory_by_sku(self, df_forecast, sku):
        """
        Calculate inventory metrics for a specific SKU.
        
        Args:
            df_forecast (pd.DataFrame): DataFrame containing forecast data with 'sku' and 'forecast' columns
            sku (str): SKU identifier
            
        Returns:
            dict: Dictionary containing inventory metrics
        """
        # Filter dataframe for the specific SKU
        df_forecast_filtrado = df_forecast[df_forecast['sku'] == sku]
        
        if df_forecast_filtrado.empty:
            raise ValueError(f"No forecast data found for SKU: {sku}")
            
        # Calculate standard deviation of monthly forecasted demand
        desviacion_estandar = df_forecast_filtrado['forecast'].std()
        
        # Calculate Safety Stock (SS)
        safety_stock = self.service_level * desviacion_estandar * np.sqrt(self.lead_time)
        
        # Calculate average monthly forecasted demand
        demanda_mensual_promedio = df_forecast_filtrado['forecast'].mean()
        
        # Calculate Reorder Point (ROP)
        rop = (demanda_mensual_promedio * self.lead_time) + safety_stock
        
        # Calculate units in transit (this could be made configurable or calculated differently)
        unidades_en_camino = self._calculate_units_in_transit(df_forecast_filtrado)
        
        # Adjust ROP for units in transit
        rop_ajustado = rop - unidades_en_camino if unidades_en_camino > 0 else rop
        
        return {
            'sku': sku,
            'reorder_point': float(rop),
            'adjusted_reorder_point': float(rop_ajustado),
            'safety_stock': float(safety_stock),
            'average_monthly_demand': float(demanda_mensual_promedio),
            'standard_deviation': float(desviacion_estandar),
            'units_in_transit': float(unidades_en_camino)
        }
    
    def _calculate_units_in_transit(self, df_sku):
        """
        Calculate units in transit for a SKU.
        This is a placeholder method that could be customized based on your specific needs.
        
        Args:
            df_sku (pd.DataFrame): DataFrame containing data for a specific SKU
            
        Returns:
            float: Number of units in transit
        """
        # This is a simple implementation. You might want to replace this with actual logic
        # to calculate units in transit based on your business rules
        return 100  # Placeholder value 