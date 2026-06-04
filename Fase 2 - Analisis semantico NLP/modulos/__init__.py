#!/usr/bin/env python3
# encoding: utf-8
"""
Paquete: modulos
=================
Conjunto de módulos para el pipeline de enriquecimiento NLP con SecureBERT 2.0.

Submódulos:
    - cargar_modelos: Carga de modelos SecureBERT desde Hugging Face
    - procesar_ner: Reconocimiento de entidades nombradas (NER)
    - mapeo_mitre: Mapeo de entidades a técnicas MITRE ATT&CK
    - secuencias_autores: Agrupación de posts por autor
    - procesar_datos: Lectura/escritura de CSV y generación de JSON HMM
    - main: Orquestador principal con interfaz CLI
"""

__version__ = "2.0.0"
__author__ = "Proyecto Titulación"