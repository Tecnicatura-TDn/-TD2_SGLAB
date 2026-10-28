@echo off
setlocal
rem Copiar toda la carpeta client. No solicita elevacion de administrador.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\instalar-cliente.ps1"
if errorlevel 1 pause
endlocal
