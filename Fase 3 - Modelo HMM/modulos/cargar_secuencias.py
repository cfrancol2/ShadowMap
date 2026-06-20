#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo: cargar_secuencias
=========================
Carga las secuencias de autores desde el JSON generado por la Fase 2,
mapea las técnicas MITRE a fases de la Cyber Kill Chain y prepara
los datos para entrenar el HMM.

Funciones exportadas:
  - cargar_mapeo_kill_chain(ruta) -> dict
  - tecnica_a_fase(tecnicas, mapeo, fase_defecto) -> int
  - cargar_secuencias(ruta_json, ruta_mapeo_kill_chain) -> tuple
"""

import json
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


def cargar_mapeo_kill_chain(ruta: str) -> dict:
    """
    Carga el archivo JSON que mapea técnicas MITRE a fases de la Cyber Kill Chain.

    Parámetros
    ----------
    ruta : str
        Ruta al archivo kill_chain_fases.json.

    Retorna
    -------
    dict
        Diccionario con metadata, mapeo de técnicas y fase por defecto.
    """
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Mapeo Kill Chain cargado: {len(data['mapeo_tecnicas'])} técnicas mapeadas")
        return data
    except Exception as e:
        logger.error(f"Error cargando mapeo Kill Chain desde {ruta}: {e}")
        raise


def tecnica_a_fase(tecnicas: List[str], mapeo: dict, fase_defecto: int) -> int:
    """
    Convierte una lista de técnicas MITRE a una única fase de Kill Chain.
    Implementa la Opción A: toma la técnica con la fase "más avanzada"
    (mayor ID) en la cadena.

    Parámetros
    ----------
    tecnicas : list[str]
        Lista de IDs de técnicas MITRE (ej. ["T1566", "T1204.002"]).
    mapeo : dict
        Diccionario con 'mapeo_tecnicas' (técnica -> id_fase).
    fase_defecto : int
        ID de fase por defecto si no se reconoce ninguna técnica.

    Retorna
    -------
    int
        ID de la fase más avanzada encontrada (0-5).
        Si la lista está vacía, retorna la fase por defecto (Acciones, 5).
    """
    if not tecnicas:
        return fase_defecto

    mapa = mapeo.get('mapeo_tecnicas', {})
    fase_max = -1

    for tecnica in tecnicas:
        # Buscar coincidencia exacta, luego parcial (ej. T1003 para T1003.001)
        fase = mapa.get(tecnica)
        if fase is not None:
            if fase > fase_max:
                fase_max = fase
        else:
            # Intentar coincidencia por técnica base (sin sub-técnica)
            tecnica_base = tecnica.rsplit('.', 1)[0] if '.' in tecnica else tecnica
            fase = mapa.get(tecnica_base)
            if fase is not None and fase > fase_max:
                fase_max = fase

    return fase_max if fase_max >= 0 else fase_defecto


def cargar_secuencias(ruta_json: str, ruta_mapeo: str,
                      omitir_sin_tecnicas: bool = True) -> Tuple[Dict[str, List[int]], Dict[str, Any], dict]:
    """
    Carga las secuencias del JSON de la Fase 2, mapea técnicas a fases
    y prepara los datos para el HMM.

    Parámetros
    ----------
    ruta_json : str
        Ruta al archivo JSON con secuencias de autores (secuencias_autores.json).
    ruta_mapeo : str
        Ruta al archivo de mapeo Kill Chain.
    omitir_sin_tecnicas : bool
        Si True, omite posts sin técnicas reconocidas en lugar de asignarles
        la fase por defecto. Esto mejora significativamente la calidad de los
        datos de entrenamiento (recomendado: True).

    Retorna
    -------
    tuple
        (secuencias_por_autor, metadatos, mapeo_kill_chain)
        - secuencias_por_autor: dict {nombre_usuario: lista_de_fases}
        - metadatos: dict con información general
        - mapeo_kill_chain: dict con el mapeo completo
    """
    logger.info(f"Cargando secuencias desde {ruta_json}...")

    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error cargando {ruta_json}: {e}")
        raise

    mapeo_kill_chain = cargar_mapeo_kill_chain(ruta_mapeo)
    fase_defecto = mapeo_kill_chain.get('fase_por_defecto', 5)

    metadatos = data.get('metadata', {})
    sequences_raw = data.get('sequences', {})

    secuencias_por_autor = {}
    total_posts = 0
    posts_omitidos = 0
    autores_sin_posts = 0

    for nombre_usuario, posts in sequences_raw.items():
        secuencia_fases = []
        for post in posts:
            tecnicas = post.get('tecnicas_mitre', []) or post.get('mitre_techniques', [])

            # Si no hay técnicas reconocidas y se pide omitir, saltar el post
            if omitir_sin_tecnicas and not tecnicas:
                posts_omitidos += 1
                continue

            fase = tecnica_a_fase(tecnicas, mapeo_kill_chain, fase_defecto)
            secuencia_fases.append(fase)
            total_posts += 1

        if secuencia_fases:
            secuencias_por_autor[nombre_usuario] = secuencia_fases
        else:
            autores_sin_posts += 1

    logger.info(f"Secuencias cargadas: {len(secuencias_por_autor)} autores, {total_posts} posts totales")
    if posts_omitidos > 0:
        logger.info(f"Posts omitidos (sin técnicas reconocidas): {posts_omitidos}")
    if autores_sin_posts > 0:
        logger.info(f"Autores descartados (sin posts válidos): {autores_sin_posts}")

    num_fases = len(mapeo_kill_chain['metadata']['fases'])
    logger.info(f"Total de fases de Kill Chain: {num_fases}")
    logger.info(f"Fase por defecto (técnicas no reconocidas): ID {fase_defecto}")

    return secuencias_por_autor, metadatos, mapeo_kill_chain