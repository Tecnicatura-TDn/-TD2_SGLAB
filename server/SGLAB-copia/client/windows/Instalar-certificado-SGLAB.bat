@echo off
setlocal
title Certificado HTTPS de SGLAB
rem Se distribuye junto al certificado publico y su instalador PowerShell.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar-certificado.ps1"
set "sglab_cert_exit=%errorlevel%"
echo.
pause
exit /b %sglab_cert_exit%
