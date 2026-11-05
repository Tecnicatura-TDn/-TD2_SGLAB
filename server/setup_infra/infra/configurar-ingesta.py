#!/usr/bin/env python3
"""Extrae solamente las credenciales de ingesta a un archivo de cliente MariaDB."""
import argparse
import grp
import json
import os
from pathlib import Path
import subprocess
import tempfile


def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r') + '"'


def client_config(config):
    service = config['services']['db']
    env = service['environment']
    ports = [p for p in service['ports'] if int(p['target']) == 3306]
    if len(ports) != 1 or ports[0].get('host_ip') != '127.0.0.1':
        raise ValueError('MariaDB debe publicar un solo puerto 3306 en 127.0.0.1.')
    return '[client]\n' + '\n'.join(f'{key}={quote(value)}' for key, value in {
        'host': '127.0.0.1', 'port': ports[0]['published'], 'protocol': 'tcp',
        'user': env['DB_INGEST_USER'], 'password': env['DB_INGEST_PASSWORD'],
        'database': 'sglab', 'connect-timeout': 10,
    }.items()) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('proyecto', type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error('Ejecutar como root mediante el provisionador.')
    root = args.proyecto.resolve()
    try:
        result = subprocess.run(['docker', 'compose', '--project-directory', str(root),
            '--env-file', str(root/'.env'), '-f', str(root/'compose.yaml'),
            'config', '--format', 'json'], check=True, capture_output=True, text=True)
        content = client_config(json.loads(result.stdout))
        directory = Path('/etc/sglab')
        directory.mkdir(mode=0o750, exist_ok=True)
        directory.chmod(0o750)
        gid = grp.getgrnam('sglab-ingest').gr_gid
        os.chown(directory, 0, gid)
        fd, temporary = tempfile.mkstemp(dir=directory, prefix='.ingest-')
        try:
            with os.fdopen(fd, 'w') as output:
                output.write(content)
            os.chown(temporary, 0, gid)
            os.chmod(temporary, 0o640)
            os.replace(temporary, directory/'ingest.cnf')
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        parser.exit(1, 'No se pudo preparar la configuración de ingesta. Revisá Compose y el grupo sglab-ingest.\n')


if __name__ == '__main__':
    main()
