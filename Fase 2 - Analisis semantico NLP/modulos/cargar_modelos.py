#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo: cargar_modelos
======================
Encargado de cargar los modelos SecureBERT 2.0 desde Hugging Face
y crear los pipelines de NER y clasificación de secuencias.

Funciones exportadas:
  - cargar_mapeo_mitre(ruta) -> dict
  - cargar_modelos() -> tuple(tokenizer, modelo_ner, modelo_seq)
  - crear_pipeline_ner(modelo, tokenizer, dispositivo) -> pipeline
  - crear_pipeline_secuencias(modelo, tokenizer, dispositivo) -> pipeline
"""

import json
import logging
from typing import Tuple, Any

from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import torch

logger = logging.getLogger(__name__)


def cargar_mapeo_mitre(ruta: str) -> dict:
    """
    Carga el diccionario de mapeo MITRE ATT&CK desde un archivo JSON.

    Parámetros
    ----------
    ruta : str
        Ruta al archivo JSON con el mapeo.

    Retorna
    -------
    dict
        Diccionario con palabras clave como llaves y listas de técnicas MITRE como valores.
        Si hay error, retorna un diccionario vacío.
    """
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando mapeo MITRE desde {ruta}: {e}")
        return {}


def cargar_modelos() -> Tuple[Any, Any, Any]:
    """
    Carga los modelos SecureBERT 2.0 desde Hugging Face.
    Incluye un fallback a bert-base-uncased si SecureBERT no está disponible.

    Retorna
    -------
    tuple
        (tokenizer, modelo_ner, modelo_seq) - los tres componentes del modelo.
        modelo_ner y modelo_seq pueden ser el mismo objeto en el caso de fallback.
    """
    try:
        logger.info("Intentando cargar SecureBERT 2.0-NER desde Hugging Face...")
        tokenizador = AutoTokenizer.from_pretrained("cisco-ai/SecureBERT2.0-NER")
        modelo = AutoModelForTokenClassification.from_pretrained("cisco-ai/SecureBERT2.0-NER")
        logger.info("✅ SecureBERT 2.0-NER cargado exitosamente")
        return tokenizador, modelo, modelo

    except Exception as e:
        logger.warning(f"⚠️ No se pudo cargar SecureBERT 2.0-NER: {e}")
        logger.info("Cargando modelo alternativo (bert-base-uncased) como fallback...")

        tokenizador = AutoTokenizer.from_pretrained("bert-base-uncased")
        modelo = AutoModelForTokenClassification.from_pretrained("bert-base-uncased")
        logger.info("✅ Modelo alternativo cargado exitosamente")
        return tokenizador, modelo, modelo


def crear_pipeline_ner(modelo, tokenizador, dispositivo: str) -> pipeline:
    """
    Crea el pipeline de Named Entity Recognition (NER).

    Parámetros
    ----------
    modelo : AutoModelForTokenClassification
        Modelo cargado para clasificación de tokens.
    tokenizador : AutoTokenizer
        Tokenizador correspondiente al modelo.
    dispositivo : str
        'cuda' si hay GPU disponible, 'cpu' en caso contrario.

    Retorna
    -------
    pipeline
        Pipeline de Hugging Face configurado para NER.
    """
    return pipeline(
        "ner",
        model=modelo,
        tokenizer=tokenizador,
        device=0 if dispositivo == 'cuda' else -1,
        aggregation_strategy="simple"
    )


def crear_pipeline_secuencias(modelo, tokenizador, dispositivo: str) -> pipeline:
    """
    Crea el pipeline de clasificación de texto (secuencias).

    Parámetros
    ----------
    modelo : AutoModelForTokenClassification
        Modelo cargado para clasificación.
    tokenizador : AutoTokenizer
        Tokenizador correspondiente al modelo.
    dispositivo : str
        'cuda' si hay GPU disponible, 'cpu' en caso contrario.

    Retorna
    -------
    pipeline
        Pipeline de Hugging Face configurado para clasificación de texto.
    """
    return pipeline(
        "text-classification",
        model=modelo,
        tokenizer=tokenizador,
        device=0 if dispositivo == 'cuda' else -1
    )