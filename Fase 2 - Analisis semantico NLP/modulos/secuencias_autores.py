#!/usr/bin/env python3
# encoding: utf-8
"""
Encargado de la agrupación de posts por autor, ordenamiento cronológico
y filtrado de secuencias válidas para entrenamiento HMM.
"""

import logging
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def agrupar_por_autor(posts: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agrupa los posts por nombre de usuario y los ordena cronológicamente
    dentro de cada grupo.
    """
    secuencias = {}

    for post in posts:
        nombre_usuario = post.get('usuario', 'usuario_desconocido')
        fecha_hora_raw = post.get('fecha_hora')

        if not fecha_hora_raw:
            continue

        try:
            # Convertir fecha_hora a datetime para ordenamiento cronológico
            if isinstance(fecha_hora_raw, str):
                fecha_hora = pd.to_datetime(fecha_hora_raw)
            else:
                fecha_hora = fecha_hora_raw

            if nombre_usuario not in secuencias:
                secuencias[nombre_usuario] = []

            # Agregar post con campo datetime para ordenar después
            secuencias[nombre_usuario].append({
                **post,
                'datetime': fecha_hora
            })

        except Exception as e:
            logger.warning(
                f"Error procesando fecha_hora para post "
                f"{post.get('id_mensaje', 'desconocido')}: {e}"
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
    """
    return {
        nombre_usuario: secuencia
        for nombre_usuario, secuencia in secuencias_autores.items()
        if len(secuencia) >= longitud_minima
    }