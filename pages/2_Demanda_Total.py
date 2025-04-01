import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import timedelta, date
from dateutil.relativedelta import relativedelta
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

# --- Fuente Montserrat ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif !important;
    }
    .css-1v3fvcr { font-weight: normal !important; } /* Asegura que el peso sea normal */
    </style>
""", unsafe_allow_html=True)

st.title("📈 DEMANDA TOTAL Y QUIEBRES")
st.subheader("VISUALIZACIÓN DE DEMANDA REAL/LIMPIA POR SKU, JUNTO CON UNIDADES PERDIDAS POR QUIEBRES DE STOCK")

# --- Cargar demanda limpia desde el archivo --- 
archivo_demanda_limpia = st.file_uploader("Sube el archivo de Demanda Limpia (Excel)", type=["xlsx"])

if archivo_demanda_limpia is not None:
    # Leer archivo
    df = pd.read_excel(archivo_demanda_limpia)

    if df.empty:
        st.warning("⚠️ El archivo está vacío. Por favor verifica el archivo y vuelve a intentar.")
        st.stop()

    # --- Preprocesamiento básico ---
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['semana'] = df['fecha'].dt.to_period('W').apply(lambda r: r.start_time)

    # --- Filtro por SKU ---
    skus = sorted(df['sku'].unique())
    skus.insert(0, "TODOS")
    sku_seleccionado = st.selectbox("Selecciona un SKU", skus)

    df_filtrado = df.copy() if sku_seleccionado == "TODOS" else df[df['sku'] == sku_seleccionado]

    # --- Filtro de fechas (últimos 24 meses por defecto) ---
    fecha_min = df_filtrado['fecha'].min().date()
    fecha_max = df_filtrado['fecha'].max().date()
    fecha_min_defecto = max(fecha_min, (fecha_max - relativedelta(months=12)))

    rango_fecha = st.date_input(
        "Selecciona el rango de fechas",
        value=(fecha_min_defecto, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )

    # Aplicar filtro
    fecha_inicio = pd.to_datetime(rango_fecha[0])
    fecha_fin = pd.to_datetime(rango_fecha[1])
    df_filtrado = df_filtrado[(df_filtrado['fecha'] >= fecha_inicio) & (df_filtrado['fecha'] <= fecha_fin)]

    # --- KPIs y quiebres ---
    df_quiebre = df_filtrado.copy()
    df_quiebre['quiebre_stock'] = (df_quiebre['demanda'] == 0) & (df_quiebre['demanda_sin_outlier'] > 0)
    df_quiebre['semana'] = df_quiebre['fecha'].dt.to_period('W').dt.start_time

    total_semanas = df_quiebre['semana'].nunique()
    quiebre_semanas = df_quiebre[df_quiebre['quiebre_stock']].groupby('semana').ngroup().nunique()
    porcentaje_quiebre = round((quiebre_semanas / total_semanas) * 100, 1) if total_semanas > 0 else 0

    # --- Calcular total de unidades perdidas ---
    df_quiebre['unidades_perdidas'] = df_quiebre.apply(
        lambda row: row['demanda_sin_outlier'] if row['quiebre_stock'] else 0, axis=1
    )
    total_unidades_perdidas = int(df_quiebre['unidades_perdidas'].sum())

    # --- Mostrar KPIs (ahora con 4 columnas) ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Demanda Real Total", f"{int(df_filtrado['demanda'].sum()):,} un.")
    with col2:
        st.metric("Demanda Limpia Total", f"{int(df_filtrado['demanda_sin_outlier'].sum()):,} un.")
    with col3:
        st.metric("% Quiebre de Stock", f"{porcentaje_quiebre} %")
    with col4:
        st.metric("Unidades Perdidas", f"{total_unidades_perdidas:,} un.")

    # --- Gráfico de torta (irá debajo del gráfico semanal) ---
    fig_quiebre = go.Figure(data=[go.Pie(
        labels=['Con Quiebre', 'Sin Quiebre'],
        values=[quiebre_semanas, total_semanas - quiebre_semanas],
        hole=0.4,
        marker=dict(colors=['#EF553B', '#00CC96'])
    )])
    fig_quiebre.update_layout(
        title_text=f'Quiebre de Stock - {sku_seleccionado}',
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center", font=dict(family="Montserrat", size=12))
    )

    # --- Funciones cacheadas para procesamiento ---
    @st.cache_data
    def procesar_demanda(df_filtrado):
        # --- Semanal ---
        df_semanal = df_filtrado.groupby('semana').agg({
            'demanda': 'sum',
            'demanda_sin_outlier': 'sum'
        }).reset_index()

        fig_semanal = px.line(
            df_semanal,
            x='semana',
            y=['demanda', 'demanda_sin_outlier'],
            labels={'value': 'Unidades', 'variable': 'Tipo de Demanda'},
            title=f"Demanda Semanal - {sku_seleccionado}"
        )
        fig_semanal.update_layout(width=700, height=400)
        fig_semanal.for_each_trace(lambda t: t.update(name='Demanda Real') if t.name == 'demanda' else t.update(name='Demanda Limpia'))

        # --- Mensual ---
        df_tmp = df_filtrado.copy()
        df_tmp['fecha_fin'] = df_tmp['fecha'] + timedelta(days=6)
        rows = []

        for _, row in df_tmp.iterrows():
            dias = pd.date_range(start=row['fecha'], end=row['fecha_fin'])
            meses = dias.to_series().dt.to_period('M').value_counts().sort_index()
            total_dias = len(dias)
            for periodo, cantidad_dias in meses.items():
                fraccion = cantidad_dias / total_dias
                rows.append({
                    'mes': periodo.to_timestamp(),
                    'demanda': row['demanda'] * fraccion,
                    'demanda_sin_outlier': row['demanda_sin_outlier'] * fraccion
                })

        df_mensual = pd.DataFrame(rows).groupby('mes')[['demanda', 'demanda_sin_outlier']].sum().reset_index()

        # --- Filtrar meses incompletos (al menos 2 semanas distintas) ---
        df_tmp['mes'] = df_tmp['fecha'].dt.to_period('M').dt.to_timestamp()
        df_tmp['semana'] = df_tmp['fecha'].dt.to_period('W').dt.start_time
        semanas_por_mes = df_tmp.groupby('mes')['semana'].nunique().reset_index()
        meses_completos = semanas_por_mes[semanas_por_mes['semana'] >= 2]['mes']
        df_mensual = df_mensual[df_mensual['mes'].isin(meses_completos)]

        fig_mensual = px.line(
            df_mensual,
            x='mes',
            y=['demanda', 'demanda_sin_outlier'],
            labels={'value': 'Unidades', 'variable': 'Tipo de Demanda'},
            title=f"Demanda Mensual - {sku_seleccionado}"
        )
        fig_mensual.update_layout(width=700, height=400)
        fig_mensual.for_each_trace(lambda t: t.update(name='Demanda Real') if t.name == 'demanda' else t.update(name='Demanda Limpia'))

        return fig_semanal, fig_mensual

    # --- Procesar (cacheado) ---
    fig_semanal, fig_mensual = procesar_demanda(df_filtrado)

    # Ajustes visuales para centrar leyendas
    fig_semanal.update_layout(
        title_text='',  # Esto evita que aparezca "undefined"
        legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center")
    )

    fig_mensual.update_layout(
        title_text='',  # Esto evita que aparezca "undefined"
        legend=dict(orientation="h", y=-0.3, x=0.5, xanchor="center")
    )

    fig_quiebre.update_layout(
        title_text='',  # evitamos que aparezca "undefined"
        legend=dict(
            orientation="h",  # Hace que la leyenda sea horizontal
            y=-0.4,  # Mueve la leyenda un poco más abajo
            x=0.5,  # Centra la leyenda horizontalmente
            xanchor="center",
            font=dict(family="Montserrat", size=12)
        ),
        height=350,  # Ajusta el tamaño aquí según necesites
        margin=dict(t=120)  # Puedes aumentar esto para mover el gráfico hacia abajo
    )

    # Títulos centrados como anotaciones
    fig_semanal.add_annotation(
        text=f"Demanda Semanal - {sku_seleccionado}",
        xref="paper", yref="paper",
        x=0.5, y=1.15,
        showarrow=False,
        font=dict(size=16, family="Montserrat", color="black"),
        align="center"
    )

    fig_mensual.add_annotation(
        text=f"Demanda Mensual - {sku_seleccionado}",
        xref="paper", yref="paper",
        x=0.5, y=1.15,
        showarrow=False,
        font=dict(size=16, family="Montserrat", color="black"),
        align="center"
    )

    fig_quiebre.add_annotation(
        text="Quiebres de Stock",
        xref="paper", yref="paper",
        x=0.5, y=1.35,  # Ajusta esta parte para mover el título más abajo
        showarrow=False,
        font=dict(size=16, family="Montserrat", color="black"),
        align="center"
    )

    # --- Mostrar los gráficos en 3 columnas (alineados) ---
    col1, col2, col3 = st.columns([1.15, 1.15, 1])

    with col1:
        st.plotly_chart(fig_semanal, use_container_width=True)

    with col2:
        st.plotly_chart(fig_mensual, use_container_width=True)

    with col3:
        st.plotly_chart(fig_quiebre, use_container_width=True)

    # --- TOP 10 SKUs con mayor número de unidades perdidas por quiebre de stock ---
    df_quiebre_top = df_quiebre.copy()
    df_quiebre_top['unidades_perdidas'] = df_quiebre_top.apply(
        lambda row: row['demanda_sin_outlier'] if row['quiebre_stock'] else 0, axis=1
    )

    resumen_quiebres = df_quiebre_top.groupby('sku').agg(
        semanas_quiebre=('quiebre_stock', 'sum'),
        semanas_totales=('semana', 'nunique'),
        unidades_perdidas=('unidades_perdidas', 'sum')
    ).reset_index()

    resumen_quiebres['porcentaje_quiebre'] = (
        100 * resumen_quiebres['semanas_quiebre'] / resumen_quiebres['semanas_totales']
    ).round(1)

    # Formatear columnas
    resumen_quiebres['porcentaje_quiebre'] = resumen_quiebres['porcentaje_quiebre'].astype(str) + ' %'
    resumen_quiebres['unidades_perdidas'] = resumen_quiebres['unidades_perdidas'].astype(int)

    # Ordenar por unidades perdidas
    top10_quiebres = resumen_quiebres.sort_values(by='unidades_perdidas', ascending=False).head(10)

    # --- Unidades perdidas por mes --- 
    df_quiebre_top['fecha'] = pd.to_datetime(df_quiebre_top['fecha'])
    df_quiebre_top['mes'] = df_quiebre_top['fecha'].dt.to_period('M').dt.to_timestamp()
    unidades_perdidas_mes = df_quiebre_top[df_quiebre_top['quiebre_stock']].groupby('mes')['unidades_perdidas'].sum().reset_index()
    unidades_perdidas_mes['unidades_perdidas'] = unidades_perdidas_mes['unidades_perdidas'].astype(int)

    fig_barras = px.bar(
        unidades_perdidas_mes,
        x='mes',
        y='unidades_perdidas',
        labels={'mes': 'Mes', 'unidades_perdidas': 'Unidades Perdidas'},
        text='unidades_perdidas'
    )

    fig_barras.update_layout(
        title_text="<span style='font-weight:normal; font-size:16px; font-family: Montserrat; color:black;'>📉 Unidades Perdidas por Mes</span>",
        title_x=0.3,  # Centrado del título
        title_y=0.95,  # Ajustar la posición vertical
        title_font=dict(
            family="Montserrat",
            size=16,
            color="black",
            weight="normal"  # Eliminamos el peso de la fuente
        ),
        font=dict(
            family="Montserrat",
            size=12,
            color="black"
        )
    )

    fig_barras.update_traces(
        marker_color='orange',
        textposition='outside',
        textfont=dict(family="Montserrat", size=12)
    )

    # --- HTML para tabla personalizada centrada y angosta ---
    tabla_html = """
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap" rel="stylesheet">
    <style>
    .table-container {
        font-family: 'Montserrat', sans-serif;
        margin-top: 10px;
    }
    .table-title {
        font-size: 16px;
        font-weight: normal;
        margin-bottom: 10px;
        font-family: 'Montserrat', sans-serif;
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        text-align: center;
        font-family: 'Montserrat', sans-serif;
    }
    .custom-table th {
        background-color: #f3f3f3;
        padding: 6px;
    }
    .custom-table td {
        padding: 6px;
    }
    </style>
    <div class="table-container">
    <div class="table-title">🔔 Top 10 SKUs con mayor número de unidades perdidas por quiebre de stock</div>
    <table class="custom-table">
    <thead>
        <tr>
            <th>SKU</th>
            <th>% Quiebre</th>
            <th>Unidades Perdidas</th>
        </tr>
    </thead>
    <tbody>
    """

    for _, row in top10_quiebres.iterrows():
        tabla_html += f"""
        <tr>
            <td>{row['sku']}</td>
            <td>{row['porcentaje_quiebre']}</td>
            <td>{row['unidades_perdidas']:,}</td>
        </tr>
        """

    tabla_html += "</tbody></table></div>"

    # --- Mostrar tabla y gráfico en 2 columnas ---
    col1, col2 = st.columns([1, 1.4])

    with col1:
        components.html(tabla_html, height=500, scrolling=True)

    with col2:
        st.plotly_chart(fig_barras, use_container_width=True)

