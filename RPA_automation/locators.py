"""Locadores del formulario PeopleSync ("Registro de Nuevo Ingreso").

Se centralizan aqui todos los selectores para que el resto del codigo
(page object, runner) no dependa de IDs/XPaths escritos a mano.
"""
from selenium.webdriver.common.by import By


class FormLocators:
    # Datos personales
    NOMBRES = (By.ID, "nombres")
    DNI = (By.ID, "dni")
    FECHA_NACIMIENTO = (By.ID, "fecha_nacimiento")
    GENERO = (By.ID, "genero")
    TELEFONO = (By.ID, "telefono")
    CORREO = (By.ID, "correo")

    # Datos laborales
    AREA = (By.ID, "area")
    PUESTO = (By.ID, "puesto")
    CONTRATO = (By.ID, "contrato")
    SEDE = (By.ID, "sede")
    FECHA_INGRESO = (By.ID, "fecha_ingreso")
    MODALIDAD_RADIOS = (By.CSS_SELECTOR, "input[name='modalidad']")
    MODALIDAD_RADIO_TPL = "//input[@name='modalidad' and @value='{value}']"

    # Acciones
    BTN_REGISTRAR = (By.ID, "btn-registrar")
    BTN_LIMPIAR = (By.XPATH, "//button[contains(@onclick, 'limpiarFormulario')]")

    # Feedback / verificacion
    ALERT = (By.ID, "alert")
    ALERT_TITLE = (By.ID, "alert-title")
    ALERT_MSG = (By.ID, "alert-msg")
    COUNTER = (By.ID, "counter")
    TABLA_FILAS = (By.CSS_SELECTOR, "#tabla-body tr")
    FIELD_ERRORS_VISIBLE = (By.CSS_SELECTOR, ".field-error.show")
