import streamlit as st
import pandas as pd
import numpy as np
from datetime import date
import plotly.express as px
from modules.forecast_engine import forecast_simple

# Aplicar fuente Montserrat globalmente
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Montserrat&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"]  {
            font-family: 'Montserrat', sans-serif;
        }
    </style>
""", unsafe_allow_html=True)

# Verificar si la demanda limpia está cargada
if 'demanda_limpia' not in st.session_state:
    st.error("⚠️ No se ha cargado la demanda limpia. Por favor, ve a 'Carga Archivos' y vuelve a intentarlo.")
else:
    st.success("📈 Demanda limpia cargada correctamente.")

    # Obtener datos
    df_demanda = st.session_state['demanda_limpia']
    df_forecast = forecast_simple(df_demanda)

    # Filtro por SKU
    sku_seleccionado = st.selectbox("Selecciona un SKU", df_forecast['sku'].unique())

    # Filtrar por SKU y convertir a datetime
    df_filtrado = df_forecast[df_forecast['sku'] == sku_seleccionado].copy()
    df_filtrado['mes'] = pd.to_datetime(df_filtrado['mes'], format='%Y-%m')

    # Calcular fechas por defecto (últimos 18 meses desde la fecha más reciente)
    mes_mas_reciente = df_filtrado['mes'].max()
    fecha_inicio_default = mes_mas_reciente - pd.DateOffset(months=17)

    # Convertir fechas a tipo date para usar en st.date_input
    min_date = df_filtrado['mes'].min().date()
    max_date = df_filtrado['mes'].max().date()
    start_date = fecha_inicio_default.date()
    end_date = mes_mas_reciente.date()

    # Filtro de fechas
    st.markdown("#### Filtra por rango de fechas")
    rango_fechas = st.date_input(
        "Selecciona el rango de meses",
        value=(start_date, end_date),
        min_value=min_date,
        max_value=max_date
    )

    # Filtrar DataFrame por fechas seleccionadas
    df_filtrado = df_filtrado[
        (df_filtrado['mes'] >= pd.to_datetime(rango_fechas[0])) &
        (df_filtrado['mes'] <= pd.to_datetime(rango_fechas[1]))
    ]

    # Guardar forecast completo
    st.session_state['forecast'] = df_forecast

    # Botón de descarga
    st.download_button(
        label="📥 Descargar Forecast Calculado",
        data=df_forecast.to_csv(index=False).encode('utf-8'),
        file_name="forecast.csv",
        mime="text/csv"
    )

    # ---------- GRÁFICO ----------
    df_barras = df_filtrado.copy()
    df_barras = df_barras[~((df_barras['demanda'] <= 0) & (df_barras['forecast'] <= 0))]
    df_barras['tipo'] = np.where(df_barras['demanda'] > 0, 'Demanda histórica',
                          np.where(df_barras['forecast'] > 0, 'Forecast proyectado', ''))
    df_barras = df_barras[df_barras['tipo'] != '']

    df_plot = pd.melt(
        df_barras,
        id_vars=['mes', 'sku'],
        value_vars=['demanda', 'forecast'],
        var_name='tipo_valor',
        value_name='unidades'
    )
    df_plot = df_plot[df_plot['unidades'] > 0]
    tipo_map = {
        'demanda': 'Demanda histórica',
        'forecast': 'Forecast proyectado'
    }
    df_plot['tipo_valor'] = df_plot['tipo_valor'].map(tipo_map)

    # Crear columna con etiqueta legible para el eje X
    df_plot['mes_label'] = df_plot['mes'].dt.strftime('%b %Y')  # Ej: Mar 2024

    # Crear gráfico sin título
    fig = px.bar(
        df_plot,
        x='mes_label',
        y='unidades',
        color='tipo_valor',
        barmode='group',
        text='unidades'
    )

    fig.update_traces(textposition='outside')
    fig.update_layout(
        xaxis_title='Mes',
        yaxis_title='Unidades',
        legend_title='Tipo',
        uniformtext_minsize=8,
        uniformtext_mode='hide',
        font_family="Montserrat"
    )

    fig.update_xaxes(tickmode='linear', tickangle=45)

    # Mostrar gráfico
    st.subheader(f"📊 Gráfico: Demanda Histórica y Forecast para SKU: {sku_seleccionado}")
    st.plotly_chart(fig, use_container_width=True)

    # Mostrar tabla
    st.subheader(f"📋 Detalle del Forecast para SKU: {sku_seleccionado}")
    st.dataframe(df_filtrado)

