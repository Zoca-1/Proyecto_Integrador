#Proyecto Integrador

#1. RPA automation ---PeopleSync Income Registration

# La logica completa vive en modulos separados y reutilizables:
#   config.py           -> URLs, rutas de salida y tiempos de espera
#   locators.py          -> selectores del formulario (By.ID / By.XPATH)
#   data_loader.py        -> lectura del dataset (Google Sheets) y validacion de datos
#   peoplesync_page.py     -> Page Object: interaccion Selenium con el formulario
#   rpa_runner.py          -> orquestacion del lote de 50 registros
#   report_generator.py    -> resumen en consola + reporte Excel
#
# Este archivo es el punto de entrada original del proyecto y delega en
# main.py. Ejecutar: python RPA_automation.py [--headless | --no-headless]

from main import main

print("Librerías importadas correctamente. El entorno está listo.")

if __name__ == "__main__":
    raise SystemExit(main())
