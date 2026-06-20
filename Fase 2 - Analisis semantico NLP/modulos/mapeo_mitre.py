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
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para matching flexible:
    - Minúsculas
    - Eliminar espacios extra, guiones, puntos, barras bajas
    """
    texto = texto.lower().strip()
    texto = re.sub(r'[\s\-_./]+', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def mapear_a_mitre(entidades: List[Dict[str, Any]], mapeo_mitre: dict) -> List[str]:
    """
    Mapea las entidades detectadas por NER a técnicas MITRE ATT&CK
    usando un diccionario de mapeo predefinido.

    Implementa matching flexible:
    1. Coincidencia exacta (case-insensitive)
    2. Coincidencia con normalización (sin espacios/guiones)
    3. Coincidencia por subcadena

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

    # Pre-normalizar las claves del mapeo para matching rápido
    claves_normalizadas = {}
    for clave, tecnicas_asociadas in mapeo_mitre.items():
        clave_norm = _normalizar_texto(clave)
        claves_normalizadas[clave_norm] = tecnicas_asociadas

    for entidad in entidades:
        texto_original = entidad['text']
        texto_lower = texto_original.lower()
        texto_norm = _normalizar_texto(texto_original)

        for clave_norm, tecnicas_asociadas in claves_normalizadas.items():
            # Matching 1: coincidencia normalizada (sin espacios/guiones)
            if clave_norm in texto_norm:
                tecnicas.update(tecnicas_asociadas)
                continue

            # Matching 2: coincidencia por subcadena en texto original
            if clave_norm in texto_lower:
                tecnicas.update(tecnicas_asociadas)
                continue

            # Matching 3: si la clave tiene espacio, buscar sin espacio también
            clave_sin_espacios = clave_norm.replace(' ', '')
            texto_sin_espacios = texto_norm.replace(' ', '')
            if clave_sin_espacios and clave_sin_espacios in texto_sin_espacios:
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