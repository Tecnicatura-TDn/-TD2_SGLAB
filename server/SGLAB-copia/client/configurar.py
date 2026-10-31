#!/usr/bin/env python3
"""Configura e instala el recolector en Windows o Linux una sola vez."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import platform
import re
import shutil
import shlex
import subprocess
import sys
import tempfile

ORIGEN = Path(__file__).resolve().parent


def solicitar(actual, etiqueta, defecto=None):
    if actual is not None:
        return actual
    texto = input(f'{etiqueta}' + (f' [{defecto}]' if defecto is not None else '') + ': ').strip()
    return texto or defecto


def validar(valores):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]*', valores['servidor'] or ''):
        raise ValueError('Servidor debe ser un hostname o IPv4')
    if not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*', valores['usuario'] or ''):
        raise ValueError('Usuario SSH inválido')
    if not 1 <= valores['puerto_ssh'] <= 65535:
        raise ValueError('Puerto fuera de rango')
    remoto = valores['directorio_remoto']
    if not re.fullmatch(r'/[a-zA-Z0-9_./-]+', remoto or '') or '..' in remoto.split('/'):
        raise ValueError('Directorio remoto absoluto, sin espacios ni ..')
    if not 1 <= len(valores['laboratorio'].strip()) <= 20:
        raise ValueError('Laboratorio debe tener entre 1 y 20 caracteres')


def ejecutar(*comando):
    subprocess.run(list(map(str, comando)), check=True)


def proteger(carpeta, windows, permitir_usuario=False):
    if windows:
        # SIDs independientes del idioma de Windows: SYSTEM y Administradores.
        ejecutar('icacls', carpeta, '/inheritance:r', '/grant:r',
                 '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F')
        if permitir_usuario:
            usuario = subprocess.check_output(['whoami'], text=True).strip()
            ejecutar('icacls', carpeta, '/grant:r', usuario + ':(OI)(CI)F')
    else:
        carpeta.chmod(0o700)


def autorizar_clave(valores, clave, hosts):
    """Autoriza solo la pública; OpenSSH pide la contraseña en la terminal."""
    publica = subprocess.check_output(
        ['ssh-keygen', '-y', '-P', '', '-f', str(clave)],
        text=True, stderr=subprocess.PIPE, timeout=15).strip()
    if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+(?: [^\r\n]*)?', publica):
        # También se admiten claves de servicio RSA/ECDSA existentes.
        if not re.fullmatch(r'(?:ssh-rsa|ecdsa-sha2-nistp(?:256|384|521)) [A-Za-z0-9+/=]+(?: [^\r\n]*)?', publica):
            raise ValueError('Formato de clave pública no admitido')
    opciones = ['-p', str(valores['puerto_ssh']), '-o', 'ConnectTimeout=15',
                '-o', 'UserKnownHostsFile="' + str(hosts) + '"',
                '-o', 'GlobalKnownHostsFile=none']
    remoto = valores['usuario'] + '@' + valores['servidor']
    # La pública va en el comando remoto; la privada nunca sale de esta PC.
    comando = """set -eu
umask 077
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
auth="$HOME/.ssh/authorized_keys"
[ ! -L "$auth" ] || { echo 'authorized_keys no puede ser enlace simbólico' >&2; exit 1; }
touch "$auth"
chmod 600 "$auth"
publica=""" + shlex.quote(publica) + """
if ! grep -qF -- "$publica" "$auth"; then
    printf '\n%s\n' "$publica" >> "$auth"
fi
"""
    print('Verificá la huella SSH con el administrador antes de aceptarla. '
          'OpenSSH pedirá la contraseña del usuario receptor; no se guardará.', flush=True)
    subprocess.run(['ssh', *opciones, '-o', 'StrictHostKeyChecking=ask',
                    '-o', 'PubkeyAuthentication=no', '-o', 'PreferredAuthentications=password',
                    '-o', 'PasswordAuthentication=yes', '-o', 'BatchMode=no',
                    remoto, comando], check=True)
    # Probar exactamente el modo no interactivo que usará el recolector.
    subprocess.run(['ssh', *opciones, '-i', str(clave),
                    '-o', 'StrictHostKeyChecking=yes', '-o', 'BatchMode=yes',
                    '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none',
                    '-o', 'PreferredAuthentications=publickey', remoto, 'true'],
                   check=True, timeout=45)
    print('Clave pública autorizada y acceso sin contraseña comprobado.')


def escribir_json(ruta, datos):
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=ruta.parent, delete=False) as f:
            temporal = Path(f.name)
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(temporal, ruta)
    finally:
        if temporal:
            temporal.unlink(missing_ok=True)


def literal_systemd(valor):
    return '"' + str(valor).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'


def unidades_linux(python, script, config):
    base = f'{literal_systemd(python)} {literal_systemd(script)} --config {literal_systemd(config)}'
    def servicio(descripcion, comando, despues):
        return f'''[Unit]
Description={descripcion}
Wants=network-online.target
After={despues}

[Service]
Type=oneshot
User=root
UMask=0077
ExecStart={comando}
TimeoutStartSec=30min
'''
    return {
        'sglab-recopilar.service': servicio('SGLAB - Captura al arrancar', base, 'network-online.target') + '\n[Install]\nWantedBy=multi-user.target\n',
        'sglab-enviar.service': servicio('SGLAB - Enviar pendientes', base + ' --solo-enviar', 'network-online.target sglab-recopilar.service'),
        'sglab-enviar.timer': '''[Unit]
Description=SGLAB - Reintentar pendientes cada dos minutos
[Timer]
OnBootSec=2min
OnUnitInactiveSec=2min
Unit=sglab-enviar.service
[Install]
WantedBy=timers.target
''',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--perfil', type=Path, help='JSON con datos comunes del servidor')
    parser.add_argument('--servidor')
    parser.add_argument('--usuario')
    parser.add_argument('--puerto-ssh', type=int)
    parser.add_argument('--directorio-remoto')
    parser.add_argument('--laboratorio')
    parser.add_argument('--clave', type=Path, help='Clave privada de servicio existente; si se omite se genera una por PC')
    parser.add_argument('--autorizar-clave', action='store_true', help='Autorizar la clave existente usando contraseña SSH')
    parser.add_argument('--known-hosts', type=Path, help='Archivo de hosts verificados previamente')
    parser.add_argument('--destino', type=Path, help='Carpeta de configuración/instalación')
    parser.add_argument('--por-usuario', action='store_true', help='Windows: instalar sin administrador y ejecutar al iniciar sesion')
    parser.add_argument('--instalar', action='store_true', help='Registrar además arranque y reintentos (requiere administrador)')
    args = parser.parse_args()
    windows = platform.system() == 'Windows'
    if platform.system() not in ('Windows', 'Linux'):
        parser.error('Solo Windows o Linux')
    try:
        if args.por_usuario and (not windows or not args.instalar):
            raise ValueError('--por-usuario requiere Windows y --instalar')
        if args.instalar and not args.por_usuario and not (ctypes.windll.shell32.IsUserAnAdmin() if windows else os.geteuid() == 0):
            raise ValueError('Para --instalar abrir PowerShell como administrador o ejecutar con sudo en Linux')
        perfil = json.loads(args.perfil.read_text(encoding='utf-8')) if args.perfil else {}
        if not isinstance(perfil, dict) or set(perfil) - {'servidor', 'usuario', 'puerto_ssh', 'directorio_remoto', 'laboratorio'}:
            raise ValueError('Perfil inválido: solo admite servidor, usuario, puerto_ssh, directorio_remoto y laboratorio')
        valores = {}
        for campo, etiqueta, defecto in (
            ('servidor', 'IP o nombre del servidor', None),
            ('usuario', 'Usuario SSH receptor', None),
            ('puerto_ssh', 'Puerto SSH', 22),
            ('directorio_remoto', 'Carpeta de recepción', '/home/facu/SGLAB-copia/server/incoming'),
            ('laboratorio', 'Etiqueta del laboratorio', 'LAB01'),
        ):
            valor = getattr(args, campo)
            valores[campo] = solicitar(valor if valor is not None else perfil.get(campo), etiqueta, defecto)
        valores['puerto_ssh'] = int(valores['puerto_ssh'])
        validar(valores)
        autorizar = args.autorizar_clave or args.clave is None
        clave = args.clave.expanduser().resolve() if args.clave else None
        hosts = args.known_hosts.expanduser().resolve() if args.known_hosts else None
        if clave and not clave.is_file():
            raise ValueError('La clave privada indicada no existe')
        if hosts and not hosts.is_file():
            raise ValueError('El archivo known_hosts indicado no existe')
        if not autorizar and hosts is None:
            hosts = Path(solicitar(None, 'Ruta del archivo known_hosts verificado', str(Path.home()/'.ssh'/'known_hosts'))).expanduser().resolve()
            if not hosts.is_file():
                raise ValueError('El archivo known_hosts debe existir')
        if args.instalar or autorizar:
            for comando in ('ssh', 'scp', 'ssh-keygen'):
                if not shutil.which(comando):
                    raise ValueError(f'Instalar OpenSSH y agregar {comando} al PATH antes de continuar')
            if windows:
                # SYSTEM no puede usar el alias Python de Microsoft Store del usuario.
                if 'windowsapps' in str(Path(sys.executable).resolve()).lower():
                    raise ValueError('Usar Python instalado para todo el sistema, fuera de WindowsApps')
        defecto = (Path(os.environ.get('ProgramData', 'C:/ProgramData'))/'SGLAB' if windows else Path('/opt/sglab-cliente'))
        if windows and args.por_usuario:
            defecto = Path(os.environ['LOCALAPPDATA'])/'SGLAB'
        destino = (args.destino or (defecto if args.instalar else Path.cwd()/'sglab-cliente')).resolve()
        if any(c in str(destino) for c in ('"', '\n', '\r')):
            raise ValueError('Ruta de instalación inválida')
        # Nunca reemplazar silenciosamente una instalación ni credenciales existentes.
        if destino.exists() and any(destino.iterdir()):
            raise ValueError(f'{destino} no está vacío. Editar cliente.json para cambiar el servidor; elegir otro destino para una instalación nueva')
        if clave == destino / 'id_ed25519' or hosts == destino / 'known_hosts':
            raise ValueError('Las credenciales de origen deben estar fuera del destino nuevo')
        destino.mkdir(parents=True, exist_ok=True)
        proteger(destino, windows, permitir_usuario=not args.instalar or args.por_usuario)
        if clave:
            shutil.copyfile(clave, destino/'id_ed25519')
        else:
            ejecutar('ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                     '-C', 'SGLAB-' + platform.node(), '-f', destino/'id_ed25519')
        if hosts:
            shutil.copyfile(hosts, destino/'known_hosts')
        else:
            (destino/'known_hosts').touch(mode=0o600)
        if autorizar:
            autorizar_clave(valores, destino/'id_ed25519', destino/'known_hosts')
        if not windows:
            (destino/'id_ed25519').chmod(0o600)
            (destino/'known_hosts').chmod(0o600)
        if args.instalar:
            if windows and not args.por_usuario:
                ejecutar('icacls', destino/'id_ed25519', '/setowner', '*S-1-5-18')
            # Sin agente ni preguntas: una tarea al arrancar necesita una clave de
            # servicio utilizable sin passphrase. No se muestra la clave pública.
            prueba = subprocess.run(['ssh-keygen', '-y', '-P', '', '-f', str(destino/'id_ed25519')],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=15)
            if prueba.returncode:
                raise ValueError('La clave de servicio debe ser válida y usable sin passphrase para el arranque automático')
            host = valores['servidor'] if valores['puerto_ssh'] == 22 else f"[{valores['servidor']}]:{valores['puerto_ssh']}"
            prueba = subprocess.run(['ssh-keygen', '-F', host, '-f', str(destino/'known_hosts')],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=15)
            if prueba.returncode:
                raise ValueError('known_hosts no contiene la identidad verificada del servidor y puerto configurados')
        script = destino/'client'/'recopilar.py'
        script.parent.mkdir()
        shutil.copyfile(ORIGEN/'recopilar.py', script)
        shutil.copyfile(ORIGEN/'ventana.py', script.parent/'ventana.py')
        valores.update(ci=0, salida=str(destino/'pendientes'), clave=str(destino/'id_ed25519'),
                       known_hosts=str(destino/'known_hosts'), reintentos=3, espera=10)
        config = destino/'cliente.json'
        escribir_json(config, valores)
        print(f'Configuración guardada: {config}')
        if args.instalar:
            if windows:
                ps = script.parent/'windows'/'instalar-tareas.ps1'
                ps.parent.mkdir()
                shutil.copyfile(ORIGEN/'windows'/'instalar-tareas.ps1', ps)
                comando = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'RemoteSigned', '-File', ps, '-Python', sys.executable, '-Config', config]
                if args.por_usuario:
                    comando.append('-PorUsuario')
                ejecutar(*comando)
            else:
                for nombre, contenido in unidades_linux(Path(sys.executable).resolve(), script, config).items():
                    (Path('/etc/systemd/system')/nombre).write_text(contenido, encoding='utf-8')
                if shutil.which('restorecon'):
                    ejecutar('restorecon', '-RF', destino)
                ejecutar('systemctl', 'daemon-reload')
                ejecutar('systemctl', 'enable', 'sglab-recopilar.service')
                ejecutar('systemctl', 'enable', '--now', 'sglab-enviar.timer')
            print('Inicio de sesión y reintentos configurados.' if args.por_usuario else 'Arranque y reintentos instalados. La captura se hará en el próximo arranque.')
        else:
            print('Configuración preparada; no se registraron tareas de arranque.')
        print('Para cambiar la dirección del servidor, editar cliente.json; no editar recopilar.py.')
        return 0
    except (OSError, ValueError, TypeError, EOFError, subprocess.SubprocessError) as exc:
        print(f'No se completó la configuración: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
