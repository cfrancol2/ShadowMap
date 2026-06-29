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

    # Inicializa el procesador con modelos SecureBERT 2.0.
    def __init__(self, ruta_mapeo_mitre: str = 'mitre_mapping.json'):
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
        try:
            # Extraer contenido limpio del post
            contenido_limpio = post.get('cuerpo_limpio', '') or post.get('cuerpo', '') or ''

            # Procesar NER con SecureBERT
            entidades = procesar_ner.procesar_ner(contenido_limpio, self.pipeline_ner)

            # Mapear entidades a técnicas MITRE
            tecnicas_mitre = mapeo_mitre.mapear_a_mitre(entidades, self.mapeo_mitre)

            # Calcular puntuación de amenaza
            puntuacion_amenaza = mapeo_mitre.calcular_puntuacion_amenaza(entidades, tecnicas_mitre)

            # Construir post enriquecido
            post_enriquecido = {
                **post,
                "entidades": json.dumps([{
                    "type": e["type"],
                    "text": e["text"],
                    "confidence": e["confidence"]
                } for e in entidades], ensure_ascii=False),
                "tecnicas_mitre": json.dumps(tecnicas_mitre, ensure_ascii=False),
                "puntuacion_amenaza": puntuacion_amenaza,
                "cantidad_entidades": len(entidades),
                "cantidad_tecnicas": len(tecnicas_mitre)
            }

            return post_enriquecido

        except Exception as e:
            logger.error(f"Error procesando post {post.get('id_mensaje', 'desconocido')}: {e}")
            return {
                **post,
                "entidades": "[]",
                "tecnicas_mitre": "[]",
                "puntuacion_amenaza": 0.0,
                "cantidad_entidades": 0,
                "cantidad_tecnicas": 0
            }


# ---------------------------------------------------------------------------
# Función principal (CLI)
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="main.py - Pipeline NLP con SecureBERT 2.0 para enriquecer datos de Dark Web",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--input", "-i",
        default="../Datos/forum_records_clean.csv",
        help="Ruta al CSV de entrada con posts limpios (default: ../Datos/forum_records_clean.csv)"
    )
    parser.add_argument(
        "--output-csv", "-o",
        default="../Datos/datos_enriquecidos.csv",
        help="Ruta al CSV de salida con datos enriquecidos (default: ../Datos/datos_enriquecidos.csv)"
    )
    parser.add_argument(
        "--output-hmm", "-m",
        default="../Datos/secuencias_autores.json",
        help="Ruta al JSON de salida con secuencias para HMM (default: ../Datos/secuencias_autores.json)"
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

if __name__ == "__main__":
    main()