"""Ejercita la cola y el transporte SQL sin tocar una BD ni Docker reales."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('jq'), 'Requiere jq')
class SpawnLocal(unittest.TestCase):
    def test_confirmacion_sql_y_rechazo_sin_docker(self):
        for status in (0, 1):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                bin_dir = root/'bin'
                bin_dir.mkdir()
                data = root/'data'
                (data/'incoming').mkdir(parents=True)
                identity = '11111111-1111-4111-8111-111111111111'
                capture = {'meta': {'id_ejecucion': identity, 'version_formato': '1.1',
                    'version_script': 'test', 'codigo_laboratorio': 'LAB01', 'ci_reportada': 0,
                    'fecha_evento': '2026-11-04T00:00:00Z'}, 'equipo': {}, 'hardware': {},
                    'red': {}, 'perifericos': {}, 'diagnostico': {'errores_lectura': []}}
                # Sustituir únicamente parser y conexión; se ejecutan jq y spawn reales.
                (data/'incoming'/f'SGLAB-{identity}.toml').write_text(json.dumps(capture))
                scripts = {'tomlq': '#!/bin/sh\ncat "$2"\n',
                    'docker': '#!/bin/sh\nexit 99\n',
                    'mariadb': f'''#!/bin/sh
[ "$1" = "--defaults-file=$SGLAB_DB_CONFIG" ] || exit 98
cat > "$SQL_CAPTURE"
[ {status} = 0 ] || exit 1
printf 'INSERTADO\\n'
'''}
                for name, script in scripts.items():
                    path = bin_dir/name
                    path.write_text(script)
                    path.chmod(0o755)
                config = root/'ingest.cnf'
                config.write_text('[client]\n')
                env = dict(os.environ, PATH=str(bin_dir)+':'+os.environ['PATH'],
                    SGLAB_DATA_DIR=str(data), SGLAB_DB_CONFIG=str(config),
                    SGLAB_TOMLQ=str(bin_dir/'tomlq'), SQL_CAPTURE=str(root/'sql'))
                subprocess.run(['bash', str(ROOT/'server/bin/spawn.sh'), '--once'],
                    env=env, check=True, capture_output=True, timeout=20)
                destination = data/('processed' if status == 0 else 'rejected')
                self.assertEqual(len(list(destination.glob('job.*/*.toml'))), 1)
                self.assertIn('INSERT INTO registro', (root/'sql').read_text())
