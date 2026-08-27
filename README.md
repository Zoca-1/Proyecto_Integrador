# Proyecto Integrador: RPA Automation, SUNAT Scraper & Lichess API

Repositorio consolidado que integra soluciones de automatización de procesos robóticos (RPA), scraping de datos financieros y análisis cuantitativo de APIs deportivas en Python.

---

## Tabla de Contenidos
1. [PeopleSync RPA Automation](#1-peoplesync-rpa-automation--income-registration)
2. [SUNAT Exchange Rate Web Scraper](#2-sunat-exchange-rate-web-scraper)
3. [Lichess Data Science & Tournament Automation](#3-lichess-data-science--tournament-automation)

---

## Instalación General del Repositorio

Clona el repositorio e ingresa al directorio raíz antes de trabajar en cualquiera de los módulos:

git clone https://github.com/Zoca-1/Proyecto_Integrador.git
cd Proyecto_Integrador

---

### 1. PeopleSync RPA Automation — Income Registration
Sistema de automatización de procesos robóticos (RPA) en Python con Selenium diseñado para procesar el registro masivo de personal desde Google Sheets e interactuar de forma autónoma con el formulario web PeopleSync.

# Requisitos Previos
Python 3.10+

Google Chrome (el driver chromedriver es gestionado automáticamente por el proyecto).

# Configuración e Instalación

# 1. Clonar el repositorio y navegar a la carpeta RPA
git clone [https://github.com/Zoca-1/Proyecto_Integrador.git](https://github.com/Zoca-1/Proyecto_Integrador.git)
cd Proyecto_Integrador/RPA_automation

# 2. Crear y activar el entorno virtual (PowerShell)
python -m venv env_hw2
.\env_hw2\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt

# Instrucciones de Ejecución
Ejecución Manual desde Consola

python RPA_automation.py
Nota sobre el modo Headless: Por defecto, el proyecto ejecuta el navegador en segundo plano (HEADLESS_DEFAULT = True en config.py). Para visualizar la automatización en pantalla, cambia el parámetro a False o ajústalo al instanciar el ejecutable.

# Ejecución Desatendida (Windows Task Scheduler)
El proyecto incluye el archivo run_rpa.bat diseñado para integrarse con el Programador de Tareas de Windows:

Abre el Programador de tareas (taskschd.msc).

Haz clic en Crear tarea básica -->

Asigna un nombre (ej. RPA_PeopleSync) y define la frecuencia (ej. Diariamente).

En Acción, selecciona Iniciar un programa.

Configura los parámetros:
Programa o script: Ruta absoluta de run_rpa.bat (ej. C:\Ruta\A\Tu\Proyecto\RPA_automation\run_rpa.bat).

Iniciar en (opcional): Ruta absoluta del directorio raíz de la subcarpeta (ej. C:\Ruta\A\Tu\Proyecto\RPA_automation).

# Archivos de Salida Generados
reporte_ejecucion_peoplesync.xlsx: Hoja de cálculo con el resumen de los 50 registros procesados, especificando el estado (EXITO / FALLIDO) y el motivo exacto de omisión.

rpa_execution.log: Bitácora técnica de logs que sirve como evidencia del flujo, registrando las advertencias (WARNING) de registros incompatibles y la confirmación de envíos (INFO).

---

### 2. SUNAT Exchange Rate Web Scraper
Bot automatizado en Python para la extracción, estructuración y consolidación diaria de las tasas de cambio oficiales (Compra y Venta) publicadas por la SUNAT (Superintendencia Nacional de Aduanas y de Administración Tributaria del Perú).

# Descripción del Proyecto
El script realiza web scraping sobre el portal oficial de la SUNAT utilizando Selenium para simular la navegación en contexto real de navegador y ejecutar peticiones directas al endpoint dinámico de la entidad. Construye un calendario continuo desde Enero de 2024 hasta el mes actual, manejando adecuadamente los vacíos de datos correspondientes a fines de semana, feriados o días sin publicación oficial (NaN).

Está diseñado para ejecutarse de forma autónoma y desatendida en segundo plano mediante el Programador de Tareas de Windows (Task Scheduler).

# Tecnologías Utilizadas
Python 3.x
Selenium (Navegación web en modo headless)
Pandas (Tratamiento, limpieza y consolidación de series de tiempo)
OpenPyXL (Exportación de reportes en formato Excel)
Windows Batch (.bat) (Automatización de tareas programadas)

# Estructura del Proyecto

SUNAT_scraper/
├── data/
│   ├── tipo_cambio_sunat_2024_actual.csv
│   └── tipo_cambio_sunat_2024_actual.xlsx
├── requirements.txt
├── run_sunat_scraper.bat
├── scraper.log
└── sunat_scraper.py

# Instalación y Uso Local

# 1. Navegar a la subcarpeta del scraper
cd Proyecto_Integrador/SUNAT_scraper

# 2. Crear y activar entorno virtual
python -m venv env
.\env\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecución manual
python sunat_scraper.py

# Automatización en Windows Task Scheduler
Abre el Programador de Tareas (taskschd.msc).

Crea una nueva tarea asignando un nombre (ej. Scraper SUNAT).

En Desencadenadores, define el horario diario de ejecución.

En Acciones:

Acción: Iniciar un programa

Programa o script: Selecciona la ruta de tu archivo run_sunat_scraper.bat.

Iniciar en (opcional): Pega la ruta de la carpeta SUNAT_scraper (sin comillas y sin barra final \).

En Condiciones, permitir la ejecución con cualquier conexión de red activa.

---

### 3. Lichess Data Science & Tournament Automation Project
Consiste en la integración con la API pública de Lichess para la extracción, análisis estadístico y visualización de datos de partidas de ajedrez, así como la automatización segura de creación de torneos.

# Tecnologías Utilizadas
Python 3.10+
Pandas: Procesamiento, limpieza y estructuración de datos.
Matplotlib: Generación de gráficos y dashboard estático.

Requests: Consumo de la API REST / NDJSON de Lichess.
python-dotenv: Manejo seguro de variables de entorno y claves de API.

# Estructura del Proyecto
part_a_game_analysis.py: Extrae partidas vía streaming (NDJSON), procesa los datos con Pandas, calcula métricas de rendimiento y genera un dashboard con Matplotlib.
part_b_tournament_automation.py: Evalúa un calendario semanal de eventos, valida reglas de negocio (fechas/horarios) y simula (DRY_RUN) o crea torneos en Lichess usando peticiones HTTP POST autenticadas.
games_data.csv: Dataset generado con el registro detallado de las partidas descargadas.
game_statistics.csv: Resumen estadístico procesado (distribución de victorias, derrotas, empates y variación de rating).
lichess_analysis.png: Dashboard gráfico exportado con las visualizaciones del análisis.
.env.example: Plantilla de configuración para la variable del token de la API de Lichess.

# Requisitos Previos e Instalación

# 1. Navegar a la subcarpeta de Lichess
cd Proyecto_Integrador/LICHESS_API

# 2. Activar entorno virtual e instalar dependencias
.\env\Scripts\Activate.ps1
pip install -r requirements.txt

# Configuración de Credenciales
Crea una copia del archivo .env.example y nómbralo .env:

PowerShell
Copy-Item .env.example .env
Genera tu token personal en Lichess API Tokens con los permisos de tournament:write.

Edita el archivo .env agregando tu token:

Fragmento de código
LICHESS_API_TOKEN=lip_PegaTuTokenAqui

# Ejecución del Proyecto
# Parte A: Extracción y Análisis de Partidas

python part_a_game_analysis.py
Resultado: Descarga las partidas del usuario configurado y genera automáticamente games_data.csv, game_statistics.csv y la imagen lichess_analysis.png.

# Parte B: Automatización de Torneos

python part_b_tournament_automation.py
Resultado: Por defecto corre en modo simulación (DRY_RUN = True), validando el calendario y descartando torneos pasados sin afectar la API en producción. Para publicar torneos reales, modifica a DRY_RUN = False dentro del script.





