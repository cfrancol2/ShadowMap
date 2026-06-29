# Scraping-Onion-Sites

Herramienta de **ingesta OSINT en Dark Web** para extraer conversaciones de foros `.onion`,
anonimizar PII y preprocesar los datos para análisis posterior en la Fase 2 (NLP/HMM).

## Objetivo (Capa de Ingesta)

Esta es la **Capa de Ingesta** del proyecto de titulación. Su propósito es:

- Rastreo por Tor de sitios `.onion`
- Extracción de estructura de foros (posts, usuarios, fechas, respuestas)
- Anonimización de datos sensibles (PII: emails, IPs, direcciones BTC, etc.)
- **Preprocesamiento y limpieza** del corpus para la Fase 2
- Exportación estructurada en **CSV** y **JSONL**

## Flujo de trabajo (Pipeline Fase 1)

```
seeds.txt ─┐
identifiers.txt ─┤
                 ▼
          ┌──────────────────┐
          │  forum_scraper   │  ← Rastreo .onion + extracción de foros
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │   anonymizer     │  ← Anonimización PII (dentro del scraper)
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────┐
          │ output/           │
          │ forum_records.*   │  ← JSONL (crudos)
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────────────────────┐
          │ ../Datos/forum_records.csv        │  ← CSV crudo en carpeta Datos/
          └────────┬─────────────────────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  Preprocesador   │  ← Limpieza, normalización, features
          └────────┬─────────┘
                   │
                   ▼
          ┌──────────────────────────────────┐
          │ ../Datos/forum_records_clean.csv  │  ← CSV listo para Fase 2
          └──────────────────────────────────┘
```

## Archivos del proyecto

| Archivo | Función |
|---|---|
| `forum_scraper.py` | Scraper principal: rastrea foros `.onion` mediante Tor |
| `anonymizer.py` | Módulo de anonimización PII (emails, IPs, BTC, .onion) |
| `Preprocesador.py` | Limpieza y normalización de texto para análisis NLP |
| `dashboard.py` | Dashboard interactivo con Streamlit para visualización |
| `requirements.txt` | Dependencias Python del scraper |
| `seeds.txt` | URLs `.onion` semilla para iniciar el rastreo (una por línea) |
| `identifiers.txt` | Palabras clave de amenazas para filtrado temático |
| `README Fase1.md` | Este documento |

## Requisitos

1. **Python 3.9+**
2. **Tor corriendo localmente** (puertos SOCKS 9050 / Control 9051)
3. Dependencias Python:

```bash
pip install -r requirements.txt
```

## Esquema de datos

### 1. Salida del scraper (`forum_records.csv`) — 10 campos en español

Cada registro extraído del foro contiene:

- `id_mensaje` — identificador único del mensaje (string)
- `huella_contenido` — hash SHA1 del contenido para deduplicación (string)
- `id_hilo` — identificador del hilo (string)
- `id_mensaje_padre` — ID del mensaje padre si es respuesta, vacío si no (string)
- `usuario` — nombre del autor anonimizado con prefijo `USER_` (string)
- `fecha_hora` — marca de tiempo en formato ISO UTC (string)
- `titulo` — título completo de la página/hilo (string)
- `cuerpo` — cuerpo del mensaje (string, mínimo 20 caracteres)
- `texto_citado` — texto citado dentro del post (string)
- `url_original` — URL original de donde se extrajo el post (string)

### 2. Salida del preprocesador (`forum_records_clean.csv`) — 17 campos

El **Preprocesador** toma el CSV del scraper y genera un archivo limpio con:

| # | Campo | Tipo | Descripción |
|---|-------|------|-------------|
| 1 | `id_mensaje` | `str` | Identificador único del mensaje |
| 2 | `huella_contenido` | `str` | Hash de contenido para deduplicación |
| 3 | `id_hilo` | `str` | Identificador del hilo |
| 4 | `id_mensaje_padre` | `str` | ID del mensaje padre |
| 5 | `usuario` | `str` | Nombre de usuario |
| 6 | `fecha_hora` | `str` | Marca de tiempo original |
| 7 | `fecha` | `datetime` | Fecha como datetime |
| 8 | `año` | `int` | Año derivado de la fecha |
| 9 | `mes` | `int` | Mes derivado de la fecha |
| 10 | `dia` | `int` | Día derivado de la fecha |
| 11 | `hora` | `int` | Hora derivada de la fecha |
| 12 | `titulo_limpio` | `str` | Título normalizado (minúsculas, sin caracteres especiales) |
| 13 | `cuerpo_limpio` | `str` | Cuerpo del mensaje limpiado (**entrada para la Fase 2**) |
| 14 | `texto_citado_limpio` | `str` | Texto citado normalizado |
| 15 | `longitud_titulo` | `int` | Cantidad de caracteres del título |
| 16 | `longitud_cuerpo` | `int` | Cantidad de caracteres del cuerpo |
| 17 | `url_original` | `str` | URL original del post |

> **Filtro aplicado**: se descartan registros con `cuerpo_limpio` < 50 caracteres.

## Ejecución

### Paso 1: Scraper de foros `.onion`

Desde la carpeta `Fase 1 - Scraping-Onion-Sites`:

```bash
python forum_scraper.py \
  --seeds seeds.txt \
  --keywords identifiers.txt \
  --max-depth 2 \
  --delay 5 \
  --max-retries 3 \
  --failure-threshold 10 \
  --pause-hours 1 \
  --checkpoint-file output/checkpoint.json \
  --log-file output/scraper.log \
  --jsonl-out output/forum_records.jsonl \
  --csv-out ../Datos/forum_records.csv \
  --report-out output/report.txt
 #--days-back 2
```

Reanudar ejecución previa:

```bash
python forum_scraper.py --resume --checkpoint-file output/checkpoint.json
```

### Paso 2: Preprocesamiento y limpieza

Una vez generado el CSV del scraper, ejecutar el preprocesador:

```bash
python Preprocesador.py \
  --input ../Datos/forum_records.csv \
  --output ../Datos/forum_records_clean.csv
```

Esto genera `forum_records_clean.csv` en la carpeta `Datos/`, que es la entrada directa para la **Fase 2** (enriquecimiento NLP con SecureBERT).

## Monitoreo y manejo de errores (implementado en el scraper)

El scraper incluye mecanismos robustos para entornos onion inestables:

- **Logging robusto**
  - Registro en consola y archivo (`--log-file`, por defecto `output/scraper.log`)
  - Guarda errores de timeout, errores 5xx, códigos HTTP no esperados y eventos de baneo.

- **Resiliencia / reanudación**
  - Guarda estado de ejecución en checkpoint (`--checkpoint-file`, por defecto `output/checkpoint.json`)
  - Permite continuar desde el último estado con `--resume`
  - Incluye pausa automática por demasiados fallos consecutivos:
    - `--failure-threshold` (por defecto 10)
    - `--pause-hours` (por defecto 1.0)

- **Detección de baneo**
  - Detecta respuestas **403**
  - Detecta redirecciones sospechosas a home/login desde rutas tipo thread/post/topic
  - Ante detección: rota circuito Tor y reintenta URL.

- **Guardado incremental de datos**
  - Los registros se guardan automáticamente después de procesar cada página
  - Deduplicación por página antes de guardar (evita duplicados en el mismo hilo)
  - Permite pausar/cerrar el programa y reanudar sin perder datos
  - Los archivos CSV y JSONL se actualizan incrementalmente (modo append)
  - Ideal para ejecuciones largas donde se necesita seguridad de datos

- **Reporte de registros por página**
  - Cada página visitada registra en `report.txt` la cantidad de posts extraídos con el formato: `REGISTROS_PAGINA | <cantidad> | <url>`

## Anonimización (PII)

El módulo `anonymizer.py` reemplaza datos sensibles por tokens hash estables:

| Tipo de dato | Formato | Ejemplo |
|---|---|---|
| Email | `EMAIL_<hash>` | `EMAIL_a1b2c3d4e5f6g7h8` |
| IP v4 | `IPV4_<hash>` | `IPV4_9a8b7c6d5e4f3g2h` |
| Dirección .onion | `ONION_<hash>` | `ONION_1a2b3c4d5e6f7g8h` |
| Dirección BTC | `BTC_<hash>` | `BTC_f8e7d6c5b4a3g2h1` |

## Salidas generadas

| Archivo | Descripción |
|---|---|
| `output/forum_records.jsonl` | Registros estructurados (formato JSONL para pipelines) |
| `../Datos/forum_records.csv` | Datos crudos tabulares en español |
| `../Datos/forum_records_clean.csv` | **Datos preprocesados y limpios** (entrada para Fase 2) |
| `output/report.txt` | Reporte de coincidencias `keyword | count | url` y `REGISTROS_PAGINA | count | url` |
| `output/scraper.log` | Bitácora detallada de ejecución |

## Nota ética y legal

Uso exclusivamente académico y de investigación defensiva. Se deben cumplir leyes locales,
lineamientos institucionales y políticas éticas para recolección de datos.