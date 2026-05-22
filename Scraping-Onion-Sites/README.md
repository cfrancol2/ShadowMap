# Scraping-Onion-Sites (Adaptado para Titulación)

Herramienta de **ingesta OSINT en Dark Web** para extraer conversaciones de foros `.onion`, anonimizar PII y guardar datos estructurados para análisis posterior (NLP/HMM).

## Objetivo

Esta versión está enfocada en la **Capa de Ingesta** de tu proyecto de titulación:

- Rastreo por Tor de sitios `.onion`
- Extracción de estructura de foros (posts, usuarios, fechas, respuestas)
- Anonimización de datos sensibles (PII)
- Exportación para análisis en **JSONL** y **CSV**

## Archivos actuales (limpios)

- `forum_scraper.py` → Scraper principal adaptado
- `anonymizer.py` → Módulo de anonimización PII
- `requirements.txt` → Dependencias para entorno virtual
- `README.md` → Este documento

## Esquema de datos por registro

Cada registro ingerido incluye:

- `message_id` (string único)
- `thread_id` (string)
- `parent_message_id` (string nullable)
- `forum_name` (string)
- `category` (string)
- `username` (string anonimizado)
- `user_role` (string)
- `timestamp` (datetime UTC)
- `title` (string)
- `body` (texto completo)
- `quoted_text` (texto nullable)
- `extracted_entities` (JSON opcional)
- `raw_url` (string)

## Requisitos

1. Python 3.9+
2. Tor corriendo localmente (SOCKS/Control ports, típicamente 9050/9051)
3. Dependencias Python:

```bash
pip install -r requirements.txt
```

## Monitoreo y manejo de errores (implementado)

El scraper incluye mecanismos para entornos onion inestables:

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
  - **NUEVO**: Los registros se guardan automáticamente después de procesar cada página
  - Deduplicación por página antes de guardar (evita duplicados en el mismo hilo)
  - Permite pausar/cerrar el programa y reanudar sin perder datos
  - Los archivos CSV y JSONL se actualizan incrementalmente (modo append)
  - Ideal para ejecuciones largas donde se necesita seguridad de datos

## Archivos de entrada esperados

- `seeds.txt` → URLs `.onion` semilla (una por línea)
- `identifiers.txt` → keywords de interés (una por línea)

## Ejecución

Desde la carpeta `Scraping-Onion-Sites`:

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
  --csv-out output/forum_records.csv \
  --report-out output/report.txt
```

Reanudar ejecución previa:

```bash
python forum_scraper.py --resume --checkpoint-file output/checkpoint.json
```

Opcional (Telegram):

```bash
python forum_scraper.py --send-telegram
```

> Para Telegram debes tener `telegram_config.py` con `BOT_TOKEN` y `CHAT_ID`.

## Salidas generadas

- `output/forum_records.jsonl` → registros estructurados (ideal para pipelines)
- `output/forum_records.csv` → análisis tabular rápido
- `output/report.txt` → coincidencias `keyword | url`

## Nota ética y legal

Uso exclusivamente académico y de investigación defensiva. Debes cumplir leyes locales, lineamientos institucionales y políticas éticas para recolección de datos.
