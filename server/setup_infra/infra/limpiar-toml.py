#!/usr/bin/env python3
"""Retira trabajos confirmados de var/processed; por defecto solo simula."""
import argparse
import fcntl
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[1]
TOML = re.compile(r'SGLAB-[0-9a-fA-F-]{36}\.toml\Z')
JOB = re.compile(r'job\.[A-Za-z0-9]+\Z')


def candidates(processed, days, now):
    cutoff = now - days * 86400
    if processed.is_symlink():
        raise ValueError('processed no puede ser un enlace simbólico.')
    if not processed.is_dir():
        return
    for job in sorted(processed.iterdir()):
        if job.is_symlink() or not job.is_dir() or not JOB.fullmatch(job.name):
            continue
        files = list(job.iterdir())
        if len(files) != 2 or any(p.is_symlink() or not p.is_file() for p in files):
            continue
        log = job / 'resultado.log'
        captures = [p for p in files if TOML.fullmatch(p.name)]
        if not log.is_file() or len(captures) != 1:
            continue
        # Un log reciente retiene un TOML viejo importado o reenviado hoy.
        if max(p.stat().st_mtime for p in [job, *files]) >= cutoff:
            continue
        if log.stat().st_size > 128 or log.read_bytes().strip() not in (b'INSERTADO', b'YA_PROCESADO'):
            continue
        yield job, captures[0], log


def clean(data, days=30, apply=False, now=None):
    if days < 7:
        raise ValueError('La retención mínima es de siete días.')
    if data.is_symlink():
        raise ValueError('El directorio de datos no puede ser un enlace simbólico.')
    if not data.is_dir():
        raise ValueError('No existe el directorio de datos.')
    count = 0
    with (data / '.limpieza.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for job, capture, log in candidates(data / 'processed', days, now if now is not None else time.time()):
            if apply:
                # Sin borrado recursivo: cualquier contenido inesperado se conserva.
                capture.unlink()
                log.unlink()
                job.rmdir()
            count += 1
            print(('Eliminado: ' if apply else 'Se eliminaría: ') + job.name)
    print(f'Trabajos {"eliminados" if apply else "elegibles"}: {count}; retención: {days} días.')
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dias', type=int, default=30)
    parser.add_argument('--aplicar', action='store_true', help='Eliminar; sin esta opción solo simula')
    args = parser.parse_args()
    try:
        clean(ROOT / 'var', args.dias, args.aplicar)
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1, 'No se completó la limpieza: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
