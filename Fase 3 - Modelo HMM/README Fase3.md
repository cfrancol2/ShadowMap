# Fase 3: Modelo Oculto de Markov (HMM) para Análisis de Comportamiento

**Capa de Modelado Predictivo** - Predicción de fases de la Cyber Kill Chain basada en secuencias de autores de foros .onion

---

## 📋 Descripción General

Esta fase implementa un **Modelo Oculto de Markov (HMM)** para analizar y predecir el comportamiento de autores en foros de la Dark Web. Utilizando las secuencias de técnicas MITRE ATT&CK generadas en la Fase 2, el modelo aprende patrones de transición entre fases de la **Cyber Kill Chain** y predice el siguiente movimiento probable de cada autor.

### 🎯 Objetivos Principales

1. **Mapeo a Cyber Kill Chain**: Convertir técnicas MITRE ATT&CK en fases discretas (0-5) de la Kill Chain
2. **Modelado de Comportamiento**: Entrenar un HMM categórico que capture patrones de transición entre fases
3. **Predicción de Siguiente Fase**: Para cada autor, predecir la fase más probable de su próxima acción
4. **Identificación de Perfiles**: Descubrir estados ocultos que representan perfiles de comportamiento atacante
5. **Visualización**: Generar dashboard con matrices de transición, distribuciones y secuencias individuales

---

## 🏗️ Arquitectura del Sistema (Modular)

La Fase 3 está organizada en **módulos independientes** con nombres descriptivos en español.

```
Fase 3 - Modelo HMM/
├── modulos/                       # Código fuente modular
│   ├── main.py                    # Orquestador principal del pipeline HMM
│   ├── cargar_secuencias.py       # Carga y mapeo de técnicas MITRE a Kill Chain
│   ├── entrenar_hmm.py            # Entrenamiento del modelo CategoricalHMM
│   ├── predecir_siguiente.py      # Predicción de siguiente fase por autor
│   └── __init__.py                # Inicializador del paquete
├── dashboard_hmm.py               # Dashboard interactivo Streamlit para visualizar resultados
├── dashboard_ia.py                # Dashboard IA con Google Gemini para análisis en lenguaje natural
├── kill_chain_fases.json          # Mapeo MITRE → Cyber Kill Chain (87+ técnicas)
├── requirements.txt               # Dependencias completas
└── README Fase3.md                # Esta documentación
```

### Diagrama de Flujo

```
Datos/
├── secuencias_autores.json ─┐     ← Salida de Fase 2
├── datos_enriquecidos.csv ──┤
                             ▼
                    ┌──────────────────┐
                    │     main.py      │ ← Orquestador
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────────┐ ┌──────────┐ ┌──────────────┐
    │cargar_secuencias│ │entrenar_ │ │predecir_     │
    │.py              │ │hmm.py    │ │siguiente.py  │
    └────────┬────────┘ └────┬─────┘ └──────┬───────┘
             │               │              │
             ▼               ▼              ▼
      Técnicas MITRE →  CategoricalHMM   Predicción
      mapeadas a       Baum-Welch        siguiente fase
      fases (0-5)      n_estados=4       por autor
             │               │              │
             └───────────────┼──────────────┘
                             ▼
                    ┌────────────────────────┐
                    │ ../Datos/              │
                    │ modelo_hmm.pkl         │ ← Modelo entrenado
                    │ reporte_autores.csv    │ ← Reporte CSV
                    └────────────────────────┘
                             │
                             ▼
                    ┌──────────────────────┐
                    │  dashboard_hmm.py    │ ← Visualización Streamlit
                    └──────────────────────┘
```

### Responsabilidad de cada Módulo

| Módulo | Responsabilidad |
|--------|----------------|
| `main.py` | Orquesta todo el pipeline: carga secuencias → entrena HMM → predice → visualiza |
| `cargar_secuencias.py` | Carga el JSON de la Fase 2, mapea técnicas MITRE a fases de Kill Chain (Opción A: fase más avanzada) |
| `entrenar_hmm.py` | Entrena un `CategoricalHMM` con algoritmo Baum-Welch, guarda/carga modelo en pickle |
| `predecir_siguiente.py` | Predice la siguiente fase usando Forward + Viterbi, genera reporte CSV por autor |
| `dashboard_ia.py` | Dashboard independiente con IA (DeepSeek, Mistral, Gemini, Groq) para análisis en lenguaje natural |

---

## 🔧 Tecnologías Utilizadas

### Librerías Principales

| Librería | Versión | Propósito |
|----------|---------|-----------|
| `hmmlearn` | ≥0.3.0 | Modelos Ocultos de Markov (CategoricalHMM) |
| `pandas` | ≥2.0.0 | Manipulación de datos tabulares y reportes CSV |
| `numpy` | ≥1.24.0 | Operaciones numéricas y álgebra lineal |
| `matplotlib` | ≥3.7.0 | Generación de gráficos estáticos PNG |
| `seaborn` | ≥0.12.0 | Heatmaps de matrices de transición |
| `streamlit` | ≥1.30.0 | Dashboard interactivo para visualización de resultados |

---

## 🚀 Ejecución del Pipeline

### Requisitos Previos

1. **Python 3.9+**
2. **Archivo de entrada**: `secuencias_autores.json` generado por la Fase 2
3. **Archivo de mapeo**: `kill_chain_fases.json` (incluido en el proyecto)

### Instalación de Dependencias

```bash
# Desde la carpeta "Fase 3 - Modelo HMM"
pip install -r requirements.txt
```

### Ejecución con datos reales (desde Fase 2)

```bash
python modulos/main.py \
    --input ../Datos/secuencias_autores.json \
    --kill-chain kill_chain_fases.json \
    --modelo ../Datos/modelo_hmm.pkl \
    --reporte-csv ../Datos/reporte_autores.csv
```

### Parámetros Configurables

| Parámetro | Abreviatura | Descripción | Valor por Defecto |
|-----------|-------------|-------------|-------------------|
| `--input` | `-i` | Ruta al JSON de secuencias de la Fase 2 | `../Datos/secuencias_autores.json` |
| `--kill-chain` | `-k` | Ruta al JSON de mapeo Kill Chain | `kill_chain_fases.json` |
| `--modelo` | `-m` | Ruta para guardar/cargar el modelo HMM | `../Datos/modelo_hmm.pkl` |
| `--reporte-csv` | `-r` | Ruta para el reporte CSV de autores | `../Datos/reporte_autores.csv` |
| `--n-estados` | `-e` | Número de estados ocultos (perfiles) | `4` |
| `--n-iter` | `-n` | Iteraciones máximas para entrenamiento | `100` |
| `--retrain` | — | Forzar re-entrenamiento aunque exista modelo guardado | `False` |

### Ejemplo de ejecución con parámetros personalizados

```bash
python modulos/main.py \
    -i ../Datos/secuencias_autores.json \
    -k kill_chain_fases.json \
    -e 5 \
    -n 200 \
    --retrain
```

---

## 🧠 Modelo HMM: Fundamentos

### ¿Qué es un Modelo Oculto de Markov (HMM)?

Un HMM es un modelo estadístico donde se asume que el sistema subyacente es un proceso de Markov con **estados ocultos** (no observables), y cada estado genera una **observación** visible. En este proyecto:

- **Estados ocultos**: Perfiles de comportamiento del atacante (ej. "explorador", "ejecutor", "persistente")
- **Observaciones**: Fases de la Cyber Kill Chain (0-5)
- **Transiciones**: Probabilidad de pasar de un perfil a otro
- **Emisiones**: Probabilidad de que un perfil genere una fase específica

### Las 6 Fases de la Cyber Kill Chain

| ID | Fase | Descripción |
|----|------|-------------|
| 0 | **Reconocimiento / Preparación** | Identificación de objetivos y preparación de arsenal |
| 1 | **Entrega** | Transmisión del arma al objetivo |
| 2 | **Explotación** | Ejecución del código en el sistema objetivo |
| 3 | **Instalación** | Establecimiento de acceso persistente |
| 4 | **Comando y Control (C2)** | Comunicación con la infraestructura de mando |
| 5 | **Acciones sobre objetivos** | Ejecución del objetivo final del ataque |

### Algoritmo de Mapeo: Opción A (Fase más Avanzada)

Cuando un post contiene múltiples técnicas MITRE, se selecciona la fase de la técnica **más avanzada** en la cadena (mayor ID). Esto captura el progreso máximo alcanzado por el atacante.

---

## 📊 Salidas Generadas

### 1. `modelo_hmm.pkl` — Modelo HMM entrenado

Modelo serializado con `pickle` que contiene:
- `startprob_`: Probabilidades iniciales de cada estado oculto
- `transmat_`: Matriz de transición entre estados (n_estados × n_estados)
- `emissionprob_`: Matriz de emisión (n_estados × n_fases)

### 2. `reporte_autores.csv` — Reporte por autor

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `usuario` | `str` | Identificador del autor anonimizado |
| `cantidad_posts` | `int` | Número de posts del autor en la secuencia |
| `estado_dominante` | `int` | Estado oculto más frecuente (perfil de comportamiento) |
| `siguiente_fase_id` | `int` | ID de la fase predicha (0-5) |
| `siguiente_fase_nombre` | `str` | Nombre de la fase predicha |
| `confianza_prediccion` | `float` | Probabilidad de la predicción (0.0 - 1.0) |
| `mensaje` | `str` | Estado del análisis ("OK" o "Secuencia demasiado corta") |

### 3. Dashboard Interactivo (`dashboard_hmm.py`)

Dashboard interactivo con **Streamlit** para visualizar todos los resultados del modelo HMM:

- **📈 Matriz de Transición**: Heatmap interactivo de probabilidades entre estados ocultos
- **📊 Probabilidades de Emisión**: Heatmap y gráficos por cada estado oculto
- **🔍 Análisis por Atacante**: Selector de autor con predicción de siguiente fase y probabilidades
- **📋 Reporte General**: Tabla con filtros, gráficos de distribución y descarga CSV/JSON
- **⚙️ Estados del Modelo**: Parámetros, matrices completas y diagrama Sankey de flujo

Para ejecutarlo:
```bash
streamlit run dashboard_hmm.py
```

### 4. Dashboard IA (`dashboard_ia.py`)

Dashboard independiente que utiliza **inteligencia artificial** para generar análisis en lenguaje natural de los resultados del HMM.

**Proveedores soportados (todos con tier gratuito):**

| Proveedor | Modelo | Cuota Gratis | Registro |
|-----------|--------|-------------|----------|
| **DeepSeek** | V3 / R1 | $5 de crédito | [platform.deepseek.com](https://platform.deepseek.com) |
| **Mistral** | Small / Large | Créditos iniciales | [console.mistral.ai](https://console.mistral.ai) |
| **Google Gemini** | 2.0 Flash | 15 req/min | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| **Groq** | Llama 3.3 70B | 30 req/min | [console.groq.com](https://console.groq.com/keys) |

Ejecución:
```bash
streamlit run dashboard_ia.py
```

---

## 🛠️ Pipeline Detallado

### Paso 1: Carga de secuencias (`cargar_secuencias.py`)

1. Lee el archivo JSON `secuencias_autores.json` de la Fase 2
2. Carga el mapeo `kill_chain_fases.json` (técnica MITRE → fase)
3. Para cada post de cada autor, convierte las técnicas MITRE a una fase (0-5)
4. Si un post no tiene técnicas reconocidas, usa la fase por defecto (Acciones, 5)
5. Retorna diccionario `{usuario: [fase_0, fase_1, ...]}`

### Paso 2: Entrenamiento del HMM (`entrenar_hmm.py`)

1. Valida que haya suficientes datos (total_posts ≥ n_estados × 3)
2. Concatena todas las secuencias en un array 1D
3. Inicializa `CategoricalHMM` con:
   - `n_components`: estados ocultos (default 4)
   - `n_iter`: iteraciones Baum-Welch (default 100)
   - `tol`: tolerancia de convergencia (1e-4)
4. Entrena con el algoritmo **Baum-Welch** (EM)
5. Guarda el modelo en `modelo_hmm.pkl`
6. **Reanudación inteligente**: Si ya existe un modelo guardado, lo carga sin reentrenar (a menos que se use `--retrain`)

### Paso 3: Predicción de siguiente fase (`predecir_siguiente.py`)

Para cada autor con ≥2 posts:
1. Aplica el algoritmo **Viterbi** para determinar la secuencia de estados ocultos
2. Obtiene el último estado oculto
3. Calcula la distribución de probabilidad del siguiente estado (matriz de transición)
4. Calcula la probabilidad de cada fase (matriz de emisión)
5. Selecciona la fase con mayor probabilidad como **predicción**
6. Calcula la **confianza** como la probabilidad normalizada de la fase predicha

### Paso 4: Reporte CSV (`predecir_siguiente.py`)

Genera un archivo CSV tabular con todos los autores, su estado dominante, la fase predicha y la confianza.

### Paso 5: Dashboard interactivo (`dashboard_hmm.py`)

Dashboard interactivo desarrollado con **Streamlit** para visualizar los resultados del modelo HMM en tiempo real:
- **Matriz de Transición**: Heatmap interactivo de probabilidades entre estados ocultos
- **Probabilidades de Emisión**: Heatmap y gráficos por cada estado oculto
- **Análisis por Atacante**: Selector de autor con predicción de siguiente fase y probabilidades
- **Reporte General**: Tabla con filtros, gráficos de distribución y descarga CSV/JSON
- **Estados del Modelo**: Parámetros, matrices completas y diagrama Sankey de flujo

Ejecución:
```bash
streamlit run dashboard_hmm.py
```

---

## 📈 Métricas del Modelo

### Parámetros del HMM

| Parámetro | Valor Default | Descripción |
|-----------|---------------|-------------|
| Estados ocultos | 4 | Perfiles de comportamiento atacante |
| Observaciones | 6 | Fases de la Cyber Kill Chain (0-5) |
| Iteraciones | 100 | Máximo de iteraciones Baum-Welch |
| Tolerancia | 1e-4 | Criterio de convergencia |

### Validación de Secuencias

1. **Longitud mínima**: ≥2 posts por autor para predicción
2. **Longitud mínima de entrenamiento**: ≥2 posts por autor
3. **Umbral de datos**: total_posts ≥ n_estados × 3 para evitar overfitting
4. **Mapeo de técnicas**: Coincidencia exacta primero, luego parcial (técnica base)
5. **Fase por defecto**: Técnicas no reconocidas → fase 5 (Acciones sobre objetivos)

---

## 🔄 Reejecución y Mantenimiento

### Características de Diseño

- **Reanudación inteligente**: El modelo entrenado se guarda en `modelo_hmm.pkl`. Si ya existe, se carga automáticamente sin reentrenar
- **Forzar reentrenamiento**: Usar `--retrain` para reentrenar desde cero
- **Actualizable**: Si se actualiza `kill_chain_fases.json` o las secuencias de entrada, basta reejecutar
- **Modular**: Cada componente (carga, entrenamiento, predicción, visualización) puede actualizarse independientemente
- **Logging completo**: Registro detallado en `hmm_processing_log.txt`

### Actualización del Mapeo Kill Chain

```bash
# Editar el archivo JSON para agregar/modificar técnicas MITRE
# Luego reejecutar con --retrain para aplicar cambios
python modulos/main.py --retrain
```

---

## 🎓 Casos de Uso

### 1. Análisis de Comportamiento por Autor

```python
import pandas as pd

# Cargar reporte de autores
df = pd.read_csv('../Datos/reporte_autores.csv')

# Autores con mayor confianza de predicción
top_confianza = df.sort_values('confianza_prediccion', ascending=False).head(10)

# Autores que se espera avancen a fase crítica (Acciones sobre objetivos)
en_ataque = df[df['siguiente_fase_nombre'] == 'Acciones sobre objetivos']
```

### 2. Carga del Modelo Entrenado

```python
import pickle

with open('../Datos/modelo_hmm.pkl', 'rb') as f:
    modelo = pickle.load(f)

print(f"Estados ocultos: {modelo.n_components}")
print(f"Matriz de transición:\n{modelo.transmat_}")
print(f"Probabilidades iniciales: {modelo.startprob_}")
```

### 3. Identificación de Perfiles de Atacante

Los estados ocultos aprendidos por el HMM representan **perfiles de comportamiento**:

- **Estado 0**: Perfil de **reconocimiento** — altas probabilidades de fase 0
- **Estado 1**: Perfil de **ejecución** — altas probabilidades de fases 2-3
- **Estado 2**: Perfil de **persistencia** — altas probabilidades de fase 3-4
- **Estado 3**: Perfil de **acción final** — altas probabilidades de fase 5

---

## 📚 Referencias

- **hmmlearn**: Biblioteca de modelos ocultos de Markov para Python
- **Cyber Kill Chain**: Framework de Lockheed Martin para ciclo de vida de ataques
- **MITRE ATT&CK**: Base de conocimientos de técnicas de adversarios
- **Baum-Welch**: Algoritmo EM para entrenamiento de HMM
- **Algoritmo de Viterbi**: Decodificación de la secuencia de estados más probable
- **Algoritmo Forward**: Cálculo de probabilidad de observaciones

---

## ✅ Criterios de Éxito

1. ✅ Mapeo correcto de técnicas MITRE a 6 fases de Cyber Kill Chain
2. ✅ Entrenamiento exitoso del modelo CategoricalHMM con Baum-Welch
3. ✅ Predicción de siguiente fase para autores con ≥2 posts
4. ✅ Generación de reporte CSV con confianza de predicción
5. ✅ Dashboard visual con matriz de transición, distribución y secuencias
5b. ✅ Dashboard IA con análisis en lenguaje natural (múltiples proveedores: DeepSeek, Mistral, Gemini, Groq)
6. ✅ Reanudación inteligente (carga de modelo guardado sin reentrenar)
7. ✅ Logging completo y manejo de errores robusto
8. ✅ Compatibilidad con salida de Fase 2 (`secuencias_autores.json`)

---

## 🚀 Próximos Pasos (Integración)

1. **Sistema de Alertas**: Notificar cuando un autor se acerque a fase crítica
2. **Clustering de Autores**: Agrupar por perfil de comportamiento para análisis de redes
3. **Evaluación Temporal**: Validar predicciones contra datos futuros
4. **Modelos Avanzados**: Comparar HMM con LSTM/Transformers para predicción de secuencias

**¡ShadowMap - Fase 3 completada! Listo para visualizar con el Dashboard Integrador. 🚀**
