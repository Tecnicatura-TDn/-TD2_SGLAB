#!/usr/bin/env python3
"""Genera un servicio y timer systemd diario para los respaldos de este servidor."""
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
    args = parser.parse_args()
    user = pwd.getpwnam(args.usuario)
    if user.pw_uid == 0:
        parser.error('Usar el usuario del proyecto con acceso a Docker, no root.')
    destination = ROOT / 'var/systemd'
    destination.mkdir(parents=True, exist_ok=True)
    service = f'''[Unit]
Description=SGLAB - Respaldo privado de base, MFA y HTTPS
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
User={user.pw_name}
SupplementaryGroups=docker
ExecStart={quote(sys.executable)} {quote(ROOT / 'infra/respaldos.py')} crear
UMask=0077
TimeoutStartSec=30min
'''
    timer = '''[Unit]
Description=SGLAB - Respaldo diario a las 03:00 (hora local del servidor)

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=5min
Unit=sglab-backup.service

[Install]
WantedBy=timers.target
'''
    for name, content in [('sglab-backup.service', service), ('sglab-backup.timer', timer)]:
        path = destination / name
        path.write_text(content)
        path.chmod(0o644)
    print('Unidades generadas en', destination)
    print('Instalar ambas unidades en /etc/systemd/system, ejecutar daemon-reload y enable --now sglab-backup.timer.')


if __name__ == '__main__':
    main()
