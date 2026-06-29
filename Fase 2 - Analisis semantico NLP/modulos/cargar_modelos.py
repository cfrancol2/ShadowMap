#!/usr/bin/env python3
# encoding: utf-8
# Módulo: cargar_modelos

# Encargado de cargar los modelos SecureBERT 2.0 desde Hugging Face
# y crear los pipelines de NER y clasificación de secuencias.

# Funciones exportadas:
#  cargar_mapeo_mitre(ruta) -> dict
#  cargar_modelos() -> tuple(tokenizer, modelo_ner, modelo_seq)
#  crear_pipeline_ner(modelo, tokenizer, dispositivo) -> pipeline
#  crear_pipeline_secuencias(modelo, tokenizer, dispositivo) -> pipeline


import json
import logging
from typing import Tuple, Any

from transformers import AutoTokenizer, AutoModelForTokenClassification
from transformers import pipeline
import torch

logger = logging.getLogger(__name__)


def cargar_mapeo_mitre(ruta: str) -> dict:
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando mapeo MITRE desde {ruta}: {e}")
        return {}


def cargar_modelos() -> Tuple[Any, Any, Any]:    
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
    return pipeline(
        "ner",
        model=modelo,
        tokenizer=tokenizador,
        device=0 if dispositivo == 'cuda' else -1,
        aggregation_strategy="simple"
    )


def crear_pipeline_secuencias(modelo, tokenizador, dispositivo: str) -> pipeline:
    return pipeline(
        "text-classification",
        model=modelo,
        tokenizer=tokenizador,
        device=0 if dispositivo == 'cuda' else -1
    )