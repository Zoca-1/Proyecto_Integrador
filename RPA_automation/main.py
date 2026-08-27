"""Punto de entrada del RPA PeopleSync - Registro de Nuevo Ingreso.

Uso:
    python main.py                 # headless activado (por defecto)
    python main.py --no-headless   # abre Chrome visible
    python main.py --headless      # fuerza headless explicitamente

Pensado para ejecutarse sin intervencion manual (p. ej. via Windows Task
Scheduler): registra toda la actividad en un archivo de log ademas de
consola, y nunca requiere entrada interactiva del usuario.
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime

import config
from report_generator import ReportGenerator
from rpa_runner import PeopleSyncRPARunner


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RPA de registro de ingresos en PeopleSync HRIS.")
    parser.add_argument(
        "--headless",
        dest="headless",
        action=argparse.BooleanOptionalAction,
        default=config.HEADLESS_DEFAULT,
        help="Ejecuta Chrome en modo headless (por defecto: activado; recomendado para Task Scheduler).",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    logger = logging.getLogger("peoplesync_rpa")
    args = parse_args()

    logger.info("Iniciando proceso RPA PeopleSync (headless=%s).", args.headless)
    started_at = datetime.now()

    runner = PeopleSyncRPARunner(headless=args.headless)
    try:
        results = runner.run()
    except Exception:
        logger.exception("El proceso RPA fallo de forma irrecuperable antes de completar el lote.")
        return 1

    finished_at = datetime.now()

    report = ReportGenerator(results, started_at, finished_at)
    report.print_console_summary()
    report.to_excel()

    logger.info("Proceso finalizado. %d/%d registros cargados con exito.", len(report.exitosos), report.total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
