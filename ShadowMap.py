#!/usr/bin/env python3
# encoding: utf-8
"""
Dashboard Integrador - Proyecto de Titulación TI
=================================================
Interfaz unificada para las 3 fases del proyecto:
  - Fase 1: Scraping de foros .onion
  - Fase 2: Análisis Semántico NLP con SecureBERT
  - Fase 3: Modelo HMM para predicción de comportamiento

Uso:
    streamlit run dashboard_integrador.py

Requiere:
    pip install streamlit pandas plotly numpy
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import pickle
import os
import sys
import subprocess
import threading
import queue
import time
from datetime import datetime
from collections import Counter
from pathlib import Path

import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Integrador - Proyecto Titulación",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Constantes de rutas
# ---------------------------------------------------------------------------
RUTA_BASE = Path(".")
RUTA_FASE1 = RUTA_BASE / "Fase 1 - Scraping-Onion-Sites"
RUTA_FASE2 = RUTA_BASE / "Fase 2 - Analisis semantico NLP"
RUTA_FASE3 = RUTA_BASE / "Fase 3 - Modelo HMM"
RUTA_DATOS = RUTA_BASE / "Datos"

ARCHIVOS_DATOS = {
    "forum_records.csv": RUTA_DATOS / "forum_records.csv",
    "forum_records_clean.csv": RUTA_DATOS / "forum_records_clean.csv",
    "datos_enriquecidos.csv": RUTA_DATOS / "datos_enriquecidos.csv",
    "secuencias_autores.json": RUTA_DATOS / "secuencias_autores.json",
    "modelo_hmm.pkl": RUTA_DATOS / "modelo_hmm.pkl",
    "reporte_autores.csv": RUTA_DATOS / "reporte_autores.csv",
}

COLORES_FASES = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
NOMBRES_FASES = ["Reconocimiento", "Entrega", "Explotación", "Instalación", "C2", "Acciones"]

# ---------------------------------------------------------------------------
# Gestor de ejecución en segundo plano
# ---------------------------------------------------------------------------

class EjecutorEnSegundoPlano:
    """Ejecuta comandos en un hilo separado y captura logs en tiempo real."""

    def __init__(self):
        self.proceso = None
        self.log_queue = queue.Queue()
        self.en_ejecucion = False
        self.completado = False
        self.codigo_salida = None
        self.hilo = None

    def ejecutar(self, comando, cwd=None):
        """Inicia la ejecución de un comando en un hilo separado."""
        if self.en_ejecucion:
            return False

        self.en_ejecucion = True
        self.completado = False
        self.codigo_salida = None
        self.log_queue = queue.Queue()

        self.hilo = threading.Thread(
            target=self._ejecutar_comando,
            args=(comando, cwd),
            daemon=True
        )
        self.hilo.start()
        return True

    def detener(self):
        """Detiene el proceso y todo su árbol de procesos hijos."""
        if self.proceso is None:
            return False

        pid = self.proceso.pid
        try:
            if sys.platform == "win32":
                # En Windows: taskkill mata todo el árbol de procesos
                subprocess.run(
                    f"taskkill /F /T /PID {pid}",
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
            else:
                # En Linux/macOS: mata el grupo de procesos
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(1)
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except:
                    pass
        except Exception as e:
            try:
                self.proceso.terminate()
                time.sleep(0.5)
                self.proceso.kill()
            except:
                pass

        self.log_queue.put("⏹️ PROCESO DETENIDO POR USUARIO")
        self.en_ejecucion = False
        self.completado = True
        return True

    def _ejecutar_comando(self, comando, cwd):
        """Ejecuta el comando y captura la salida."""
        try:
            # Forzar salida sin buffer para logs en tiempo real
            if "python " in comando or "python3 " in comando:
                comando = comando.replace("python ", "python -u ", 1)
                comando = comando.replace("python3 ", "python3 -u ", 1)

            self.proceso = subprocess.Popen(
                comando,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=0,
                cwd=str(cwd) if cwd else None
            )

            for linea in iter(self.proceso.stdout.readline, ''):
                if linea:
                    self.log_queue.put(linea.strip())

            self.proceso.stdout.close()
            self.codigo_salida = self.proceso.wait()

            if self.codigo_salida == 0:
                self.log_queue.put("✅ PROCESO COMPLETADO EXITOSAMENTE")
            elif self.codigo_salida == -1:
                pass  # Proceso terminado por el usuario
            else:
                self.log_queue.put(f"❌ PROCESO FALLIDO (código: {self.codigo_salida})")

        except Exception as e:
            self.log_queue.put(f"❌ ERROR: {str(e)}")
        finally:
            self.en_ejecucion = False
            self.completado = True

    def obtener_logs(self):
        """Obtiene todos los logs acumulados."""
        logs = []
        while not self.log_queue.empty():
            try:
                logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return logs

    def esta_ejecutando(self):
        return self.en_ejecucion

    def esta_completado(self):
        return self.completado


# Inicializar ejecutores en session_state
if 'ejecutor_fase1' not in st.session_state:
    st.session_state.ejecutor_fase1 = EjecutorEnSegundoPlano()
if 'ejecutor_fase2' not in st.session_state:
    st.session_state.ejecutor_fase2 = EjecutorEnSegundoPlano()
if 'ejecutor_fase3' not in st.session_state:
    st.session_state.ejecutor_fase3 = EjecutorEnSegundoPlano()
if 'logs_fase1' not in st.session_state:
    st.session_state.logs_fase1 = []
if 'logs_fase2' not in st.session_state:
    st.session_state.logs_fase2 = []
if 'logs_fase3' not in st.session_state:
    st.session_state.logs_fase3 = []


def actualizar_logs(executor_key, log_key):
    """Actualiza los logs desde la cola del ejecutor."""
    ejecutor = st.session_state[executor_key]
    nuevos = ejecutor.obtener_logs()
    if nuevos:
        st.session_state[log_key].extend(nuevos)


def rerun_seguro():
    """rerun que no crashea si el event loop ya está cerrado."""
    try:
        st.rerun()
    except RuntimeError:
        pass


# ---------------------------------------------------------------------------
# Funciones de carga de datos (con caché)
# ---------------------------------------------------------------------------

@st.cache_data
def cargar_csv(ruta):
    """Carga un archivo CSV."""
    if not os.path.exists(ruta):
        return None
    try:
        df = pd.read_csv(ruta)
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'], errors='coerce')
        if 'fecha_hora' in df.columns:
            df['fecha_hora'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error cargando {ruta}: {e}")
        return None


@st.cache_data
def cargar_json(ruta):
    """Carga un archivo JSON."""
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


@st.cache_data
def cargar_modelo_hmm(ruta):
    """Carga modelo HMM desde pickle."""
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'rb') as f:
            return pickle.load(f)
    except:
        return None


def verificar_archivos():
    """Verifica qué archivos de datos están disponibles."""
    estado = {}
    for nombre, ruta in ARCHIVOS_DATOS.items():
        estado[nombre] = os.path.exists(ruta)
    return estado


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------

st.sidebar.title("🎯 Dashboard Integrador")
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Estado de Archivos")

estado_archivos = verificar_archivos()
for nombre, existe in estado_archivos.items():
    icono = "✅" if existe else "❌"
    st.sidebar.markdown(f"{icono} {nombre}")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Rutas")
st.sidebar.markdown(f"**Datos:** `{RUTA_DATOS}`")
st.sidebar.markdown(f"**Fase 1:** `{RUTA_FASE1.name}`")
st.sidebar.markdown(f"**Fase 2:** `{RUTA_FASE2.name}`")
st.sidebar.markdown(f"**Fase 3:** `{RUTA_FASE3.name}`")

# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------

st.title("🎯 Dashboard Integrador - Proyecto de Titulación")
st.markdown("---")

# KPIs globales
col_k1, col_k2, col_k3, col_k4 = st.columns(4)

df_clean = cargar_csv(ARCHIVOS_DATOS["forum_records_clean.csv"])
df_enriquecido = cargar_csv(ARCHIVOS_DATOS["datos_enriquecidos.csv"])
df_reporte = cargar_csv(ARCHIVOS_DATOS["reporte_autores.csv"])

with col_k1:
    if df_clean is not None:
        st.metric("🌐 Posts (F1)", f"{len(df_clean):,}")
    else:
        st.metric("🌐 Posts (F1)", "N/A")

with col_k2:
    if df_enriquecido is not None:
        st.metric("🧠 Posts Enriquecidos (F2)", f"{len(df_enriquecido):,}")
    else:
        st.metric("🧠 Posts Enriquecidos", "N/A")

with col_k3:
    if df_reporte is not None:
        st.metric("🕵️ Autores Analizados (F3)", len(df_reporte))
    else:
        st.metric("🕵️ Autores Analizados", "N/A")

with col_k4:
    modelo = cargar_modelo_hmm(ARCHIVOS_DATOS["modelo_hmm.pkl"])
    if modelo is not None:
        st.metric("🧠 Estados HMM", modelo.n_components)
    else:
        st.metric("🧠 Estados HMM", "N/A")

st.markdown("---")

# ---------------------------------------------------------------------------
# Pestañas principales
# ---------------------------------------------------------------------------

tab_f1, tab_f2, tab_f3, tab_global, tab_datos = st.tabs([
    "🌐 Fase 1 - Scraping",
    "🧠 Fase 2 - NLP",
    "🕵️ Fase 3 - HMM",
    "📊 Dashboard Global",
    "📋 Datos Crudos"
])

# ============================================================================
# PESTAÑA FASE 1 - SCRAPING
# ============================================================================

with tab_f1:
    st.subheader("🌐 Fase 1: Scraping de Foros .onion")

    col_ejec, col_logs = st.columns([1, 2])

    with col_ejec:
        st.markdown("### ▶️ Ejecutar Pipeline Fase 1")

        if st.button("🔍 Ejecutar Scraper", use_container_width=True,
                     disabled=st.session_state.ejecutor_fase1.esta_ejecutando()):
            comando = 'python forum_scraper.py --seeds seeds.txt --keywords identifiers.txt --max-depth 2 --delay 5 --csv-out ../Datos/forum_records.csv'
            st.session_state.logs_fase1 = []
            exito = st.session_state.ejecutor_fase1.ejecutar(comando, RUTA_FASE1)
            if exito:
                st.success("Ejecutando scraper...")
            else:
                st.error("Ya hay un proceso en ejecución")

        if st.button("🧹 Ejecutar Preprocesador", use_container_width=True,
                     disabled=st.session_state.ejecutor_fase1.esta_ejecutando()):
            comando = 'python Preprocesador.py --input ../Datos/forum_records.csv --output ../Datos/forum_records_clean.csv'
            st.session_state.logs_fase1 = []
            exito = st.session_state.ejecutor_fase1.ejecutar(comando, RUTA_FASE1)
            if exito:
                st.success("Ejecutando preprocesador...")
            else:
                st.error("Ya hay un proceso en ejecución")

        if st.button("⏹️ Detener", use_container_width=True,
                     disabled=not st.session_state.ejecutor_fase1.esta_ejecutando()):
            st.session_state.ejecutor_fase1.detener()
            st.warning("⏹️ Proceso detenido")

        if st.button("🗑️ Limpiar Logs", use_container_width=True):
            st.session_state.logs_fase1 = []

        # Estado del ejecutor
        if st.session_state.ejecutor_fase1.esta_ejecutando():
            st.info("🔄 Ejecutando...")
        elif st.session_state.ejecutor_fase1.completado:
            if st.session_state.ejecutor_fase1.codigo_salida == 0:
                st.success("✅ Completado exitosamente")
            else:
                st.error(f"❌ Fallido (código: {st.session_state.ejecutor_fase1.codigo_salida})")

    with col_logs:
        st.markdown("### 📜 Logs en Tiempo Real")
        actualizar_logs('ejecutor_fase1', 'logs_fase1')
        logs_placeholder = st.empty()
        with logs_placeholder.container():
            if st.session_state.logs_fase1:
                st.code("\n".join(st.session_state.logs_fase1[-80:]), language="bash")
            else:
                st.info("No hay logs aún. Ejecuta un proceso.")
        if st.session_state.ejecutor_fase1.esta_ejecutando():
            rerun_seguro()

    # Visualización de datos de Fase 1
    st.markdown("---")
    st.markdown("### 📊 Datos Actuales de Fase 1")

    if df_clean is not None:
        col_izq, col_der = st.columns(2)

        with col_izq:
            st.metric("📝 Total Posts", f"{len(df_clean):,}")
            if 'usuario' in df_clean.columns:
                st.metric("👤 Usuarios Únicos", df_clean['usuario'].nunique())
            if 'id_hilo' in df_clean.columns:
                st.metric("🧵 Hilos Únicos", df_clean['id_hilo'].nunique())

        with col_der:
            if 'fecha' in df_clean.columns and not df_clean['fecha'].isna().all():
                st.metric("📅 Días Activos", df_clean['fecha'].dt.date.nunique())
            if 'longitud_cuerpo' in df_clean.columns:
                st.metric("📏 Longitud Promedio", f"{int(df_clean['longitud_cuerpo'].mean()):,} chars")

        # Top autores
        if 'usuario' in df_clean.columns:
            st.markdown("### 👥 Top Autores más Activos")
            top_n_f1 = st.slider("Top N autores:", 5, 30, 10, key="top_f1")
            top_autores = df_clean['usuario'].value_counts().head(top_n_f1)

            fig = px.bar(
                x=top_autores.values,
                y=top_autores.index,
                orientation='h',
                title=f"Top {top_n_f1} Autores",
                labels={'x': 'Posts', 'y': 'Autor'},
                color=top_autores.values,
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de Fase 1 disponibles. Ejecuta el scraper y preprocesador.")

# ============================================================================
# PESTAÑA FASE 2 - NLP
# ============================================================================

with tab_f2:
    st.subheader("🧠 Fase 2: Análisis Semántico con SecureBERT")

    col_ejec2, col_logs2 = st.columns([1, 2])

    with col_ejec2:
        st.markdown("### ▶️ Ejecutar Pipeline Fase 2")

        if st.button("🧠 Ejecutar NLP Pipeline", use_container_width=True,
                     disabled=st.session_state.ejecutor_fase2.esta_ejecutando()):
            comando = 'python modulos/main.py --input ../Datos/forum_records_clean.csv --output-csv ../Datos/datos_enriquecidos.csv --output-hmm ../Datos/secuencias_autores.json'
            st.session_state.logs_fase2 = []
            exito = st.session_state.ejecutor_fase2.ejecutar(comando, RUTA_FASE2)
            if exito:
                st.success("Ejecutando NLP pipeline...")
            else:
                st.error("Ya hay un proceso en ejecución")

        if st.button("⏹️ Detener Fase 2", use_container_width=True,
                     disabled=not st.session_state.ejecutor_fase2.esta_ejecutando()):
            st.session_state.ejecutor_fase2.detener()
            st.warning("⏹️ Proceso detenido")

        if st.button("🗑️ Limpiar Logs F2", use_container_width=True):
            st.session_state.logs_fase2 = []

        if st.session_state.ejecutor_fase2.esta_ejecutando():
            st.info("🔄 Ejecutando NLP... (puede tomar varios minutos)")
        elif st.session_state.ejecutor_fase2.completado:
            if st.session_state.ejecutor_fase2.codigo_salida == 0:
                st.success("✅ NLP completado exitosamente")
            else:
                st.error(f"❌ Fallido (código: {st.session_state.ejecutor_fase2.codigo_salida})")

    with col_logs2:
        st.markdown("### 📜 Logs en Tiempo Real")
        actualizar_logs('ejecutor_fase2', 'logs_fase2')
        logs_placeholder2 = st.empty()
        with logs_placeholder2.container():
            if st.session_state.logs_fase2:
                st.code("\n".join(st.session_state.logs_fase2[-80:]), language="bash")
            else:
                st.info("No hay logs aún. Ejecuta el NLP pipeline.")
        if st.session_state.ejecutor_fase2.esta_ejecutando():
            rerun_seguro()

    # Visualización de datos de Fase 2
    st.markdown("---")
    st.markdown("### 📊 Datos Enriquecidos (Fase 2)")

    if df_enriquecido is not None:
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)

        with col_m1:
            st.metric("📝 Total Posts", f"{len(df_enriquecido):,}")

        with col_m2:
            if 'cantidad_entidades' in df_enriquecido.columns:
                total_entidades = df_enriquecido['cantidad_entidades'].sum()
                st.metric("🔍 Entidades Detectadas", f"{total_entidades:,}")

        with col_m3:
            if 'puntuacion_amenaza' in df_enriquecido.columns:
                prom_amenaza = df_enriquecido['puntuacion_amenaza'].mean()
                st.metric("⚠️ Amenaza Promedio", f"{prom_amenaza:.2f}")

        with col_m4:
            if 'cantidad_tecnicas' in df_enriquecido.columns:
                total_tecnicas = df_enriquecido['cantidad_tecnicas'].sum()
                st.metric("🎯 Técnicas MITRE", f"{total_tecnicas:,}")

        # Top amenazas
        if 'puntuacion_amenaza' in df_enriquecido.columns and 'cuerpo_limpio' in df_enriquecido.columns:
            st.markdown("### ⚠️ Top Posts más Amenazantes")
            top_threats = df_enriquecido.nlargest(10, 'puntuacion_amenaza')

            fig_threat = px.bar(
                top_threats,
                x='puntuacion_amenaza',
                y='id_mensaje' if 'id_mensaje' in top_threats.columns else top_threats.index,
                orientation='h',
                color='puntuacion_amenaza',
                color_continuous_scale='Reds',
                title="Top 10 Posts con Mayor Puntuación de Amenaza",
                labels={'puntuacion_amenaza': 'Amenaza', 'y': 'Post'}
            )
            st.plotly_chart(fig_threat, use_container_width=True)

        # Distribución de entidades
        st.markdown("---")
        st.markdown("### 📈 Distribuciones")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            if 'cantidad_entidades' in df_enriquecido.columns:
                fig_ent = px.histogram(
                    df_enriquecido,
                    x='cantidad_entidades',
                    nbins=20,
                    title="Distribución de Entidades por Post",
                    labels={'cantidad_entidades': 'Cantidad de Entidades'},
                    color_discrete_sequence=['#3498db']
                )
                st.plotly_chart(fig_ent, use_container_width=True)

        with col_g2:
            if 'puntuacion_amenaza' in df_enriquecido.columns:
                fig_amen = px.histogram(
                    df_enriquecido,
                    x='puntuacion_amenaza',
                    nbins=20,
                    title="Distribución de Puntuación de Amenaza",
                    labels={'puntuacion_amenaza': 'Puntuación'},
                    color_discrete_sequence=['#e74c3c']
                )
                st.plotly_chart(fig_amen, use_container_width=True)
    else:
        st.info("No hay datos enriquecidos disponibles. Ejecuta el NLP pipeline.")

# ============================================================================
# PESTAÑA FASE 3 - HMM
# ============================================================================

with tab_f3:
    st.subheader("🕵️ Fase 3: Modelo HMM - Predicción de Comportamiento")

    col_ejec3, col_logs3 = st.columns([1, 2])

    with col_ejec3:
        st.markdown("### ▶️ Ejecutar Pipeline Fase 3")

        col_params1, col_params2 = st.columns(2)
        with col_params1:
            n_estados = st.number_input("Estados ocultos:", min_value=2, max_value=10, value=4)
        with col_params2:
            n_iter = st.number_input("Iteraciones:", min_value=10, max_value=500, value=100)

        if st.button("🕵️ Entrenar HMM", use_container_width=True,
                     disabled=st.session_state.ejecutor_fase3.esta_ejecutando()):
            comando = f'python modulos/main.py -i ../Datos/secuencias_autores.json -k kill_chain_fases.json -m ../Datos/modelo_hmm.pkl -r ../Datos/reporte_autores.csv -e {n_estados} -n {n_iter}'
            st.session_state.logs_fase3 = []
            exito = st.session_state.ejecutor_fase3.ejecutar(comando, RUTA_FASE3)
            if exito:
                st.success("Ejecutando entrenamiento HMM...")
            else:
                st.error("Ya hay un proceso en ejecución")

        if st.button("⏹️ Detener Fase 3", use_container_width=True,
                     disabled=not st.session_state.ejecutor_fase3.esta_ejecutando()):
            st.session_state.ejecutor_fase3.detener()
            st.warning("⏹️ Proceso detenido")

        if st.button("🗑️ Limpiar Logs F3", use_container_width=True):
            st.session_state.logs_fase3 = []

        if st.session_state.ejecutor_fase3.esta_ejecutando():
            st.info("🔄 Entrenando HMM...")
        elif st.session_state.ejecutor_fase3.completado:
            if st.session_state.ejecutor_fase3.codigo_salida == 0:
                st.success("✅ HMM entrenado exitosamente")
            else:
                st.error(f"❌ Fallido (código: {st.session_state.ejecutor_fase3.codigo_salida})")

    with col_logs3:
        st.markdown("### 📜 Logs en Tiempo Real")
        actualizar_logs('ejecutor_fase3', 'logs_fase3')
        logs_placeholder3 = st.empty()
        with logs_placeholder3.container():
            if st.session_state.logs_fase3:
                st.code("\n".join(st.session_state.logs_fase3[-80:]), language="bash")
            else:
                st.info("No hay logs aún. Ejecuta el entrenamiento HMM.")
        if st.session_state.ejecutor_fase3.esta_ejecutando():
            rerun_seguro()

    # Visualización de resultados HMM
    st.markdown("---")
    st.markdown("### 📊 Resultados del Modelo HMM")

    modelo = cargar_modelo_hmm(ARCHIVOS_DATOS["modelo_hmm.pkl"])
    df_reporte = cargar_csv(ARCHIVOS_DATOS["reporte_autores.csv"])
    secuencias_data = cargar_json(ARCHIVOS_DATOS["secuencias_autores.json"])

    if modelo is not None:
        tab_hmm1, tab_hmm2, tab_hmm3 = st.tabs([
            "📈 Matriz de Transición",
            "📊 Probabilidades de Emisión",
            "🔍 Análisis por Atacante"
        ])

        with tab_hmm1:
            st.markdown("#### Matriz de Transición entre Estados Ocultos")
            transmat = modelo.transmat_
            n_est = transmat.shape[0]
            etiquetas = [f"Estado {i}" for i in range(n_est)]

            fig_trans = go.Figure(data=go.Heatmap(
                z=transmat,
                x=etiquetas,
                y=etiquetas,
                text=np.round(transmat, 3),
                texttemplate="%{text}",
                textfont={"size": 12},
                colorscale="YlOrRd",
                zmin=0, zmax=1,
                hovertemplate="Desde: %{y}<br>Hacia: %{x}<br>Prob: %{z:.3f}<extra></extra>"
            ))
            fig_trans.update_layout(
                title="Probabilidades de Transición",
                xaxis_title="Estado Siguiente",
                yaxis_title="Estado Actual",
                width=500, height=450
            )

            col_t1, col_t2 = st.columns([3, 2])
            with col_t1:
                st.plotly_chart(fig_trans, use_container_width=True)
            with col_t2:
                st.markdown("##### Persistencia por Estado")
                persistencia = np.diag(transmat)
                df_persist = pd.DataFrame({
                    "Estado": etiquetas,
                    "Permanecer": persistencia,
                    "Tipo": ["Estable" if p > 0.7 else "Moderado" if p > 0.4 else "Transitorio"
                             for p in persistencia]
                })
                st.dataframe(df_persist, use_container_width=True)

        with tab_hmm2:
            st.markdown("#### Probabilidades de Emisión por Estado")
            emisiones = modelo.emissionprob_

            fig_em = go.Figure(data=go.Heatmap(
                z=emisiones,
                x=NOMBRES_FASES[:emisiones.shape[1]],
                y=etiquetas,
                text=np.round(emisiones, 3),
                texttemplate="%{text}",
                textfont={"size": 11},
                colorscale="Viridis",
                zmin=0, zmax=1
            ))
            fig_em.update_layout(
                title="Probabilidad de Emitir cada Fase",
                xaxis_title="Fase de Kill Chain",
                yaxis_title="Estado Oculto",
                width=700, height=350
            )
            st.plotly_chart(fig_em, use_container_width=True)

        with tab_hmm3:
            st.markdown("#### Análisis por Atacante")

            if df_reporte is not None and 'usuario' in df_reporte.columns:
                autores_lista = df_reporte['usuario'].tolist()
                autor_sel = st.selectbox("Selecciona un atacante:", sorted(autores_lista))

                if autor_sel:
                    autor_data = df_reporte[df_reporte['usuario'] == autor_sel].iloc[0]

                    col_a1, col_a2, col_a3 = st.columns(3)
                    with col_a1:
                        st.metric("Posts", int(autor_data.get('cantidad_posts', 0)))
                    with col_a2:
                        fase_pred = autor_data.get('siguiente_fase_nombre', 'N/A')
                        st.metric("Fase Predicha", fase_pred)
                    with col_a3:
                        conf = float(autor_data.get('confianza_prediccion', 0))
                        st.metric("Confianza", f"{conf:.1%}")
            else:
                st.info("No hay reporte de autores disponible.")
    else:
        st.info("No hay modelo HMM entrenado. Ejecuta el entrenamiento desde esta pestaña.")

# ============================================================================
# PESTAÑA DASHBOARD GLOBAL
# ============================================================================

with tab_global:
    st.subheader("📊 Dashboard Global - Integración de las 3 Fases")

    # Estadísticas generales
    st.markdown("### 📈 Estadísticas del Proyecto")

    col_est1, col_est2, col_est3, col_est4 = st.columns(4)

    with col_est1:
        if df_clean is not None:
            st.metric("🌐 Posts Scrapeados (F1)", f"{len(df_clean):,}")
        else:
            st.metric("🌐 Posts Scrapeados", "N/A")

    with col_est2:
        if df_enriquecido is not None:
            st.metric("🧠 Posts Enriquecidos (F2)", f"{len(df_enriquecido):,}")
        else:
            st.metric("🧠 Posts Enriquecidos", "N/A")

    with col_est3:
        if df_reporte is not None:
            st.metric("🕵️ Autores Analizados (F3)", len(df_reporte))
        else:
            st.metric("🕵️ Autores Analizados", "N/A")

    with col_est4:
        if modelo is not None:
            st.metric("🧠 Estados HMM", modelo.n_components)
        else:
            st.metric("🧠 Estados HMM", "N/A")

    # Secuencia completa del pipeline
    st.markdown("---")
    st.markdown("### 🔄 Estado del Pipeline Completo")

    pipeline_status = {
        "Fase 1: Scraping": "✅ Completa" if estado_archivos["forum_records_clean.csv"] else "⏳ Pendiente",
        "Fase 1: Preprocesamiento": "✅ Completa" if estado_archivos["forum_records_clean.csv"] else "⏳ Pendiente",
        "Fase 2: NLP (SecureBERT)": "✅ Completa" if estado_archivos["datos_enriquecidos.csv"] else "⏳ Pendiente",
        "Fase 2: Secuencias HMM": "✅ Completa" if estado_archivos["secuencias_autores.json"] else "⏳ Pendiente",
        "Fase 3: Entrenamiento HMM": "✅ Completa" if estado_archivos["modelo_hmm.pkl"] else "⏳ Pendiente",
        "Fase 3: Reporte Autores": "✅ Completa" if estado_archivos["reporte_autores.csv"] else "⏳ Pendiente",
    }

    df_pipeline = pd.DataFrame([
        {"Etapa": etapa, "Estado": estado}
        for etapa, estado in pipeline_status.items()
    ])

    fig_pipeline = px.bar(
        df_pipeline,
        x="Etapa",
        y=[1] * len(df_pipeline),
        color="Estado",
        color_discrete_map={"✅ Completa": "#2ecc71", "⏳ Pendiente": "#f39c12"},
        title="Progreso del Pipeline",
        labels={"y": ""}
    )
    fig_pipeline.update_layout(
        showlegend=True,
        yaxis_visible=False,
        height=300
    )
    st.plotly_chart(fig_pipeline, use_container_width=True)

    # Gráficos cruzados
    st.markdown("---")
    st.markdown("### 📊 Análisis Cruzado")

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        if df_enriquecido is not None and 'puntuacion_amenaza' in df_enriquecido.columns:
            st.markdown("#### Distribución de Amenaza")
            fig_hist = px.histogram(
                df_enriquecido,
                x='puntuacion_amenaza',
                nbins=30,
                title="Puntuación de Amenaza (Fase 2)",
                color_discrete_sequence=['#e74c3c']
            )
            st.plotly_chart(fig_hist, use_container_width=True)

    with col_c2:
        if df_reporte is not None and 'confianza_prediccion' in df_reporte.columns:
            st.markdown("#### Confianza de Predicciones HMM")
            fig_conf = px.histogram(
                df_reporte,
                x='confianza_prediccion',
                nbins=20,
                title="Distribución de Confianza (Fase 3)",
                color_discrete_sequence=['#3498db']
            )
            st.plotly_chart(fig_conf, use_container_width=True)

    # Información del proyecto
    st.markdown("---")
    st.markdown("### 📋 Información del Proyecto")

    with st.expander("📖 Sobre el Proyecto"):
        st.markdown("""
        **Proyecto de Titulación TI** - Análisis de amenazas en foros de la Dark Web

        Este proyecto integra 3 fases:
        1. **Fase 1 - Scraping**: Extracción de datos de foros .onion con anonimización PII
        2. **Fase 2 - NLP**: Procesamiento con SecureBERT para detección de entidades y mapeo MITRE
        3. **Fase 3 - HMM**: Modelos Ocultos de Markov para predicción de comportamiento de atacantes

        **Tecnologías**: Python, Streamlit, SecureBERT, HMM, MITRE ATT&CK, Cyber Kill Chain
        """)

    with st.expander("📂 Archivos Generados"):
        df_archivos = pd.DataFrame([
            {"Archivo": nombre, "Ruta": str(ruta), "Existe": "✅" if estado_archivos.get(nombre, False) else "❌"}
            for nombre, ruta in ARCHIVOS_DATOS.items()
        ])
        st.dataframe(df_archivos, use_container_width=True, hide_index=True)

# ============================================================================
# PESTAÑA DATOS CRUDOS
# ============================================================================

with tab_datos:
    st.subheader("📋 Exploración de Datos Crudos")

    archivo_seleccionado = st.selectbox(
        "Selecciona un archivo para explorar:",
        options=[n for n, e in estado_archivos.items() if e],
        index=0 if any(estado_archivos.values()) else None
    )

    if archivo_seleccionado:
        ruta = ARCHIVOS_DATOS[archivo_seleccionado]

        if archivo_seleccionado.endswith('.csv'):
            df_vista = cargar_csv(ruta)
            if df_vista is not None:
                st.markdown(f"**{len(df_vista)} registros × {len(df_vista.columns)} columnas**")

                # Selector de columnas
                cols_disp = df_vista.columns.tolist()
                cols_sel = st.multiselect(
                    "Seleccionar columnas:",
                    cols_disp,
                    default=cols_disp[:min(6, len(cols_disp))]
                )

                if cols_sel:
                    # Paginación
                    regs_por_pag = st.selectbox("Registros por página:", [10, 25, 50, 100], index=1)
                    pagina = st.number_input("Página:", min_value=1, max_value=max(1, len(df_vista) // regs_por_pag + 1), value=1)
                    inicio = (pagina - 1) * regs_por_pag
                    fin = min(inicio + regs_por_pag, len(df_vista))

                    st.dataframe(df_vista[cols_sel].iloc[inicio:fin], use_container_width=True)
                    st.caption(f"Mostrando {inicio}-{fin} de {len(df_vista)}")

                    # Descarga
                    formato_desc = st.radio("Formato:", ["CSV", "JSON"], horizontal=True, key="formato_desc")
                    if formato_desc == "CSV":
                        data_str = df_vista.to_csv(index=False).encode('utf-8')
                        mime = "text/csv"
                        ext = "csv"
                    else:
                        data_str = df_vista.to_json(orient='records', force_ascii=False).encode('utf-8')
                        mime = "application/json"
                        ext = "json"

                    st.download_button(
                        label=f"⬇️ Descargar {archivo_seleccionado} como {formato_desc}",
                        data=data_str,
                        file_name=f"{archivo_seleccionado.rsplit('.', 1)[0]}_export.{ext}",
                        mime=mime
                    )

        elif archivo_seleccionado.endswith('.json'):
            data_json = cargar_json(ruta)
            if data_json:
                st.json(data_json)
        elif archivo_seleccionado.endswith('.pkl'):
            st.info("Los archivos .pkl (modelo) no se pueden visualizar directamente como texto.")

    else:
        st.info("No hay archivos de datos disponibles. Ejecuta las fases del pipeline para generar datos.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        🎯 Dashboard Integrador - Proyecto de Titulación TI ·
        3 Fases: Scraping · NLP · HMM
    </div>
    """,
    unsafe_allow_html=True
)