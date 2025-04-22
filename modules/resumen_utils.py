import pandas as pd
import numpy as np
import streamlit as st


def consolidar_historico_stock(df_demanda, df_maestro):
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

    if not df_maestro.empty:
        resumen = resumen.merge(df_maestro[['sku', 'precio_venta']], on='sku', how='left')
        resumen['valor_perdido_euros'] = resumen['unidades_perdidas'] * resumen['precio_venta']
    else:
        resumen['valor_perdido_euros'] = 0

    st.session_state["resumen_historico"] = resumen
    return resumen


def consolidar_proyeccion_futura(df_forecast, df_stock, df_repos, df_maestro):
    from modules.stock_projector import project_stock

    resumen_futuro = []

    for sku in df_forecast['sku'].unique():
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

    if not df_maestro.empty:
        df_final = df_final.merge(df_maestro, on='sku', how='left')

    st.session_state['stock_proyectado'] = df_final
    return df_final


def generar_contexto_negocio(df_forecast, df_proyeccion, df_hist):
    try:
        # --- Verificación obligatoria ---
        if "resultados_inventario" not in st.session_state or not st.session_state["resultados_inventario"]:
            return "⚠️ Las políticas de inventario aún no han sido calculadas. Ve al módulo 'Gestión de Inventarios' primero."

        resumen_forecast = df_forecast[df_forecast['tipo_mes'] == 'proyección'].groupby('sku')['forecast'].mean().round(1).reset_index()
        resumen_forecast.columns = ['SKU', 'Forecast Promedio Mensual']

        stock_final = df_proyeccion.sort_values('mes').groupby('sku').last().reset_index()
        stock_final = stock_final[['sku', 'stock_final_mes']]
        stock_final.columns = ['SKU', 'Stock Proyectado']

        df_proy = df_proyeccion.groupby('sku').agg({
            'forecast': 'sum',
            'stock_final_mes': 'last'
        }).reset_index()
        df_proy['unidades_a_comprar'] = df_proy['forecast'] - df_proy['stock_final_mes']
        df_proy['accion'] = df_proy['unidades_a_comprar'].apply(lambda x: 'Comprar' if x > 0 else 'No comprar')
        compras = df_proy[df_proy['accion'] == 'Comprar'][['sku', 'unidades_a_comprar']].rename(columns={
            'sku': 'SKU',
            'unidades_a_comprar': 'Unidades a Comprar'
        })

        perdidas = df_hist.groupby('sku')[['unidades_perdidas', 'valor_perdido_euros']].sum().reset_index()
        perdidas.columns = ['SKU', 'Unidades Perdidas', 'Pérdida Hist. (€)']

        tasa_quiebre = df_hist.groupby('sku').apply(
            lambda x: (x['unidades_perdidas'].sum() / (x['demanda_real'].sum() + x['unidades_perdidas'].sum()) * 100)
            if (x['demanda_real'].sum() + x['unidades_perdidas'].sum()) > 0 else 0
        ).reset_index(name='Tasa de Quiebre (%)')
        tasa_quiebre.columns = ['SKU', 'Tasa de Quiebre (%)']

        demanda_total = df_hist.groupby('sku')[['demanda_real', 'demanda_limpia']].sum().reset_index()
        demanda_total.columns = ['SKU', 'Demanda Real 12M', 'Demanda Limpia 12M']

        # --- Cargar políticas desde resultados_inventario ---
        resultados = st.session_state["resultados_inventario"]
        politicas_df = pd.DataFrame([
            {
                "SKU": sku,
                "ROP": datos["politicas"].get("rop_original", 0),
                "EOQ": datos["politicas"].get("eoq", 0),
                "Safety Stock": datos["politicas"].get("safety_stock", 0)
            }
            for sku, datos in resultados.items()
            if datos.get("politicas") is not None
        ])

        df_contexto = resumen_forecast \
            .merge(stock_final, on='SKU', how='left') \
            .merge(compras, on='SKU', how='left') \
            .merge(perdidas, on='SKU', how='left') \
            .merge(tasa_quiebre, on='SKU', how='left') \
            .merge(demanda_total, on='SKU', how='left') \
            .merge(politicas_df, on='SKU', how='left')

        df_contexto = df_contexto.fillna(0)
        st.session_state['contexto_negocio_por_sku'] = df_contexto

        texto = "Aquí tienes un resumen del negocio por SKU:\n\n"
        for _, row in df_contexto.iterrows():
            texto += (
                f"🔹 SKU: {row['SKU']}\n"
                f"   • Forecast mensual promedio: {row['Forecast Promedio Mensual']} unidades\n"
                f"   • Stock proyectado: {row['Stock Proyectado']} unidades\n"
                f"   • Unidades a comprar: {int(row['Unidades a Comprar']) if row['Unidades a Comprar'] > 0 else 0}\n"
                f"   • Unidades perdidas históricas: {int(row['Unidades Perdidas'])}\n"
                f"   • Pérdida histórica: € {int(row['Pérdida Hist. (€)'])}\n"
                f"   • Tasa de quiebre: {row['Tasa de Quiebre (%)']:.1f}%\n"
                f"   • Demanda real 12M: {int(row['Demanda Real 12M'])}\n"
                f"   • Demanda limpia 12M: {int(row['Demanda Limpia 12M'])}\n"
                f"   • ROP: {int(row['ROP'])}, EOQ: {int(row['EOQ'])}, Safety Stock: {int(row['Safety Stock'])}\n\n"
            )

        st.session_state["contexto_negocio"] = texto

        # --- Generar contexto general agregado ---
        contexto_general = {}
        contexto_general["Total Unidades a Comprar"] = int(df_contexto["Unidades a Comprar"].sum())
        contexto_general["Total SKUs a Comprar"] = int((df_contexto["Unidades a Comprar"] > 0).sum())

        maestro = st.session_state.get("maestro", pd.DataFrame())
        if not maestro.empty:
            df_tmp = df_contexto.merge(maestro[['sku', 'costo_fabricacion']], left_on="SKU", right_on="sku", how="left")
            df_tmp['Costo Total Compra (€)'] = df_tmp['Unidades a Comprar'] * df_tmp['costo_fabricacion']
            contexto_general["Costo Total Compra (€)"] = int(df_tmp['Costo Total Compra (€)'].sum())
        else:
            contexto_general["Costo Total Compra (€)"] = 0

        repos = st.session_state.get("reposiciones", pd.DataFrame())
        if not repos.empty:
            contexto_general["Total Unidades en Camino"] = int(repos['cantidad'].sum())
            unidades_en_camino_por_sku = repos.groupby('sku')['cantidad'].sum().reset_index()
            contexto_general["Unidades en Camino por SKU"] = unidades_en_camino_por_sku.to_dict(orient="records")
        else:
            contexto_general["Total Unidades en Camino"] = 0
            contexto_general["Unidades en Camino por SKU"] = []

        st.session_state["contexto_negocio_general"] = contexto_general

        return texto

    except Exception as e:
        return f"No se pudo generar el contexto dinámico del negocio aún. Error: {e}"
