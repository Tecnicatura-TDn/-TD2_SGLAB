#!/usr/bin/env python3
"""Prepara HTTPS para una IP interna; nunca regenera una CA existente."""
import argparse
import fcntl
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def openssl(*arguments, check=True):
    return subprocess.run(['openssl', *map(str, arguments)], check=check,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def same_key(cert, key):
    return (openssl('x509', '-in', cert, '-pubkey', '-noout').stdout ==
            openssl('pkey', '-in', key, '-pubout').stdout)


def update_env(path, values):
    content = path.read_text()
    for name, value in values.items():
        line = name + '=' + value
        pattern = r'^' + re.escape(name) + r'=.*$'
        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, lambda _: line, content, flags=re.MULTILINE)
        else:
            content = content.rstrip() + '\n' + line + '\n'
    fd, temporary = tempfile.mkstemp(prefix='.env.https-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def windows_package(public, ca, origin):
    """Distribuye solo la CA publica; las claves privadas nunca entran al ZIP."""
    der = openssl('x509', '-in', ca, '-outform', 'DER').stdout
    fingerprint = hashlib.sha256(der).hexdigest().upper()
    files = {'SGLAB-CA.cer': der, 'SGLAB-CA.sha256': (fingerprint + '\r\n').encode()}
    for name in ('Instalar-certificado-SGLAB.bat', 'instalar-certificado.ps1'):
        source = ROOT / 'client/windows' / name
        files[name] = source.read_text().replace('\n', '\r\n').encode('ascii')
    files['INSTRUCCIONES.txt'] = (
        'Certificado HTTPS de SGLAB\r\n\r\n'
        '1. Extraer TODO el ZIP en una carpeta de Windows.\r\n'
        '2. Doble clic en Instalar-certificado-SGLAB.bat.\r\n'
        '3. Confirmar la instalacion de SGLAB Autoridad Local si Windows lo pide.\r\n'
        '4. Cerrar todas las ventanas del navegador y volver a abrirlo.\r\n'
        '5. Acceder a ' + origin + '\r\n\r\n'
        'Se instala la CA en las raices de confianza del usuario actual.\r\n'
        'No solicita elevacion de administrador. Las politicas institucionales pueden restringirlo.\r\n'
        'El paquete contiene un certificado publico, sin claves privadas.\r\n'
        'Alternativa manual: abrir SGLAB-CA.cer, Instalar certificado, Usuario actual,\r\n'
        'Entidades de certificacion raiz de confianza.\r\n\r\n'
        'Si sigue el error, revisar certmgr.msc en el mismo usuario de Windows:\r\n'
        'Entidades de certificacion raiz de confianza > Certificados > SGLAB Autoridad Local.\r\n'
        'Huella SHA-256 del certificado: ' + fingerprint + '\r\n'
    ).encode('ascii')
    path = public / 'Instalar-certificado-SGLAB.zip'
    fd, temporary = tempfile.mkstemp(prefix='.certificado-', suffix='.zip', dir=public)
    os.close(fd)
    try:
        with ZipFile(temporary, 'w', compression=ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr('Certificado-SGLAB/' + name, content)
        os.replace(temporary, path)
        path.chmod(0o644)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path


def configure(ip, port, renew=False):
    env = ROOT / '.env'
    if not env.is_file():
        raise ValueError('Primero crear .env con las credenciales del despliegue.')
    http = re.search(r'^APP_PORT=[\'"]?(\d+)', env.read_text(), re.MULTILINE)
    if http and int(http.group(1)) == port:
        raise ValueError('HTTP y HTTPS necesitan puertos diferentes.')
    pki, tls, public = (ROOT / 'var' / name for name in ('pki', 'tls', 'certificados'))
    for directory in (pki, tls, public):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
    ca, ca_key = pki / 'SGLAB-CA.crt', pki / 'SGLAB-CA.key'
    if ca.exists() != ca_key.exists():
        raise ValueError('La CA está incompleta. Restaurar su certificado y clave; no reemplazarla.')
    if not ca.exists():
        with tempfile.TemporaryDirectory(prefix='.ca-', dir=pki) as temporary:
            work = Path(temporary)
            openssl('req', '-x509', '-newkey', 'rsa:3072', '-nodes', '-sha256',
                    '-days', '3650', '-subj', '/CN=SGLAB Autoridad Local',
                    '-addext', 'basicConstraints=critical,CA:TRUE,pathlen:0',
                    '-addext', 'keyUsage=critical,keyCertSign,cRLSign',
                    '-keyout', work / 'ca.key', '-out', work / 'ca.crt')
            shutil.copyfile(work / 'ca.key', ca_key)
            ca_key.chmod(0o600)
            shutil.copyfile(work / 'ca.crt', ca)
            ca.chmod(0o644)
    ca_key.chmod(0o600)
    if not same_key(ca, ca_key):
        raise ValueError('El certificado y la clave de la CA no coinciden.')
    if openssl('x509', '-in', ca, '-noout', '-checkend', 366 * 86400, check=False).returncode:
        raise ValueError('La CA vence en menos de un año: planificar su renovación y distribución.')
    cert, key = tls / 'server.crt', tls / 'server.key'
    valid = (cert.is_file() and key.is_file() and
             openssl('x509', '-in', cert, '-noout', '-checkip', ip, check=False).returncode == 0 and
             openssl('x509', '-in', cert, '-noout', '-checkend', 30 * 86400, check=False).returncode == 0 and
             openssl('verify', '-CAfile', ca, cert, check=False).returncode == 0 and
             same_key(cert, key))
    if renew or not valid:
        with tempfile.TemporaryDirectory(prefix='.cert-', dir=tls) as temporary:
            work = Path(temporary)
            openssl('req', '-new', '-newkey', 'rsa:3072', '-nodes', '-sha256',
                    '-subj', '/CN=' + ip, '-keyout', work / 'server.key', '-out', work / 'server.csr')
            sans = ','.join(dict.fromkeys(['IP:' + ip, 'IP:127.0.0.1', 'DNS:localhost']))
            (work / 'extensions.cnf').write_text(
                'basicConstraints=critical,CA:FALSE\n'
                'keyUsage=critical,digitalSignature,keyEncipherment\n'
                'extendedKeyUsage=serverAuth\n'
                'subjectKeyIdentifier=hash\nauthorityKeyIdentifier=keyid,issuer\n'
                'subjectAltName=' + sans + '\n')
            openssl('x509', '-req', '-in', work / 'server.csr', '-CA', ca, '-CAkey', ca_key,
                    '-set_serial', hex(secrets.randbits(159) or 1), '-days', '365', '-sha256',
                    '-extfile', work / 'extensions.cnf', '-out', work / 'server.crt')
            openssl('verify', '-CAfile', ca, '-verify_ip', ip, work / 'server.crt')
            # Apache carga ambos al reiniciar. La CA privada nunca se monta en Docker.
            shutil.copyfile(work / 'server.key', key)
            key.chmod(0o600)
            shutil.copyfile(work / 'server.crt', cert)
            cert.chmod(0o644)
    key.chmod(0o600)
    shutil.copyfile(ca, public / ca.name)
    (public / ca.name).chmod(0o644)
    origin = 'https://' + ip + (':' + str(port) if port != 443 else '')
    values = {'SGLAB_HTTPS_ORIGIN': origin, 'APP_HTTPS_PORT': str(port)}
    # Preparar el callback local mientras la OAuth App todavía no está registrada.
    configured = re.search(r'^GITHUB_CLIENT_ID=(.+)$', env.read_text(), re.MULTILINE)
    if not configured or configured.group(1).strip() in ("''", '""'):
        values['GITHUB_REDIRECT_URI'] = origin + '/?page=github_callback'
    update_env(env, values)
    package = windows_package(public, ca, origin)
    print('HTTPS preparado para ' + origin)
    print('Certificado público para las PC: ' + str(public / ca.name))
    print('Instalador Windows (extraer ZIP y abrir BAT): ' + str(package))
    print(openssl('x509', '-in', ca, '-noout', '-fingerprint', '-sha256').stdout.decode().strip())
    print(openssl('x509', '-in', cert, '-noout', '-enddate').stdout.decode().strip())
    print('Aplicar: docker compose up -d --build --force-recreate web')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ip', type=ipaddress.IPv4Address, help='IP fija del servidor en el laboratorio')
    parser.add_argument('--puerto', type=int, default=443)
    parser.add_argument('--renovar', action='store_true', help='Emitir de nuevo el certificado del servidor con la misma CA')
    args = parser.parse_args()
    if not 1 <= args.puerto <= 65535:
        parser.error('El puerto debe estar entre 1 y 65535.')
    os.umask(0o077)
    ROOT.joinpath('var').mkdir(exist_ok=True)
    with ROOT.joinpath('var/.https.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            configure(str(args.ip), args.puerto, args.renovar)
        except (ValueError, OSError, subprocess.CalledProcessError) as exc:
            parser.exit(1, 'No se pudo preparar HTTPS: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
