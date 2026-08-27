"""Orquestador del proceso RPA: recorre el dataset y opera el formulario."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import config
from data_loader import DatasetLoader, EmployeeRecord
from locators import FormLocators as L
from peoplesync_page import PeopleSyncFormPage

logger = logging.getLogger("peoplesync_rpa")

_COMPATIBILITY_FIELDS = ("genero", "area", "puesto", "contrato", "sede", "modalidad")


@dataclass
class RecordResult:
    row_number: int
    dni: str
    apellidos_nombres: str
    status: str  # "EXITO" | "FALLIDO"
    motivo: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class PeopleSyncRPARunner:
    """Abre el navegador una sola vez y procesa los 50 registros del dataset."""

    def __init__(self, headless: bool = config.HEADLESS_DEFAULT):
        self._headless = headless
        self._driver: Optional[webdriver.Chrome] = None
        self._page: Optional[PeopleSyncFormPage] = None
        self._vocab: dict[str, list[str]] = {}

    # ------------------------------------------------------------------ #
    # Ciclo de vida del navegador
    # ------------------------------------------------------------------ #
    def _build_driver(self) -> webdriver.Chrome:
        options = Options()
        if self._headless:
            options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-notifications")
        options.add_argument("--log-level=3")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def _load_vocabulary(self) -> None:
        """Lee del DOM en vivo las opciones validas de cada campo (sin hardcodear listas)."""
        self._vocab = {
            "genero": self._page.get_select_options(L.GENERO),
            "area": self._page.get_select_options(L.AREA),
            "puesto": self._page.get_select_options(L.PUESTO),
            "contrato": self._page.get_select_options(L.CONTRATO),
            "sede": self._page.get_select_options(L.SEDE),
            "modalidad": self._page.get_radio_values(L.MODALIDAD_RADIOS),
        }
        logger.info("Vocabulario del formulario cargado: %s", {k: len(v) for k, v in self._vocab.items()})

    def _check_compatibility(self, record: EmployeeRecord) -> list[str]:
        errors = []
        for campo in _COMPATIBILITY_FIELDS:
            valor = getattr(record, campo)
            permitidos = self._vocab.get(campo, [])
            if valor not in permitidos:
                errors.append(
                    f"El valor '{valor}' del campo '{campo}' no esta entre las opciones "
                    f"disponibles en el formulario."
                )
        return errors

    # ------------------------------------------------------------------ #
    # Ejecucion principal
    # ------------------------------------------------------------------ #
    def run(self) -> list[RecordResult]:
        records = DatasetLoader(config.DATASET_CSV_URL).load()
        logger.info("Dataset cargado: %d registros.", len(records))

        results: list[RecordResult] = []
        self._driver = self._build_driver()
        try:
            self._page = PeopleSyncFormPage(self._driver)
            self._page.open()  # unica carga completa de la pagina
            self._load_vocabulary()

            for record in records:
                results.append(self._process_record(record))
        finally:
            if self._driver:
                self._driver.quit()

        return results

    def _process_record(self, record: EmployeeRecord) -> RecordResult:
        base = dict(row_number=record.row_number, dni=record.dni, apellidos_nombres=record.apellidos_nombres)

        format_errors = record.validate()
        if format_errors:
            motivo = " | ".join(format_errors)
            logger.warning("Registro %s omitido (datos inconsistentes): %s", record.record_id, motivo)
            return RecordResult(**base, status="FALLIDO", motivo=motivo)

        compat_errors = self._check_compatibility(record)
        if compat_errors:
            motivo = " | ".join(compat_errors)
            logger.warning("Registro %s omitido (incompatible con el formulario): %s", record.record_id, motivo)
            return RecordResult(**base, status="FALLIDO", motivo=motivo)

        try:
            self._page.fill_record(record)
            outcome = self._page.submit_and_verify(record.dni)
            if outcome.success:
                logger.info(
                    "Registro %s cargado con exito (total acumulado: %s).",
                    record.record_id, outcome.total_registros,
                )
                return RecordResult(**base, status="EXITO")

            logger.warning("Registro %s fallo al enviarse: %s", record.record_id, outcome.reason)
            self._safe_reset()
            return RecordResult(**base, status="FALLIDO", motivo=outcome.reason or "Fallo no especificado en el envio.")
        except Exception as exc:  # noqa: BLE001 - no debe detener el lote por un fallo individual
            logger.exception("Error inesperado procesando el registro %s", record.record_id)
            self._safe_reset()
            return RecordResult(**base, status="FALLIDO", motivo=f"Error inesperado durante el llenado/envio: {exc}")

    def _safe_reset(self) -> None:
        try:
            self._page.reset_form()
        except Exception:
            logger.exception("No se pudo limpiar el formulario tras un fallo; se continua de todas formas.")
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = PeopleSyncRPARunner(headless=False)
    results = runner.run()
import csv

if __name__ == "__main__":
    # 1. Guardar todos los logs en un archivo de texto 'ejecucion_rpa.log'
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("ejecucion_rpa.log", encoding="utf-8"), # Archivo guardado
            logging.StreamHandler()                                     # Salida en consola
        ]
    )

    runner = PeopleSyncRPARunner(headless=False)
    resultados = runner.run()

    # 2. Exportar la tabla de resultados a 'reporte_resultados.csv'
    with open("reporte_resultados.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Fila", "DNI", "Apellidos y Nombres", "Estado", "Motivo", "Timestamp"])
        for r in resultados:
            writer.writerow([r.row_number, r.dni, r.apellidos_nombres, r.status, r.motivo, r.timestamp])

    print("\nArchivos 'ejecucion_rpa.log' y 'reporte_resultados.csv' generados con éxito.")

