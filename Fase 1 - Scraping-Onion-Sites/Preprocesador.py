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
    if 'cuerpo' in df.columns:
        df['cuerpo_limpio'] = df['cuerpo'].apply(limpiar_texto)

    if 'titulo' in df.columns:
        df['titulo_limpio'] = df['titulo'].apply(limpiar_texto)

    if 'texto_citado' in df.columns:
        df['texto_citado_limpio'] = df['texto_citado'].apply(limpiar_texto)

    # Convertir fecha_hora a datetime y extraer características
    if 'fecha_hora' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha_hora'], errors='coerce')
        df['año'] = df['fecha'].dt.year
        df['mes'] = df['fecha'].dt.month
        df['dia'] = df['fecha'].dt.day
        df['hora'] = df['fecha'].dt.hour

    # Calcular longitudes de texto
    if 'cuerpo_limpio' in df.columns:
        df['longitud_cuerpo'] = df['cuerpo_limpio'].apply(len)

    if 'titulo_limpio' in df.columns:
        df['longitud_titulo'] = df['titulo_limpio'].apply(len)

    # Filtrar registros con contenido mínimo
    min_body_length = 50  # Caracteres mínimos en el cuerpo
    df_filtrado = df[df['longitud_cuerpo'] >= min_body_length] if 'longitud_cuerpo' in df.columns else df

    # Seleccionar columnas útiles para el análisis
    columnas_finales = [
        'id_mensaje', 'huella_contenido', 'id_hilo',
        'usuario', 'fecha_hora', 'fecha', 'año', 'mes', 'dia', 'hora',
        'titulo_limpio', 'cuerpo_limpio', 'texto_citado_limpio',
        'longitud_titulo', 'longitud_cuerpo',
        'url_original'
    ]

    # Asegurarse de que las columnas existan antes de seleccionar
    columnas_existentes = [col for col in columnas_finales if col in df_filtrado.columns]
    df_final = df_filtrado[columnas_existentes]

    # Forzar tipos de datos para consistencia (antes de guardar)
    
    columnas_str = ['id_mensaje', 'huella_contenido', 'id_hilo', 'id_mensaje_padre',
                    'usuario', 'fecha_hora', 'titulo_limpio', 'cuerpo_limpio',
                    'texto_citado_limpio', 'url_original']
    # Cambia los tipos de texto a "string" para aprovechar las funcionalidades de pandas con cadenas
    for col in columnas_str:
        if col in df_final.columns:
            df_final[col] = df_final[col].fillna('').astype("string")

    
    columnas_int = ['año', 'mes', 'dia', 'hora', 'longitud_titulo', 'longitud_cuerpo']
    for col in columnas_int:
        if col in df_final.columns:
            df_final[col] = df_final[col].fillna(0).astype(int)

    # Guardar el resultado
    df_final.to_csv(ruta_salida, index=False)
    print(f"Preprocesamiento completado. Guardado en: {ruta_salida}")
    print(f"Registros originales: {len(df)}")
    print(f"Registros después de filtrado: {len(df_filtrado)}")
    print(f"Columnas en el resultado: {list(df_final.columns)}")

    # Verificar tipos resultantes
    print("\nTipos de datos en el archivo final:")
    for col in df_final.columns:
        print(f"  {col}: {df_final[col].dtype}")

def main():
    """Punto de entrada para ejecución desde línea de comandos."""
    parser = argparse.ArgumentParser(description="Preprocesador para datos del scraper de foros .onion")
    parser.add_argument("--input", "-i", default="../Datos/forum_records.csv",
                       help="Ruta al CSV de entrada")
    parser.add_argument("--output", "-o", default="../Datos/forum_records_clean.csv",
                       help="Ruta al CSV de salida preprocesado")
    args = parser.parse_args()

    preprocesar_csv(args.input, args.output)

if __name__ == "__main__":
    main()