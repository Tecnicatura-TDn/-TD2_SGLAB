@echo off
setlocal
rem Ejecuta la instalacion del usuario actual, sin pedir elevacion.
set "SGLAB_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
set "SGLAB_DIR=%LOCALAPPDATA%\SGLAB"
if not exist "%SGLAB_PYTHON%" (
    echo No se encontro Python. Ejecuta primero Instalar-SGLAB.bat.
    pause
    exit /b 1
)
if not exist "%SGLAB_DIR%\cliente.json" (
    echo No se encontro la configuracion. Ejecuta primero Instalar-SGLAB.bat.
    pause
    exit /b 1
)
if not exist "%SGLAB_DIR%\client\ventana.py" (
    echo La instalacion del recolector esta incompleta. Revisa la carpeta SGLAB del usuario.
    pause
    exit /b 1
)
start "SGLAB" "%SGLAB_PYTHON%" "%SGLAB_DIR%\client\ventana.py" --config "%SGLAB_DIR%\cliente.json"
exit /b 0
