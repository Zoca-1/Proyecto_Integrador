"""Configuracion central del proceso RPA PeopleSync.

Centraliza URLs, rutas de salida y tiempos de espera para evitar
valores fijos (hardcoding) dispersos por los demas modulos.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

FORM_URL = "https://the-paul2002.github.io/Proyecto-IA-/Homework1/"

SHEET_ID = "1EjaoSJKdzdUBNF3XJZuTlxA21D-0vy0wkGaMR8wHVgs"
DATASET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

REPORT_PATH = BASE_DIR / "reporte_ejecucion_peoplesync.xlsx"
LOG_PATH = BASE_DIR / "rpa_execution.log"

DEFAULT_TIMEOUT = 10        # segundos para esperas estandar (WebDriverWait)
SUBMIT_RESULT_TIMEOUT = 8   # segundos esperando confirmacion tras enviar el formulario

# Headless activado por defecto: apto para ejecucion desatendida via
# Windows Task Scheduler. Puede sobreescribirse con --headless/--no-headless.
HEADLESS_DEFAULT = True

MAX_RECORDS = 50
