#!/usr/bin/env python3
"""Respaldos privados completos y restauración de prueba aislada de SGLAB."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
DUMPOPTS = ['--single-transaction', '--routines', '--events', '--triggers',
            '--hex-blob', '--order-by-primary', '--skip-comments', '--databases', 'sglab']


def run(args, **kwargs):
    return subprocess.run(args, check=True, stderr=subprocess.PIPE, **kwargs)


def compose(*args):
    return ['docker', 'compose', '--project-directory', str(ROOT), '--env-file',
            str(ROOT / '.env'), '-f', str(ROOT / 'compose.yaml'), *args]


def dump_command(container=None):
    command = ['sh', '-c', 'export MYSQL_PWD="$MARIADB_ROOT_PASSWORD"; exec mariadb-dump -uroot "$@"', 'dump', *DUMPOPTS]
    return ['docker', 'exec', container, *command] if container else compose('exec', '-T', 'db', *command)


def backup():
    destination = ROOT / 'var/backups/automaticos'
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.chmod(0o700)
    with (destination / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with tempfile.TemporaryDirectory(prefix='.backup-', dir=destination) as temporary:
            work = Path(temporary)
            sql = work / 'database.sql'
            with sql.open('wb') as output:
                run(dump_command(), stdout=output)
            if sql.stat().st_size == 0:
                raise RuntimeError('El dump está vacío.')
            with (work / 'web-state.tar').open('wb') as output:
                run(compose('exec', '-T', 'web', 'tar', '-C', '/var/lib/sglab-web', '-cf', '-', '.'), stdout=output)
            # Fallar si faltan elementos necesarios para recuperar HTTPS/configuración.
            required = [ROOT / '.env', ROOT / 'var/pki', ROOT / 'var/tls']
            for path in required:
                if not path.exists():
                    raise RuntimeError('Falta un componente del respaldo: ' + str(path))
            manifest = {'created_utc': datetime.now(timezone.utc).isoformat(),
                        'database_sha256': hashlib.sha256(sql.read_bytes()).hexdigest(),
                        'format': 1,
                        'files_sha256': {name: hashlib.sha256((work / name).read_bytes()).hexdigest()
                                         for name in ['database.sql', 'web-state.tar']}}
            for path in required:
                paths = path.rglob('*') if path.is_dir() else [path]
                for item in paths:
                    if item.is_file():
                        manifest['files_sha256'][str(item.relative_to(ROOT))] = hashlib.sha256(item.read_bytes()).hexdigest()
            (work / 'manifest.json').write_text(json.dumps(manifest, indent=2))
            archive = work / 'backup.tar.gz'
            with tarfile.open(archive, 'w:gz') as bundle:
                for name in ['database.sql', 'web-state.tar', 'manifest.json']:
                    bundle.add(work / name, arcname=name)
                for path in required:
                    bundle.add(path, arcname=str(path.relative_to(ROOT)))
            with tarfile.open(archive, 'r:gz') as bundle:
                validate(bundle, manifest)
            final = destination / ('sglab-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + secrets.token_hex(3) + '.tar.gz')
            archive.chmod(0o600)
            os.replace(archive, final)
        # Solo borrar nuestros respaldos vencidos, después de completar uno nuevo.
        for old in destination.glob('sglab-*.tar.gz'):
            if old.is_file() and not old.is_symlink() and old.stat().st_mtime < time.time() - 7 * 86400:
                old.unlink()
        print('Respaldo verificado:', final)
        return final


def validate(bundle, manifest):
    for name, expected in manifest['files_sha256'].items():
        if hashlib.sha256(bundle.extractfile(name).read()).hexdigest() != expected:
            raise RuntimeError('Falló la integridad de un componente del respaldo.')


def verify(archive):
    name = 'sglab-restore-test-' + secrets.token_hex(6)
    with tempfile.TemporaryDirectory(prefix='sglab-restore-') as temporary:
        sql = Path(temporary) / 'database.sql'
        with tarfile.open(archive, 'r:gz') as bundle:
            # No extraer rutas del archivo ni ejecutar su contenido en el servidor activo.
            manifest = json.load(bundle.extractfile('manifest.json'))
            validate(bundle, manifest)
            with sql.open('wb') as output:
                source = bundle.extractfile('database.sql')
                shutil.copyfileobj(source, output)
        if hashlib.sha256(sql.read_bytes()).hexdigest() != manifest['database_sha256']:
            raise RuntimeError('La integridad del SQL no coincide.')
        try:
            run(['docker', 'run', '-d', '--name', name, '--network', 'none',
                 '--tmpfs', '/var/lib/mysql:rw', '-e', 'MARIADB_ROOT_PASSWORD=' + secrets.token_urlsafe(32),
                 'mariadb:11.4'], stdout=subprocess.DEVNULL)
            for attempt in range(90):
                ready = subprocess.run(['docker', 'exec', name, 'healthcheck.sh', '--connect', '--innodb_initialized'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError('MariaDB de prueba no inició.')
            with sql.open('rb') as source:
                run(['docker', 'exec', '-i', name, 'sh', '-c',
                     'export MYSQL_PWD="$MARIADB_ROOT_PASSWORD"; exec mariadb -uroot'], stdin=source, stdout=subprocess.DEVNULL)
            with (Path(temporary) / 'restored.sql').open('wb') as output:
                run(dump_command(name), stdout=output)
            restored = hashlib.sha256((Path(temporary) / 'restored.sql').read_bytes()).hexdigest()
            if restored != manifest['database_sha256']:
                raise RuntimeError('El dump restaurado difiere del original.')
            print('Restauración aislada OK: SQL restaurado y vuelto a exportar idéntico al original.')
        finally:
            subprocess.run(['docker', 'rm', '-f', '-v', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['crear', 'verificar'])
    parser.add_argument('archive', nargs='?', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'crear':
            backup()
        elif args.archive:
            verify(args.archive)
        else:
            parser.error('Indicar el archivo .tar.gz a verificar.')
    except (OSError, RuntimeError, subprocess.SubprocessError, tarfile.TarError, ValueError, KeyError) as error:
        # No imprimir stderr de comandos ni secretos de sus argumentos.
        detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        parser.exit(1, 'Falló el respaldo/restauración: ' + detail + '. Revisar Docker y los archivos requeridos.\n')


if __name__ == '__main__':
    main()
