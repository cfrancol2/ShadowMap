#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo principal: main.py (Fase 3)
====================================
Orquestador del pipeline de Modelos Ocultos de Markov (HMM) para análisis
de comportamiento de autores en foros .onion.

Pipeline:
1. Cargar secuencias de autores desde la Fase 2 (JSON con técnicas MITRE)
2. Mapear técnicas MITRE a fases de la Cyber Kill Chain
3. Entrenar modelo HMM categórico (CategoricalHMM)
4. Analizar cada autor: predecir siguiente fase de Kill Chain
5. Generar reportes CSV y visualizaciones

Uso:
    python main.py

Ejemplo:
    python main.py --input ../Datos/secuencias_autores.json --kill-chain ../kill_chain_fases.json
"""

import argparse
import json
import logging
import sys
import os

# Importar módulos locales
import cargar_secuencias
import entrenar_hmm
import predecir_siguiente

# ---------------------------------------------------------------------------
# Configuración de logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('hmm_processing_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def main():
    """
    Ejecuta el pipeline completo de la Fase 3.
    """
    parser = argparse.ArgumentParser(
        description="main.py - HMM para análisis de comportamiento en foros .onion",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--input", "-i",
        default="../Datos/secuencias_autores.json",
        help="Ruta al JSON de secuencias de la Fase 2 (default: ../Datos/secuencias_autores.json)"
    )
    parser.add_argument(
        "--kill-chain", "-k",
        default="../kill_chain_fases.json",
        help="Ruta al JSON de mapeo Kill Chain (default: ../kill_chain_fases.json)"
    )
    parser.add_argument(
        "--modelo", "-m",
        default="../Datos/modelo_hmm.pkl",
        help="Ruta para guardar/cargar el modelo HMM (default: ../Datos/modelo_hmm.pkl)"
    )
    parser.add_argument(
        "--reporte-csv", "-r",
        default="../Datos/reporte_autores.csv",
        help="Ruta para el reporte CSV de autores (default: ../Datos/reporte_autores.csv)"
    )
    parser.add_argument(
        "--n-estados", "-e",
        type=int, default=4,
        help="Número de estados ocultos (perfiles de comportamiento, default: 4)"
    )
    parser.add_argument(
        "--n-iter", "-n",
        type=int, default=100,
        help="Iteraciones máximas para entrenamiento (default: 100)"
    )
    parser.add_argument(
        "--retrain", action="store_true",
        help="Forzar re-entrenamiento aunque exista un modelo guardado"
    )
    parser.add_argument(
        "--omitir-sin-tecnicas", action="store_true", default=True,
        help="Omitir posts sin técnicas MITRE reconocidas (recomendado, default: True)"
    )
    parser.add_argument(
        "--incluir-sin-tecnicas", action="store_true",
        help="Incluir posts sin técnicas asignándoles fase por defecto (desactiva --omitir-sin-tecnicas)"
    )

    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # PIPELINE
    # -----------------------------------------------------------------------
    logger.info("=" * 60)
    logger.info("INICIANDO FASE 3 - MODELO HMM")
    logger.info("=" * 60)
    logger.info(f"Configuración: {vars(args)}")

    # Paso 1: Cargar secuencias
    logger.info("\n" + "-" * 40)
    logger.info("PASO 1: Cargando secuencias de autores")
    logger.info("-" * 40)

    omitir = not args.incluir_sin_tecnicas
    secuencias, metadatos, mapeo_kill = cargar_secuencias.cargar_secuencias(
        args.input, args.kill_chain, omitir_sin_tecnicas=omitir
    )

    if not secuencias:
        logger.error("No hay secuencias para procesar. Verifica el archivo de entrada.")
        return 1

    # Mostrar resumen
    fases = mapeo_kill.get('metadata', {}).get('fases', [])
    logger.info(f"Fases de Kill Chain: {len(fases)}")
    for f in fases:
        logger.info(f"  [{f['id']}] {f['nombre']}: {f['descripcion']}")
    logger.info(f"Autores cargados: {len(secuencias)}")
    logger.info(f"Posts totales: {sum(len(s) for s in secuencias.values())}")

    # Paso 2: Entrenar HMM
    logger.info("\n" + "-" * 40)
    logger.info("PASO 2: Entrenando modelo HMM")
    logger.info("-" * 40)

    modelo = None

    # Verificar si ya existe un modelo guardado
    if not args.retrain and os.path.exists(args.modelo):
        logger.info(f"Modelo existente encontrado en: {args.modelo}")
        modelo = entrenar_hmm.cargar_modelo(args.modelo)

    if modelo is None:
        modelo = entrenar_hmm.entrenar_hmm(
            secuencias,
            n_estados=args.n_estados,
            n_iter=args.n_iter
        )

        if modelo is None:
            logger.error("No se pudo entrenar el modelo HMM")
            return 1

        # Guardar modelo
        entrenar_hmm.guardar_modelo(modelo, args.modelo)

    # Mostrar parámetros del modelo
    logger.info(f"\nModelo entrenado: {modelo.n_components} estados, {modelo.emissionprob_.shape[1]} observaciones")
    logger.info(f"Probabilidades iniciales: {modelo.startprob_}")

    # Paso 3: Analizar autores y predecir siguiente fase
    logger.info("\n" + "-" * 40)
    logger.info("PASO 3: Analizando autores y prediciendo siguiente fase")
    logger.info("-" * 40)

    resultados = predecir_siguiente.analizar_autores(modelo, secuencias, mapeo_kill)

    autores_ok = sum(1 for d in resultados.values() if d.get('mensaje') == 'OK')
    autores_cortos = sum(1 for d in resultados.values() if 'corta' in d.get('mensaje', ''))
    logger.info(f"Autores analizados: {autores_ok} con predicción, {autores_cortos} con datos insuficientes")

    # Mostrar algunos ejemplos
    for usuario, data in list(resultados.items())[:5]:
        siguiente = data['siguiente']
        if siguiente.get('fase_predicha') is not None:
            logger.info(f"  {usuario}: secuencia={data['secuencia']} → "
                       f"siguiente={siguiente['nombre_fase']} "
                       f"(confianza={siguiente['confianza']:.2%})")

    # Paso 4: Generar reporte CSV
    logger.info("\n" + "-" * 40)
    logger.info("PASO 4: Generando reporte CSV")
    logger.info("-" * 40)

    predecir_siguiente.generar_reporte_csv(resultados, mapeo_kill, args.reporte_csv)
    logger.info(f"Reporte guardado en: {args.reporte_csv}")

    # -----------------------------------------------------------------------
    # Resumen final
    # -----------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("FASE 3 COMPLETADA")
    logger.info("=" * 60)
    logger.info(f"📊 Modelo HMM: {args.modelo}")
    logger.info(f"📋 Reporte autores: {args.reporte_csv}")
    logger.info(f"🎯 Total autores analizados: {len(resultados)}")
    logger.info(f"✅ Predicciones generadas: {autores_ok}")
    logger.info(f"💡 Visualiza los resultados con: streamlit run dashboard_hmm.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())