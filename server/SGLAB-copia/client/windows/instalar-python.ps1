# Ejecutar como usuario normal. Requiere Internet y WinGet.
# Python se instala solo para el usuario actual.
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

try {
    $Python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
    if (-not (Test-Path -LiteralPath $Python)) {
        if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
            throw 'Falta WinGet. Instala o actualiza App Installer desde Microsoft Store y vuelve a ejecutar este script.'
        }
        Write-Host 'Instalando Python 3.13 para el usuario actual...'
        & winget.exe install --exact --id Python.Python.3.13 --source winget `
            --scope user --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "WinGet no completo la instalacion (codigo $LASTEXITCODE)."
        }
    } else {
        Write-Host 'Python 3.13 ya esta instalado para el usuario actual.'
    }

    if (-not (Test-Path -LiteralPath $Python)) {
        throw "No se encontro Python en $Python. Revisa la ubicacion de la instalacion."
    }
    & $Python -c 'import sys; assert sys.version_info >= (3, 9); print(sys.version.split()[0])'
    if ($LASTEXITCODE -ne 0) { throw 'Python no funciona o su version no es compatible.' }

    # Hace visible el PATH actualizado en esta misma consola.
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + `
        [Environment]::GetEnvironmentVariable('Path', 'User')
    Write-Host "Python listo: $Python"
    Write-Host 'Ahora podes configurar el cliente con:'
    $Configurar = Join-Path $PSScriptRoot '..\configurar.py'
    $Perfil = Join-Path $PSScriptRoot '..\perfiles\pruebas.json'
    Write-Host ('& "{0}" "{1}" --perfil "{2}" --instalar --por-usuario' -f $Python, $Configurar, $Perfil)
} catch {
    Write-Error $_
    exit 1
}
