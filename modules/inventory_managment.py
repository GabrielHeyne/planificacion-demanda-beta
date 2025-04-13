import pandas as pd
import numpy as np

# Variables del cálculo
lead_time = 4  # Lead Time en meses
nivel_servicio = 1.65  # Z para nivel de servicio 95%

# Datos de ejemplo (suponiendo que ya tienes estos datos en df_forecast)
# df_forecast debe tener las columnas 'sku' y 'forecast' para que esta parte funcione

# Filtramos el dataframe para un SKU específico (ya hecho antes en el código)
df_forecast_filtrado = df_forecast[df_forecast['sku'] == sku_sel]

# Calcular la desviación estándar de la demanda mensual proyectada (forecast)
desviacion_estandar = df_forecast_filtrado['forecast'].std()

# Calcular el Safety Stock (SS)
safety_stock = nivel_servicio * desviacion_estandar * np.sqrt(lead_time)

# Calcular el ROP (Reorder Point) considerando el safety stock y la demanda mensual proyectada
# Demanda mensual proyectada en base al forecast
demanda_mensual_promedio = df_forecast_filtrado['forecast'].mean()

# Calcular el Reorder Point (ROP)
rop = (demanda_mensual_promedio * lead_time) + safety_stock

# El ROP puede ser ajustado para reflejar las unidades en camino si es necesario
# Por ejemplo, si tienes datos de unidades en camino, puedes restarlos del ROP
# Vamos a suponer que 'unidades_en_camino' es un valor que ya tienes cargado
unidades_en_camino = 100  # Este valor debe ser calculado o recuperado según el contexto

# Ajustamos el ROP si hay unidades en camino
rop_ajustado = rop - unidades_en_camino if unidades_en_camino > 0 else rop

# Mostramos el resultado
st.write(f"El ROP calculado es: {rop:.2f} unidades")
st.write(f"El ROP ajustado por unidades en camino es: {rop_ajustado:.2f} unidades")
st.write(f"El Safety Stock calculado es: {safety_stock:.2f} unidades")

