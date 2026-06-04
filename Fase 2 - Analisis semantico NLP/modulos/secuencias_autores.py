#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo: secuencias_autores
===========================
Encargado de la agrupación de posts por autor, ordenamiento cronológico
y filtrado de secuencias válidas para entrenamiento HMM.

Funciones exportadas:
  - agrupar_por_autor(posts) -> dict[str, list[dict]]
  - filtrar_secuencias(secuencias_autores, longitud_minima) -> dict[str, list[dict]]
"""

import logging
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def agrupar_por_autor(posts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupa los posts por nombre de usuario y los ordena cronológicamente
    dentro de cada grupo.

    Parámetros
    ----------
    posts : list[dict]
        Lista de diccionarios, cada uno representando un post enriquecido.
        Cada post debe tener al menos:
        - 'username': nombre del autor
        - 'timestamp': marca de tiempo del post

    Retorna
    -------
    dict[str, list[dict]]
        Diccionario donde las llaves son nombres de usuario y los valores
        son listas de posts ordenados cronológicamente (más antiguo primero).
        Los posts sin timestamp válido son omitidos.
    """
    secuencias = {}

    for post in posts:
        nombre_usuario = post.get('username', 'usuario_desconocido')
        timestamp = post.get('timestamp')

        if not timestamp:
            continue

        try:
            # Convertir timestamp a datetime para ordenamiento cronológico
            if isinstance(timestamp, str):
                fecha_hora = pd.to_datetime(timestamp)
            else:
                fecha_hora = timestamp

            if nombre_usuario not in secuencias:
                secuencias[nombre_usuario] = []

            # Agregar post con campo datetime para ordenar después
            secuencias[nombre_usuario].append({
                **post,
                'datetime': fecha_hora
            })

        except Exception as e:
            logger.warning(
                f"Error procesando timestamp para post "
                f"{post.get('message_id', 'desconocido')}: {e}"
            )
            continue

    # Ordenar cada secuencia cronológicamente (más antiguo primero)
    for nombre_usuario in secuencias:
        secuencias[nombre_usuario].sort(key=lambda x: x['datetime'])

    return secuencias


def filtrar_secuencias(secuencias_autores: Dict[str, List[Dict[str, Any]]],
                       longitud_minima: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """
    Filtra las secuencias de autores, conservando solo aquellas que tengan
    una longitud mínima requerida (útil para entrenamiento HMM).

    Parámetros
    ----------
    secuencias_autores : dict[str, list[dict]]
        Diccionario de secuencias agrupadas por autor.
    longitud_minima : int, opcional
        Número mínimo de posts que debe tener una secuencia para ser válida.
        Por defecto es 3.

    Retorna
    -------
    dict[str, list[dict]]
        Diccionario filtrado con solo las secuencias que cumplen
        la longitud mínima.
    """
    return {
        nombre_usuario: secuencia
        for nombre_usuario, secuencia in secuencias_autores.items()
        if len(secuencia) >= longitud_minima
    }