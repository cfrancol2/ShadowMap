# Análisis del Caso y Requerimientos del Producto

## 1. Contexto del caso práctico

El caso consiste en diseñar e implementar una **capa de ingesta OSINT en Dark Web** para recolectar conversaciones de foros `.onion`, con fines de análisis de ciberamenazas y generación de inteligencia accionable.

La solución se orienta a:

- identificar señales tempranas de campañas maliciosas,
- extraer información estructurada para modelos de NLP/HMM,
- mantener trazabilidad temporal de la actividad observada.

---

## 2. Problema a resolver

Las organizaciones suelen reaccionar de forma tardía ante incidentes porque dependen de indicadores posteriores al ataque. Existe la necesidad de una herramienta que:

- observe conversaciones potencialmente relevantes en foros clandestinos,
- detecte patrones y términos de riesgo,
- conserve evidencia estructurada para análisis técnico posterior.

---

## 3. Alternativas de solución consideradas

### Alternativa A: Recolección manual
- **Ventaja:** control humano directo.
- **Desventaja:** no escalable, lenta, propensa a sesgos y errores.

### Alternativa B: Scraper básico sin resiliencia
- **Ventaja:** implementación rápida.
- **Desventaja:** alta tasa de fallos por inestabilidad onion, poca continuidad operativa.

### Alternativa C: Scraper robusto con resiliencia, logging y anti-baneo (**seleccionada**)
- **Ventaja:** continuidad operativa, trazabilidad, recuperación ante fallos, datos reutilizables.
- **Desventaja:** mayor complejidad técnica inicial.

---

## 4. Alcance funcional del producto

El producto cubre:

1. Ingesta de URLs semilla (`seeds.txt`).
2. Descubrimiento de nuevos enlaces `.onion` durante el rastreo.
3. Extracción de contenido y metadatos de posts.
4. Detección de palabras clave de interés (`identifiers.txt`).
5. Anonimización de campos sensibles (PII).
6. Almacenamiento estructurado en JSONL y CSV.
7. Logging de eventos y errores.
8. Checkpoint para reanudación.
9. Detección de baneo (403/redirecciones sospechosas) y rotación de circuito Tor.

---

## 5. Requerimientos funcionales

### RF-01: Carga de semillas
El sistema debe leer URLs `.onion` desde un archivo `seeds.txt`.

### RF-02: Carga de keywords
El sistema debe leer términos de búsqueda desde `identifiers.txt`.

### RF-03: Rastreo recursivo
El sistema debe recorrer enlaces `.onion` encontrados hasta una profundidad configurable.

### RF-04: Extracción de registros estructurados
El sistema debe generar registros con al menos estos campos:

- `message_id`
- `thread_id`
- `parent_message_id`
- `forum_name`
- `category`
- `username`
- `user_role`
- `timestamp`
- `title`
- `body`
- `quoted_text`
- `extracted_entities`
- `raw_url`

### RF-05: Detección de coincidencias
El sistema debe identificar keywords presentes en el contenido HTML/texto de las páginas.

### RF-06: Exportación de datos
El sistema debe exportar resultados en:

- `forum_records.jsonl`
- `forum_records.csv`
- `report.txt` (keyword | url)

### RF-07: Logging
El sistema debe registrar eventos operativos, errores y estados de ejecución en archivo de log.

### RF-08: Reanudación
El sistema debe guardar y cargar checkpoints para continuar ejecuciones interrumpidas.

### RF-09: Mitigación de bloqueos
El sistema debe detectar posibles bloqueos/baneos y rotar circuito Tor automáticamente.

---

## 6. Requerimientos no funcionales

### RNF-01: Seguridad y privacidad
La solución debe anonimizar información sensible antes de persistirla.

### RNF-02: Robustez
La solución debe tolerar fallos de red, caídas de servicios onion y timeouts.

### RNF-03: Trazabilidad
Toda ejecución debe quedar auditada mediante logs y checkpoints.

### RNF-04: Escalabilidad operativa
Debe poder ejecutarse por periodos prolongados (horas/días) con recuperación automática.

### RNF-05: Configurabilidad
Parámetros como profundidad, pausas, retries, umbrales y rutas de salida deben ser configurables por CLI.

### RNF-06: Mantenibilidad
El código debe estar comentado/documentado en español para facilitar mantenimiento académico y técnico.

### RNF-07: Portabilidad
Debe ejecutarse en entornos Linux orientados a seguridad (p. ej. Whonix Workstation) con dependencias declaradas en `requirements.txt`.

---

## 7. Criterios de aceptación

1. El sistema inicia con `seeds.txt` e `identifiers.txt` válidos.
2. El sistema produce salidas JSONL/CSV/TXT sin errores de formato.
3. El log registra intentos, errores y reintentos.
4. Al interrumpir y reanudar con checkpoint, no pierde continuidad.
5. Ante señales de baneo, intenta rotación de circuito y continúa.
6. Los campos de usuario/contenido sensible quedan anonimizados en salida final.

---

## 8. Supuestos y restricciones

- El acceso a Tor está disponible en el entorno de ejecución.
- Las fuentes `.onion` utilizadas son parte de un contexto autorizado de investigación.
- El uso es académico/defensivo y cumple políticas éticas y legales aplicables.
