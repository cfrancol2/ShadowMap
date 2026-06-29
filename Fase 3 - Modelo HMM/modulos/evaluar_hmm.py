#!/usr/bin/env python3
# encoding: utf-8
"""
Módulo: evaluar_hmm
====================
Evalúa el rendimiento del modelo HMM entrenado usando métricas de
clasificación (Precisión, Recall, F1-score) y visualizaciones.

Pipeline de evaluación:
1. División hold-out (train/test) de las secuencias de autores
2. Entrenamiento del HMM solo con datos de entrenamiento
3. Predicción de la siguiente fase vs fase real (última fase)
4. Cálculo de métricas: Precisión, Recall, F1-score (macro/weighted)
5. Matriz de confusión multi-clase (6 fases de Kill Chain)
6. Análisis por autor: fase real vs predicha, confianza
7. Generación de reportes CSV y gráficos PNG

Funciones exportadas:
  - dividir_train_test(secuencias, test_ratio, random_state) -> tuple
  - evaluar_modelo(modelo, secuencias_prueba, mapeo) -> dict
  - calcular_metricas(y_true, y_pred, nombres_clases) -> dict
  - generar_matriz_confusion(y_true, y_pred, nombres_fases, ruta_salida) -> None
  - graficar_metricas(metricas, ruta_salida) -> None
  - graficar_confianza(predicciones, ruta_salida) -> None
  - generar_reporte_evaluacion(metricas, analisis_autores, ruta_csv) -> None
  - ejecutar_evaluacion_completa(modelo, secuencias, mapeo, ruta_salida) -> dict
"""

import logging
import os
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from collections import Counter

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# División de datos
# ---------------------------------------------------------------------------

def dividir_train_test(secuencias_por_autor: Dict[str, List[int]],
                       test_ratio: float = 0.2,
                       random_state: int = 42) -> Tuple[Dict[str, List[int]], Dict[str, List[int]]]:
    """
    Divide las secuencias de autores en conjuntos de entrenamiento y prueba.

    La división se realiza a nivel de autor (no de secuencia individual),
    para que cada autor aparezca en un solo conjunto. Esto simula la
    validación temporal: el modelo se entrena con un subconjunto de autores
    y se evalúa con autores no vistos.

    Parámetros
    ----------
    secuencias_por_autor : dict
        Diccionario {nombre_usuario: [fase_0, fase_1, ..., fase_n]}.
    test_ratio : float
        Proporción de autores para el conjunto de prueba (default: 0.2).
    random_state : int
        Semilla para reproducibilidad.

    Retorna
    -------
    tuple
        (secuencias_train, secuencias_test)
    """
    rng = np.random.RandomState(random_state)
    usuarios = list(secuencias_por_autor.keys())
    rng.shuffle(usuarios)

    n_test = max(1, int(len(usuarios) * test_ratio))
    n_test = min(n_test, len(usuarios) - 1)  # Asegurar al menos 1 en train

    usuarios_test = usuarios[:n_test]
    usuarios_train = usuarios[n_test:]

    train = {u: secuencias_por_autor[u] for u in usuarios_train}
    test = {u: secuencias_por_autor[u] for u in usuarios_test}

    logger.info(f"División hold-out: {len(train)} train, {len(test)} test "
                f"(test_ratio={test_ratio:.0%})")

    return train, test


# ---------------------------------------------------------------------------
# Métricas de clasificación
# ---------------------------------------------------------------------------

def calcular_metricas(y_true: List[int], y_pred: List[int],
                      nombres_clases: List[str]) -> Dict:
    """
    Calcula Precisión, Recall y F1-score para cada fase de la Kill Chain,
    así como promedios macro y weighted.

    Parámetros
    ----------
    y_true : list[int]
        Fases reales (ground truth).
    y_pred : list[int]
        Fases predichas por el modelo.
    nombres_clases : list[str]
        Nombres de cada fase (ej. ["Reconocimiento", "Entrega", ...]).

    Retorna
    -------
    dict
        Diccionario con:
        - por_fase: dict {fase_id: {precision, recall, f1, soporte}}
        - precision_macro, recall_macro, f1_macro
        - precision_weighted, recall_weighted, f1_weighted
        - accuracy
        - total_muestras
    """
    if not y_true or not y_pred:
        logger.warning("No hay muestras para calcular métricas")
        return {"por_fase": {}, "accuracy": 0.0, "total_muestras": 0}

    n_clases = len(nombres_clases)
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    # Métricas por clase (one-vs-all)
    por_fase = {}
    sum_precision = 0.0
    sum_recall = 0.0
    sum_f1 = 0.0
    total_support = 0

    for c in range(n_clases):
        tp = int(np.sum((y_true == c) & (y_pred == c)))
        fp = int(np.sum((y_true != c) & (y_pred == c)))
        fn = int(np.sum((y_true == c) & (y_pred != c)))
        support = int(np.sum(y_true == c))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        nombre = nombres_clases[c] if c < len(nombres_clases) else f"Fase {c}"

        por_fase[nombre] = {
            "fase_id": c,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "soporte": support
        }

        # Para promedios weighted
        sum_precision += precision * support
        sum_recall += recall * support
        sum_f1 += f1 * support
        total_support += support

    # Accuracy general
    accuracy = float(np.mean(y_true == y_pred))

    # Promedios macro (promedio simple)
    fases_activas = [f for f in por_fase.values() if f["soporte"] > 0]
    precision_macro = np.mean([f["precision"] for f in fases_activas]) if fases_activas else 0.0
    recall_macro = np.mean([f["recall"] for f in fases_activas]) if fases_activas else 0.0
    f1_macro = np.mean([f["f1"] for f in fases_activas]) if fases_activas else 0.0

    # Promedios weighted
    precision_weighted = sum_precision / total_support if total_support > 0 else 0.0
    recall_weighted = sum_recall / total_support if total_support > 0 else 0.0
    f1_weighted = sum_f1 / total_support if total_support > 0 else 0.0

    resultado = {
        "por_fase": por_fase,
        "precision_macro": round(float(precision_macro), 4),
        "recall_macro": round(float(recall_macro), 4),
        "f1_macro": round(float(f1_macro), 4),
        "precision_weighted": round(float(precision_weighted), 4),
        "recall_weighted": round(float(recall_weighted), 4),
        "f1_weighted": round(float(f1_weighted), 4),
        "accuracy": round(accuracy, 4),
        "total_muestras": len(y_true)
    }

    logger.info(f"Métricas calculadas: {len(y_true)} muestras, "
                f"Accuracy={accuracy:.2%}, F1-macro={f1_macro:.4f}")

    return resultado


# ---------------------------------------------------------------------------
# Evaluación del modelo
# ---------------------------------------------------------------------------

def evaluar_modelo(modelo, secuencias_test: Dict[str, List[int]],
                   mapeo: dict) -> Dict:
    """
    Evalúa el modelo HMM en el conjunto de prueba.

    Para cada autor en test:
    1. Usa toda su secuencia para predecir la siguiente fase
    2. Compara la predicción con la fase REAL (última fase de la secuencia)
    3. Registra la confianza de la predicción

    Parámetros
    ----------
    modelo : CategoricalHMM
        Modelo HMM entrenado.
    secuencias_test : dict
        Secuencias del conjunto de prueba {usuario: [fases]}.
    mapeo : dict
        Diccionario con el mapeo Kill Chain.

    Retorna
    -------
    dict
        Diccionario con:
        - y_true: fases reales
        - y_pred: fases predichas
        - predicciones: lista detallada por autor
        - confianzas: lista de confianzas
    """
    # Importar la función de predicción del módulo existente
    import predecir_siguiente

    fases = mapeo.get('metadata', {}).get('fases', [])
    nombres_fases = [f['nombre'] for f in fases]

    y_true = []
    y_pred = []
    predicciones = []
    confianzas = []

    for usuario, secuencia in secuencias_test.items():
        if len(secuencia) < 2:
            # Necesitamos al menos 2 posts: uno para entrenar y uno como ground truth
            continue

        # La última fase es el ground truth (lo que realmente ocurrió)
        fase_real = secuencia[-1]

        # Usamos la secuencia SIN el último elemento para predecir
        secuencia_parcial = secuencia[:-1]

        # Predecir siguiente fase
        resultado = predecir_siguiente.predecir_siguiente_fase(
            modelo, secuencia_parcial, mapeo
        )

        fase_predicha = resultado['fase_predicha']
        confianza = resultado['confianza']

        if fase_predicha is not None:
            y_true.append(fase_real)
            y_pred.append(fase_predicha)
            confianzas.append(confianza)

            predicciones.append({
                "usuario": usuario,
                "secuencia_completa": secuencia,
                "secuencia_usada": secuencia_parcial,
                "fase_real": fase_real,
                "fase_real_nombre": nombres_fases[fase_real] if fase_real < len(nombres_fases) else f"Fase {fase_real}",
                "fase_predicha": fase_predicha,
                "fase_predicha_nombre": resultado['nombre_fase'],
                "confianza": confianza,
                "correcto": fase_real == fase_predicha
            })

    logger.info(f"Evaluación: {len(y_true)} autores evaluados en test")

    return {
        "y_true": y_true,
        "y_pred": y_pred,
        "predicciones": predicciones,
        "confianzas": confianzas,
        "nombres_fases": nombres_fases
    }


# ---------------------------------------------------------------------------
# Visualizaciones
# ---------------------------------------------------------------------------

def generar_matriz_confusion(y_true: List[int], y_pred: List[int],
                             nombres_fases: List[str],
                             ruta_salida: str) -> None:
    """
    Genera un heatmap de la matriz de confusión multi-clase.

    Parámetros
    ----------
    y_true : list[int]
        Fases reales.
    y_pred : list[int]
        Fases predichas.
    nombres_fases : list[str]
        Nombres de cada fase.
    ruta_salida : str
        Ruta para guardar la imagen PNG.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError:
        logger.warning("matplotlib/seaborn no disponibles, omitiendo matriz de confusión")
        return

    n_clases = len(nombres_fases)
    matriz = np.zeros((n_clases, n_clases), dtype=int)

    for t, p in zip(y_true, y_pred):
        if 0 <= t < n_clases and 0 <= p < n_clases:
            matriz[t][p] += 1

    fig, ax = plt.subplots(figsize=(10, 8))

    # Acortar nombres para mejor visualización
    nombres_cortos = []
    for nombre in nombres_fases:
        if len(nombre) > 20:
            nombre = nombre[:18] + "..."
        nombres_cortos.append(nombre)

    sns.heatmap(matriz, annot=True, fmt='d', cmap='Blues',
                xticklabels=nombres_cortos,
                yticklabels=nombres_cortos,
                ax=ax)

    ax.set_xlabel('Fase Predicha', fontsize=12)
    ax.set_ylabel('Fase Real', fontsize=12)
    ax.set_title('Matriz de Confusión - Modelo HMM\nPredicción de Siguiente Fase de Kill Chain', fontsize=14)

    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()

    os.makedirs(os.path.dirname(ruta_salida) or '.', exist_ok=True)
    plt.savefig(ruta_salida, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Matriz de confusión guardada en: {ruta_salida}")


def graficar_metricas(metricas: Dict, ruta_salida: str) -> None:
    """
    Genera un gráfico de barras con Precisión, Recall y F1-score por fase.

    Parámetros
    ----------
    metricas : dict
        Resultado de calcular_metricas().
    ruta_salida : str
        Ruta para guardar la imagen PNG.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib no disponible, omitiendo gráfico de métricas")
        return

    por_fase = metricas.get("por_fase", {})
    if not por_fase:
        logger.warning("No hay métricas por fase para graficar")
        return

    fases = list(por_fase.keys())
    precisiones = [por_fase[f]["precision"] for f in fases]
    recalls = [por_fase[f]["recall"] for f in fases]
    f1s = [por_fase[f]["f1"] for f in fases]

    # Acortar nombres si son muy largos
    fases_cortas = []
    for nombre in fases:
        if len(nombre) > 20:
            nombre = nombre[:18] + "..."
        fases_cortas.append(nombre)

    x = np.arange(len(fases_cortas))
    ancho = 0.25

    fig, ax = plt.subplots(figsize=(12, 6))

    barras1 = ax.bar(x - ancho, precisiones, ancho, label='Precisión', color='#2196F3', alpha=0.85)
    barras2 = ax.bar(x, recalls, ancho, label='Recall', color='#4CAF50', alpha=0.85)
    barras3 = ax.bar(x + ancho, f1s, ancho, label='F1-Score', color='#FF9800', alpha=0.85)

    # Agregar valores sobre las barras
    for barras in [barras1, barras2, barras3]:
        for barra in barras:
            altura = barra.get_height()
            if altura > 0:
                ax.annotate(f'{altura:.2f}',
                           xy=(barra.get_x() + barra.get_width() / 2, altura),
                           xytext=(0, 3), textcoords="offset points",
                           ha='center', va='bottom', fontsize=7)

    ax.set_xlabel('Fase de Kill Chain', fontsize=12)
    ax.set_ylabel('Valor', fontsize=12)
    ax.set_title('Métricas de Clasificación por Fase\n(Precisión, Recall, F1-Score)', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(fases_cortas, rotation=45, ha='right', fontsize=9)
    ax.set_ylim(0, 1.15)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3)

    # Agregar métricas globales como texto
    texto_global = (f"Accuracy: {metricas.get('accuracy', 0):.2%} | "
                    f"F1-macro: {metricas.get('f1_macro', 0):.4f} | "
                    f"F1-weighted: {metricas.get('f1_weighted', 0):.4f}")
    ax.text(0.5, -0.22, texto_global, transform=ax.transAxes,
            ha='center', fontsize=10, style='italic', color='#333')

    plt.tight_layout()

    os.makedirs(os.path.dirname(ruta_salida) or '.', exist_ok=True)
    plt.savefig(ruta_salida, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Gráfico de métricas guardado en: {ruta_salida}")


def graficar_confianza(confianzas: List[float], ruta_salida: str) -> None:
    """
    Genera un histograma de la distribución de confianza de predicciones.

    Parámetros
    ----------
    confianzas : list[float]
        Lista de valores de confianza (0.0 - 1.0).
    ruta_salida : str
        Ruta para guardar la imagen PNG.
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib no disponible, omitiendo histograma de confianza")
        return

    if not confianzas:
        logger.warning("No hay datos de confianza para graficar")
        return

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.hist(confianzas, bins=20, color='#673AB7', alpha=0.75, edgecolor='white')

    # Líneas de referencia
    media = np.mean(confianzas)
    mediana = np.median(confianzas)
    ax.axvline(media, color='#E91E63', linestyle='--', linewidth=1.5, label=f'Media: {media:.3f}')
    ax.axvline(mediana, color='#FF5722', linestyle='-.', linewidth=1.5, label=f'Mediana: {mediana:.3f}')

    ax.set_xlabel('Confianza de Predicción', fontsize=12)
    ax.set_ylabel('Frecuencia', fontsize=12)
    ax.set_title('Distribución de Confianza de Predicciones del HMM', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)

    # Estadísticas
    texto_stats = (f"N={len(confianzas)} | "
                   f"Mín={min(confianzas):.3f} | "
                   f"Máx={max(confianzas):.3f} | "
                   f"DE={np.std(confianzas):.3f}")
    ax.text(0.5, -0.18, texto_stats, transform=ax.transAxes,
            ha='center', fontsize=10, style='italic', color='#333')

    plt.tight_layout()

    os.makedirs(os.path.dirname(ruta_salida) or '.', exist_ok=True)
    plt.savefig(ruta_salida, dpi=150, bbox_inches='tight')
    plt.close()

    logger.info(f"Histograma de confianza guardado en: {ruta_salida}")


# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

def generar_reporte_evaluacion(metricas: Dict, predicciones: List[Dict],
                               ruta_csv: str) -> None:
    """
    Genera un archivo CSV con el reporte detallado de evaluación.

    Contiene:
    - Hoja 1: Métricas por fase y globales
    - Hoja 2: Resultado por autor (fase real vs predicha)

    Parámetros
    ----------
    metricas : dict
        Resultado de calcular_metricas().
    predicciones : list[dict]
        Lista de predicciones individuales por autor.
    ruta_csv : str
        Ruta donde guardar el CSV.
    """
    os.makedirs(os.path.dirname(ruta_csv) or '.', exist_ok=True)

    # 1. Métricas por fase
    registros_metricas = []
    por_fase = metricas.get("por_fase", {})
    for nombre_fase, datos in por_fase.items():
        registros_metricas.append({
            "metrica": nombre_fase,
            "precision": datos["precision"],
            "recall": datos["recall"],
            "f1_score": datos["f1"],
            "soporte": datos["soporte"]
        })

    # Agregar métricas globales
    registros_metricas.append({
        "metrica": "--- GLOBAL ---",
        "precision": "",
        "recall": "",
        "f1_score": "",
        "soporte": ""
    })
    registros_metricas.append({
        "metrica": "Accuracy",
        "precision": metricas.get("accuracy", 0),
        "recall": "",
        "f1_score": "",
        "soporte": metricas.get("total_muestras", 0)
    })
    registros_metricas.append({
        "metrica": "F1-macro",
        "precision": "",
        "recall": "",
        "f1_score": metricas.get("f1_macro", 0),
        "soporte": ""
    })
    registros_metricas.append({
        "metrica": "F1-weighted",
        "precision": "",
        "recall": "",
        "f1_score": metricas.get("f1_weighted", 0),
        "soporte": ""
    })

    df_metricas = pd.DataFrame(registros_metricas)

    # 2. Detalle por autor
    registros_autores = []
    for pred in predicciones:
        registros_autores.append({
            "usuario": pred["usuario"],
            "secuencia": str(pred["secuencia_completa"]),
            "fase_real_id": pred["fase_real"],
            "fase_real": pred["fase_real_nombre"],
            "fase_predicha_id": pred["fase_predicha"],
            "fase_predicha": pred["fase_predicha_nombre"],
            "confianza": round(pred["confianza"], 4),
            "correcto": pred["correcto"]
        })

    df_autores = pd.DataFrame(registros_autores)

    # Guardar ambas hojas en un solo CSV (concatenadas con separador)
    with open(ruta_csv, 'w', encoding='utf-8', newline='') as f:
        f.write("=== MÉTRICAS DE EVALUACIÓN ===\n")
        df_metricas.to_csv(f, index=False)
        f.write("\n=== DETALLE POR AUTOR ===\n")
        df_autores.to_csv(f, index=False)

    logger.info(f"Reporte de evaluación guardado en: {ruta_csv}")


# ---------------------------------------------------------------------------
# Pipeline completo de evaluación
# ---------------------------------------------------------------------------

def ejecutar_evaluacion_completa(modelo, secuencias: Dict[str, List[int]],
                                 mapeo: dict,
                                 ruta_salida: str = "../Datos/evaluacion") -> Dict:
    """
    Ejecuta el pipeline completo de evaluación del modelo HMM.

    1. Divide datos en train/test (hold-out 80/20)
    2. Evalúa predicciones en el conjunto de test
    3. Calcula métricas (Precisión, Recall, F1-score)
    4. Genera matriz de confusión (PNG)
    5. Genera gráfico de métricas por fase (PNG)
    6. Genera histograma de confianza (PNG)
    7. Genera reporte CSV detallado

    Parámetros
    ----------
    modelo : CategoricalHMM
        Modelo HMM entrenado.
    secuencias : dict
        Secuencias completas de autores.
    mapeo : dict
        Diccionario con el mapeo Kill Chain.
    ruta_salida : str
        Directorio base para las salidas.

    Retorna
    -------
    dict
        Diccionario con todas las métricas y resultados.
    """
    logger.info("=" * 60)
    logger.info("INICIANDO EVALUACIÓN DEL MODELO HMM")
    logger.info("=" * 60)

    os.makedirs(ruta_salida, exist_ok=True)

    # Paso 1: División hold-out
    logger.info("\n--- Paso 1: División train/test ---")
    train, test = dividir_train_test(secuencias, test_ratio=0.2, random_state=42)

    # Paso 2: Evaluar modelo en conjunto de prueba
    logger.info("\n--- Paso 2: Evaluando modelo en conjunto de prueba ---")
    evaluacion = evaluar_modelo(modelo, test, mapeo)

    y_true = evaluacion["y_true"]
    y_pred = evaluacion["y_pred"]
    predicciones = evaluacion["predicciones"]
    confianzas = evaluacion["confianzas"]
    nombres_fases = evaluacion["nombres_fases"]

    if not y_true:
        logger.error("No se pudieron generar predicciones para evaluar. "
                     "Verifica que el conjunto de prueba tenga autores con ≥2 posts.")
        return {"error": "Sin datos suficientes para evaluación"}

    # Paso 3: Calcular métricas
    logger.info("\n--- Paso 3: Calculando métricas de clasificación ---")
    metricas = calcular_metricas(y_true, y_pred, nombres_fases)

    # Mostrar resultados
    logger.info(f"\n📊 RESULTADOS DE EVALUACIÓN")
    logger.info(f"  Accuracy: {metricas['accuracy']:.2%}")
    logger.info(f"  F1-score (macro): {metricas['f1_macro']:.4f}")
    logger.info(f"  F1-score (weighted): {metricas['f1_weighted']:.4f}")
    logger.info(f"  Precisión (macro): {metricas['precision_macro']:.4f}")
    logger.info(f"  Recall (macro): {metricas['recall_macro']:.4f}")
    logger.info(f"  Total muestras evaluadas: {metricas['total_muestras']}")

    # Precisión de predicciones correctas
    n_correctos = sum(1 for p in predicciones if p["correcto"])
    logger.info(f"  Predicciones correctas: {n_correctos}/{len(predicciones)} "
                f"({n_correctos/len(predicciones):.2%})")

    # Paso 4: Matriz de confusión
    logger.info("\n--- Paso 4: Generando matriz de confusión ---")
    generar_matriz_confusion(y_true, y_pred, nombres_fases,
                             os.path.join(ruta_salida, "matriz_confusion.png"))

    # Paso 5: Gráfico de métricas
    logger.info("\n--- Paso 5: Generando gráfico de métricas por fase ---")
    graficar_metricas(metricas, os.path.join(ruta_salida, "grafico_metricas.png"))

    # Paso 6: Histograma de confianza
    logger.info("\n--- Paso 6: Generando histograma de confianza ---")
    graficar_confianza(confianzas, os.path.join(ruta_salida, "grafico_confianza.png"))

    # Paso 7: Reporte CSV
    logger.info("\n--- Paso 7: Generando reporte CSV ---")
    generar_reporte_evaluacion(metricas, predicciones,
                               os.path.join(ruta_salida, "reporte_evaluacion.csv"))

    # Resumen de archivos generados
    logger.info("\n" + "=" * 60)
    logger.info("EVALUACIÓN COMPLETADA")
    logger.info("=" * 60)
    logger.info(f"📁 Archivos generados en: {ruta_salida}/")
    logger.info(f"  📊 matriz_confusion.png")
    logger.info(f"  📈 grafico_metricas.png")
    logger.info(f"  📉 grafico_confianza.png")
    logger.info(f"  📋 reporte_evaluacion.csv")

    # Retornar resultados completos
    resultado_completo = {
        "metricas": metricas,
        "predicciones": predicciones,
        "confianzas": confianzas,
        "y_true": y_true,
        "y_pred": y_pred,
        "nombres_fases": nombres_fases,
        "train_size": len(train),
        "test_size": len(test)
    }

    return resultado_completo