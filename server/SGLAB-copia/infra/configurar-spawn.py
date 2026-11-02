#!/usr/bin/env python3
"""Genera la unidad de spawn para el usuario y la ruta de este servidor Linux."""
import argparse
import grp
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def literal(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'


def unidad(project, user, bash, docker_group):
    group = 'SupplementaryGroups=docker\n' if docker_group else ''
    return f'''[Unit]
Description=SGLAB - Ingesta de reportes TOML
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
{group}WorkingDirectory={str(project).replace('%', '%%')}
Environment={literal('SGLAB_DATA_DIR=' + str(project / 'var'))}
Environment={literal('SGLAB_COMPOSE_DIR=' + str(project))}
Environment={literal('SGLAB_TOMLQ=' + str(project / '.venv/bin/tomlq'))}
ExecStart={literal(bash)} {literal(project / 'server/bin/spawn.sh')}
Restart=on-failure
RestartSec=5
UMask=0077

[Install]
WantedBy=multi-user.target
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usuario', help='Usuario Linux dueño de la instalación; por defecto, el usuario actual')
    parser.add_argument('--proyecto', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        name = args.usuario
        if name is None:
            name = os.environ.get('SUDO_USER') if os.geteuid() == 0 else pwd.getpwuid(os.getuid()).pw_name
        if not name:
            raise ValueError('Indicar --usuario con el usuario Linux que operará spawn; no usar root por defecto.')
        try:
            user = pwd.getpwnam(name)
        except KeyError:
            raise ValueError('El usuario Linux indicado no existe en este servidor.')
        if user.pw_uid == 0:
            raise ValueError('Indicar el usuario Linux dueño del proyecto, sin ejecutar spawn como root.')
        project = args.proyecto.resolve()
        if any(c in str(project) for c in ('\n', '\r', '$')):
            raise ValueError('La ruta del proyecto no puede contener saltos de línea ni $.')
        for path in (project/'compose.yaml', project/'.env', project/'server/bin/spawn.sh'):
            if not path.is_file():
                raise ValueError('No se encontró ' + str(path))
        tomlq = project/'.venv/bin/tomlq'
        if not tomlq.is_file() or not os.access(tomlq, os.X_OK):
            raise ValueError('Crear el entorno .venv e instalar server/ingest/requirements-bash.txt en este servidor.')
        try:
            subprocess.run([str(tomlq), '--version'], check=True, capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.SubprocessError):
            raise ValueError('El tomlq de .venv no funciona; recrear el entorno local, sin copiarlo desde otra máquina.')
        bash = shutil.which('bash')
        if not bash:
            raise ValueError('No se encontró bash.')
        try:
            grp.getgrnam('docker')
            docker_group = True
        except KeyError:
            docker_group = False
        output = project/'var/systemd/sglab-spawn.service'
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix='.spawn-', dir=output.parent)
        try:
            with os.fdopen(fd, 'w') as stream:
                stream.write(unidad(project, user.pw_name, bash, docker_group))
            os.replace(temporary, output)
            output.chmod(0o644)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print('Unidad generada: ' + str(output))
        print('Usuario: ' + user.pw_name)
        print('Proyecto: ' + str(project))
        print('Aplicar desde la raíz de SGLAB:')
        print('sudo install -m 0644 var/systemd/sglab-spawn.service /etc/systemd/system/sglab-spawn.service')
        print('sudo systemctl daemon-reload')
        print('sudo systemctl reset-failed sglab-spawn')
        print('sudo systemctl enable sglab-spawn')
        print('sudo systemctl restart sglab-spawn')
        return 0
    except (OSError, ValueError) as exc:
        parser.exit(1, 'No se pudo preparar el servicio: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
