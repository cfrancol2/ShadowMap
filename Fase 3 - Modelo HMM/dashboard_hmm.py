#!/usr/bin/env python3
# encoding: utf-8
"""
Dashboard interactivo HMM - Visualización de resultados del modelo
===================================================================
Muestra la matriz de transición entre estados ocultos, probabilidades
de emisión, y análisis individual por atacante con las probabilidades
de pasar de un estado a otro.

Uso:
    streamlit run dashboard_hmm.py

Requiere:
    pip install streamlit pandas plotly numpy
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import pickle
import os
from collections import Counter

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Configuración de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard HMM - Análisis de Comportamiento",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Rutas por defecto
# ---------------------------------------------------------------------------
RUTA_MODELO = "../Datos/modelo_hmm.pkl"
RUTA_REPORTE = "../Datos/reporte_autores.csv"
RUTA_KILL_CHAIN = "kill_chain_fases.json"
RUTA_SECUENCIAS = "../Datos/secuencias_autores.json"

COLORES_FASES = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
NOMBRES_FASES_DEFECTO = [
    "Reconocimiento", "Entrega", "Explotación",
    "Instalación", "C2", "Acciones"
]

# ---------------------------------------------------------------------------
# Funciones de carga
# ---------------------------------------------------------------------------

@st.cache_data
def cargar_modelo(ruta):
    """Carga el modelo HMM entrenado (pickle)."""
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'rb') as f:
            modelo = pickle.load(f)
        return modelo
    except Exception as e:
        st.error(f"Error cargando modelo: {e}")
        return None


@st.cache_data
def cargar_reporte(ruta):
    """Carga el reporte CSV de autores."""
    if not os.path.exists(ruta):
        return None
    try:
        df = pd.read_csv(ruta)
        return df
    except Exception as e:
        st.error(f"Error cargando reporte: {e}")
        return None


@st.cache_data
def cargar_kill_chain(ruta):
    """Carga el JSON de fases de Kill Chain."""
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error cargando Kill Chain: {e}")
        return None


@st.cache_data
def cargar_secuencias(ruta):
    """Carga el JSON de secuencias de autores."""
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        st.error(f"Error cargando secuencias: {e}")
        return None


@st.cache_data
def cargar_datos_enriquecidos(ruta="../Datos/datos_enriquecidos.csv"):
    """Carga el CSV enriquecido de la Fase 2 para contexto."""
    if not os.path.exists(ruta):
        return None
    try:
        df = pd.read_csv(ruta)
        return df
    except:
        return None


def obtener_nombres_fases(mapeo_kill):
    """Obtiene nombres de fases desde el mapeo o usa valores por defecto."""
    if mapeo_kill and 'metadata' in mapeo_kill and 'fases' in mapeo_kill['metadata']:
        fases = mapeo_kill['metadata']['fases']
        return [f['nombre'] for f in fases]
    return NOMBRES_FASES_DEFECTO


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------

st.sidebar.title("🕵️ Dashboard HMM")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Rutas de archivos")

ruta_modelo = st.sidebar.text_input("Modelo HMM (.pkl):", value=RUTA_MODELO)
ruta_reporte = st.sidebar.text_input("Reporte autores (.csv):", value=RUTA_REPORTE)
ruta_kill = st.sidebar.text_input("Kill Chain (.json):", value=RUTA_KILL_CHAIN)
ruta_sec = st.sidebar.text_input("Secuencias (.json):", value=RUTA_SECUENCIAS)

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

with st.spinner("Cargando datos..."):
    modelo = cargar_modelo(ruta_modelo)
    df_reporte = cargar_reporte(ruta_reporte)
    mapeo_kill = cargar_kill_chain(ruta_kill)
    secuencias_data = cargar_secuencias(ruta_sec)

nombres_fases = obtener_nombres_fases(mapeo_kill)
n_fases = len(nombres_fases)

# Estado de carga
datos_disponibles = {
    "modelo": modelo is not None,
    "reporte": df_reporte is not None,
    "kill_chain": mapeo_kill is not None,
    "secuencias": secuencias_data is not None
}

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Estado de datos")

for nombre, disponible in datos_disponibles.items():
    icono = "✅" if disponible else "❌"
    st.sidebar.markdown(f"{icono} {nombre.replace('_', ' ').title()}")

# ---------------------------------------------------------------------------
# Validación mínima
# ---------------------------------------------------------------------------

if not any(datos_disponibles.values()):
    st.title("🕵️ Dashboard HMM - Análisis de Comportamiento")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col2:
        st.warning("### 📂 No se encontraron datos")
        st.markdown("""
        Para usar este dashboard, primero debes ejecutar la Fase 3:

        ```bash
        cd "Fase 3 - Modelo HMM"
        pip install -r requirements.txt
        python modulos/main.py
        ```

        Luego actualiza las rutas en el panel lateral.
        """)
    st.stop()

# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------

st.title("🕵️ Dashboard del Modelo HMM")
st.markdown("---")

# ---------------------------------------------------------------------------
# KPIs generales
# ---------------------------------------------------------------------------

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if modelo is not None:
        st.metric("🧠 Estados Ocultos", modelo.n_components)
    else:
        st.metric("🧠 Estados Ocultos", "N/A")

with col2:
    if modelo is not None:
        st.metric("👁️ Observaciones (Fases)", modelo.emissionprob_.shape[1])
    else:
        st.metric("👁️ Observaciones", "N/A")

with col3:
    if df_reporte is not None:
        st.metric("👤 Autores Analizados", len(df_reporte))
    else:
        st.metric("👤 Autores", "N/A")

with col4:
    if df_reporte is not None and 'confianza_prediccion' in df_reporte.columns:
        conf_prom = df_reporte['confianza_prediccion'].mean()
        st.metric("🎯 Confianza Promedio", f"{conf_prom:.2%}")
    else:
        st.metric("🎯 Confianza Prom.", "N/A")

with col5:
    if df_reporte is not None:
        con_pred = len(df_reporte[df_reporte.get('mensaje', '') == 'OK'])
        st.metric("✅ Predicciones Válidas", con_pred)
    else:
        st.metric("✅ Predicciones", "N/A")

st.markdown("---")

# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Matriz de Transición",
    "📊 Probabilidades de Emisión",
    "🔍 Análisis por Atacante",
    "📋 Reporte General",
    "⚙️ Estados del Modelo"
])

# ============================================================================
# PESTAÑA 1: Matriz de Transición
# ============================================================================

with tab1:
    st.subheader("📈 Matriz de Transición entre Estados Ocultos")

    if modelo is None:
        st.warning("No hay modelo HMM cargado. Revisa la ruta del archivo .pkl")
    else:
        st.markdown("""
        La **matriz de transición** muestra la probabilidad de pasar de un estado oculto (fila)
        a otro estado oculto (columna) en el siguiente paso. Los estados ocultos representan
        **perfiles de comportamiento** del atacante.
        """)

        transmat = modelo.transmat_
        n_estados = transmat.shape[0]

        # Heatmap interactivo con Plotly
        etiquetas_estados = [f"Estado {i}" for i in range(n_estados)]

        fig = go.Figure(data=go.Heatmap(
            z=transmat,
            x=etiquetas_estados,
            y=etiquetas_estados,
            text=np.round(transmat, 3),
            texttemplate="%{text}",
            textfont={"size": 12},
            colorscale="YlOrRd",
            zmin=0,
            zmax=1,
            hovertemplate="Desde: %{y}<br>Hacia: %{x}<br>Probabilidad: %{z:.3f}<extra></extra>"
        ))

        fig.update_layout(
            title="Probabilidades de Transición entre Estados Ocultos",
            xaxis_title="Estado Siguiente",
            yaxis_title="Estado Actual",
            xaxis={'side': 'bottom'},
            width=600,
            height=500,
        )

        col_izq, col_der = st.columns([3, 2])

        with col_izq:
            st.plotly_chart(fig, use_container_width=True)

        with col_der:
            st.markdown("### 📖 Interpretación")
            st.markdown(f"""
            - **{n_estados} estados ocultos** descubiertos por el modelo
            - Cada fila suma **1.0** (distribución de probabilidad)
            - Valores altos en la diagonal → comportamiento **persistente**
            - Valores fuera de la diagonal → **cambios de perfil**
            """)

            # Mostrar tabla de transición
            st.markdown("### 📋 Matriz en tabla")
            df_trans = pd.DataFrame(
                transmat,
                index=etiquetas_estados,
                columns=etiquetas_estados
            )
            df_trans = df_trans.round(3)
            st.dataframe(df_trans, use_container_width=True)

        # Análisis de persistencia por estado
        st.markdown("### 🔍 Análisis de Persistencia por Estado")
        persistencia = np.diag(transmat)
        df_persist = pd.DataFrame({
            "Estado": etiquetas_estados,
            "Probabilidad de Permanecer": persistencia,
            "Interpretación": [
                "Muy persistente (perfil estable)" if p > 0.7 else
                "Moderadamente persistente" if p > 0.4 else
                "Muy transitorio (cambia frecuentemente)"
                for p in persistencia
            ]
        })
        st.dataframe(df_persist, use_container_width=True)

        # Gráfico de barras de persistencia
        fig_bar = px.bar(
            df_persist,
            x="Estado",
            y="Probabilidad de Permanecer",
            color="Probabilidad de Permanecer",
            color_continuous_scale="RdYlGn",
            range_color=[0, 1],
            text_auto='.2f',
            title="Probabilidad de Permanecer en el Mismo Estado"
        )
        fig_bar.update_traces(textposition='outside')
        st.plotly_chart(fig_bar, use_container_width=True)

# ============================================================================
# PESTAÑA 2: Probabilidades de Emisión
# ============================================================================

with tab2:
    st.subheader("📊 Probabilidades de Emisión por Estado Oculto")

    if modelo is None:
        st.warning("No hay modelo HMM cargado.")
    else:
        st.markdown("""
        La **matriz de emisión** muestra la probabilidad de que un estado oculto genere
        cada fase de la Cyber Kill Chain. Esto permite interpretar qué significa
        cada estado oculto en términos de comportamiento.
        """)

        emisiones = modelo.emissionprob_
        n_estados = emisiones.shape[0]

        # Heatmap de emisiones
        etiquetas_estados = [f"Estado {i}" for i in range(n_estados)]

        fig_em = go.Figure(data=go.Heatmap(
            z=emisiones,
            x=nombres_fases,
            y=etiquetas_estados,
            text=np.round(emisiones, 3),
            texttemplate="%{text}",
            textfont={"size": 11},
            colorscale="Viridis",
            zmin=0,
            zmax=1,
            hovertemplate="Estado: %{y}<br>Fase: %{x}<br>Probabilidad: %{z:.3f}<extra></extra>"
        ))

        fig_em.update_layout(
            title="Probabilidad de Emitir cada Fase por Estado",
            xaxis_title="Fase de Cyber Kill Chain",
            yaxis_title="Estado Oculto",
            width=800,
            height=400,
        )

        st.plotly_chart(fig_em, use_container_width=True)

        # Interpretación de cada estado
        st.markdown("### 📖 Perfiles de Comportamiento por Estado")

        for i in range(n_estados):
            fase_dominante = np.argmax(emisiones[i])
            prob_max = emisiones[i][fase_dominante]

            with st.expander(f"**Estado {i}** — Fase dominante: {nombres_fases[fase_dominante]} ({prob_max:.1%})"):
                # Gráfico de barras para este estado
                df_estado = pd.DataFrame({
                    "Fase": nombres_fases,
                    "Probabilidad": emisiones[i]
                })

                fig_est = px.bar(
                    df_estado,
                    x="Fase",
                    y="Probabilidad",
                    color="Probabilidad",
                    color_continuous_scale="Viridis",
                    range_color=[0, 1],
                    text_auto='.2%',
                    title=f"Distribución de Emisión - Estado {i}"
                )
                fig_est.update_traces(textposition='outside')
                st.plotly_chart(fig_est, use_container_width=True)

                # Descripción del perfil
                fases_altas = [(j, emisiones[i][j]) for j in range(n_fases)
                               if emisiones[i][j] > 0.2]
                fases_altas.sort(key=lambda x: -x[1])

                descripcion = f"**Perfil**: "
                if fases_altas:
                    desc = " | ".join([f"{nombres_fases[j]}: {p:.1%}" for j, p in fases_altas])
                    descripcion += desc
                else:
                    descripcion += "Sin fase dominante clara"

                st.markdown(descripcion)

# ============================================================================
# PESTAÑA 3: Análisis por Atacante
# ============================================================================

with tab3:
    st.subheader("🔍 Análisis de Comportamiento por Atacante")

    # Obtener lista de autores
    autores_disponibles = []

    if df_reporte is not None and 'usuario' in df_reporte.columns:
        autores_reporte = df_reporte['usuario'].tolist()
        autores_disponibles.extend(autores_reporte)

    if secuencias_data and 'sequences' in secuencias_data:
        autores_sec = list(secuencias_data['sequences'].keys())
        # Agregar los que no estén ya
        for a in autores_sec:
            if a not in autores_disponibles:
                autores_disponibles.append(a)

    if not autores_disponibles:
        st.warning("No hay datos de autores disponibles. Carga el reporte CSV o las secuencias JSON.")
    else:
        autor_seleccionado = st.selectbox(
            "Selecciona un atacante:",
            options=sorted(autores_disponibles),
            index=0
        )

        if autor_seleccionado:
            col_info, col_pred = st.columns([2, 1])

            with col_info:
                st.markdown(f"### 👤 Atacante: `{autor_seleccionado}`")

                # Datos del reporte
                if df_reporte is not None and autor_seleccionado in df_reporte['usuario'].values:
                    autor_data = df_reporte[df_reporte['usuario'] == autor_seleccionado].iloc[0]

                    st.markdown("#### 📋 Datos del Reporte")
                    st.json({
                        "Cantidad de posts": int(autor_data.get('cantidad_posts', 0)),
                        "Estado dominante": int(autor_data.get('estado_dominante', -1)) if pd.notna(autor_data.get('estado_dominante')) else "N/A",
                        "Fase predicha": autor_data.get('siguiente_fase_nombre', 'N/A'),
                        "Confianza predicción": f"{float(autor_data.get('confianza_prediccion', 0)):.2%}",
                        "Mensaje": autor_data.get('mensaje', 'N/A')
                    })
                else:
                    st.info("Este autor no está en el reporte CSV (posiblemente secuencia corta).")

            with col_pred:
                # Predicción visual
                if df_reporte is not None and autor_seleccionado in df_reporte['usuario'].values:
                    autor_data = df_reporte[df_reporte['usuario'] == autor_seleccionado].iloc[0]
                    fase_predicha = autor_data.get('siguiente_fase_nombre', 'N/A')
                    confianza = float(autor_data.get('confianza_prediccion', 0))

                    st.markdown("#### 🎯 Predicción")
                    st.markdown(f"""
                    <div style="text-align: center; padding: 20px; border: 2px solid #3498db;
                         border-radius: 10px; background-color: #f0f8ff;">
                        <h3 style="margin: 0;">{fase_predicha}</h3>
                        <p style="font-size: 24px; margin: 10px 0; color: #2ecc71;">
                            {confianza:.1%}
                        </p>
                        <p style="color: gray;">confianza</p>
                    </div>
                    """, unsafe_allow_html=True)

            # ------------------------------------------------------------------
            # Probabilidades de transición para este atacante
            # ------------------------------------------------------------------
            st.markdown("---")
            st.markdown("### 🔄 Probabilidades de Cambio de Estado")

            if modelo is not None:
                # Determinar el estado dominante del autor
                estado_dominante = None
                if df_reporte is not None and autor_seleccionado in df_reporte['usuario'].values:
                    ed = autor_data.get('estado_dominante')
                    if pd.notna(ed):
                        estado_dominante = int(ed)

                if estado_dominante is not None and estado_dominante < modelo.n_components:
                    transiciones = modelo.transmat_[estado_dominante]
                    etiquetas_estados = [f"Estado {i}" for i in range(modelo.n_components)]

                    st.markdown(f"""
                    **Desde el Estado {estado_dominante}** (estado dominante de {autor_seleccionado}),
                    las probabilidades de transición a otros estados son:
                    """)

                    col1, col2 = st.columns([3, 2])

                    with col1:
                        df_trans_autor = pd.DataFrame({
                            "Estado Destino": etiquetas_estados,
                            "Probabilidad": transiciones
                        })

                        fig_trans = px.bar(
                            df_trans_autor,
                            x="Estado Destino",
                            y="Probabilidad",
                            color="Probabilidad",
                            color_continuous_scale="YlOrRd",
                            range_color=[0, 1],
                            text_auto='.2%',
                            title=f"Transiciones desde Estado {estado_dominante} para {autor_seleccionado}"
                        )
                        fig_trans.update_traces(textposition='outside')
                        st.plotly_chart(fig_trans, use_container_width=True)

                    with col2:
                        # Mostrar también la probabilidad de cada fase como siguiente paso
                        if n_fases > 0:
                            st.markdown("#### 📊 Probabilidad de cada fase como siguiente paso")
                            # Calcular: P(fase) = suma(P(estado_sig) * P(fase|estado_sig))
                            probs_fase = np.zeros(n_fases)
                            for s in range(modelo.n_components):
                                prob_estado = transiciones[s]
                                for f in range(n_fases):
                                    probs_fase[f] += prob_estado * modelo.emissionprob_[s, f]
                            probs_fase /= probs_fase.sum()

                            df_fases = pd.DataFrame({
                                "Fase": nombres_fases,
                                "Probabilidad": probs_fase
                            })

                            fig_fases = px.bar(
                                df_fases,
                                x="Fase",
                                y="Probabilidad",
                                color="Probabilidad",
                                color_continuous_scale="Viridis",
                                range_color=[0, 1],
                                text_auto='.1%',
                                title="Probabilidad de cada fase como siguiente acción"
                            )
                            fig_fases.update_traces(textposition='outside')
                            st.plotly_chart(fig_fases, use_container_width=True)

                else:
                    st.info("No se pudo determinar el estado dominante para este autor.")

            # ------------------------------------------------------------------
            # Secuencia temporal del autor (si hay datos de secuencias)
            # ------------------------------------------------------------------
            st.markdown("---")
            st.markdown("### 📈 Secuencia de Fases del Atacante")

            if secuencias_data and 'sequences' in secuencias_data:
                sequences = secuencias_data['sequences']
                if autor_seleccionado in sequences:
                    posts = sequences[autor_seleccionado]

                    # Extraer fases si están disponibles (recalcular con kill chain)
                    fases_observadas = []
                    for post in posts:
                        tecnicas = post.get('tecnicas_mitre', [])
                        if mapeo_kill and tecnicas:
                            mapa_tecnicas = mapeo_kill.get('mapeo_tecnicas', {})
                            fase_defecto = mapeo_kill.get('fase_por_defecto', 5)
                            fase_max = -1
                            for t in tecnicas:
                                fase = mapa_tecnicas.get(t)
                                if fase is not None and fase > fase_max:
                                    fase_max = fase
                            fases_observadas.append(fase_max if fase_max >= 0 else fase_defecto)
                        else:
                            # Sin técnicas, asignar fase por defecto
                            fases_observadas.append(5)

                    if fases_observadas:
                        df_sec = pd.DataFrame({
                            "Post": list(range(1, len(fases_observadas) + 1)),
                            "Fase": fases_observadas,
                            "Nombre Fase": [nombres_fases[f] if f < len(nombres_fases) else f"Fase {f}"
                                            for f in fases_observadas]
                        })

                        fig_sec = px.line(
                            df_sec,
                            x="Post",
                            y="Fase",
                            markers=True,
                            text="Nombre Fase",
                            title=f"Evolución de fases de {autor_seleccionado}",
                            range_y=[-0.5, n_fases - 0.5]
                        )
                        fig_sec.update_traces(
                            textposition="top center",
                            line=dict(color='#3498db', width=3),
                            marker=dict(size=10, color='#2ecc71')
                        )
                        fig_sec.update_layout(
                            yaxis=dict(
                                tickmode='array',
                                tickvals=list(range(n_fases)),
                                ticktext=nombres_fases
                            )
                        )
                        st.plotly_chart(fig_sec, use_container_width=True)

                        # También mostrar los posts en detalle
                        with st.expander("📝 Ver detalle de posts"):
                            for i, post in enumerate(posts):
                                st.markdown(f"""
                                **Post {i + 1}** — Fecha: {post.get('fecha_hora', 'N/A')}
                                - Técnicas MITRE: {', '.join(post.get('tecnicas_mitre', ['Ninguna']))}
                                - Fase asignada: {nombres_fases[fases_observadas[i]] if fases_observadas[i] < len(nombres_fases) else fases_observadas[i]}
                                """)
                    else:
                        st.info("No se pudieron determinar las fases para este autor.")
                else:
                    st.info(f"No hay datos de secuencia para {autor_seleccionado}.")
            else:
                st.info("No hay archivo de secuencias cargado.")

# ============================================================================
# PESTAÑA 4: Reporte General
# ============================================================================

with tab4:
    st.subheader("📋 Reporte General de Autores")

    if df_reporte is not None:
        st.markdown(f"**Total de autores en reporte:** {len(df_reporte)}")

        # Filtros
        col_filtro1, col_filtro2 = st.columns(2)

        with col_filtro1:
            if 'mensaje' in df_reporte.columns:
                mensajes_unicos = df_reporte['mensaje'].unique().tolist()
                filtro_mensaje = st.multiselect(
                    "Filtrar por mensaje:",
                    options=mensajes_unicos,
                    default=mensajes_unicos
                )
                df_filtrado = df_reporte[df_reporte['mensaje'].isin(filtro_mensaje)]
            else:
                df_filtrado = df_reporte

        with col_filtro2:
            if 'estado_dominante' in df_reporte.columns:
                estados_vals = sorted(df_filtrado['estado_dominante'].dropna().unique().tolist())
                if estados_vals:
                    filtro_estado = st.multiselect(
                        "Filtrar por estado dominante:",
                        options=estados_vals,
                        default=estados_vals
                    )
                    df_filtrado = df_filtrado[df_filtrado['estado_dominante'].isin(filtro_estado)]

        st.markdown(f"**Mostrando:** {len(df_filtrado)} autores")

        # Tabla principal
        columnas_mostrar = [c for c in ['usuario', 'cantidad_posts', 'estado_dominante',
                                         'siguiente_fase_nombre', 'confianza_prediccion', 'mensaje']
                           if c in df_filtrado.columns]

        st.dataframe(
            df_filtrado[columnas_mostrar].sort_values('confianza_prediccion', ascending=False)
            if 'confianza_prediccion' in df_filtrado.columns
            else df_filtrado[columnas_mostrar],
            use_container_width=True,
            hide_index=True
        )

        # Gráficos de distribución
        st.markdown("---")
        st.markdown("### 📊 Distribuciones")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            if 'estado_dominante' in df_filtrado.columns:
                conteo_estados = df_filtrado['estado_dominante'].value_counts().reset_index()
                conteo_estados.columns = ['Estado', 'Cantidad']
                conteo_estados = conteo_estados.sort_values('Estado')

                fig_dist = px.bar(
                    conteo_estados,
                    x='Estado',
                    y='Cantidad',
                    color='Cantidad',
                    color_continuous_scale='Viridis',
                    text_auto=True,
                    title="Distribución de Estados Dominantes"
                )
                fig_dist.update_traces(textposition='outside')
                st.plotly_chart(fig_dist, use_container_width=True)

        with col_g2:
            if 'siguiente_fase_nombre' in df_filtrado.columns:
                conteo_fases = df_filtrado['siguiente_fase_nombre'].value_counts().reset_index()
                conteo_fases.columns = ['Fase', 'Cantidad']

                fig_fases = px.bar(
                    conteo_fases,
                    x='Fase',
                    y='Cantidad',
                    color='Cantidad',
                    color_continuous_scale='Reds',
                    text_auto=True,
                    title="Distribución de Fases Predichas"
                )
                fig_fases.update_traces(textposition='outside')
                st.plotly_chart(fig_fases, use_container_width=True)

        # Scatter: cantidad de posts vs confianza
        st.markdown("### 📈 Relación: Posts vs Confianza")
        if 'cantidad_posts' in df_filtrado.columns and 'confianza_prediccion' in df_filtrado.columns:
            fig_scatter = px.scatter(
                df_filtrado,
                x='cantidad_posts',
                y='confianza_prediccion',
                color='estado_dominante' if 'estado_dominante' in df_filtrado.columns else None,
                hover_data=['usuario', 'siguiente_fase_nombre'],
                title="Confianza de Predicción vs Cantidad de Posts",
                labels={
                    'cantidad_posts': 'Cantidad de Posts',
                    'confianza_prediccion': 'Confianza de Predicción',
                    'estado_dominante': 'Estado Dominante'
                }
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        # Descarga
        st.markdown("---")
        st.markdown("### 💾 Descargar Reporte")

        formato = st.radio("Formato:", ["CSV", "JSON"], horizontal=True, key="formato_reporte")

        if formato == "CSV":
            data_str = df_filtrado.to_csv(index=False).encode('utf-8')
            mime = "text/csv"
            ext = "csv"
        else:
            data_str = df_filtrado.to_json(orient='records', force_ascii=False).encode('utf-8')
            mime = "application/json"
            ext = "json"

        st.download_button(
            label=f"⬇️ Descargar como {formato}",
            data=data_str,
            file_name=f"reporte_hmm_filtrado.{ext}",
            mime=mime
        )

    else:
        st.warning("No hay reporte CSV cargado. Revisa la ruta en el panel lateral.")

# ============================================================================
# PESTAÑA 5: Estados del Modelo
# ============================================================================

with tab5:
    st.subheader("⚙️ Parámetros y Estados del Modelo HMM")

    if modelo is not None:
        col_izq, col_der = st.columns(2)

        with col_izq:
            st.markdown("### 📐 Parámetros del Modelo")
            st.json({
                "n_components (estados ocultos)": modelo.n_components,
                "n_features (observaciones)": modelo.emissionprob_.shape[1],
                "tolerancia": modelo.tol,
                "random_state": modelo.random_state,
            })

        with col_der:
            st.markdown("### 📊 Probabilidades Iniciales")
            # Mostrar startprob
            df_start = pd.DataFrame({
                "Estado": [f"Estado {i}" for i in range(modelo.n_components)],
                "Probabilidad Inicial": modelo.startprob_
            })

            fig_start = px.bar(
                df_start,
                x="Estado",
                y="Probabilidad Inicial",
                color="Probabilidad Inicial",
                color_continuous_scale="Blues",
                range_color=[0, 1],
                text_auto='.2%',
                title="Distribución Inicial de Estados"
            )
            fig_start.update_traces(textposition='outside')
            st.plotly_chart(fig_start, use_container_width=True)

        # Matriz completa de transición + emisión
        st.markdown("---")
        st.markdown("### 📋 Matriz Completa de Transición")
        transmat = modelo.transmat_
        etiquetas = [f"Estado {i}" for i in range(transmat.shape[0])]
        df_trans_completa = pd.DataFrame(
            transmat,
            index=etiquetas,
            columns=etiquetas
        ).round(4)
        st.dataframe(df_trans_completa, use_container_width=True)

        st.markdown("### 📋 Matriz Completa de Emisión")
        emisiones = modelo.emissionprob_
        df_emision = pd.DataFrame(
            emisiones,
            index=etiquetas,
            columns=nombres_fases
        ).round(4)
        st.dataframe(df_emision, use_container_width=True)

        # Diagrama de flujo de estados
        st.markdown("---")
        st.markdown("### 🔄 Diagrama de Flujo de Estados")

        st.markdown("""
        El siguiente diagrama muestra cómo los atacantes fluyen entre estados ocultos.
        Las flechas más gruesas indican mayor probabilidad de transición.
        """)

        # Mostrar transiciones más significativas (> 0.1)
        transmat = modelo.transmat_
        n_estados = transmat.shape[0]
        etiquetas_estados = [f"Estado {i}" for i in range(n_estados)]

        # Crear nodos para Sankey
        sources = []
        targets = []
        values = []
        labels_sankey = etiquetas_estados.copy()
        # Agregar fases como nodos destino
        fase_offset = n_estados
        labels_sankey.extend(nombres_fases)

        for i in range(n_estados):
            for j in range(n_estados):
                if transmat[i][j] > 0.05:  # Umbral mínimo
                    sources.append(i)
                    targets.append(j)
                    values.append(round(transmat[i][j], 3))

        if sources:
            fig_sankey = go.Figure(data=go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=labels_sankey[:n_estados],  # Solo estados por ahora
                    color=COLORES_FASES[:n_estados]
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    hovertemplate='Desde: %{source.label}<br>Hacia: %{target.label}<br>Prob: %{value:.2%}<extra></extra>'
                )
            ))

            fig_sankey.update_layout(
                title="Flujo de Transiciones entre Estados Ocultos (prob > 0.05)",
                font=dict(size=12)
            )

            st.plotly_chart(fig_sankey, use_container_width=True)
        else:
            st.info("No hay transiciones significativas para mostrar.")

    else:
        st.warning("No hay modelo HMM cargado.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        🕵️ Dashboard HMM - Proyecto de Titulación TI ·
        Modelo Oculto de Markov para análisis de comportamiento en foros .onion
    </div>
    """,
    unsafe_allow_html=True
)