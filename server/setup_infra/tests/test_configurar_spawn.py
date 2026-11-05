"""Generación portable de unidades; no instala ni inicia servicios."""
import contextlib
import grp
import importlib.util
import io
import os
from pathlib import Path
import pwd
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('configurar_spawn', Path(__file__).resolve().parents[1]/'infra/configurar-spawn.py')
configurar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configurar)


class ConfigurarSpawn(unittest.TestCase):
    def test_unidad_utiliza_usuario_y_ruta_del_destino(self):
        project = Path('/home/sebapancho/SGLAB')
        text = configurar.unidad(project, 'sebapancho', '/usr/bin/bash')
        self.assertIn('User=sebapancho\n', text)
        self.assertIn('WorkingDirectory=/home/sebapancho/SGLAB\n', text)
        self.assertIn('SGLAB_TOMLQ=/home/sebapancho/SGLAB/.venv/bin/tomlq', text)
        self.assertIn('SGLAB_DB_CONFIG=/etc/sglab/ingest.cnf', text)
        self.assertNotIn('SupplementaryGroups=docker', text)
        self.assertIn('NoNewPrivileges=true', text)
        self.assertIn('ProtectSystem=strict', text)
        self.assertIn('ConditionPathExists=/etc/sglab/ingest.cnf', text)
        self.assertNotIn('facu', text)
        self.assertNotIn('sglab-ingest', text)

    def test_no_requiere_grupos_que_no_existen_y_escapa_porcentajes(self):
        text = configurar.unidad(Path('/srv/Proyecto 50%'), 'asistente', '/bin/bash')
        self.assertNotIn('SupplementaryGroups=', text)
        self.assertIn('WorkingDirectory=/srv/Proyecto 50%%\n', text)

    def test_genera_archivo_sin_instalar_el_servicio(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('compose.yaml', 'server/bin/spawn.sh'):
                path = root/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('prueba')
            parser = root/'.venv/bin/tomlq'
            parser.parent.mkdir(parents=True)
            parser.write_text('#!/bin/sh\nexit 0\n')
            parser.chmod(0o700)
            user = pwd.getpwuid(os.getuid())
            if user.pw_uid == 0:
                self.skipTest('La generación necesita una cuenta de servicio no root')
            with patch.object(sys, 'argv', ['configurar-spawn.py', '--usuario', user.pw_name, '--proyecto', str(root)]), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(configurar.main(), 0)
            text = (root/'var/systemd/sglab-spawn.service').read_text()
            self.assertIn('User='+user.pw_name+'\n', text)
            self.assertIn(str(root/'.venv/bin/tomlq'), text)
            self.assertNotIn('SupplementaryGroups=', text)

    def test_usuario_inexistente_se_rechaza_antes_de_generar(self):
        with patch.object(sys, 'argv', ['configurar-spawn.py', '--usuario', 'inexistente']), \
                patch.object(configurar.pwd, 'getpwnam', side_effect=KeyError('inexistente')), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as failure:
                configurar.main()
            self.assertEqual(failure.exception.code, 1)


if __name__ == '__main__':
    unittest.main()
