"""Carga y validacion de los datos de entrada (dataset de colaboradores)."""
from __future__ import annotations

import re
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Optional

import pandas as pd

DNI_RE = re.compile(r"^\d{8}$")
TELEFONO_RE = re.compile(r"^9\d{8}$")
CORREO_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d")


@dataclass
class EmployeeRecord:
    row_number: int
    apellidos_nombres: str
    dni: str
    fecha_nacimiento: str
    genero: str
    telefono: str
    correo: str
    area: str
    puesto: str
    contrato: str
    sede: str
    fecha_ingreso: str
    modalidad: str

    @property
    def record_id(self) -> str:
        return self.dni or f"fila-{self.row_number}"

    def validate(self) -> list[str]:
        """Valida formato/consistencia de los datos, independientemente del formulario."""
        errors: list[str] = []

        if not self.apellidos_nombres.strip():
            errors.append("El campo 'apellidos_nombres' esta vacio.")
        if not DNI_RE.match(self.dni or ""):
            errors.append(f"DNI '{self.dni}' no tiene el formato de 8 digitos numericos.")
        if not TELEFONO_RE.match(self.telefono or ""):
            errors.append(f"Telefono '{self.telefono}' no cumple el formato 9XXXXXXXX.")
        if not CORREO_RE.match(self.correo or ""):
            errors.append(f"Correo '{self.correo}' no tiene un formato valido.")
        if self.fecha_nacimiento_iso is None:
            errors.append(f"Fecha de nacimiento '{self.fecha_nacimiento}' no es una fecha valida.")
        if self.fecha_ingreso_iso is None:
            errors.append(f"Fecha de ingreso '{self.fecha_ingreso}' no es una fecha valida.")
        for campo in ("genero", "area", "puesto", "contrato", "sede", "modalidad"):
            if not str(getattr(self, campo, "")).strip():
                errors.append(f"El campo '{campo}' esta vacio.")

        return errors

    @staticmethod
    def _to_iso(value: str) -> Optional[str]:
        if not value:
            return None
        value = value.strip()
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @property
    def fecha_nacimiento_iso(self) -> Optional[str]:
        return self._to_iso(self.fecha_nacimiento)

    @property
    def fecha_ingreso_iso(self) -> Optional[str]:
        return self._to_iso(self.fecha_ingreso)


class DatasetLoader:
    """Lee el dataset de colaboradores publicado en Google Sheets (export CSV)."""

    EXPECTED_COLUMNS = [f.name for f in fields(EmployeeRecord) if f.name != "row_number"]

    def __init__(self, csv_url: str):
        self._csv_url = csv_url

    def load(self) -> list[EmployeeRecord]:
        df = pd.read_csv(self._csv_url, dtype=str, keep_default_na=False)

        missing = set(self.EXPECTED_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"El dataset no contiene las columnas esperadas: {sorted(missing)}")

        records: list[EmployeeRecord] = []
        for i, row in enumerate(df.to_dict(orient="records"), start=1):
            records.append(
                EmployeeRecord(row_number=i, **{col: row[col] for col in self.EXPECTED_COLUMNS})
            )
        return records
