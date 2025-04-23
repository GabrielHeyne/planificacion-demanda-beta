import streamlit as st
import pandas as pd
import unidecode

def responder_general(pregunta):
    contexto = st.session_state.get("contexto_negocio_general", {})
    pregunta_limpia = unidecode.unidecode(pregunta.lower())

    # --- INTENCIÓN: Ranking de pérdidas ---
    if any(p in pregunta_limpia for p in ["top perdidas", "mayor perdidas", "mas perdidas", "quiebre alto", "productos que mas se pierden", "ranking perdidas", "sku con mas perdidas", "sku con mayor perdida", "sku mas perdidas", "productos con mas perdidas", "mas quiebres", "top 10 perdidas", "top de perdidas", "top 10 de perdidas"]):
        df_hist = st.session_state.get("resumen_historico", pd.DataFrame())
        if not df_hist.empty:
            top = df_hist.groupby("sku")["unidades_perdidas"].sum().sort_values(ascending=False).head(10).reset_index()
            respuesta = "🔝 Top 10 SKUs con más unidades perdidas:\n\n"
            for i, row in top.iterrows():
                respuesta += f"{i+1}. {row['sku']}: {int(row['unidades_perdidas'])} unidades perdidas\n"
            return respuesta

    # --- INTENCIÓN: Ranking de ventas ---
    if any(p in pregunta_limpia for p in ["top ventas", "top de ventas", "mas vendidos", "productos mas vendidos", "ventas altas", "mayor venta", "skus mas vendidos", "top 10 de ventas", "con mas ventas", "productos que mas venden", "mayores ventas", "mas ventas"]):
        df_hist = st.session_state.get("resumen_historico", pd.DataFrame())
        if not df_hist.empty:
            top = df_hist.groupby("sku")["demanda_real"].sum().sort_values(ascending=False).head(10).reset_index()
            respuesta = "🏆 Top 10 SKUs más vendidos (demanda real):\n\n"
            for i, row in top.iterrows():
                respuesta += f"{i+1}. {row['sku']}: {int(row['demanda_real'])} unidades vendidas\n"
            return respuesta


    # --- INTENCIÓN: Descargar detalle de compras ---
    if any(p in pregunta_limpia for p in ["excel", "descargar", "detalle", "archivo"]) and any(p in pregunta_limpia for p in ["comprar", "compras", "reponer"]):
        df = st.session_state.get("contexto_negocio_por_sku", pd.DataFrame())
        df_export = df[df["Unidades a Comprar"] > 0][["SKU", "Unidades a Comprar"]]
        st.markdown("### 📋 Detalle de SKUs a Comprar")
        st.dataframe(df_export, use_container_width=True)
        st.download_button("📥 Descargar Excel de compras", df_export.to_csv(index=False).encode("utf-8"), "compras_sugeridas.csv", "text/csv")
        return "📄 Aquí tienes el archivo con el detalle de los SKUs a comprar."

    # --- INTENCIÓN: Descargar demanda histórica ---
    if any(p in pregunta_limpia for p in ["excel", "descargar", "archivo"]) and any(p in pregunta_limpia for p in ["demanda historica", "demanda pasada", "real", "historial"]):
        df = st.session_state.get("demanda_limpia", pd.DataFrame())
        df_export = df[["sku", "fecha", "demanda", "demanda_sin_outlier"]]
        st.markdown("### 📋 Demanda Histórica")
        st.dataframe(df_export.head(50), use_container_width=True)
        st.download_button("📥 Descargar demanda histórica", df_export.to_csv(index=False).encode("utf-8"), "demanda_historica.csv", "text/csv")
        return "📄 Aquí tienes el archivo con la demanda histórica."

    # --- INTENCIÓN: Descargar políticas de inventario ---
    if any(p in pregunta_limpia for p in ["excel", "descargar", "archivo", "detalle"]) and any(p in pregunta_limpia for p in ["politica", "rop", "eoq", "safety"]):
        df = st.session_state.get("contexto_negocio_por_sku", pd.DataFrame())
        df_export = df[["SKU", "ROP", "EOQ", "Safety Stock"]]
        st.markdown("### 📋 Políticas de Inventario")
        st.dataframe(df_export, use_container_width=True)
        st.download_button("📥 Descargar políticas", df_export.to_csv(index=False).encode("utf-8"), "politicas_inventario.csv", "text/csv")
        return "📄 Aquí tienes el archivo con las políticas de inventario por SKU."

    # --- INTENCIÓN: Descargar forecast y demanda proyectada ---
    if any(p in pregunta_limpia for p in ["excel", "descargar", "archivo"]) and any(p in pregunta_limpia for p in ["forecast", "pronostico", "proyeccion"]):
        df = st.session_state.get("forecast", pd.DataFrame())
        df_export = df[["sku", "mes", "demanda", "demanda_limpia", "forecast", "tipo_mes"]]
        st.markdown("### 📋 Forecast y Demanda")
        st.dataframe(df_export.head(50), use_container_width=True)
        st.download_button("📥 Descargar forecast", df_export.to_csv(index=False).encode("utf-8"), "forecast_y_demanda.csv", "text/csv")
        return "📄 Aquí tienes el archivo con la demanda proyectada y forecast."

    # --- INTENCIÓN: Reposiciones en camino (PRIORIDAD ALTA) ---
    if any(p in pregunta_limpia for p in ["en camino", "en transito", "vienen", "reposiciones", "en viaje"]):
        return f"🚚 Actualmente hay **{contexto.get('Total Unidades en Camino', 0):,} unidades en camino**."

    # --- INTENCIÓN: Stock actual total ---
    if any(x in pregunta_limpia for x in ["stock", "inventario", "existencias", "disponible", "tenemos"]):
        df_stock = st.session_state.get("stock_actual", pd.DataFrame())
        total = int(df_stock['stock'].sum()) if not df_stock.empty else 0
        return f"📦 El stock actual total es de **{total:,} unidades**."

    # --- INTENCIÓN: Políticas de inventario ---
    if any(x in pregunta_limpia for x in ["politica", "rop", "eoq", "safety", "inventario de seguridad"]):
        df = st.session_state.get("contexto_negocio_por_sku", pd.DataFrame())
        st.markdown("### 📋 Vista previa: Políticas de Inventario")
        st.dataframe(df[["SKU", "ROP", "EOQ", "Safety Stock"]], use_container_width=True)
        st.download_button("📥 Descargar políticas de inventario", df.to_csv(index=False).encode("utf-8"), "politicas_inventario.csv", "text/csv")
        return "📄 Aquí tienes las políticas de inventario por SKU."

    # --- INTENCIÓN: Compra sugerida ---
    if (
        any(x in pregunta_limpia for x in ["cuanto", "cuantas", "deberia", "necesito", "reponer", "comprar"]) and
        not any(x in pregunta_limpia for x in ["stock", "inventario", "existencias", "politica", "en camino", "en transito", "reposiciones", "vienen"])
    ):
        return (
            f"🛒 En total, deberías comprar **{contexto.get('Total Unidades a Comprar', 0):,} unidades** "
            f"distribuidas en **{contexto.get('Total SKUs a Comprar', 0):,} SKUs**."
        )

    # --- INTENCIÓN: Costo total ---
    if any(p in pregunta_limpia for p in ["costo", "cuanto cuesta", "valor total", "precio total", "fabricacion total"]):
        return f"💰 El costo total estimado de fabricación para la compra es de **€{contexto.get('Costo Total Compra (€)', 0):,}**."

    # --- INTENCIÓN: Ventas totales / demanda real ---
    if any(p in pregunta_limpia for p in ["vendidas", "venta real", "demanda real", "cuanto se ha vendido", "demanda historica", "ventas totales"]):
        df_demand = st.session_state.get("demanda_limpia", pd.DataFrame())
        total_vendidas = int(df_demand["demanda"].sum()) if not df_demand.empty else 0
        return f"📈 En los últimos 12 meses se han vendido **{total_vendidas:,} unidades**."

    # --- INTENCIÓN: Pérdidas históricas ---
    if any(p in pregunta_limpia for p in ["perdidas", "productos perdidos", "no se vendieron", "unidades que faltaron"]):
        total_perdidas = contexto.get("Total Unidades Perdidas", None)
        if total_perdidas is None:
            df_hist = st.session_state.get("resumen_historico", pd.DataFrame())
            total_perdidas = int(df_hist["unidades_perdidas"].sum()) if not df_hist.empty else 0
        return f"🔻 Se han perdido **{total_perdidas:,} unidades** por quiebres de stock."

    # --- INTENCIÓN: Pérdidas económicas ---
    if any(p in pregunta_limpia for p in ["euros", "valor perdido", "venta perdida", "perdida economica"]):
        df_hist = st.session_state.get("resumen_historico", pd.DataFrame())
        perdidas_eur = int(df_hist["valor_perdido_euros"].sum()) if not df_hist.empty else 0
        return f"💸 La pérdida total estimada en euros por quiebres ha sido de **€{perdidas_eur:,}**."

    # --- INTENCIÓN: Tasa de quiebre ---
    if any(p in pregunta_limpia for p in ["tasa de quiebre", "porcentaje perdido", "nivel de servicio", "break rate"]):
        df_hist = st.session_state.get("resumen_historico", pd.DataFrame())
        if not df_hist.empty:
            perdidas = df_hist["unidades_perdidas"].sum()
            vendidas = df_hist["demanda_real"].sum()
            tasa = (perdidas / (vendidas + perdidas) * 100) if (vendidas + perdidas) > 0 else 0
            return f"📉 La tasa de quiebre acumulada es de **{tasa:.1f}%**."
        return "No se pudo calcular la tasa de quiebre porque no hay datos históricos suficientes."


    return None
