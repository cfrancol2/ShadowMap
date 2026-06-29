#!/usr/bin/env python3
# encoding: utf-8
"""
Encargado de la lectura/escritura de archivos CSV y la generación
de secuencias en formato JSON para entrenamiento HMM.
"""

import json
import logging
from typing import List, Dict, Any, Callable

import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)


def procesar_csv(ruta_entrada: str,
                 ruta_salida: str,
                 funcion_procesar_post: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
    """
    Lee un archivo CSV, procesa cada post con la función proporcionada
    y guarda el resultado en un nuevo CSV enriquecido.
    """
    try:
        logger.info(f"Cargando datos desde {ruta_entrada}...")
        dataframe = pd.read_csv(ruta_entrada)

        logger.info(f"Procesando {len(dataframe)} posts con SecureBERT 2.0...")
        posts_enriquecidos = []

        # Procesar cada fila con barra de progreso
        for _, fila in tqdm(dataframe.iterrows(), total=len(dataframe), desc="Procesando posts"):
            post_dict = fila.to_dict()
            post_enriquecido = funcion_procesar_post(post_dict)
            posts_enriquecidos.append(post_enriquecido)

        # Crear DataFrame enriquecido y guardar
        dataframe_enriquecido = pd.DataFrame(posts_enriquecidos)

        logger.info(f"Guardando datos enriquecidos en {ruta_salida}...")
        dataframe_enriquecido.to_csv(ruta_salida, index=False)

        logger.info(f"Procesamiento completado. {len(posts_enriquecidos)} posts procesados.")
        logger.info(f"Datos enriquecidos guardados en: {ruta_salida}")

    except Exception as e:
        logger.error(f"Error procesando CSV: {e}")
        raise


def generar_secuencias_hmm(ruta_csv_entrada: str,
                           ruta_json_salida: str,
                           funcion_agrupar: Callable,
                           funcion_filtrar: Callable) -> None:
    """
    Genera secuencias de autores para entrenamiento HMM a partir
    de un CSV enriquecido, y las guarda en formato JSON.
    """
    from datetime import datetime

    try:
        logger.info(f"Cargando datos enriquecidos desde {ruta_csv_entrada}...")
        dataframe = pd.read_csv(ruta_csv_entrada)

        # Convertir a lista de diccionarios
        posts = dataframe.to_dict('records')

        logger.info("Agrupando posts por autor...")
        secuencias_por_autor = funcion_agrupar(posts)

        logger.info("Filtrando secuencias con longitud minima de 3 posts...")
        secuencias_filtradas = funcion_filtrar(secuencias_por_autor)

        # Preparar datos en formato HMM
        datos_hmm = {
            "metadata": {
                "total_autores": len(secuencias_por_autor),
                "secuencias_validas": len(secuencias_filtradas),
                "generado_en": datetime.now().isoformat(),
                "longitud_minima_secuencia": 3
            },
            "sequences": {}
        }

        for nombre_usuario, secuencia in secuencias_filtradas.items():
            datos_hmm["sequences"][nombre_usuario] = [
                {
                    "id_mensaje": post.get("id_mensaje"),
                    "fecha_hora": post.get("fecha_hora"),
                    "puntuacion_amenaza": post.get("puntuacion_amenaza"),
                    "entidades": json.loads(post["entidades"]) if isinstance(post.get("entidades"), str) else post.get("entidades"),
                    "tecnicas_mitre": json.loads(post["tecnicas_mitre"]) if isinstance(post.get("tecnicas_mitre"), str) else post.get("tecnicas_mitre")
                }
                for post in secuencia
            ]

        logger.info(f"Guardando secuencias HMM en {ruta_json_salida}...")
        with open(ruta_json_salida, 'w', encoding='utf-8') as f:
            json.dump(datos_hmm, f, ensure_ascii=False, indent=2)

        logger.info(f"Secuencias HMM generadas: {len(secuencias_filtradas)} autores validos")
        logger.info(f"Datos para HMM guardados en: {ruta_json_salida}")

    except Exception as e:
        logger.error(f"Error generando secuencias HMM: {e}")
        raise