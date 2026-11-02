# Lanzador interactivo utilizado por client/Instalar-SGLAB.bat.
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$CodigoSalidaSglab = 1
$TranscripcionSglab = $false
$EtapaSglab = 'inicio'
$RegistroSglab = Join-Path $env:LOCALAPPDATA 'SGLAB-instalacion.log'
try {
    try {
        Start-Transcript -LiteralPath $RegistroSglab -Append -ErrorAction Stop | Out-Null
        $TranscripcionSglab = $true
    } catch {
        Write-Warning ('No se pudo iniciar el registro: ' + $RegistroSglab)
    }
    Write-Host '=== Instalacion del cliente SGLAB ==='
    Write-Host ('Usuario de Windows: ' + [Environment]::UserName)
    Write-Host ('Configuracion esperada: ' + (Join-Path $env:LOCALAPPDATA 'SGLAB\cliente.json'))
    $EtapaSglab = 'instalacion de Python'
    Write-Host 'Se instalara Python si falta y luego se configurara esta PC.'
    & (Join-Path $PSScriptRoot 'instalar-python.ps1')
    if ($LASTEXITCODE -ne 0) { throw ('La instalacion de Python termino con codigo ' + $LASTEXITCODE) }
    $Python = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'
    if (-not (Test-Path -LiteralPath $Python)) { throw 'No se encontro Python.' }

    $EtapaSglab = 'comprobacion de OpenSSH'
    $env:Path += ';' + (Join-Path $env:WINDIR 'System32\OpenSSH')
    foreach ($Comando in @('ssh.exe', 'scp.exe', 'ssh-keygen.exe')) {
        if (-not (Get-Command $Comando -ErrorAction SilentlyContinue)) {
            throw "No se encontro $Comando en esta PC. OpenSSH debe estar instalado previamente."
        }
    }
    $Configurar = Join-Path $PSScriptRoot '..\configurar.py'
    $EtapaSglab = 'configuracion local, autorizacion SSH y tareas'
    # Sin perfil fijo: pregunta los datos del servidor y laboratorio de esta PC.
    & $Python $Configurar --instalar --por-usuario --reanudar
    if ($LASTEXITCODE -ne 0) { throw ('El configurador termino con codigo ' + $LASTEXITCODE + '. Revisa el error anterior.') }
    $ConfiguracionSglab = Join-Path $env:LOCALAPPDATA 'SGLAB\cliente.json'
    if (-not (Test-Path -LiteralPath $ConfiguracionSglab -PathType Leaf)) { throw 'El configurador no genero cliente.json en la ruta esperada.' }
    Get-Content -LiteralPath $ConfiguracionSglab -Raw | ConvertFrom-Json | Out-Null
    $CodigoSalidaSglab = 0
    Write-Host 'Instalacion completada. El recolector funcionara automaticamente al iniciar sesion.'
} catch {
    Write-Host ('ERROR en ' + $EtapaSglab + ': ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host ('Registro para revisar: ' + $RegistroSglab)
} finally {
    if ($TranscripcionSglab) { Stop-Transcript | Out-Null }
}
exit $CodigoSalidaSglab
