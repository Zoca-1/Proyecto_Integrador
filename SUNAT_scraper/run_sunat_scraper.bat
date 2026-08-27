@echo off
REM =====================================================================
REM Lanzador del scraper de Tipo de Cambio SUNAT para el Programador de
REM Tareas de Windows. Funciona sin importar el directorio de trabajo
REM desde el que lo invoque el Programador de Tareas.
REM =====================================================================

setlocal

REM %~dp0 = carpeta donde reside este .bat (con backslash final)
set "PROJECT_DIR=%~dp0"
set "VENV_PYTHON=%PROJECT_DIR%env\Scripts\python.exe"

pushd "%PROJECT_DIR%"

if exist "%VENV_PYTHON%" (
    "%VENV_PYTHON%" "%PROJECT_DIR%sunat_scraper.py" %*
) else (
    python "%PROJECT_DIR%sunat_scraper.py" %*
)

set "EXIT_CODE=%ERRORLEVEL%"

popd
endlocal & exit /b %EXIT_CODE%
