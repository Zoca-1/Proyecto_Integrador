"""
Scraper del Tipo de Cambio Oficial SUNAT (Compra/Venta).

Fuente: https://e-consulta.sunat.gob.pe/cl-at-ittipcam/tcS01Alias

La pagina renderiza los datos via una llamada AJAX (POST JSON) a
`/cl-at-ittipcam/tcS01Alias/listarTipoCambio`, protegida en apariencia por
reCAPTCHA v3. Sin embargo el propio JS de SUNAT (sunatrecaptcha3.js) reemplaza
`window.grecaptcha` por un stub que genera un token aleatorio en el cliente y
lo resuelve de inmediato, sin validacion real contra Google. Por ello el
scraper usa Selenium para cargar la pagina real (misma sesion/cookies que un
navegador legitimo) y ejecuta esa misma llamada AJAX dentro del contexto del
navegador via `execute_async_script`, en vez de parsear el widget de
calendario del DOM (mucho mas fragil).

Uso:
    python sunat_scraper.py
    python sunat_scraper.py --start-year 2024 --start-month 1 --end-year 2026 --end-month 8
    python sunat_scraper.py --no-headless   (para depurar visualmente)
"""

import argparse
import calendar
import logging
import random
import sys
import time
from datetime import date, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

BASE_DIR = Path(__file__).resolve().parent

BASE_URL = "https://e-consulta.sunat.gob.pe/cl-at-ittipcam/tcS01Alias"
CONTEXT_APP = "/cl-at-ittipcam"

PAGE_LOAD_TIMEOUT = 30
SCRIPT_TIMEOUT = 30
MAX_RETRIES_PER_MONTH = 3

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Ejecutado dentro del navegador: reutiliza $ (jQuery), grecaptcha (stub de
# SUNAT) y CONTEXT_APP tal como lo hace papeleta.js en la pagina original.
AJAX_SCRIPT = """
const anio = arguments[0];
const mes = arguments[1];
const done = arguments[2];

function llamar(token) {
    const params = JSON.stringify({anio: anio, mes: mes, token: token});
    $.ajax({
        type: "POST",
        url: CONTEXT_APP + "/tcS01Alias/listarTipoCambio",
        dataType: "json",
        data: params,
        contentType: "application/json; charset=utf-8",
        success: function (resultado) {
            done({ok: true, data: resultado});
        },
        error: function (xhr, status, err) {
            done({ok: false, error: status + ": " + err, httpStatus: xhr.status});
        }
    });
}

try {
    if (typeof grecaptcha === "undefined" || typeof $ === "undefined") {
        done({ok: false, error: "jQuery/grecaptcha no disponibles en la pagina"});
    } else {
        grecaptcha.ready(function () {
            grecaptcha
                .execute(typeof site_key_sunat !== "undefined" ? site_key_sunat : "", {action: "token"})
                .then(llamar)
                .catch(function (e) { done({ok: false, error: String(e)}); });
        });
    }
} catch (e) {
    done({ok: false, error: String(e)});
}
"""


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("sunat_scraper")
    logger.setLevel(logging.DEBUG)

    log_path = BASE_DIR / "scraper.log"
    file_handler = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(fmt)
    console_handler.setFormatter(fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def parse_args() -> argparse.Namespace:
    today = date.today()
    parser = argparse.ArgumentParser(
        description="Scraper del Tipo de Cambio Oficial SUNAT (Compra/Venta)."
    )
    parser.add_argument("--start-year", type=int, default=2024, help="Anio de inicio (default: 2024)")
    parser.add_argument("--start-month", type=int, default=1, help="Mes de inicio, 1-12 (default: 1)")
    parser.add_argument("--end-year", type=int, default=today.year, help="Anio de fin (default: anio actual)")
    parser.add_argument("--end-month", type=int, default=today.month, help="Mes de fin, 1-12 (default: mes actual)")
    parser.add_argument(
        "--output-dir", type=str, default="data", help="Carpeta de salida relativa al script (default: data)"
    )
    parser.add_argument(
        "--output-name",
        type=str,
        default="tipo_cambio_sunat_2024_actual",
        help="Nombre base (sin extension) de los archivos CSV/XLSX de salida",
    )
    parser.add_argument("--min-delay", type=float, default=1.5, help="Retardo minimo entre meses, en segundos")
    parser.add_argument("--max-delay", type=float, default=3.5, help="Retardo maximo entre meses, en segundos")
    parser.add_argument(
        "--no-headless", action="store_true", help="Desactiva el modo headless (util para depurar)"
    )
    return parser.parse_args()


def month_range(start_year: int, start_month: int, end_year: int, end_month: int):
    """Genera tuplas (anio, mes 1-indexado) desde el inicio hasta el fin, inclusive."""
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def build_driver(headless: bool, logger: logging.Logger) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--log-level=3")
    options.add_argument(f"user-agent={USER_AGENT}")

    logger.debug("Resolviendo chromedriver via webdriver-manager...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    driver.set_script_timeout(SCRIPT_TIMEOUT)
    return driver


def load_base_page(driver: webdriver.Chrome, logger: logging.Logger) -> None:
    logger.info(f"Cargando pagina base: {BASE_URL}")
    driver.get(BASE_URL)

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "fecAsistenciaBusq"))
    )
    WebDriverWait(driver, 20).until(
        lambda d: d.execute_script(
            "return typeof jQuery !== 'undefined' && typeof grecaptcha !== 'undefined';"
        )
    )
    logger.info("Pagina base cargada y librerias JS (jQuery/grecaptcha) listas.")


def fetch_month(
    driver: webdriver.Chrome, year: int, month_1idx: int, logger: logging.Logger
) -> list[dict]:
    """Devuelve la lista cruda de registros {fecPublica, valTipo, codTipo} para un mes."""
    month_0idx = month_1idx - 1  # la API de SUNAT espera el mes 0-indexado (0=enero)

    last_error = None
    for attempt in range(1, MAX_RETRIES_PER_MONTH + 1):
        try:
            result = driver.execute_async_script(AJAX_SCRIPT, year, month_0idx)
            if result.get("ok"):
                data = result.get("data") or []
                logger.info(f"{year}-{month_1idx:02d}: {len(data)} registros obtenidos.")
                return data
            last_error = result.get("error", "error desconocido")
            logger.warning(
                f"{year}-{month_1idx:02d}: intento {attempt}/{MAX_RETRIES_PER_MONTH} fallido -> {last_error}"
            )
        except Exception as exc:  # timeout de script, driver caido, etc.
            last_error = str(exc)
            logger.warning(
                f"{year}-{month_1idx:02d}: intento {attempt}/{MAX_RETRIES_PER_MONTH} con excepcion -> {last_error}"
            )
        time.sleep(2)

    logger.error(f"{year}-{month_1idx:02d}: sin datos tras {MAX_RETRIES_PER_MONTH} intentos ({last_error}).")
    return []


def records_to_daily_map(records: list[dict]) -> dict:
    """Convierte los registros crudos {fecPublica: DD/MM/YYYY, codTipo: C/V, valTipo} a
    un dict {date: {"Tipo_Compra": float, "Tipo_Venta": float}}."""
    daily = {}
    for rec in records:
        try:
            fecha = datetime.strptime(rec["fecPublica"], "%d/%m/%Y").date()
            valor = float(rec["valTipo"])
        except (KeyError, ValueError, TypeError):
            continue

        entry = daily.setdefault(fecha, {"Tipo_Compra": None, "Tipo_Venta": None})
        if rec.get("codTipo") == "C":
            entry["Tipo_Compra"] = valor
        elif rec.get("codTipo") == "V":
            entry["Tipo_Venta"] = valor
    return daily


def build_calendar_dataframe(
    daily_data: dict, start_year: int, start_month: int, end_year: int, end_month: int
) -> pd.DataFrame:
    """Proyecta los datos scrapeados sobre un calendario continuo dia a dia;
    fines de semana/feriados/dias sin publicacion quedan como NaN."""
    range_start = date(start_year, start_month, 1)
    last_day = calendar.monthrange(end_year, end_month)[1]
    range_end = date(end_year, end_month, last_day)

    all_days = pd.date_range(start=range_start, end=range_end, freq="D")
    df = pd.DataFrame({"Fecha": all_days})
    df["Tipo_Compra"] = df["Fecha"].dt.date.map(lambda d: daily_data.get(d, {}).get("Tipo_Compra"))
    df["Tipo_Venta"] = df["Fecha"].dt.date.map(lambda d: daily_data.get(d, {}).get("Tipo_Venta"))
    df["Fecha"] = df["Fecha"].dt.strftime("%Y-%m-%d")
    return df


def save_outputs(df: pd.DataFrame, output_dir: Path, output_name: str, logger: logging.Logger) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{output_name}.csv"
    xlsx_path = output_dir / f"{output_name}.xlsx"

    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_excel(xlsx_path, index=False, engine="openpyxl")

    logger.info(f"CSV guardado en:  {csv_path}")
    logger.info(f"Excel guardado en: {xlsx_path}")


def main() -> int:
    args = parse_args()
    logger = setup_logging()

    if (args.start_year, args.start_month) > (args.end_year, args.end_month):
        logger.error("El rango de fechas es invalido: el inicio es posterior al fin.")
        return 1

    logger.info("=" * 70)
    logger.info("Iniciando scraper de Tipo de Cambio SUNAT")
    logger.info(
        f"Rango: {args.start_year}-{args.start_month:02d} -> {args.end_year}-{args.end_month:02d}"
    )

    driver = None
    daily_data: dict = {}
    months = list(month_range(args.start_year, args.start_month, args.end_year, args.end_month))

    try:
        driver = build_driver(headless=not args.no_headless, logger=logger)
        load_base_page(driver, logger)

        for idx, (year, month) in enumerate(months):
            records = fetch_month(driver, year, month, logger)
            daily_data.update(records_to_daily_map(records))

            if idx < len(months) - 1:
                delay = random.uniform(args.min_delay, args.max_delay)
                logger.debug(f"Esperando {delay:.2f}s antes del siguiente mes...")
                time.sleep(delay)

        df = build_calendar_dataframe(
            daily_data, args.start_year, args.start_month, args.end_year, args.end_month
        )
        output_dir = (BASE_DIR / args.output_dir).resolve()
        save_outputs(df, output_dir, args.output_name, logger)

        published_days = df["Tipo_Compra"].notna().sum()
        logger.info(
            f"Proceso finalizado. {len(df)} dias en calendario, {published_days} con tipo de cambio publicado."
        )
        return 0

    except Exception:
        logger.exception("Error fatal durante la ejecucion del scraper.")
        return 1

    finally:
        if driver is not None:
            try:
                driver.quit()
                logger.info("WebDriver cerrado correctamente.")
            except Exception:
                logger.exception("Error al cerrar el WebDriver.")


if __name__ == "__main__":
    sys.exit(main())
