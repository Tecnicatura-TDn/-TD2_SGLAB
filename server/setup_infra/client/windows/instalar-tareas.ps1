# Ejecutar una vez desde PowerShell como administrador.
# No almacena contraseñas: usa SYSTEM. Esa cuenta debe poder leer la clave SSH
# y known_hosts indicados por la configuración y encontrar scp.exe/ssh.exe.
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$Config,
    [switch]$PorUsuario
)
$ErrorActionPreference = 'Stop'
$Script = (Resolve-Path (Join-Path $PSScriptRoot '..\recopilar.py')).Path
$Python = (Resolve-Path $Python).Path
$Config = (Resolve-Path $Config).Path
foreach ($Ruta in @($Script, $Python, $Config)) {
    if ($Ruta.Contains('"')) { throw 'Las rutas no pueden contener comillas' }
}
$Argumentos = '"{0}" --config "{1}"' -f $Script, $Config
if ($PorUsuario) {
    $Identidad = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $Usuario = $Identidad.Name
    $Sufijo = '-' + $Identidad.User.Value
    $Principal = New-ScheduledTaskPrincipal -UserId $Usuario -LogonType Interactive -RunLevel Limited
    $Inicio = New-ScheduledTaskTrigger -AtLogOn -User $Usuario
} else {
    $Admin = New-Object System.Security.Principal.WindowsPrincipal([System.Security.Principal.WindowsIdentity]::GetCurrent())
    if (-not $Admin.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'El modo de arranque SYSTEM requiere administrador. Para usuario normal usar -PorUsuario.'
    }
    $Sufijo = ''
    $Principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
    $Inicio = New-ScheduledTaskTrigger -AtStartup
}
$Ajustes = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$Captura = New-ScheduledTaskAction -Execute $Python -Argument $Argumentos
Register-ScheduledTask -TaskName ('SGLAB-Recopilar' + $Sufijo) -Action $Captura -Trigger $Inicio -Principal $Principal -Settings $Ajustes -Force | Out-Null
$Envio = New-ScheduledTaskAction -Execute $Python -Argument ($Argumentos + ' --solo-enviar')
$Reintento = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName ('SGLAB-EnviarPendientes' + $Sufijo) -Action $Envio -Trigger $Reintento -Principal $Principal -Settings $Ajustes -Force | Out-Null
Write-Output 'Tareas instaladas: usuario normal al iniciar sesion; SYSTEM al arrancar. Reenvio cada dos minutos.'
