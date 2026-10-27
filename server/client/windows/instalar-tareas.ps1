# Ejecutar una vez desde PowerShell como administrador.
# No almacena contraseñas: usa SYSTEM. Esa cuenta debe poder leer la clave SSH
# y known_hosts indicados por la configuración y encontrar scp.exe/ssh.exe.
#Requires -RunAsAdministrator
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$Config
)
$ErrorActionPreference = 'Stop'
$Script = (Resolve-Path (Join-Path $PSScriptRoot '..\recopilar.py')).Path
$Python = (Resolve-Path $Python).Path
$Config = (Resolve-Path $Config).Path
foreach ($Ruta in @($Script, $Python, $Config)) {
    if ($Ruta.Contains('"')) { throw 'Las rutas no pueden contener comillas' }
}
$Argumentos = '"{0}" --config "{1}"' -f $Script, $Config
$Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$Ajustes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$Captura = New-ScheduledTaskAction -Execute $Python -Argument $Argumentos
$Inicio = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName 'SGLAB-Recopilar' -Action $Captura -Trigger $Inicio -Principal $Principal -Settings $Ajustes -Force | Out-Null
$Envio = New-ScheduledTaskAction -Execute $Python -Argument ($Argumentos + ' --solo-enviar')
$Reintento = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName 'SGLAB-EnviarPendientes' -Action $Envio -Trigger $Reintento -Principal $Principal -Settings $Ajustes -Force | Out-Null
Write-Output 'Tareas instaladas. La recopilación ocurre al arrancar; los pendientes se reintentan cada dos minutos.'
