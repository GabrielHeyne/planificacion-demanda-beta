import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from utils.render_logo_sidebar import render_logo_sidebar
from utils.filtros import aplicar_filtro_sku  # Importamos la función de filtros

# --- Cargar estilos y logo ---
def load_css():
    with open("utils/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
load_css()
render_logo_sidebar()

# --- Título de la página ---
st.markdown("<h1 style='font-size: 26px; font-weight: 500;'>📦 PROYECCIÓN DE STOCK MENSUAL</h1>", unsafe_allow_html=True)
st.markdown("<p style='font-size: 16px;'>Proyección de stock por SKU y análisis de pérdidas estimadas</p>", unsafe_allow_html=True)

# --- Validaciones de datos ---
if "proyeccion_stock" not in st.session_state or st.session_state["proyeccion_stock"].empty:
    st.warning("⚠️ Aún no se ha proyectado el stock. Ve a la página de Inicio y presiona 'Comenzar planificación'.")
    st.stop()

df_proyeccion = st.session_state["proyeccion_stock"].copy()
df_maestro = st.session_state.get("maestro", pd.DataFrame())
df_stock = st.session_state.get("stock_actual", pd.DataFrame())
df_stock_hist = st.session_state.get("stock_historico", pd.DataFrame())

# --- Filtro reutilizable por SKU ---
df_proyeccion['mes'] = pd.to_datetime(df_proyeccion['mes'])  # Asegurarse de que la columna mes sea datetime
df_filtrado, sku_sel = aplicar_filtro_sku(df_proyeccion, incluir_todos=False, key="sku_proyeccion")  # Aplicar el filtro por SKU con la función de filtros.py

df_resultado = df_filtrado[df_filtrado["sku"] == sku_sel].copy()
if df_resultado.empty:
    st.warning("⚠️ No hay proyección disponible para este SKU.")
    st.stop()

# --- Stock inicial (última fila disponible)
stock_inicial = int(df_filtrado["stock_inicial_mes"].iloc[0])
unidades_perdidas = int(df_resultado["unidades_perdidas"].sum())
unidades_repos = int(df_resultado["repos_aplicadas"].sum())

# --- KPIs visuales ---
st.markdown("<div class='titulo-con-fondo'>📌 Información del Producto Seleccionado</div>", unsafe_allow_html=True)

def tarjeta_kpi(label, value):
    return f"""
    <div style="
        background-color:#ffffff;
        padding:16px;
        border-radius:12px;
        text-align:center;
        height:90px;
        width:100%;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        margin: 10px;
        border: 1px solid #B0B0B0;
    ">
        <div style="font-size:14px; font-weight:500;">{label}</div>
        <div style="font-size:26px;">{value}</div>
    </div>
    """

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(tarjeta_kpi("Stock Inicial", f"{stock_inicial} unidades"), unsafe_allow_html=True)
with col2:
    st.markdown(tarjeta_kpi("Unidades en Camino", f"{unidades_repos} unidades"), unsafe_allow_html=True)
with col3:
    st.markdown(tarjeta_kpi("Unidades Perdidas Proyectadas", f"{unidades_perdidas} unidades"), unsafe_allow_html=True)

# --- Tabla de proyección ---
st.markdown("<div class='titulo-con-fondo'>📊 Tabla de Proyección Detallada</div>", unsafe_allow_html=True)
st.dataframe(df_resultado, use_container_width=True)

# --- Gráficos en 2 columnas ---
colg1, colg2 = st.columns(2)

with colg1:
    st.markdown("<div class='titulo-con-fondo'>📉 Stock Proyectado por Mes</div>", unsafe_allow_html=True)
    fig_stock = go.Figure()
    fig_stock.add_trace(go.Scatter(
        x=df_resultado['mes'],
        y=df_resultado['stock_final_mes'],
        mode='lines+markers',
        name='Stock Final',
        line=dict(color='royalblue', width=3),
        marker=dict(size=7)
    ))
    fig_stock.update_layout(
        xaxis_title="Mes",
        yaxis_title="Unidades",
        height=420,
        margin=dict(t=50),
        xaxis=dict(tickformat="%b %Y", dtick="M1", tickangle=-45),
        yaxis=dict(range=[0, max(df_resultado['stock_final_mes'].max(), 10)])
    )
    st.plotly_chart(fig_stock, use_container_width=True)

with colg2:
    st.markdown("<div class='titulo-con-fondo'>💸 Pérdidas Estimadas por Quiebres (en €)</div>", unsafe_allow_html=True)
    fig_loss = go.Figure()
    fig_loss.add_trace(go.Bar(
        x=df_resultado['mes'],
        y=df_resultado['perdida_proyectada_euros'],
        name="Pérdida estimada (€)",
        marker_color='crimson'
    ))
    fig_loss.update_layout(
        xaxis_title="Mes",
        yaxis_title="Pérdida (€)",
        height=420,
        margin=dict(t=50),
        xaxis=dict(tickformat="%b %Y", dtick="M1", tickangle=-45),
        yaxis=dict(range=[0, max(df_resultado['perdida_proyectada_euros'].max(), 10)])
    )
    st.plotly_chart(fig_loss, use_container_width=True)

# --- Gráfico de stock histórico mensual ---
if not df_stock_hist.empty:
    df_hist = df_stock_hist[df_stock_hist['sku'] == sku_sel].copy()
    if not df_hist.empty:
        df_hist['mes'] = pd.to_datetime(df_hist['fecha']).dt.to_period('M').dt.to_timestamp()
        df_hist = df_hist.groupby('mes')['stock'].sum().reset_index()

        st.markdown("<div class='titulo-con-fondo'>📚 Evolución Histórica del Stock</div>", unsafe_allow_html=True)
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=df_hist['mes'],
            y=df_hist['stock'],
            mode='lines+markers',
            name='Stock Histórico',
            line=dict(color='gray', width=3),
            marker=dict(size=7)
        ))
        fig_hist.update_layout(
            xaxis_title="Mes",
            yaxis_title="Stock Disponible",
            height=420,
            margin=dict(t=50),
            xaxis=dict(tickformat="%b %Y", dtick="M1", tickangle=-45)
        )
        st.plotly_chart(fig_hist, use_container_width=True)

# --- Descargar CSV ---
def generar_csv(df):
    df_export = df.copy()
    df_export.columns = [col.replace("_", " ").capitalize() for col in df_export.columns]
    return df_export.to_csv(index=False).encode('utf-8')

csv = generar_csv(df_resultado)
st.download_button(
    label="📥 Descargar archivo CSV",
    data=csv,
    file_name=f"proyeccion_stock_{sku_sel}.csv",
    mime="text/csv"
)

# --- Gráfico de Demanda Mensual Real vs Limpia ---
if "demanda_limpia" in st.session_state:
    df_demanda = st.session_state["demanda_limpia"].copy()
    df_demanda['fecha'] = pd.to_datetime(df_demanda['fecha'])
    df_demanda['mes'] = df_demanda['fecha'].dt.to_period('M').dt.to_timestamp()

    df_mensual = df_demanda.groupby(['sku', 'mes'])[['demanda', 'demanda_sin_outlier']].sum().reset_index()
    df_sku_mensual = df_mensual[df_mensual['sku'] == sku_sel]

    if not df_sku_mensual.empty:
        st.markdown("<div class='titulo-con-fondo'>📈 Demanda Mensual Real vs Limpia</div>", unsafe_allow_html=True)
        fig_demanda = go.Figure()
        fig_demanda.add_trace(go.Scatter(
            x=df_sku_mensual['mes'],
            y=df_sku_mensual['demanda'],
            mode='lines+markers',
            name='Demanda Real',
            line=dict(color='darkblue', width=2),
            marker=dict(size=6)
        ))
        fig_demanda.add_trace(go.Scatter(
            x=df_sku_mensual['mes'],
            y=df_sku_mensual['demanda_sin_outlier'],
            mode='lines+markers',
            name='Demanda Limpia',
            line=dict(color='orange', width=2),
            marker=dict(size=6)
        ))
        fig_demanda.update_layout(
            xaxis_title="Mes",
            yaxis_title="Unidades",
            height=420,
            margin=dict(t=50),
            xaxis=dict(tickformat="%b %Y", dtick="M1", tickangle=-45),
            legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")  # 👈 leyenda arriba y centrada
        )
        st.plotly_chart(fig_demanda, use_container_width=True)
