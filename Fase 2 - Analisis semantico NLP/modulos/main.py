#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo principal: main.py
==========================
Orquestador que coordina todo el pipeline de enriquecimiento NLP:
1. Carga modelos SecureBERT 2.0
2. Procesa NER para detección de entidades
3. Mapea entidades a técnicas MITRE ATT&CK
4. Calcula puntuación de amenaza
5. Agrupa posts por autor y genera secuencias HMM

Uso desde línea de comandos:
    python main.py --input <csv_entrada> --output-csv <csv_salida> --output-hmm <json_salida>

Ejemplo:
    python main.py --input ../datos_limpios.csv --output-csv enriquecido.csv --output-hmm secuencias.json
"""

import argparse
import json
import logging
import sys
import os

import torch

# Importar módulos locales
import cargar_modelos
import procesar_ner
import mapeo_mitre
import secuencias_autores
import procesar_datos

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('processing_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clase ProcesadorSecureBERT
# ---------------------------------------------------------------------------

class ProcesadorSecureBERT:
    """
    Clase principal que coordina el pipeline completo de enriquecimiento.

    Encapsula los modelos cargados, los pipelines y orquesta el flujo:
    texto -> NER -> MITRE mapping -> threat score -> post enriquecido.
    """

    def __init__(self, ruta_mapeo_mitre: str = 'mitre_mapping.json'):
        """
        Inicializa el procesador con modelos SecureBERT 2.0.

        Parámetros
        ----------
        ruta_mapeo_mitre : str
            Ruta al archivo JSON con el mapeo MITRE ATT&CK.
        """
        # Cargar mapeo MITRE
        self.mapeo_mitre = cargar_modelos.cargar_mapeo_mitre(ruta_mapeo_mitre)

        # Determinar dispositivo (GPU si está disponible)
        self.dispositivo = 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"Usando dispositivo: {self.dispositivo}")

        # Cargar modelos SecureBERT
        self.tokenizador, self.modelo_ner, self.modelo_sec = cargar_modelos.cargar_modelos()

        # Crear pipelines
        self.pipeline_ner = cargar_modelos.crear_pipeline_ner(
            self.modelo_ner, self.tokenizador, self.dispositivo
        )
        self.pipeline_secuencias = cargar_modelos.crear_pipeline_secuencias(
            self.modelo_sec, self.tokenizador, self.dispositivo
        )

        logger.info("Modelos SecureBERT 2.0 cargados exitosamente")

    def procesar_post(self, post: dict) -> dict:
        """
        Procesa un post individual: NER, mapeo MITRE y puntuación de amenaza.

        Parámetros
        ----------
        post : dict
            Diccionario con los datos del post. Debe contener al menos
            'body_limpio' o 'body' con el texto a analizar.

        Retorna
        -------
        dict
            Post enriquecido con los campos adicionales:
            - entities: JSON con entidades detectadas
            - mitre_techniques: JSON con técnicas MITRE
            - threat_score: puntuación de amenaza (0-1)
            - entity_count: cantidad de entidades
            - mitre_count: cantidad de técnicas
        """
        try:
            # Extraer contenido limpio del post
            contenido_limpio = post.get('body_limpio', '') or post.get('body', '') or ''

            # Procesar NER con SecureBERT
            entidades = procesar_ner.procesar_ner(contenido_limpio, self.pipeline_ner)

            # Mapear entidades a técnicas MITRE
            tecnicas_mitre = mapeo_mitre.mapear_a_mitre(entidades, self.mapeo_mitre)

            # Calcular puntuación de amenaza
            puntuacion_amenaza = mapeo_mitre.calcular_puntuacion_amenaza(entidades, tecnicas_mitre)

            # Construir post enriquecido
            post_enriquecido = {
                **post,
                "entities": json.dumps([{
                    "type": e["type"],
                    "text": e["text"],
                    "confidence": e["confidence"]
                } for e in entidades], ensure_ascii=False),
                "mitre_techniques": json.dumps(tecnicas_mitre, ensure_ascii=False),
                "threat_score": puntuacion_amenaza,
                "entity_count": len(entidades),
                "mitre_count": len(tecnicas_mitre)
            }

            return post_enriquecido

        except Exception as e:
            logger.error(f"Error procesando post {post.get('message_id', 'desconocido')}: {e}")
            return {
                **post,
                "entities": "[]",
                "mitre_techniques": "[]",
                "threat_score": 0.0,
                "entity_count": 0,
                "mitre_count": 0
            }


# ---------------------------------------------------------------------------
# Función principal (CLI)
# ---------------------------------------------------------------------------

def main():
    """
    Función principal para ejecución desde línea de comandos.
    Parsea argumentos, inicializa el procesador y ejecuta el pipeline completo.
    """
    parser = argparse.ArgumentParser(
        description="main.py - Pipeline NLP con SecureBERT 2.0 para enriquecer datos de Dark Web",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--input", "-i",
        default="test_input.csv",
        help="Ruta al CSV de entrada con posts limpios (default: test_input.csv)"
    )
    parser.add_argument(
        "--output-csv", "-o",
        default="enriched_forum_data.csv",
        help="Ruta al CSV de salida con datos enriquecidos (default: enriched_forum_data.csv)"
    )
    parser.add_argument(
        "--output-hmm", "-m",
        default="author_sequences.json",
        help="Ruta al JSON de salida con secuencias para HMM (default: author_sequences.json)"
    )
    parser.add_argument(
        "--mitre-mapping", "-d",
        default="mitre_mapping.json",
        help="Ruta al archivo JSON de mapeo MITRE (default: mitre_mapping.json)"
    )

    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # INICIO DEL PIPELINE
    # -----------------------------------------------------------------------
    sys.exit(_ejecutar_pipeline(args))


def _ejecutar_pipeline(args) -> int:
    """
    Ejecuta el pipeline completo de enriquecimiento.

    Parámetros
    ----------
    args : argparse.Namespace
        Argumentos parseados de la línea de comandos.

    Retorna
    -------
    int
        0 si la ejecución fue exitosa, 1 si hubo error.
    """
    try:
        logger.info("Iniciando pipeline de enriquecimiento NLP con SecureBERT 2.0...")
        logger.info(f"Configuración: {vars(args)}")

        # Paso 1: Inicializar procesador (carga modelos, mapeo MITRE, pipelines)
        procesador = ProcesadorSecureBERT(ruta_mapeo_mitre=args.mitre_mapping)

        # Paso 2: Procesar CSV completo -> datos enriquecidos
        procesar_datos.procesar_csv(
            ruta_entrada=args.input,
            ruta_salida=args.output_csv,
            funcion_procesar_post=procesador.procesar_post
        )

        # Paso 3: Generar secuencias de autores para HMM
        procesar_datos.generar_secuencias_hmm(
            ruta_csv_entrada=args.output_csv,
            ruta_json_salida=args.output_hmm,
            funcion_agrupar=secuencias_autores.agrupar_por_autor,
            funcion_filtrar=secuencias_autores.filtrar_secuencias
        )

        logger.info("✅ Procesamiento completado exitosamente!")
        logger.info(f"📊 Datos enriquecidos: {args.output_csv}")
        logger.info(f"🔗 Secuencias HMM: {args.output_hmm}")

        return 0

    except Exception as e:
        logger.error(f"❌ Error fatal en el pipeline: {e}")
        return 1


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()