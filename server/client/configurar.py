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
    parser.add_argument('--clave', type=Path, help='Clave privada de servicio ya autorizada en el servidor')
    parser.add_argument('--known-hosts', type=Path, help='Archivo de hosts verificados previamente')
    parser.add_argument('--destino', type=Path, help='Carpeta de configuración/instalación')
    parser.add_argument('--instalar', action='store_true', help='Registrar además arranque y reintentos (requiere administrador)')
    args = parser.parse_args()
    windows = platform.system() == 'Windows'
    if platform.system() not in ('Windows', 'Linux'):
        parser.error('Solo Windows o Linux')
    try:
        if args.instalar and not (ctypes.windll.shell32.IsUserAnAdmin() if windows else os.geteuid() == 0):
            raise ValueError('Para --instalar abrir PowerShell como administrador o ejecutar con sudo en Linux')
        perfil = json.loads(args.perfil.read_text(encoding='utf-8')) if args.perfil else {}
        if not isinstance(perfil, dict) or set(perfil) - {'servidor', 'usuario', 'puerto_ssh', 'directorio_remoto', 'laboratorio'}:
            raise ValueError('Perfil inválido: solo admite servidor, usuario, puerto_ssh, directorio_remoto y laboratorio')
        valores = {}
        for campo, etiqueta, defecto in (
            ('servidor', 'IP o nombre del servidor', None),
            ('usuario', 'Usuario SSH receptor', None),
            ('puerto_ssh', 'Puerto SSH', 22),
            ('directorio_remoto', 'Carpeta de recepción', '/srv/sglab/incoming'),
            ('laboratorio', 'Etiqueta del laboratorio', 'LAB01'),
        ):
            valor = getattr(args, campo)
            valores[campo] = solicitar(valor if valor is not None else perfil.get(campo), etiqueta, defecto)
        valores['puerto_ssh'] = int(valores['puerto_ssh'])
        validar(valores)
        clave = Path(solicitar(args.clave, 'Ruta de la clave privada SSH de servicio')).expanduser().resolve()
        hosts = Path(solicitar(args.known_hosts, 'Ruta del archivo known_hosts verificado', str(Path.home()/'.ssh'/'known_hosts'))).expanduser().resolve()
        if not clave.is_file() or not hosts.is_file():
            raise ValueError('La clave privada y known_hosts deben existir antes de configurar')
        if args.instalar:
            for comando in ('ssh', 'scp', 'ssh-keygen'):
                if not shutil.which(comando):
                    raise ValueError(f'Instalar OpenSSH y agregar {comando} al PATH antes de continuar')
            if windows:
                # SYSTEM no puede usar el alias Python de Microsoft Store del usuario.
                if 'windowsapps' in str(Path(sys.executable).resolve()).lower():
                    raise ValueError('Usar Python instalado para todo el sistema, fuera de WindowsApps')
        defecto = (Path(os.environ.get('ProgramData', 'C:/ProgramData'))/'SGLAB' if windows else Path('/opt/sglab-cliente'))
        destino = (args.destino or (defecto if args.instalar else Path.cwd()/'sglab-cliente')).resolve()
        if any(c in str(destino) for c in ('"', '\n', '\r')):
            raise ValueError('Ruta de instalación inválida')
        # Nunca reemplazar silenciosamente una instalación ni credenciales existentes.
        if destino.exists() and any(destino.iterdir()):
            raise ValueError(f'{destino} no está vacío. Editar cliente.json para cambiar el servidor; elegir otro destino para una instalación nueva')
        if clave == destino / 'id_ed25519' or hosts == destino / 'known_hosts':
            raise ValueError('Las credenciales de origen deben estar fuera del destino nuevo')
        destino.mkdir(parents=True, exist_ok=True)
        proteger(destino, windows, permitir_usuario=not args.instalar)
        shutil.copyfile(clave, destino/'id_ed25519')
        shutil.copyfile(hosts, destino/'known_hosts')
        if not windows:
            (destino/'id_ed25519').chmod(0o600)
            (destino/'known_hosts').chmod(0o600)
        if args.instalar:
            if windows:
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
                ejecutar('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'RemoteSigned', '-File', ps, '-Python', sys.executable, '-Config', config)
            else:
                for nombre, contenido in unidades_linux(Path(sys.executable).resolve(), script, config).items():
                    (Path('/etc/systemd/system')/nombre).write_text(contenido, encoding='utf-8')
                if shutil.which('restorecon'):
                    ejecutar('restorecon', '-RF', destino)
                ejecutar('systemctl', 'daemon-reload')
                ejecutar('systemctl', 'enable', 'sglab-recopilar.service')
                ejecutar('systemctl', 'enable', '--now', 'sglab-enviar.timer')
            print('Arranque y reintentos instalados. La captura se hará en el próximo arranque.')
        else:
            print('Configuración preparada; no se registraron tareas de arranque.')
        print('Para cambiar la dirección del servidor, editar cliente.json; no editar recopilar.py.')
        return 0
    except (OSError, ValueError, TypeError, EOFError, subprocess.SubprocessError) as exc:
        print(f'No se completó la configuración: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
