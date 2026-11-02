"""Retención y publicación de respaldos, sin tocar Docker ni datos reales."""
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('respaldos', Path(__file__).resolve().parents[1] / 'infra/respaldos.py')
respaldos = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(respaldos)


class Respaldos(unittest.TestCase):
    def setup_project(self, root):
        (root / '.env').write_text('CONFIGURACION DE PRUEBA')
        for name in ['pki', 'tls']:
            (root / 'var' / name).mkdir(parents=True)
            (root / 'var' / name / 'test.key').write_text('CLAVE DE PRUEBA')
        dest = root / 'var/backups/automaticos'
        dest.mkdir(parents=True)
        for name in ['sglab-antiguo.tar.gz', 'manual.tar.gz', 'sglab-reciente.tar.gz']:
            (dest / name).write_text('anterior')
        for name in ['sglab-antiguo.tar.gz', 'manual.tar.gz']:
            os.utime(dest / name, (time.time() - 8*86400,) * 2)
        return dest

    @staticmethod
    def docker_stub(args, **kwargs):
        if 'mariadb-dump' in ' '.join(args):
            kwargs['stdout'].write(b'CREATE DATABASE sglab;\n')
        else:
            with tarfile.open(fileobj=kwargs['stdout'], mode='w') as bundle:
                data = b'k' * 32
                info = tarfile.TarInfo('./totp-key.bin'); info.size = len(data)
                bundle.addfile(info, io.BytesIO(data))

    def test_complete_backup_and_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dest = self.setup_project(root)
            with patch.object(respaldos, 'ROOT', root), patch.object(respaldos, 'run', self.docker_stub):
                result = respaldos.backup()
            self.assertEqual(result.stat().st_mode & 0o777, 0o600)
            self.assertEqual(dest.stat().st_mode & 0o777, 0o700)
            self.assertFalse((dest / 'sglab-antiguo.tar.gz').exists())
            self.assertTrue((dest / 'manual.tar.gz').exists())
            self.assertTrue((dest / 'sglab-reciente.tar.gz').exists())
            with tarfile.open(result) as bundle:
                import json
                manifest = json.load(bundle.extractfile('manifest.json'))
                respaldos.validate(bundle, manifest)
                self.assertIn('.env', manifest['files_sha256'])
                self.assertIn('var/pki/test.key', manifest['files_sha256'])
                manifest['files_sha256']['database.sql'] = 'invalid'
                with self.assertRaises(RuntimeError):
                    respaldos.validate(bundle, manifest)

    def test_failure_preserves_previous_and_does_not_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); dest = self.setup_project(root)
            with patch.object(respaldos, 'ROOT', root), patch.object(respaldos, 'run', side_effect=subprocess.CalledProcessError(1, 'docker')):
                with self.assertRaises(subprocess.CalledProcessError):
                    respaldos.backup()
            self.assertTrue((dest / 'sglab-antiguo.tar.gz').exists())
            self.assertEqual(len(list(dest.glob('*.tar.gz'))), 3)
            self.assertFalse(list(dest.glob('.backup-*')))


if __name__ == '__main__':
    unittest.main()
