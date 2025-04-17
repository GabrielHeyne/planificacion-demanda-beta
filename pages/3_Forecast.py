import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from modules.forecast_engine import forecast_simple

# Cargar CSS
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Cargar el CSS
load_css()

# Render logo
from utils import render_logo_sidebar  
render_logo_sidebar()

st.markdown('<h1 style="font-size: 26px; margin-bottom: 2px; font-weight: 500;">FORECAST DE DEMANDA POR SKU</h1>', unsafe_allow_html=True)


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

    # Calcular Demanda Promedio (Últimos 6 meses móviles)
    ultimo_mes_con_demandas = df_filtrado[df_filtrado['demanda'] > 0]['mes'].max()  # Último mes con demanda

    # Filtramos los últimos 6 meses antes del último mes con demanda
    df_ultimos_6_meses = df_filtrado[df_filtrado['mes'] <= ultimo_mes_con_demandas].tail(6)

    # Calcular el promedio de demanda de esos meses
    if len(df_ultimos_6_meses) > 0:
        demanda_promedio_6 = df_ultimos_6_meses['demanda'].mean()
    else:
        demanda_promedio_6 = 0.0  # Si no hay datos, asignamos 0

    # Redondear la demanda promedio a 1 decimal
    demanda_promedio_6 = round(demanda_promedio_6, 1)

    # Forecast Proyectado (redondeado)
    forecast_proyectado = df_filtrado['forecast'].mean()
    forecast_proyectado = round(forecast_proyectado, 1)

    # Calcular DPA resumen basado solo en meses tipo backtest
    df_backtest = df_filtrado[df_filtrado['tipo_mes'] == 'backtest'].sort_values('mes')
    dpa_valores = df_backtest['dpa_movil'].dropna()

    if not dpa_valores.empty:
        dpa_resumen = dpa_valores.iloc[-3:].mean()
        dpa_resumen = round(dpa_resumen, 3)  # Redondear el DPA a 3 decimales
    else:
        dpa_resumen = "–"  # Si no hay datos, mostrar guion

    # Mostrar los KPIs en tarjetas
    kpi_template = """
    <div style="
            background-color:#ffffff;
            padding:16px;
            border-radius:12px;
            text-align:center;
            height:110px;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
            margin: 10px;
            border: 1px solid #B0B0B0;
            box-shadow: none;
        ">
        <div style="font-size:14px; font-weight:500; margin-bottom:6px;">{label}</div>
        <div style="font-size:30px;">{value}</div>
    </div>
    """

    col1, col2, col3 = st.columns(3)

    # Mostrar Demanda Promedio
    col1.markdown(kpi_template.format(label="Demanda Promedio (Últimos 6 meses)", value=f"{demanda_promedio_6} unidades"), unsafe_allow_html=True)

    # Mostrar Forecast Proyectado
    col2.markdown(kpi_template.format(label="Forecast Proyectado", value=f"{forecast_proyectado} unidades"), unsafe_allow_html=True)

    # Mostrar DPA móvil
    col3.markdown(kpi_template.format(label="DPA Móvil (Últimos meses de Backtest)", value=f"{dpa_resumen:.1%}" if isinstance(dpa_resumen, float) else dpa_resumen), unsafe_allow_html=True)

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
        font_family='Poppins, sans-serif',  # Fuente del gráfico
        uniformtext_minsize=8,
        uniformtext_mode='hide',
        xaxis_tickangle=45,
        legend=dict(
            orientation='h',  # Esto pone la leyenda de manera horizontal
            yanchor='bottom',  # Pone la leyenda arriba
            y=1.05,  # Un pequeño ajuste para mover la leyenda por encima del gráfico
            xanchor='center',  # Centra la leyenda horizontalmente
            x=0.5
        )
    )

    # Título para el gráfico con el SKU seleccionado, centrado
    st.markdown(f'<h1 style="font-size: 22px; margin-bottom: 2px; font-weight: 400; text-align: center;">📊 Gráfico: Demanda Histórica y Forecast para SKU: {sku_seleccionado}</h1>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)

    # -------- TABLA DETALLE --------
    df_tabla = df_filtrado.copy()
    df_tabla['dpa_movil'] = df_tabla['dpa_movil'].apply(lambda x: f"{x:.2%}" if pd.notnull(x) and x > 0 else "–")

    columnas_ordenadas = ['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'tipo_mes', 'dpa_movil']
    df_tabla = df_tabla[columnas_ordenadas]

    st.subheader(f"📋 Detalle del Forecast para SKU: {sku_seleccionado}")
    st.dataframe(df_tabla)

    # --- Crear archivo CSV para descarga ---
    def generar_csv(df_forecast):
        df_forecast = df_forecast.copy()
        df_forecast['forecast'] = df_forecast['forecast'].round(0)
        
        # Selección de las columnas relevantes
        df_export = df_forecast[['sku', 'mes', 'demanda', 'demanda_limpia', 'forecast', 'dpa_movil']]
        df_export.columns = ['SKU', 'Mes', 'Demanda Real', 'Demanda Limpia', 'Forecast', 'DPA Móvil']
        
        # Convertir el dataframe a un archivo CSV
        csv = df_export.to_csv(index=False).encode('utf-8')
        return csv

    # --- Botón para descargar el CSV ---
    csv = generar_csv(df_forecast)
    st.download_button(
        label="📥 Descargar Forecast Calculado",
        data=csv,
        file_name="forecast.csv",
        mime="text/csv"
    )
