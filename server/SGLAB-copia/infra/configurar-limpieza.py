#!/usr/bin/env python3
"""Genera el servicio y timer diario de limpieza de TOML procesados."""
import argparse
import os
from pathlib import Path
import pwd
import sys

ROOT = Path(__file__).resolve().parents[1]


def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usuario', default=os.environ.get('SUDO_USER') or pwd.getpwuid(os.getuid()).pw_name)
    parser.add_argument('--dias', type=int, default=30)
    args = parser.parse_args()
    user = pwd.getpwnam(args.usuario)
    if user.pw_uid == 0 or args.dias < 7:
        parser.error('Indicar usuario del proyecto (no root) y retención de al menos siete días.')
    destination = ROOT / 'var/systemd'
    destination.mkdir(parents=True, exist_ok=True)
    service = f'''[Unit]
Description=SGLAB - Limpieza de TOML procesados y confirmados

[Service]
Type=oneshot
User={user.pw_name}
ExecStart={quote(sys.executable)} {quote(ROOT / 'infra/limpiar-toml.py')} --dias {args.dias} --aplicar
UMask=0077
NoNewPrivileges=true
TimeoutStartSec=15min
'''
    timer = '''[Unit]
Description=SGLAB - Limpieza diaria de TOML a las 04:00

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true
RandomizedDelaySec=5min
Unit=sglab-limpieza.service

[Install]
WantedBy=timers.target
'''
    for name, content in [('sglab-limpieza.service', service), ('sglab-limpieza.timer', timer)]:
        path = destination / name
        path.write_text(content)
        path.chmod(0o644)
    print('Unidades generadas en', destination)


if __name__ == '__main__':
    main()
