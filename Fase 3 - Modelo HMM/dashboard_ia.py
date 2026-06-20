#!/usr/bin/env python3
# encoding: utf-8
"""
Dashboard IA - Análisis inteligente de resultados HMM con múltiples proveedores
===============================================================================
Dashboard independiente que carga los resultados del modelo HMM y utiliza
inteligencia artificial para generar interpretaciones en lenguaje natural
de los patrones de comportamiento detectados.

Proveedores soportados:
  - DeepSeek (V3 / R1) — API compatible con OpenAI
  - Mistral (Small / Large) — API compatible con OpenAI
  - Google Gemini (2.0 Flash) — API nativa
  - Groq (Llama 3.3 70B) — API compatible con OpenAI

Uso:
    streamlit run dashboard_ia.py

Requiere:
    pip install streamlit pandas plotly numpy openai google-generativeai
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import pickle
import os
import time

import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------------------------
# Configuración de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard IA - Análisis HMM con Inteligencia Artificial",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Configuración de proveedores
# ---------------------------------------------------------------------------

PROVEEDORES = {
    "DeepSeek": {
        "modelo_default": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "ayuda_url": "https://platform.deepseek.com",
        "ayuda_texto": "DeepSeek Platform",
        "descripcion": "Modelo V3 — Excelente rendimiento, $5 de crédito gratis al registrarse",
        "sdk": "openai",
    },
    "Mistral": {
        "modelo_default": "mistral-small-latest",
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "ayuda_url": "https://console.mistral.ai",
        "ayuda_texto": "Mistral Console",
        "descripcion": "Mistral Small — Buen balance entre calidad y velocidad",
        "sdk": "openai",
    },
    "Google Gemini": {
        "modelo_default": "gemini-2.0-flash",
        "api_key_env": "GOOGLE_API_KEY",
        "ayuda_url": "https://aistudio.google.com/app/apikey",
        "ayuda_texto": "Google AI Studio",
        "descripcion": "Gemini 2.0 Flash — Rápido y gratuito (15 req/min)",
        "sdk": "google",
    },
    "Groq": {
        "modelo_default": "llama-3.3-70b-versatile",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "ayuda_url": "https://console.groq.com/keys",
        "ayuda_texto": "Groq Console",
        "descripcion": "Llama 3.3 70B — Ultra rápido, 30 req/min gratis",
        "sdk": "openai",
    },
}

# ---------------------------------------------------------------------------
# Rutas por defecto
# ---------------------------------------------------------------------------
RUTA_MODELO = "../Datos/modelo_hmm.pkl"
RUTA_REPORTE = "../Datos/reporte_autores.csv"
RUTA_KILL_CHAIN = "kill_chain_fases.json"
RUTA_SECUENCIAS = "../Datos/secuencias_autores.json"

NOMBRES_FASES_DEFECTO = [
    "Reconocimiento", "Entrega", "Explotación",
    "Instalación", "C2", "Acciones"
]


# ---------------------------------------------------------------------------
# Funciones de carga de datos
# ---------------------------------------------------------------------------

@st.cache_data
def cargar_modelo(ruta):
    """Carga el modelo HMM entrenado (pickle)."""
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        st.error(f"Error cargando modelo: {e}")
        return None


@st.cache_data
def cargar_reporte(ruta):
    """Carga el reporte CSV de autores."""
    if not os.path.exists(ruta):
        return None
    try:
        return pd.read_csv(ruta)
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
            return json.load(f)
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
            return json.load(f)
    except Exception as e:
        st.error(f"Error cargando secuencias: {e}")
        return None


def obtener_nombres_fases(mapeo_kill):
    """Obtiene nombres de fases desde el mapeo o usa valores por defecto."""
    if mapeo_kill and 'metadata' in mapeo_kill and 'fases' in mapeo_kill['metadata']:
        return [f['nombre'] for f in mapeo_kill['metadata']['fases']]
    return NOMBRES_FASES_DEFECTO


# ---------------------------------------------------------------------------
# Funciones de IA
# ---------------------------------------------------------------------------

def inicializar_proveedor(nombreProveedor, api_key, modelo_nombre=None):
    """
    Inicializa el cliente del proveedor de IA seleccionado.
    Retorna (cliente, modelo_nombre) o (None, None) si hay error.
    """
    config = PROVEEDORES[nombreProveedor]
    modelo = modelo_nombre or config["modelo_default"]

    try:
        if config["sdk"] == "openai":
            from openai import OpenAI
            cliente = OpenAI(api_key=api_key, base_url=config["base_url"])
            return cliente, modelo

        elif config["sdk"] == "google":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            cliente = genai.GenerativeModel(modelo)
            return cliente, modelo

    except ImportError as e:
        paquete = "openai" if config["sdk"] == "openai" else "google-generativeai"
        st.error(f"❌ Falta instalar `{paquete}`. Ejecuta: `pip install {paquete}`")
        return None, None
    except Exception as e:
        st.error(f"❌ Error inicializando {nombreProveedor}: {e}")
        return None, None

    return None, None


def llamar_ia(nombreProveedor, cliente, modelo_nombre, prompt, max_reintentos=2):
    """
    Llama al proveedor de IA con manejo de errores y reintentos.
    Retorna el texto de respuesta o un mensaje de error.
    """
    for intento in range(max_reintentos + 1):
        try:
            config = PROVEEDORES[nombreProveedor]

            if config["sdk"] == "openai":
                respuesta = cliente.chat.completions.create(
                    model=modelo_nombre,
                    messages=[
                        {"role": "system", "content": "Eres un experto analista de ciberseguridad. Responde siempre en español."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4096,
                )
                return respuesta.choices[0].message.content

            elif config["sdk"] == "google":
                respuesta = cliente.generate_content(prompt)
                return respuesta.text

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                if intento < max_reintentos:
                    tiempo_espera = 5 * (intento + 1)
                    st.warning(f"⚠️ Límite de tasa alcanzado. Reintentando en {tiempo_espera}s... (intento {intento + 1}/{max_reintentos})")
                    time.sleep(tiempo_espera)
                    continue
                else:
                    return (
                        f"❌ **Error 429: Cuota agotada en {nombreProveedor}**\n\n"
                        f"Tu cuota gratuita se ha agotado. Opciones:\n"
                        f"1. **Espera** unos minutos y vuelve a intentar\n"
                        f"2. **Cambia de proveedor** en el panel lateral\n"
                        f"3. **Verifica tu plan** en la consola del proveedor\n\n"
                        f"Detalle del error: {error_str[:200]}"
                    )
            else:
                return f"❌ Error al llamar a {nombreProveedor}: {error_str[:300]}"

    return f"❌ Error desconocido al llamar a {nombreProveedor}"


def compilar_metricas_modelo(modelo_hmm, df_reporte, mapeo_kill, nombres_fases):
    """
    Compila las métricas del modelo HMM en un texto estructurado
    para enviar como prompt a la IA.
    """
    lineas = []
    lineas.append("=== DATOS DEL MODELO HMM ===")
    lineas.append(f"Estados ocultos (perfiles de comportamiento): {modelo_hmm.n_components}")
    lineas.append(f"Observaciones (fases de Kill Chain): {modelo_hmm.emissionprob_.shape[1]}")
    lineas.append(f"Fases: {', '.join(nombres_fases)}")
    lineas.append("")

    # Probabilidades iniciales
    lineas.append("=== PROBABILIDADES INICIALES DE ESTADOS ===")
    for i, p in enumerate(modelo_hmm.startprob_):
        lineas.append(f"  Estado {i}: {p:.4f}")
    lineas.append("")

    # Matriz de transición
    transmat = modelo_hmm.transmat_
    lineas.append("=== MATRIZ DE TRANSICIÓN ===")
    etiquetas = [f"Estado {i}" for i in range(transmat.shape[0])]
    header = "         " + "  ".join([f"→{e:>8}" for e in etiquetas])
    lineas.append(header)
    for i, fila in enumerate(transmat):
        vals = "  ".join([f"{v:>8.4f}" for v in fila])
        lineas.append(f"  {etiquetas[i]:>8}: {vals}")
    lineas.append("")

    # Persistencia
    persistencia = np.diag(transmat)
    lineas.append("=== PERSISTENCIA POR ESTADO ===")
    for i, p in enumerate(persistencia):
        tipo = "muy persistente" if p > 0.7 else "moderadamente persistente" if p > 0.4 else "transitorio"
        lineas.append(f"  Estado {i}: {p:.4f} ({tipo})")
    lineas.append("")

    # Matriz de emisión
    emisiones = modelo_hmm.emissionprob_
    lineas.append("=== MATRIZ DE EMISIÓN (qué fases genera cada perfil) ===")
    header = "         " + "  ".join([f"{f:>14}" for f in nombres_fases])
    lineas.append(header)
    for i, fila in enumerate(emisiones):
        vals = "  ".join([f"{v:>14.4f}" for v in fila])
        fase_dom = nombres_fases[np.argmax(fila)]
        lineas.append(f"  Estado {i}: {vals}  ← dominante: {fase_dom}")
    lineas.append("")

    # Reporte de autores
    if df_reporte is not None:
        lineas.append("=== PREDICCIONES POR AUTOR ===")
        lineas.append(f"Total de autores analizados: {len(df_reporte)}")

        if 'confianza_prediccion' in df_reporte.columns:
            conf_prom = df_reporte['confianza_prediccion'].mean()
            conf_min = df_reporte['confianza_prediccion'].min()
            conf_max = df_reporte['confianza_prediccion'].max()
            lineas.append(f"Confianza promedio: {conf_prom:.4f}")
            lineas.append(f"Confianza mínima: {conf_min:.4f}")
            lineas.append(f"Confianza máxima: {conf_max:.4f}")

        if 'siguiente_fase_nombre' in df_reporte.columns:
            conteo = df_reporte['siguiente_fase_nombre'].value_counts()
            lineas.append("\nDistribución de fases predichas:")
            for fase, count in conteo.items():
                pct = count / len(df_reporte) * 100
                lineas.append(f"  {fase}: {count} autores ({pct:.1f}%)")

        if 'estado_dominante' in df_reporte.columns:
            conteo_est = df_reporte['estado_dominante'].dropna().value_counts().sort_index()
            lineas.append("\nDistribución de estados dominantes:")
            for estado, count in conteo_est.items():
                pct = count / len(df_reporte) * 100
                lineas.append(f"  Estado {int(estado)}: {count} autores ({pct:.1f}%)")

        # Top 10
        if 'confianza_prediccion' in df_reporte.columns:
            top = df_reporte.nlargest(10, 'confianza_prediccion')
            lineas.append("\nTop 10 autores con mayor confianza:")
            for _, row in top.iterrows():
                lineas.append(
                    f"  {row['usuario']}: "
                    f"fase={row.get('siguiente_fase_nombre', 'N/A')}, "
                    f"confianza={row.get('confianza_prediccion', 0):.2%}, "
                    f"posts={row.get('cantidad_posts', 0)}"
                )

        # Autores en fase crítica
        if 'siguiente_fase_nombre' in df_reporte.columns:
            criticos = df_reporte[
                df_reporte['siguiente_fase_nombre'].isin(['Acciones sobre objetivos', 'Acciones'])
            ]
            if len(criticos) > 0:
                lineas.append(f"\n⚠️ Autores en fase CRÍTICA (Acciones sobre objetivos): {len(criticos)}")
                for _, row in criticos.head(10).iterrows():
                    lineas.append(
                        f"  {row['usuario']}: confianza={row.get('confianza_prediccion', 0):.2%}"
                    )

    return "\n".join(lineas)


def generar_prompt_ia(metricas_texto):
    """Genera el prompt completo para enviar a la IA."""
    return f"""Eres un experto analista de ciberseguridad especializado en threat intelligence
y análisis de comportamiento de actores maliciosos en la Dark Web.

A continuación se presentan los resultados de un Modelo Oculto de Markov (HMM)
entrenado con secuencias de técnicas MITRE ATT&CK extraídas de posts de autores
en foros .onion. Los estados ocultos del HMM representan perfiles de comportamiento
de los atacantes, y las observaciones son las 6 fases de la Cyber Kill Chain.

--- INICIO DE DATOS ---
{metricas_texto}
--- FIN DE DATOS ---

Proporciona un análisis completo en español que incluya:

1. **RESUMEN EJECUTIVO** (2-3 párrafos): Visión general de los patrones detectados.

2. **INTERPRETACIÓN DE PERFILES**: Para cada estado oculto, explica qué tipo de
   atacante representa. Asigna un nombre descriptivo a cada perfil.

3. **ANÁLISIS DE TRANSICIONES**: ¿Qué perfiles permanecen estables? ¿Cuáles evolucionan?

4. **ALERTAS DE RIESGO**: ¿Hay autores en fase crítica? ¿Qué perfiles son más peligrosos?

5. **RECOMENDACIONES DE MONITOREO**: ¿Qué vigilar de cerca?

6. **CONCLUSIONES**: Síntesis final con los hallazgos más importantes.

Responde de forma clara y técnica, pero accesible para un auditor de seguridad."""


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------

st.sidebar.title("🤖 Dashboard IA")
st.sidebar.markdown("---")

# Selector de proveedor
st.sidebar.markdown("### 🧠 Proveedor de IA")
proveedorSeleccionado = st.sidebar.selectbox(
    "Selecciona el proveedor:",
    options=list(PROVEEDORES.keys()),
    index=0,
    key="proveedor"
)

configProveedor = PROVEEDORES[proveedorSeleccionado]
st.sidebar.info(configProveedor["descripcion"])

# API Key
st.sidebar.markdown("### 🔑 API Key")
variable_entorno = os.environ.get(configProveedor["api_key_env"], "")

api_key = st.sidebar.text_input(
    "API Key:",
    value=variable_entorno,
    type="password",
    help=f"Obtén tu API key en {configProveedor['ayuda_url']}"
)

if not api_key:
    st.sidebar.warning("⚠️ Se requiere una API key")
    st.sidebar.markdown(f"[🔑 Obtener key en {configProveedor['ayuda_texto']}]({configProveedor['ayuda_url']})")

# Modelo (opcional)
st.sidebar.markdown("### ⚙️ Modelo")
modelo_custom = st.sidebar.text_input(
    "Nombre del modelo (dejar vacío para default):",
    value="",
    help=f"Default: {configProveedor['modelo_default']}"
)
modelo_elegido = modelo_custom.strip() if modelo_custom.strip() else None

st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 Rutas de archivos")

ruta_modelo = st.sidebar.text_input("Modelo HMM (.pkl):", value=RUTA_MODELO)
ruta_reporte = st.sidebar.text_input("Reporte autores (.csv):", value=RUTA_REPORTE)
ruta_kill = st.sidebar.text_input("Kill Chain (.json):", value=RUTA_KILL_CHAIN)
ruta_sec = st.sidebar.text_input("Secuencias (.json):", value=RUTA_SECUENCIAS)

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

with st.spinner("Cargando datos del modelo HMM..."):
    modelo_hmm = cargar_modelo(ruta_modelo)
    df_reporte = cargar_reporte(ruta_reporte)
    mapeo_kill = cargar_kill_chain(ruta_kill)
    secuencias_data = cargar_secuencias(ruta_sec)

nombres_fases = obtener_nombres_fases(mapeo_kill)
n_fases = len(nombres_fases)

datos_disponibles = {
    "modelo": modelo_hmm is not None,
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
    st.title("🤖 Dashboard IA - Análisis HMM con Inteligencia Artificial")
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col2:
        st.warning("### 📂 No se encontraron datos")
        st.markdown("""
        Para usar este dashboard, primero ejecuta la Fase 3:

        ```bash
        cd "Fase 3 - Modelo HMM"
        pip install -r requirements.txt
        python modulos/main.py
        ```
        """)
    st.stop()

# ---------------------------------------------------------------------------
# Cabecera
# ---------------------------------------------------------------------------

st.title("🤖 Dashboard IA - Análisis HMM con Inteligencia Artificial")
st.markdown(
    "Análisis inteligente de resultados del Modelo Oculto de Markov "
    f"utilizando **{proveedorSeleccionado}** para interpretación en lenguaje natural."
)
st.markdown("---")

# KPIs
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🧠 Estados", modelo_hmm.n_components if modelo_hmm else "N/A")
with col2:
    st.metric("👤 Autores", len(df_reporte) if df_reporte is not None else "N/A")
with col3:
    if df_reporte is not None and 'confianza_prediccion' in df_reporte.columns:
        st.metric("🎯 Confianza Prom.", f"{df_reporte['confianza_prediccion'].mean():.1%}")
    else:
        st.metric("🎯 Confianza", "N/A")
with col4:
    icono_key = "✅" if api_key else "❌"
    st.metric(f"🔑 {proveedorSeleccionado}", f"{icono_key} Key")

st.markdown("---")

# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------

tab1, tab2, tab3 = st.tabs([
    "📊 Resumen del Modelo",
    "🔍 Análisis por Autor",
    "🤖 Análisis con IA"
])

# ============================================================================
# PESTAÑA 1: Resumen del Modelo
# ============================================================================

with tab1:
    st.subheader("📊 Resumen del Modelo HMM")

    if modelo_hmm is None:
        st.warning("No hay modelo HMM cargado.")
    else:
        col_izq, col_der = st.columns(2)

        with col_izq:
            st.markdown("### 📈 Matriz de Transición")
            transmat = modelo_hmm.transmat_
            n_est = transmat.shape[0]
            etiq = [f"Estado {i}" for i in range(n_est)]

            fig = go.Figure(data=go.Heatmap(
                z=transmat, x=etiq, y=etiq,
                text=np.round(transmat, 3), texttemplate="%{text}",
                textfont={"size": 12}, colorscale="YlOrRd", zmin=0, zmax=1,
                hovertemplate="Desde: %{y}<br>Hacia: %{x}<br>Prob: %{z:.3f}<extra></extra>"
            ))
            fig.update_layout(xaxis_title="Estado Siguiente", yaxis_title="Estado Actual", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col_der:
            st.markdown("### 📊 Matriz de Emisión")
            emisiones = modelo_hmm.emissionprob_
            fig_em = go.Figure(data=go.Heatmap(
                z=emisiones, x=nombres_fases, y=etiq,
                text=np.round(emisiones, 3), texttemplate="%{text}",
                textfont={"size": 11}, colorscale="Viridis", zmin=0, zmax=1,
                hovertemplate="Estado: %{y}<br>Fase: %{x}<br>Prob: %{z:.3f}<extra></extra>"
            ))
            fig_em.update_layout(xaxis_title="Fase de Kill Chain", yaxis_title="Estado Oculto", height=400)
            st.plotly_chart(fig_em, use_container_width=True)

        # Perfiles
        st.markdown("### 🎭 Perfiles de Comportamiento")
        cols_p = st.columns(n_est)
        for i in range(n_est):
            with cols_p[i]:
                f_dom = np.argmax(emisiones[i])
                st.markdown(f"""
                **Estado {i}**
                - Fase: **{nombres_fases[f_dom]}**
                - Prob: **{emisiones[i][f_dom]:.1%}**
                - Persistencia: **{transmat[i][i]:.1%}**
                """)

        # Distribución
        if df_reporte is not None and 'siguiente_fase_nombre' in df_reporte.columns:
            st.markdown("### 🎯 Distribución de Fases Predichas")
            conteo = df_reporte['siguiente_fase_nombre'].value_counts().reset_index()
            conteo.columns = ['Fase', 'Cantidad']
            fig_pie = px.pie(conteo, values='Cantidad', names='Fase',
                            color_discrete_sequence=px.colors.qualitative.Set2, hole=0.3)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)

# ============================================================================
# PESTAÑA 2: Análisis por Autor
# ============================================================================

with tab2:
    st.subheader("🔍 Análisis por Autor")

    autores_disp = []
    if df_reporte is not None and 'usuario' in df_reporte.columns:
        autores_disp = sorted(df_reporte['usuario'].tolist())

    if not autores_disp:
        st.warning("No hay datos de autores disponibles.")
    else:
        autor = st.selectbox("Selecciona un atacante:", options=autores_disp)

        if autor and df_reporte is not None:
            adata = df_reporte[df_reporte['usuario'] == autor].iloc[0]

            c1, c2 = st.columns([2, 1])
            with c1:
                st.markdown(f"### 👤 `{autor}`")
                st.json({
                    "Posts": int(adata.get('cantidad_posts', 0)),
                    "Estado dominante": int(adata.get('estado_dominante', -1))
                    if pd.notna(adata.get('estado_dominante')) else "N/A",
                    "Fase predicha": adata.get('siguiente_fase_nombre', 'N/A'),
                    "Confianza": f"{float(adata.get('confianza_prediccion', 0)):.2%}",
                })

            with c2:
                conf = float(adata.get('confianza_prediccion', 0))
                fase = adata.get('siguiente_fase_nombre', 'N/A')
                st.markdown(f"""
                <div style="text-align:center; padding:20px; border:2px solid #3498db;
                     border-radius:10px; background-color:#f0f8ff;">
                    <h3 style="margin:0;">{fase}</h3>
                    <p style="font-size:24px; margin:10px 0; color:#2ecc71;">{conf:.1%}</p>
                    <p style="color:gray;">confianza</p>
                </div>
                """, unsafe_allow_html=True)

            if modelo_hmm is not None:
                st.markdown("### 🎯 Probabilidad de cada fase")
                ed = adata.get('estado_dominante')
                if pd.notna(ed):
                    estado_dom = int(ed)
                    trans = modelo_hmm.transmat_[estado_dom]
                    probs = np.zeros(n_fases)
                    for s in range(modelo_hmm.n_components):
                        for f in range(n_fases):
                            probs[f] += trans[s] * modelo_hmm.emissionprob_[s, f]
                    probs /= probs.sum()

                    df_f = pd.DataFrame({"Fase": nombres_fases, "Probabilidad": probs})
                    fig_f = px.bar(df_f, x="Fase", y="Probabilidad", color="Probabilidad",
                                  color_continuous_scale="Viridis", range_color=[0, 1], text_auto='.1%')
                    fig_f.update_traces(textposition='outside')
                    st.plotly_chart(fig_f, use_container_width=True)

# ============================================================================
# PESTAÑA 3: Análisis con IA
# ============================================================================

with tab3:
    st.subheader("🤖 Análisis con Inteligencia Artificial")
    st.markdown(f"Proveedor actual: **{proveedorSeleccionado}** — {configProveedor['descripcion']}")

    if not api_key:
        st.warning(
            f"⚠️ Se requiere una API key de **{proveedorSeleccionado}**.\n\n"
            f"[🔗 Obtener key en {configProveedor['ayuda_texto']}]({configProveedor['ayuda_url']})"
        )

        # Mostrar opciones alternativas
        st.markdown("---")
        st.markdown("### 🔄 Otras opciones disponibles")
        for nombre, cfg in PROVEEDORES.items():
            if nombre != proveedorSeleccionado:
                st.markdown(f"- **{nombre}**: {cfg['descripcion']} — [Obtener key]({cfg['ayuda_url']})")

    elif modelo_hmm is None:
        st.warning("No hay modelo HMM cargado.")
    else:
        st.markdown("""
        **¿Qué hace esta función?**
        1. Compila las métricas del modelo (matrices, predicciones, etc.)
        2. Las envía a la IA con un prompt especializado en ciberseguridad
        3. Recibe un análisis completo en lenguaje natural
        """)

        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            generar = st.button("🚀 Generar Análisis IA", type="primary", use_container_width=True)
        with col_info:
            if st.checkbox("Ver métricas compiladas (debug)", value=False):
                metricas = compilar_metricas_modelo(modelo_hmm, df_reporte, mapeo_kill, nombres_fases)
                st.code(metricas, language=None)

        if generar:
            with st.spinner(f"🤖 Inicializando {proveedorSeleccionado}..."):
                cliente, modelo_nom = inicializar_proveedor(proveedorSeleccionado, api_key, modelo_elegido)

            if cliente is not None:
                with st.spinner("📊 Compilando métricas..."):
                    metricas = compilar_metricas_modelo(modelo_hmm, df_reporte, mapeo_kill, nombres_fases)
                    prompt = generar_prompt_ia(metricas)

                with st.spinner(f"🧠 Enviando a {proveedorSeleccionado}... (puede tardar 10-30s)"):
                    respuesta = llamar_ia(proveedorSeleccionado, cliente, modelo_nom, prompt)

                st.markdown("---")
                st.markdown("## 📝 Análisis Generado por IA")
                st.markdown(respuesta)

                st.session_state['respuesta_ia'] = respuesta
                st.session_state['proveedor_ia'] = proveedorSeleccionado
                st.session_state['timestamp_ia'] = time.strftime("%Y-%m-%d %H:%M:%S")

                st.markdown("---")
                st.download_button(
                    label="⬇️ Descargar análisis como TXT",
                    data=f"Proveedor: {proveedorSeleccionado}\nModelo: {modelo_nom}\nFecha: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{'='*60}\n\n{respuesta}".encode('utf-8'),
                    file_name=f"analisis_ia_{proveedorSeleccionado.lower().replace(' ', '_')}.txt",
                    mime="text/plain"
                )

        elif 'respuesta_ia' in st.session_state:
            prov = st.session_state.get('proveedor_ia', 'IA')
            ts = st.session_state.get('timestamp_ia', 'N/A')
            st.info(f"📋 Último análisis ({prov}) — {ts}")
            st.markdown("## 📝 Análisis Generado por IA")
            st.markdown(st.session_state['respuesta_ia'])

            st.download_button(
                label="⬇️ Descargar análisis como TXT",
                data=st.session_state['respuesta_ia'].encode('utf-8'),
                file_name="analisis_ia_hmm.txt",
                mime="text/plain"
            )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
        🤖 Dashboard IA - Proyecto de Titulación TI ·
        Análisis de comportamiento en foros .onion con HMM + IA
    </div>
    """,
    unsafe_allow_html=True
)