#!/usr/bin/env python3
# encoding: utf-8
"""
ShadowMap - Ejecutor por Consola
=================================
Interfaz de consola para ejecutar las fases del pipeline de manera
independiente o todas juntas.

Uso:
    python run_pipeline.py                    # Menu interactivo
    python run_pipeline.py --todo             # Ejecutar todas las fases
    python run_pipeline.py --fase 1           # Ejecutar solo Fase 1
    python run_pipeline.py --fase 2           # Ejecutar solo Fase 2
    python run_pipeline.py --fase 3           # Ejecutar solo Fase 3
    python run_pipeline.py --dashboard        # Lanzar dashboard IA
"""

import argparse
import os
import sys
import subprocess
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuracion de rutas
# ---------------------------------------------------------------------------

RUTA_BASE = Path(__file__).parent.resolve()
RUTA_FASE1 = RUTA_BASE / "Fase 1 - Scraping-Onion-Sites"
RUTA_FASE2 = RUTA_BASE / "Fase 2 - Analisis semantico NLP"
RUTA_FASE3 = RUTA_BASE / "Fase 3 - Modelo HMM"
RUTA_DATOS = RUTA_BASE / "Datos"

SEPARADOR = "=" * 60


def limpiar_pantalla():
    """Limpia la pantalla de la consola."""
    os.system("cls" if os.name == "nt" else "clear")


def mostrar_titulo():
    """Muestra el titulo del programa."""
    print(SEPARADOR)
    print("  SHADOWMAP - Ejecutor por Consola")
    print("  Proyecto de Titulacion TI")
    print(SEPARADOR)
    print()


def verificar_archivos():
    """Verifica el estado de los archivos de datos."""
    archivos = {
        "forum_records.csv": RUTA_DATOS / "forum_records.csv",
        "forum_records_clean.csv": RUTA_DATOS / "forum_records_clean.csv",
        "datos_enriquecidos.csv": RUTA_DATOS / "datos_enriquecidos.csv",
        "secuencias_autores.json": RUTA_DATOS / "secuencias_autores.json",
        "modelo_hmm.pkl": RUTA_DATOS / "modelo_hmm.pkl",
        "reporte_autores.csv": RUTA_DATOS / "reporte_autores.csv",
    }

    print("Estado de archivos de datos:")
    for nombre, ruta in archivos.items():
        icono = "[OK]" if ruta.exists() else "[--]"
        print(f"  {icono} {nombre}")
    print()
    return archivos


def ejecutar_comando(comando, cwd=None):
    """Ejecuta un comando y retorna el codigo de salida."""
    print(f"\n  Ejecutando: {comando}")
    print(f"  Directorio: {cwd or RUTA_BASE}")
    print("-" * 60)

    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            cwd=str(cwd) if cwd else str(RUTA_BASE),
            text=True,
        )
        print("-" * 60)
        if resultado.returncode == 0:
            print("  [OK] Fase completada exitosamente.\n")
        else:
            print(f"  [ERROR] Fase fallo con codigo: {resultado.returncode}\n")
        return resultado.returncode
    except Exception as e:
        print(f"  [ERROR] {e}\n")
        return 1


# ---------------------------------------------------------------------------
# Verificacion de Tor
# ---------------------------------------------------------------------------

def verificar_tor():
    """Verifica si hay conexion a la red Tor consultando icanhazip.com."""
    print("\n  Verificando conexion a la red Tor...")
    try:
        # Primero intentar via proxy Tor (puerto local 9050)
        proxy = urllib.request.ProxyHandler({
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        })
        opener = urllib.request.build_opener(proxy)
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        respuesta = opener.open('https://icanhazip.com', timeout=15)
        ip = respuesta.read().decode().strip()
        print(f"  [OK] Conexion Tor activa. IP de salida: {ip}")
        return True
    except Exception:
        pass

    # Intentar sin proxy (por si Whonix o configuracion global)
    try:
        respuesta = urllib.request.urlopen('https://icanhazip.com', timeout=10)
        ip = respuesta.read().decode().strip()
        print(f"  [OK] Conexion a internet activa. IP: {ip}")
        print("  [AVISO] No se detecto proxy Tor local. Verifica la configuracion.")
        return True
    except Exception:
        print("  [ERROR] No se pudo verificar la conexion a Tor.")
        print("  Asegurate de que Tor este ejecutandose (puerto 9050).")
        print("  En Kali Linux: sudo systemctl start tor")
        print("  En Whonix: el Gateway enruta el trafico automaticamente.")
        return False


# ---------------------------------------------------------------------------
# Fases del pipeline
# ---------------------------------------------------------------------------

def ejecutar_fase1():
    """Ejecuta la Fase 1: Scraping de foros .onion."""
    # Parametros por defecto
    params = {
        "seeds": "seeds.txt",
        "keywords": "identifiers.txt",
        "max_depth": "2",
        "delay": "5",
        "timeout": "35",
        "network_mode": "local-tor",
        "csv_out": "../Datos/forum_records.csv",
        "max_retries": "3",
    }

    while True:
        print(SEPARADOR)
        print("  FASE 1: Scraping de Foros .onion")
        print(SEPARADOR)
        # Verificar conexion Tor antes de mostrar opciones
        if not verificar_tor():
            print("\n  [AVISO] Sin conexion Tor. Algunas funciones pueden no estar disponibles.")
            continuar = input("  Deseas continuar de todas formas? (s/n): ").strip().lower()
            if continuar != "s":
                return 0
        print(f"  Parametros actuales:")
        print(f"    seeds={params['seeds']}, depth={params['max_depth']}, "
              f"delay={params['delay']}s, red={params['network_mode']}")
        print()

        print("""
  Opciones:
    1. Ejecutar Scraper (recolectar posts)
    2. Ejecutar Preprocesador (limpiar datos)
    3. Ejecutar ambas (Scraper + Preprocesador)
    4. Configurar parametros del Scraper
    0. Volver
        """)

        opcion = input("  Selecciona una opcion: ").strip()

        if opcion == "1":
            return ejecutar_comando(
                f"python forum_scraper.py --seeds {params['seeds']} "
                f"--keywords {params['keywords']} "
                f"--max-depth {params['max_depth']} "
                f"--delay {params['delay']} "
                f"--timeout {params['timeout']} "
                f"--network-mode {params['network_mode']} "
                f"--max-retries {params['max_retries']} "
                f"--csv-out {params['csv_out']}",
                cwd=RUTA_FASE1,
            )
        elif opcion == "2":
            ruta_in = input(f"  CSV de entrada [{params['csv_out']}]: ").strip() or params['csv_out']
            ruta_out = input("  CSV de salida [../Datos/forum_records_clean.csv]: ").strip() or "../Datos/forum_records_clean.csv"
            return ejecutar_comando(
                f"python Preprocesador.py --input {ruta_in} --output {ruta_out}",
                cwd=RUTA_FASE1,
            )
        elif opcion == "3":
            codigo = ejecutar_comando(
                f"python forum_scraper.py --seeds {params['seeds']} "
                f"--keywords {params['keywords']} "
                f"--max-depth {params['max_depth']} "
                f"--delay {params['delay']} "
                f"--timeout {params['timeout']} "
                f"--network-mode {params['network_mode']} "
                f"--max-retries {params['max_retries']} "
                f"--csv-out {params['csv_out']}",
                cwd=RUTA_FASE1,
            )
            if codigo != 0:
                return codigo
            return ejecutar_comando(
                "python Preprocesador.py --input ../Datos/forum_records.csv "
                "--output ../Datos/forum_records_clean.csv",
                cwd=RUTA_FASE1,
            )
        elif opcion == "4":
            print("\n  Configurar parametros del Scraper:")
            print("  (presiona Enter para mantener el valor actual)\n")
            params["seeds"] = input(f"    Seeds [{params['seeds']}]: ").strip() or params['seeds']
            params["keywords"] = input(f"    Keywords [{params['keywords']}]: ").strip() or params['keywords']
            params["max_depth"] = input(f"    Max depth [{params['max_depth']}]: ").strip() or params['max_depth']
            params["delay"] = input(f"    Delay entre requests [{params['delay']}s]: ").strip() or params['delay']
            params["timeout"] = input(f"    Timeout [{params['timeout']}s]: ").strip() or params['timeout']
            params["network_mode"] = input(f"    Network mode (local-tor/whonix) [{params['network_mode']}]: ").strip() or params['network_mode']
            params["max_retries"] = input(f"    Max retries [{params['max_retries']}]: ").strip() or params['max_retries']
            params["csv_out"] = input(f"    CSV salida [{params['csv_out']}]: ").strip() or params['csv_out']
            print("\n  Parametros actualizados.\n")
        elif opcion == "0":
            return 0


def ejecutar_fase2():
    """Ejecuta la Fase 2: Analisis semantico NLP."""
    # Parametros por defecto
    params = {
        "input": "../Datos/forum_records_clean.csv",
        "output_csv": "../Datos/datos_enriquecidos.csv",
        "output_hmm": "../Datos/secuencias_autores.json",
        "mitre_mapping": "mitre_mapping.json",
    }

    while True:
        print(SEPARADOR)
        print("  FASE 2: Analisis Semantico con SecureBERT")
        print(SEPARADOR)
        print(f"  Parametros actuales:")
        print(f"    input={params['input']}")
        print(f"    output={params['output_csv']}")
        print()

        print("""
  Opciones:
    1. Ejecutar pipeline NLP completo
    2. Solo generar secuencias HMM (si ya existe datos_enriquecidos.csv)
    3. Configurar parametros
    0. Volver
        """)

        opcion = input("  Selecciona una opcion: ").strip()

        if opcion == "1":
            return ejecutar_comando(
                f"python modulos/main.py "
                f"--input {params['input']} "
                f"--output-csv {params['output_csv']} "
                f"--output-hmm {params['output_hmm']} "
                f"--mitre-mapping {params['mitre_mapping']}",
                cwd=RUTA_FASE2,
            )
        elif opcion == "2":
            return ejecutar_comando(
                f"python modulos/main.py "
                f"--input {params['input']} "
                f"--output-csv {params['output_csv']} "
                f"--output-hmm {params['output_hmm']} "
                f"--mitre-mapping {params['mitre_mapping']}",
                cwd=RUTA_FASE2,
            )
        elif opcion == "3":
            print("\n  Configurar parametros de Fase 2:")
            print("  (presiona Enter para mantener el valor actual)\n")
            params["input"] = input(f"    CSV entrada [{params['input']}]: ").strip() or params['input']
            params["output_csv"] = input(f"    CSV salida [{params['output_csv']}]: ").strip() or params['output_csv']
            params["output_hmm"] = input(f"    JSON HMM salida [{params['output_hmm']}]: ").strip() or params['output_hmm']
            params["mitre_mapping"] = input(f"    MITRE mapping [{params['mitre_mapping']}]: ").strip() or params['mitre_mapping']
            print("\n  Parametros actualizados.\n")
        elif opcion == "0":
            return 0


def ejecutar_fase3():
    """Ejecuta la Fase 3: Modelo HMM."""
    # Parametros por defecto
    params = {
        "input": "../Datos/secuencias_autores.json",
        "kill_chain": "../kill_chain_fases.json",
        "modelo": "../Datos/modelo_hmm.pkl",
        "reporte_csv": "../Datos/reporte_autores.csv",
        "n_estados": "4",
        "n_iter": "100",
    }

    while True:
        print(SEPARADOR)
        print("  FASE 3: Modelo HMM - Prediccion de Comportamiento")
        print(SEPARADOR)
        print(f"  Parametros actuales:")
        print(f"    estados={params['n_estados']}, iteraciones={params['n_iter']}")
        print(f"    modelo={params['modelo']}")
        print()

        print("""
  Opciones:
    1. Entrenar modelo HMM
    2. Re-entrenar forzado (ignorar modelo existente)
    3. Configurar parametros
    4. Lanzar dashboard_ia.py (Streamlit + IA)
    0. Volver
        """)

        opcion = input("  Selecciona una opcion: ").strip()

        if opcion == "1":
            return ejecutar_comando(
                f"python modulos/main.py "
                f"-i {params['input']} "
                f"-k {params['kill_chain']} "
                f"-m {params['modelo']} "
                f"-r {params['reporte_csv']} "
                f"-e {params['n_estados']} -n {params['n_iter']}",
                cwd=RUTA_FASE3,
            )
        elif opcion == "2":
            return ejecutar_comando(
                f"python modulos/main.py "
                f"-i {params['input']} "
                f"-k {params['kill_chain']} "
                f"-m {params['modelo']} "
                f"-r {params['reporte_csv']} "
                f"-e {params['n_estados']} -n {params['n_iter']} --retrain",
                cwd=RUTA_FASE3,
            )
        elif opcion == "3":
            print("\n  Configurar parametros de Fase 3:")
            print("  (presiona Enter para mantener el valor actual)\n")
            params["input"] = input(f"    JSON secuencias [{params['input']}]: ").strip() or params['input']
            params["kill_chain"] = input(f"    Kill Chain JSON [{params['kill_chain']}]: ").strip() or params['kill_chain']
            params["modelo"] = input(f"    Modelo salida [{params['modelo']}]: ").strip() or params['modelo']
            params["reporte_csv"] = input(f"    Reporte CSV [{params['reporte_csv']}]: ").strip() or params['reporte_csv']
            params["n_estados"] = input(f"    Estados ocultos [{params['n_estados']}]: ").strip() or params['n_estados']
            params["n_iter"] = input(f"    Iteraciones [{params['n_iter']}]: ").strip() or params['n_iter']
            print("\n  Parametros actualizados.\n")
        elif opcion == "4":
            print("\n  Abriendo dashboard_ia.py en el navegador...")
            print("  (Presiona Ctrl+C para detener el servidor)\n")
            subprocess.Popen(
                ["streamlit", "run", "dashboard_ia.py"],
                cwd=str(RUTA_FASE3),
            )
            return 0
        elif opcion == "0":
            return 0


def ejecutar_todo():
    """Ejecuta todas las fases en orden."""
    print(SEPARADOR)
    print("  EJECUTANDO PIPELINE COMPLETO (Fase 1 + 2 + 3)")
    print(SEPARADOR)

    print("""
  Este proceso ejecutara:
    Fase 1: Scraping + Preprocesamiento
    Fase 2: Analisis NLP con SecureBERT
    Fase 3: Entrenamiento HMM

  NOTA: La Fase 1 puede tardar mucho dependiendo de los seeds.
  Si ya tienes datos, ejecuta solo la Fase 2 y 3.

  Continuar? (s/n): """, end="")

    confirmar = input().strip().lower()
    if confirmar != "s":
        print("  Cancelado.\n")
        return 0

    # Fase 1
    print("\n--- FASE 1 ---\n")
    ejecutar_fase1()

    # Fase 2
    print("\n--- FASE 2 ---\n")
    ejecutar_fase2()

    # Fase 3
    print("\n--- FASE 3 ---\n")
    ejecutar_fase3()

    print(SEPARADOR)
    print("  PIPELINE COMPLETO FINALIZADO")
    print(SEPARADOR)
    return 0


# ---------------------------------------------------------------------------
# Menu interactivo
# ---------------------------------------------------------------------------

def menu_interactivo():
    """Muestra el menu interactivo principal."""
    while True:
        limpiar_pantalla()
        mostrar_titulo()
        verificar_archivos()

        print("  Menu principal:")
        print("  " + "-" * 40)
        print("  1. Ejecutar Fase 1 (Scraping)")
        print("  2. Ejecutar Fase 2 (Analisis NLP)")
        print("  3. Ejecutar Fase 3 (Modelo HMM)")
        print("  4. Ejecutar pipeline COMPLETO (1+2+3)")
        print("  5. Lanzar Dashboard IA (Fase 3)")
        print("  0. Salir")
        print("  " + "-" * 40)

        opcion = input("  Selecciona una opcion: ").strip()

        if opcion == "1":
            ejecutar_fase1()
            input("\n  Presiona Enter para continuar...")
        elif opcion == "2":
            ejecutar_fase2()
            input("\n  Presiona Enter para continuar...")
        elif opcion == "3":
            ejecutar_fase3()
            input("\n  Presiona Enter para continuar...")
        elif opcion == "4":
            ejecutar_todo()
            input("\n  Presiona Enter para continuar...")
        elif opcion == "5":
            print("\n  Abriendo dashboard_ia.py...")
            subprocess.Popen(
                ["streamlit", "run", "dashboard_ia.py"],
                cwd=str(RUTA_FASE3),
            )
            input("\n  Dashboard iniciado. Presiona Enter para volver al menu...")
        elif opcion == "0":
            print("\n  Saliendo...")
            break
        else:
            print("\n  Opcion no valida.")
            input("  Presiona Enter para continuar...")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ShadowMap - Ejecutor por Consola",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--fase", type=int, choices=[1, 2, 3],
        help="Ejecutar una fase especifica (1, 2 o 3)",
    )
    parser.add_argument(
        "--todo", action="store_true",
        help="Ejecutar todas las fases en orden",
    )
    parser.add_argument(
        "--dashboard", action="store_true",
        help="Lanzar el dashboard IA (Fase 3)",
    )

    args = parser.parse_args()

    if args.fase:
        if args.fase == 1:
            sys.exit(ejecutar_fase1())
        elif args.fase == 2:
            sys.exit(ejecutar_fase2())
        elif args.fase == 3:
            sys.exit(ejecutar_fase3())
    elif args.todo:
        sys.exit(ejecutar_todo())
    elif args.dashboard:
        subprocess.Popen(
            ["streamlit", "run", "dashboard_ia.py"],
            cwd=str(RUTA_FASE3),
        )
        sys.exit(0)
    else:
        menu_interactivo()


if __name__ == "__main__":
    main()