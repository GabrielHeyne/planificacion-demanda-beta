import pandas as pd
from dateutil.relativedelta import relativedelta

def evaluar_compra_sku(
    sku: str,
    stock_inicial: int,
    fecha_actual: pd.Timestamp,
    demanda_mensual: float,
    safety_stock: float,
    eoq: float,
    df_repos: pd.DataFrame = None
):
    meses_simulados = 5
    stock = stock_inicial

    # Procesar reposiciones por mes
    repos_por_mes = {i: 0 for i in range(meses_simulados)}
    if df_repos is not None and not df_repos.empty:
        # Filtrar reposiciones del SKU
        df_sku = df_repos[df_repos['sku'] == sku].copy()
        
        # Asegurar que fecha es datetime antes de usar .dt
        if not df_sku.empty:
            df_sku['fecha'] = pd.to_datetime(df_sku['fecha'], errors='coerce')
            if df_sku['fecha'].isna().any():
                print(f"⚠️ Hay fechas inválidas en las reposiciones para el SKU {sku}")
                return {
                    "accion": "No comprar",
                    "stock_final_simulado": stock_inicial,
                    "razon": "Fechas inválidas en reposiciones"
                }
            df_sku['mes'] = df_sku['fecha'].dt.to_period('M').dt.to_timestamp()
            for i in range(meses_simulados):
                mes_sim = (fecha_actual + relativedelta(months=i)).to_period('M').to_timestamp()
                cantidad = df_sku[df_sku['mes'] == mes_sim]['cantidad'].sum()
                repos_por_mes[i] = cantidad

    # Simulación mensual de stock
    for i in range(meses_simulados):
        stock += repos_por_mes[i]
        stock -= demanda_mensual

    # Determinar si hay unidades en camino
    unidades_en_camino = sum(repos_por_mes.values())

    # Evaluar umbral y qué comparar
    if unidades_en_camino > 0:
        umbral = safety_stock
        comparar_con = round(stock)
    else:
        umbral = round((demanda_mensual * meses_simulados) + safety_stock)
        comparar_con = stock_inicial

    # Decisión
    if comparar_con < umbral:
        accion = "Comprar"
        sugerido = round(eoq if eoq is not None else umbral - comparar_con)
    else:
        accion = "No comprar"
        sugerido = 0

    return {
        "accion": accion,
        "sugerido": sugerido,
        "stock_final_simulado": round(stock),
        "umbral": umbral
    }

