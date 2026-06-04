#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo: mapeo_mitre
=====================
Encargado de mapear entidades detectadas a técnicas MITRE ATT&CK
y calcular la puntuación de amenaza de un post.

Funciones exportadas:
  - mapear_a_mitre(entidades, mapeo_mitre) -> list[str]
  - calcular_puntuacion_amenaza(entidades, tecnicas_mitre) -> float
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def mapear_a_mitre(entidades: List[Dict[str, Any]], mapeo_mitre: dict) -> List[str]:
    """
    Mapea las entidades detectadas por NER a técnicas MITRE ATT&CK
    usando un diccionario de mapeo predefinido.

    Parámetros
    ----------
    entidades : list[dict]
        Lista de entidades detectadas. Cada entidad debe tener al menos
        una llave 'text' con el texto extraído.
    mapeo_mitre : dict
        Diccionario donde las llaves son palabras clave y los valores
        son listas de IDs de técnicas MITRE (ej. "T1204.002").

    Retorna
    -------
    list[str]
        Lista ordenada de IDs de técnicas MITRE únicas encontradas.
        Retorna lista vacía si no hay coincidencias.
    """
    tecnicas = set()

    for entidad in entidades:
        texto_entidad = entidad['text'].lower()
        for clave, tecnicas_asociadas in mapeo_mitre.items():
            if clave.lower() in texto_entidad:
                tecnicas.update(tecnicas_asociadas)

    return sorted(list(tecnicas))


def calcular_puntuacion_amenaza(entidades: List[Dict[str, Any]],
                                tecnicas_mitre: List[str]) -> float:
    """
    Calcula una puntuación de amenaza (0 a 1) para un post basándose en:
    - La confianza promedio de las entidades detectadas (70% del peso)
    - La cantidad de técnicas MITRE asociadas (30% del peso)

    Parámetros
    ----------
    entidades : list[dict]
        Lista de entidades detectadas con sus confianzas.
    tecnicas_mitre : list[str]
        Lista de IDs de técnicas MITRE mapeadas.

    Retorna
    -------
    float
        Puntuación de amenaza entre 0.0 y 1.0 (redondeada a 4 decimales).
        Retorna 0.0 si no hay entidades ni técnicas.
    """
    if not entidades and not tecnicas_mitre:
        return 0.0

    # Puntuación basada en la confianza promedio de las entidades
    puntuacion_entidades = (
        sum(entidad['confidence'] for entidad in entidades) / len(entidades)
        if entidades else 0
    )

    # Puntuación basada en el número de técnicas MITRE (normalizado a 0-1)
    puntuacion_tecnicas = min(len(tecnicas_mitre) / 10, 1.0)

    # Combinar: 70% entidades, 30% técnicas
    puntuacion_final = (puntuacion_entidades * 0.7 + puntuacion_tecnicas * 0.3)
    return round(puntuacion_final, 4)