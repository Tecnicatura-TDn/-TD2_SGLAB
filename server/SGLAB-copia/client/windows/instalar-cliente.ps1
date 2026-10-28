# Lanzador interactivo utilizado por client/Instalar-SGLAB.bat.
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
try {
    Write-Host '=== Instalacion del cliente SGLAB ==='
    Write-Host 'Se instalara Python si falta y luego se configurara esta PC.'
    & (Join-Path $PSScriptRoot 'instalar-python.ps1')
    $Python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
    if (-not (Test-Path -LiteralPath $Python)) { throw 'No se encontro Python.' }

    $env:Path += ';' + (Join-Path $env:WINDIR 'System32\OpenSSH')
    foreach ($Comando in @('ssh.exe', 'scp.exe', 'ssh-keygen.exe')) {
        if (-not (Get-Command $Comando -ErrorAction SilentlyContinue)) {
            throw "No se encontro $Comando en esta PC. OpenSSH debe estar instalado previamente."
        }
    }
    $Configurar = Join-Path $PSScriptRoot '..\configurar.py'
    # Sin perfil fijo: pregunta los datos del servidor y laboratorio de esta PC.
    & $Python $Configurar --instalar --por-usuario
    if ($LASTEXITCODE -ne 0) { throw 'La configuracion no se completo. Revisa el mensaje anterior.' }
    Write-Host 'Instalacion completada. El recolector funcionara automaticamente al iniciar sesion.'
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
} finally {
    Read-Host 'Presiona ENTER para cerrar'
}
