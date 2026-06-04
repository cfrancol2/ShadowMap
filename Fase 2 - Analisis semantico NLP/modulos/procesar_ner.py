#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo: procesar_ner
=====================
Encargado del reconocimiento de entidades nombradas (NER) usando SecureBERT.
Incluye la preparación de textos enmascarados y la clasificación de entidades
de ciberseguridad.

Funciones exportadas:
  - preparar_textos_enmascarados(texto) -> list[str]
  - clasificar_entidad(palabra_predicha) -> str | None
  - calcular_confianza(salidas, indice_token_mascara) -> float
  - procesar_ner(texto, pipeline_ner) -> list[dict]
"""

import logging
from typing import List, Dict, Any, Optional

import pandas as pd
import torch

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes: patrones y palabras clave para detección de entidades
# ---------------------------------------------------------------------------

PATRONES_ENMASCARAMIENTO = [
    "The [MASK] malware",
    "The malware [MASK]",
    "[MASK] vulnerability",
    "CVE-[MASK]",
    "Using [MASK] tool",
    "[MASK] attack",
    "The [MASK] exploit",
    "[MASK] ransomware",
    "[MASK] phishing",
    "[MASK] threat"
]

PALABRAS_CLAVE_MALWARE = ["malware", "virus", "trojan", "worm", "spyware", "ransomware", "adware"]
PALABRAS_CLAVE_HERRAMIENTA = ["tool", "kit", "framework", "software", "program"]
PALABRAS_CLAVE_VULNERABILIDAD = ["vulnerability", "flaw", "bug", "exploit", "cve"]
PALABRAS_CLAVE_TECNICA = ["attack", "threat", "breach", "intrusion", "hack"]
PALABRAS_CLAVE_SECTOR = ["banking", "financial", "healthcare", "government", "enterprise"]

PALABRAS_CLAVE_GENERICAS = ["malware", "vulnerability", "tool", "attack",
                            "exploit", "threat", "virus", "trojan"]


def preparar_textos_enmascarados(texto: str) -> List[str]:
    """
    Prepara múltiples versiones del texto con máscaras ([MASK]) en diferentes
    posiciones estratégicas para mejorar la detección de entidades.

    Parámetros
    ----------
    texto : str
        Texto original a procesar.

    Retorna
    -------
    list[str]
        Hasta 5 variantes del texto con máscaras aplicadas.
    """
    variantes = []

    # Patrones predefinidos combinados con el texto original
    for patron in PATRONES_ENMASCARAMIENTO:
        if len(texto.split()) >= 3:
            variante = patron + " " + texto
            variantes.append(variante)

    # Reemplazar palabras clave genéricas por [MASK] dentro del texto
    for palabra in PALABRAS_CLAVE_GENERICAS:
        if palabra in texto.lower():
            variante = texto.replace(palabra, "[MASK]")
            variantes.append(variante)

    return variantes[:5]  # Limitar a 5 para evitar procesamiento excesivo


def clasificar_entidad(palabra_predicha: str) -> Optional[str]:
    """
    Clasifica una palabra predicha por el modelo en una categoría
    de entidad de ciberseguridad.

    Parámetros
    ----------
    palabra_predicha : str
        Palabra o token a clasificar.

    Retorna
    -------
    str or None
        Categoría de la entidad: 'MALWARE', 'TOOL', 'VULNERABILITY',
        'TECHNIQUE', 'SECTOR', o None si no se puede clasificar.
    """
    palabra = palabra_predicha.lower().strip()

    if any(keyword in palabra for keyword in PALABRAS_CLAVE_MALWARE):
        return "MALWARE"
    if any(keyword in palabra for keyword in PALABRAS_CLAVE_HERRAMIENTA):
        return "TOOL"
    if any(keyword in palabra for keyword in PALABRAS_CLAVE_VULNERABILIDAD):
        return "VULNERABILITY"
    if any(keyword in palabra for keyword in PALABRAS_CLAVE_TECNICA):
        return "TECHNIQUE"
    if any(keyword in palabra for keyword in PALABRAS_CLAVE_SECTOR):
        return "SECTOR"
    if palabra.startswith("cve-") or "cve" in palabra:
        return "VULNERABILITY"
    if len(palabra_predicha) > 3 and palabra_predicha.istitle():
        return "TOOL"  # Nombres propios suelen ser herramientas

    return None


def calcular_confianza(salidas: torch.Tensor, indice_token_mascara: torch.Tensor) -> float:
    """
    Calcula la confianza de la predicción basándose en las probabilidades
    del modelo para el token con máscara ([MASK]).

    Parámetros
    ----------
    salidas : torch.Tensor
        Salidas del modelo (logits).
    indice_token_mascara : torch.Tensor
        Índice del token [MASK] en la secuencia.

    Retorna
    -------
    float
        Valor de confianza entre 0 y 1.
    """
    logits = salidas.logits[0, indice_token_mascara]
    probabilidades = torch.softmax(logits, dim=-1)
    probabilidad_maxima, _ = torch.topk(probabilidades, 1)
    return float(probabilidad_maxima.item())


def procesar_ner(texto: str, pipeline_ner) -> List[Dict[str, Any]]:
    """
    Procesa un texto con el pipeline NER de SecureBERT para detectar
    entidades de ciberseguridad.

    Parámetros
    ----------
    texto : str
        Texto a analizar.
    pipeline_ner : pipeline
        Pipeline de Hugging Face configurado para NER.

    Retorna
    -------
    list[dict]
        Lista de entidades detectadas. Cada entidad tiene:
        - type: categoría de la entidad
        - text: texto extraído
        - confidence: confianza de la detección
        - start: posición inicial en el texto
        - end: posición final en el texto
        Si el texto está vacío o hay error, retorna lista vacía.
    """
    # Validar entrada
    if not texto or pd.isna(texto) or str(texto).strip() == "":
        return []

    try:
        resultados = pipeline_ner(str(texto))

        entidades = []
        for entidad in resultados:
            confianza = float(round(entidad['score'], 4))
            entidades.append({
                "type": entidad['entity_group'],
                "text": entidad['word'],
                "confidence": confianza,
                "start": int(entidad['start']),
                "end": int(entidad['end'])
            })

        return entidades

    except Exception as e:
        logger.error(f"Error en procesamiento NER: {e}")
        return []