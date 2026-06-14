# Fase 2: Procesamiento de Lenguaje Natural con Modelos Especializados

**Núcleo Semántico del Proyecto** - Transformación de texto de Dark Web en datos estructurados para HMM

---

## 📋 Descripción General

Esta fase implementa el **procesamiento NLP avanzado** utilizando modelos **SecureBERT 2.0** para analizar conversaciones de foros `.onion`, extraer entidades de ciberseguridad y preparar datos estructurados que alimentarán el modelo **Hidden Markov Model (HMM)** en la Fase 3.

### 🎯 Objetivos Principales

1. **Detección de Entidades Especializadas**: Identificar herramientas ofensivas, vulnerabilidades, técnicas MITRE y sectores objetivo
2. **Enriquecimiento Semántico**: Añadir metadatos estructurados a los datos crudos
3. **Mapeo a MITRE ATT&CK**: Asociar entidades detectadas con técnicas de ataque conocidas
4. **Preparación para HMM**: Crear secuencias cronológicas de posts por autor
5. **Generación de Datos Estructurados**: Produce salidas listas para modelado predictivo

---

## 🏗️ Arquitectura del Sistema (Modular)

La Fase 2 está organizada en **módulos independientes** con nombres en español para facilitar su comprensión y presentación.

```
Fase 2 - Analisis semantico NLP/
├── modulos/                    # Código fuente modular
│   ├── main.py                # Orquestador principal del pipeline
│   ├── cargar_modelos.py      # Carga de modelos SecureBERT 2.0
│   ├── procesar_ner.py        # Detección de entidades (NER)
│   ├── mapeo_mitre.py         # Mapeo a técnicas MITRE ATT&CK
│   ├── secuencias_autores.py  # Agrupación y filtrado para HMM
│   ├── procesar_datos.py      # Lectura/escritura de archivos
│   └── __init__.py            # Inicializador del paquete
├── mitre_mapping.json         # Diccionario MITRE (100+ entradas)
├── requirements.txt           # Dependencias completas
├── README Fase2.md            # Esta documentación
└── install_linux.sh           # Script de instalación para Linux
```

### Diagrama de Flujo

```
Datos/
└── forum_records_clean.csv ─┐
                             ▼
                    ┌──────────────────┐
                    │     main.py      │ ← Orquestador
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌─────────────────┐ ┌──────────┐ ┌──────────────┐
    │ cargar_modelos  │ │procesar_ │ │mapeo_mitre   │
    │ (SecureBERT)    │ │ner.py    │ │.py           │
    └────────┬────────┘ └────┬─────┘ └──────┬───────┘
             │               │              │
             ▼               ▼              ▼
      Tokenizador +    Entidades        Técnicas
      Pipeline NER    detectadas        MITRE
             │               │              │
             └───────────────┼──────────────┘
                             ▼
                    ┌──────────────────┐
                    │ procesar_datos   │ ← Guarda CSV enriquecido
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │secuencias_autores│ ← Agrupa por autor
                    └────────┬─────────┘
                             │
                             ▼
                    ┌────────────────────────┐
                    │ ../Datos/              │
                    │ datos_enriquecidos.csv │
                    │ secuencias_autores.json│
                    └────────────────────────┘
```

### Responsabilidad de cada Módulo

| Módulo | Responsabilidad |
|--------|----------------|
| `main.py` | Orquesta todo el pipeline: carga modelos → procesa NER → mapea MITRE → genera secuencias |
| `cargar_modelos.py` | Carga SecureBERT 2.0 desde Hugging Face (con fallback automático) y crea pipelines |
| `procesar_ner.py` | Reconoce entidades de ciberseguridad en el texto usando NER, filtra por confianza ≥ 0.5 y deduplica |
| `mapeo_mitre.py` | Asocia entidades detectadas con técnicas MITRE ATT&CK y calcula puntuación de amenaza |
| `secuencias_autores.py` | Agrupa posts por autor, ordena cronológicamente y filtra secuencias válidas (≥3) |
| `procesar_datos.py` | Lee/escribe archivos CSV y genera JSON con formato para HMM |

---

## 🔧 Tecnologías Utilizadas

### Modelos de Lenguaje
- **SecureBERT 2.0-NER**: Modelo especializado en ciberseguridad para detección de entidades
- **Fallback automático**: Si SecureBERT no está disponible, usa `bert-base-uncased`

### Librerías Principales
| Librería | Versión | Propósito |
|----------|---------|-----------|
| `transformers` | 4.41.2 | Carga y uso de modelos SecureBERT |
| `torch` | 2.2.2 | Backend de PyTorch para inferencia |
| `pandas` | 2.2.2 | Manipulación de datos tabulares |
| `scikit-learn` | 1.5.0 | Utilidades de machine learning |
| `tqdm` | 4.66.4 | Barras de progreso para procesamiento por lotes |

---

## 🚀 Ejecución del Pipeline

### Requisitos Previos

#### Opción 1: Instalación automática (Linux recomendado)

```bash
# Dar permisos de ejecución y ejecutar
chmod +x install_linux.sh
./install_linux.sh
```

#### Opción 2: Instalación manual (Linux/Windows)

```bash
# 1. Ir a la carpeta de la Fase 2
cd "Fase 2 - Analisis semantico NLP"

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Verificar instalación
python -c "import transformers, torch; print('Dependencias instaladas correctamente')"
```

> ⚠️ **Importante para Linux**: Si usas WSL o una máquina virtual Linux, asegúrate de ejecutar `pip` y `python` desde el entorno Linux, no desde Windows. El script `install_linux.sh` automatiza todo el proceso.
>
> 💡 **Solución rápida si pip no encuentra los módulos**: A veces hay conflictos entre versiones de Python. Usa:
> ```bash
> python3 -m pip install --upgrade pip
> python3 -m pip install -r requirements.txt
> ```

### Ejecución con datos reales (desde Fase 1)

```bash
python modulos/main.py \
    --input ../Datos/forum_records_clean.csv \
    --output-csv ../Datos/datos_enriquecidos.csv \
    --output-hmm ../Datos/secuencias_autores.json
```

### Parámetros Configurables

| Parámetro | Abreviatura | Descripción | Valor por Defecto |
|-----------|-------------|-------------|-------------------|
| `--input` | `-i` | Ruta al CSV de entrada (limpio de Fase 1) | `../Datos/forum_records_clean.csv` |
| `--output-csv` | `-o` | Ruta al CSV de salida enriquecido | `../Datos/datos_enriquecidos.csv` |
| `--output-hmm` | `-m` | Ruta al JSON de salida para HMM | `../Datos/secuencias_autores.json` |
| `--mitre-mapping` | `-d` | Ruta al archivo de mapeo MITRE | `mitre_mapping.json` |

---

## 📊 Salidas Generadas

### 1. `datos_enriquecidos.csv` — 22 campos totales

**Campos heredados de la Fase 1** (17 campos):
`id_mensaje`, `huella_contenido`, `id_hilo`, `id_mensaje_padre`, `usuario`, `fecha_hora`, `fecha`, `año`, `mes`, `dia`, `hora`, `titulo_limpio`, `cuerpo_limpio`, `texto_citado_limpio`, `longitud_titulo`, `longitud_cuerpo`, `url_original`

**Campos nuevos agregados por Fase 2** (5 campos en español):

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `entidades` | `str` (JSON) | Lista de entidades detectadas con tipo, texto y confianza |
| `tecnicas_mitre` | `str` (JSON) | Lista de IDs de técnicas MITRE ATT&CK |
| `puntuacion_amenaza` | `float` | Puntuación de amenaza entre 0.0 y 1.0 |
| `cantidad_entidades` | `int` | Número de entidades detectadas en el post |
| `cantidad_tecnicas` | `int` | Número de técnicas MITRE mapeadas |

**Ejemplo de entidad detectada**:
```json
{
  "type": "LABEL_1",
  "text": "cobalt strike",
  "confidence": 0.57,
  "start": 0,
  "end": 13
}
```

### 2. `secuencias_autores.json` (Secuencias para HMM)

**Estructura**:
```json
{
  "metadata": {
    "total_autores": 2,
    "secuencias_validas": 1,
    "generado_en": "2026-05-29T20:33:46.451480",
    "longitud_minima_secuencia": 3
  },
  "sequences": {
    "USER_a1b2c3d4e5f6g7h8": [
      {
        "id_mensaje": "msg_001",
        "fecha_hora": "2026-05-22T02:08:27.214395+00:00",
        "puntuacion_amenaza": 0.43,
        "entidades": [
          {"type": "LABEL_0", "text": "cobalt strike", "confidence": 0.57}
        ],
        "tecnicas_mitre": ["T1204.002"]
      }
    ]
  }
}
```

---

## 🎯 Flujo del Pipeline (detallado)

### Paso 1: Carga de modelos
`cargar_modelos.py` carga SecureBERT 2.0-NER desde Hugging Face y crea:
- **Pipeline NER**: Clasifica cada token del texto en categorías de ciberseguridad
- **Pipeline de clasificación**: Para análisis adicional de texto

### Paso 2: Procesamiento NER
`procesar_ner.py` toma el texto y:
1. Recibe `cuerpo_limpio` del post
2. Ejecuta el pipeline NER de SecureBERT
3. **Filtra** entidades con confianza < 0.5
4. **Deduplica** entidades (mismo tipo + texto = 1 sola vez)
5. Retorna lista de entidades con: `type`, `text`, `confidence`, `start`, `end`

### Paso 3: Mapeo MITRE
`mapeo_mitre.py` asocia cada entidad detectada con técnicas MITRE ATT&CK usando `mitre_mapping.json`

### Paso 4: Cálculo de amenaza
```python
puntuacion_amenaza = (confianza_promedio_entidades * 0.7) + (cantidad_tecnicas_mitre * 0.3)
```
- **Rango**: 0.0 (sin amenaza) a 1.0 (máxima amenaza)
- 70%: Confianza media de entidades detectadas
- 30%: Número de técnicas MITRE identificadas (normalizado a 0-1)

### Paso 5: Secuencias para HMM
`secuencias_autores.py`:
1. Agrupa posts por `usuario`
2. Ordena cronológicamente por `fecha_hora`
3. Filtra autores con menos de 3 posts
4. Genera JSON con secuencias

---

## 📈 Métricas y Validación

### Validación de Secuencias
1. **Longitud mínima**: ≥3 posts por autor (evita overfitting en HMM)
2. **Ordenamiento**: Cronológico por timestamp (más antiguo primero)
3. **Filtro de entidades**: Solo entidades con confianza ≥ 0.5
4. **Deduplicación**: Entidades repetidas (mismo tipo y texto) se cuentan una sola vez por post

---

## 🔄 Reejecución y Mantenimiento

### Características de Diseño
- **Reejecutable**: El pipeline puede ejecutarse múltiples veces sobre los mismos datos
- **Actualizable**: Si se actualiza el modelo NER o el diccionario MITRE, basta reejecutar
- **Incremental**: No requiere repetir la costosa fase de scraping
- **Modular**: Cada componente puede actualizarse independientemente
- **Logging completo**: Registro detallado en `processing_log.txt`

### Actualización de Modelos
```bash
# Para actualizar a nuevas versiones de SecureBERT
pip install --upgrade transformers torch

# El pipeline cargará automáticamente los modelos actualizados
```

---

## 🎓 Casos de Uso

### 1. Análisis de Amenazas
```python
import pandas as pd

# Cargar datos enriquecidos
df = pd.read_csv('../Datos/datos_enriquecidos.csv')

# Top 10 posts más amenazantes
top_threats = df.sort_values('puntuacion_amenaza', ascending=False).head(10)

# Entidades más frecuentes
entity_counts = df['cantidad_entidades'].value_counts()
```

### 2. Preparación para HMM
```python
import json

# Cargar secuencias para HMM
with open('../Datos/secuencias_autores.json', 'r') as f:
    hmm_data = json.load(f)

# Estadísticas de secuencias
print(f"Autores totales: {hmm_data['metadata']['total_autores']}")
print(f"Secuencias válidas: {hmm_data['metadata']['secuencias_validas']}")
```

---

## 🚨 Consideraciones de Seguridad
- **Datos sensibles**: El script procesa datos de Dark Web - usar en entornos seguros
- **Modelos grandes**: SecureBERT requiere ~2GB de memoria por modelo
- **Tiempo de ejecución**: Procesamiento por lotes para grandes volúmenes de datos
- **Compatibilidad**: Diseñado para Python 3.9+ con CUDA (recomendado)

---

## 📚 Referencias
- **SecureBERT 2.0**: Modelo especializado en ciberseguridad de Cisco AI
- **MITRE ATT&CK**: Framework de técnicas de adversarios
- **Transformers**: Librería Hugging Face para NLP
- **HMM**: Modelos Ocultos de Markov para análisis de secuencias

---

## ✅ Criterios de Éxito

1. ✅ Detección exitosa de entidades de ciberseguridad (con filtro ≥ 0.5)
2. ✅ Mapeo correcto a técnicas MITRE ATT&CK
3. ✅ Generación de secuencias válidas para HMM (≥3 posts)
4. ✅ Puntuaciones de amenaza calculadas correctamente
5. ✅ Logging completo y manejo de errores robusto
6. ✅ Compatibilidad con salida de Fase 1
7. ✅ Arquitectura modular con nombres en español
8. ✅ Fallback automático si SecureBERT no está disponible
9. ✅ Campos de salida en español

---

## 🎯 Próximos Pasos (Fase 3)

1. **Entrenamiento HMM**: Usar `secuencias_autores.json` para entrenar el modelo
2. **Análisis Predictivo**: Detectar patrones de comportamiento malicioso
3. **Visualización**: Dashboard de amenazas y tendencias
4. **Integración**: Conectar con sistemas de alerta temprana

**¡La Fase 2 está completa y lista para alimentar el modelo HMM! 🚀**