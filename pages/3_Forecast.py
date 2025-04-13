import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import plotly.graph_objects as go
from modules.forecast_engine import forecast_simple

# Fuente moderna Inter + Manrope
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Manrope:wght@600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4, h5, h6, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Manrope', sans-serif !important;
        font-weight: 700 !important;
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Verificar si la demanda está cargada
if 'demanda_limpia' not in st.session_state:
    st.error("⚠️ No se ha cargado la demanda limpia. Por favor, ve a 'Carga Archivos' y vuelve a intentarlo.")
else:
    st.success("📈 Demanda limpia cargada correctamente.")

    df_demanda = st.session_state['demanda_limpia']

    # Evitar recálculo innecesario del forecast
    if 'forecast' not in st.session_state:
        st.session_state['forecast'] = forecast_simple(df_demanda, lead_time_meses=4)

    df_forecast = st.session_state['forecast']

    # Selección de SKU
    sku_seleccionado = st.selectbox("Selecciona un SKU", df_forecast['sku'].unique())

    df_filtrado = df_forecast[df_forecast['sku'] == sku_seleccionado].copy()
    df_filtrado['mes'] = pd.to_datetime(df_filtrado['mes'], format='%Y-%m')

    # Calcular DPA resumen basado solo en meses tipo backtest
    df_backtest = df_filtrado[df_filtrado['tipo_mes'] == 'backtest'].sort_values('mes')
    dpa_valores = df_backtest['dpa_movil'].dropna()

    if not dpa_valores.empty:
        dpa_resumen = dpa_valores.iloc[-3:].mean()
        st.metric("📈 DPA móvil (últimos meses de backtest)", f"{dpa_resumen:.1%}")
    else:
        st.metric("📈 DPA móvil (últimos meses de backtest)", "–")

    # Rango de fechas
    mes_mas_reciente = df_filtrado['mes'].max()
    fecha_inicio_default = mes_mas_reciente - pd.DateOffset(months=17)

    min_date = df_filtrado['mes'].min().date()
    max_date = df_filtrado['mes'].max().date()
    start_date = fecha_inicio_default.date()
    end_date = mes_mas_reciente.date()

    st.markdown("#### Filtra por rango de fechas")
    rango_fechas = st.date_input(
        "Selecciona el rango de meses",
        value=(start_date, end_date),
        min_value=min_date,
        max_value=max_date
    )

    df_filtrado = df_filtrado[
        (df_filtrado['mes'] >= pd.to_datetime(rango_fechas[0])) &
        (df_filtrado['mes'] <= pd.to_datetime(rango_fechas[1]))
    ]

    # Botón de descarga
    st.download_button(
        label="📥 Descargar Forecast Calculado",
        data=df_forecast.to_csv(index=False).encode('utf-8'),
        file_name="forecast.csv",
        mime="text/csv"
    )

    # -------- GRÁFICO --------
    df_plot = df_filtrado.sort_values('mes')
    df_plot['mes_label'] = df_plot['mes'].dt.strftime('%b %Y')

    fig = go.Figure()

    # Demanda histórica (barras)
    fig.add_trace(go.Bar(
        x=df_plot['mes_label'],
        y=df_plot['demanda'],
        name='Demanda histórica',
        marker_color='rgba(65, 105, 225, 0.5)',
        text=df_plot['demanda'],
        textposition='outside'
    ))

    # Forecast proyectado (línea)
    df_forecast_total = df_plot[df_plot['tipo_mes'] != 'histórico'].sort_values('mes')

    fig.add_trace(go.Scatter(
        x=df_forecast_total['mes_label'],
        y=df_forecast_total['forecast'],
        name='Forecast proyectado',
        mode='lines+markers+text',
        line=dict(color='crimson', width=3),
        marker=dict(size=8),
        text=df_forecast_total['forecast'],
        textposition='top center',
        hoverinfo='x+y'
    ))

    fig.update_layout(
        barmode='overlay',
        xaxis_title='Mes',
        yaxis_title='Unidades',
        legend_title='Tipo',
        font_family='Montserrat',
        uniformtext_minsize=8,
        uniformtext_mode='hide',
        xaxis_tickangle=45
    )

    st.subheader(f"📊 Gráfico: Demanda Histórica y Forecast para SKU: {sku_seleccionado}")
    st.plotly_chart(fig, use_container_width=True)

    # -------- TABLA DETALLE --------
    df_tabla = df_filtrado.copy()
    df_tabla['dpa_movil'] = df_tabla['dpa_movil'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) and x > 0 else "–")

    columnas_ordenadas = ['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'tipo_mes', 'dpa_movil']
    df_tabla = df_tabla[columnas_ordenadas]

    st.subheader(f"📋 Detalle del Forecast para SKU: {sku_seleccionado}")
    st.dataframe(df_tabla)

