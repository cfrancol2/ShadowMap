"""
Preprocesador para datos del scraper de foros .onion
Limpia y prepara el corpus para análisis posterior.
"""

import pandas as pd
import re
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

def limpiar_texto(texto: str) -> str:
    """Limpia texto eliminando caracteres especiales y normalizando formato."""
    if not texto or pd.isna(texto):
        return ""

    # Convertir a string si no lo es
    texto = str(texto)

    # Eliminar múltiples espacios y líneas
    texto = re.sub(r'[\s\t\n\r]+', ' ', texto)

    # Eliminar caracteres especiales (mantener letras, números y espacios básicos)
    texto = re.sub(r'[^\w\sáéíóúüñÁÉÍÓÚÜÑ]', ' ', texto)

    # Eliminar tokens de anonimización si se desea (opcional)
    texto = re.sub(r'\b(USER|EMAIL|IPV4|ONION|BTC)_[a-f0-9]{16}\b', '[ANONIMIZADO]', texto)

    # Trim y minúsculas
    texto = texto.strip().lower()

    return texto

def limpiar_entidades(entidades_json: str) -> Dict[str, List[str]]:
    """Convierte el campo de entidades de JSON string a diccionario."""
    if not entidades_json or pd.isna(entidades_json):
        return {}

    try:
        return json.loads(entidades_json)
    except (json.JSONDecodeError, TypeError):
        return {}

def preprocesar_csv(ruta_entrada: str, ruta_salida: str) -> None:
    """
    Preprocesa el CSV del scraper y guarda un archivo limpio.

    Args:
        ruta_entrada: Path al CSV generado por el scraper
        ruta_salida: Path donde guardar el CSV preprocesado
    """
    # Leer el CSV
    df = pd.read_csv(ruta_entrada)

    # Aplicar limpieza a campos de texto
    if 'body' in df.columns:
        df['body_limpio'] = df['body'].apply(limpiar_texto)

    if 'title' in df.columns:
        df['title_limpio'] = df['title'].apply(limpiar_texto)

    if 'quoted_text' in df.columns:
        df['quoted_text_limpio'] = df['quoted_text'].apply(limpiar_texto)

    # Procesar entidades
    if 'extracted_entities' in df.columns:
        df['entidades'] = df['extracted_entities'].apply(limpiar_entidades)

    # Convertir timestamp a datetime y extraer características
    if 'timestamp' in df.columns:
        df['fecha'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df['año'] = df['fecha'].dt.year
        df['mes'] = df['fecha'].dt.month
        df['dia'] = df['fecha'].dt.day
        df['hora'] = df['fecha'].dt.hour

    # Calcular longitudes de texto
    if 'body_limpio' in df.columns:
        df['longitud_body'] = df['body_limpio'].apply(len)

    if 'title_limpio' in df.columns:
        df['longitud_titulo'] = df['title_limpio'].apply(len)

    # Filtrar registros con contenido mínimo
    min_body_length = 50  # Caracteres mínimos en el cuerpo
    df_filtrado = df[df['longitud_body'] >= min_body_length] if 'longitud_body' in df.columns else df

    # Seleccionar columnas útiles para el análisis
    columnas_finales = [
        'message_id', 'content_fingerprint', 'thread_id',
        'username', 'timestamp', 'fecha', 'año', 'mes', 'dia', 'hora',
        'title_limpio', 'body_limpio', 'quoted_text_limpio',
        'longitud_titulo', 'longitud_body', 'entidades',
        'forum_name', 'category', 'raw_url'
    ]

    # Asegurarse de que las columnas existan antes de seleccionar
    columnas_existentes = [col for col in columnas_finales if col in df_filtrado.columns]
    df_final = df_filtrado[columnas_existentes]

    # Guardar el resultado
    df_final.to_csv(ruta_salida, index=False)
    print(f"Preprocesamiento completado. Guardado en: {ruta_salida}")
    print(f"Registros originales: {len(df)}")
    print(f"Registros después de filtrado: {len(df_filtrado)}")
    print(f"Columnas en el resultado: {list(df_final.columns)}")

def main():
    """Punto de entrada para ejecución desde línea de comandos."""
    parser = argparse.ArgumentParser(description="Preprocesador para datos del scraper de foros .onion")
    parser.add_argument("--input", "-i", default="../../Scraping-Onion-Sites/output/forum_records.csv",
                       help="Ruta al CSV de entrada")
    parser.add_argument("--output", "-o", default="output/forum_records_clean.csv",
                       help="Ruta al CSV de salida preprocesado")
    args = parser.parse_args()

    preprocesar_csv(args.input, args.output)

if __name__ == "__main__":
    main()

    