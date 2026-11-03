#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

try {
    $certificatePath = Join-Path $PSScriptRoot 'SGLAB-CA.cer'
    $fingerprintPath = Join-Path $PSScriptRoot 'SGLAB-CA.sha256'
    if (!(Test-Path -LiteralPath $certificatePath -PathType Leaf) -or
        !(Test-Path -LiteralPath $fingerprintPath -PathType Leaf)) {
        throw 'Faltan archivos. Extrae todo el ZIP antes de ejecutar el instalador.'
    }

    $expected = (Get-Content -LiteralPath $fingerprintPath -Raw).Trim().ToUpperInvariant()
    if ($expected -notmatch '\A[0-9A-F]{64}\z') {
        throw 'La huella del paquete no es valida. Volve a obtener el ZIP del servidor.'
    }
    $certificate = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new($certificatePath)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $actual = [BitConverter]::ToString($sha.ComputeHash($certificate.RawData)).Replace('-', '')
    } finally {
        $sha.Dispose()
    }
    if ($actual -ne $expected) {
        throw 'El certificado no coincide con la huella del paquete. No se instalo.'
    }
    $now = Get-Date
    if ($certificate.NotBefore -gt $now -or $certificate.NotAfter -le $now) {
        throw 'El certificado no esta vigente. Revisa la fecha de la PC y el paquete.'
    }

    Write-Host 'SGLAB: instalar confianza para el certificado HTTPS del laboratorio.'
    Write-Host ('Autoridad: ' + $certificate.Subject)
    Write-Host ('Huella SHA-256: ' + $actual)
    Write-Host 'Almacen: raices de confianza del USUARIO ACTUAL.'
    Write-Host 'Windows puede pedir confirmar la instalacion de esta autoridad.'
    $storePath = 'Cert:\CurrentUser\Root\' + $certificate.Thumbprint
    if (Test-Path -LiteralPath $storePath) {
        Write-Host 'La autoridad de SGLAB ya esta instalada para este usuario.'
    } else {
        Import-Certificate -FilePath $certificatePath -CertStoreLocation 'Cert:\CurrentUser\Root' -ErrorAction Stop | Out-Null
    }
    if (!(Test-Path -LiteralPath $storePath)) {
        throw 'Windows no guardo la autoridad en las raices del usuario actual.'
    }
    Write-Host ''
    Write-Host 'Listo. Cerra TODAS las ventanas del navegador y volve a abrir SGLAB.'
    Write-Host 'La URL esta indicada en INSTRUCCIONES.txt.'
    exit 0
} catch {
    Write-Host ('No se pudo instalar el certificado: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Este instalador no solicita elevacion. Una politica institucional puede restringir la instalacion.'
    exit 1
}
