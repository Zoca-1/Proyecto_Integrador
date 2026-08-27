"""Generacion del reporte de ejecucion (consola + Excel)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Sequence

import pandas as pd
from openpyxl.utils import get_column_letter

import config
from rpa_runner import RecordResult

logger = logging.getLogger("peoplesync_rpa")


class ReportGenerator:
    def __init__(self, results: Sequence[RecordResult], started_at: datetime, finished_at: datetime):
        self._results = list(results)
        self._started_at = started_at
        self._finished_at = finished_at

    @property
    def total(self) -> int:
        return len(self._results)

    @property
    def exitosos(self) -> list[RecordResult]:
        return [r for r in self._results if r.status == "EXITO"]

    @property
    def fallidos(self) -> list[RecordResult]:
        return [r for r in self._results if r.status == "FALLIDO"]

    # ------------------------------------------------------------------ #
    # Consola
    # ------------------------------------------------------------------ #
    def print_console_summary(self) -> None:
        exitosos, fallidos = self.exitosos, self.fallidos
        duracion = (self._finished_at - self._started_at).total_seconds()

        print("\n" + "=" * 70)
        print("RESUMEN DE EJECUCION - PeopleSync RPA (Registro de Ingresos)")
        print("=" * 70)
        print(f"Total de registros procesados : {self.total}")
        print(f"Cargados con exito            : {len(exitosos)}")
        print(f"No cargados                   : {len(fallidos)}")
        print(f"Duracion total                 : {duracion:.1f} s")
        print("=" * 70)

        if fallidos:
            print("\nDetalle de registros fallidos:")
            for r in fallidos:
                print(f"  - [Fila {r.row_number} | DNI {r.dni}] {r.apellidos_nombres}: {r.motivo}")
        print()

    # ------------------------------------------------------------------ #
    # Excel
    # ------------------------------------------------------------------ #
    def to_excel(self, path=config.REPORT_PATH) -> None:
        pct_exito = f"{(len(self.exitosos) / self.total * 100):.1f}%" if self.total else "0.0%"

        resumen_df = pd.DataFrame(
            {
                "Metrica": [
                    "Fecha y hora de inicio",
                    "Fecha y hora de fin",
                    "Duracion (s)",
                    "Total procesados",
                    "Cargados con exito",
                    "No cargados",
                    "% de exito",
                ],
                "Valor": [
                    self._started_at.strftime("%Y-%m-%d %H:%M:%S"),
                    self._finished_at.strftime("%Y-%m-%d %H:%M:%S"),
                    round((self._finished_at - self._started_at).total_seconds(), 1),
                    self.total,
                    len(self.exitosos),
                    len(self.fallidos),
                    pct_exito,
                ],
            }
        )

        detalle_df = pd.DataFrame(
            [
                {
                    "Fila": r.row_number,
                    "DNI": r.dni,
                    "Apellidos y Nombres": r.apellidos_nombres,
                    "Estado": r.status,
                    "Motivo": r.motivo,
                    "Marca de tiempo": r.timestamp,
                }
                for r in self._results
            ]
        )

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            resumen_df.to_excel(writer, sheet_name="Resumen", index=False)
            detalle_df.to_excel(writer, sheet_name="Detalle", index=False)
            self._autosize(writer, "Resumen", resumen_df)
            self._autosize(writer, "Detalle", detalle_df)

        logger.info("Reporte Excel generado en: %s", path)

    @staticmethod
    def _autosize(writer: pd.ExcelWriter, sheet_name: str, df: pd.DataFrame) -> None:
        ws = writer.sheets[sheet_name]
        for idx, col in enumerate(df.columns, start=1):
            if len(df):
                max_len = max(len(str(col)), max(len(str(v)) for v in df[col]))
            else:
                max_len = len(str(col))
            ws.column_dimensions[get_column_letter(idx)].width = min(max_len + 3, 60)
