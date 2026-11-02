"""Limpieza aislada de trabajos confirmados; nunca usar carpetas reales."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('limpieza', Path(__file__).resolve().parents[1] / 'infra/limpiar-toml.py')
limpieza = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limpieza)
NOW = 1800000000
OLD = NOW - 31 * 86400
NAME = 'SGLAB-12345678-1234-1234-1234-123456789abc.toml'


class Limpieza(unittest.TestCase):
    def job(self, root, folder='processed', suffix='antiguo', result=b'INSERTADO\n'):
        job = root / folder / ('job.' + suffix)
        job.mkdir(parents=True)
        (job / NAME).write_text('captura')
        (job / 'resultado.log').write_bytes(result)
        for path in [*job.iterdir(), job]:
            os.utime(path, (OLD, OLD))
        return job

    def test_only_confirmed_old_jobs_and_dry_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = self.job(root)
            duplicate = self.job(root, suffix='duplicado', result=b'YA_PROCESADO\n')
            protected = [self.job(root, folder=f) for f in ['incoming', 'processing', 'rejected']]
            recent = self.job(root, suffix='reciente')
            os.utime(recent / 'resultado.log', (NOW, NOW))
            failed = self.job(root, suffix='fallido', result='Falló\n'.encode())
            extra = self.job(root, suffix='extra'); (extra / 'conservar.txt').write_text('dato')
            os.utime(extra, (OLD, OLD))
            linked = self.job(root, suffix='enlace')
            (linked / NAME).unlink(); (linked / NAME).symlink_to(protected[0] / NAME)
            os.utime(linked, (OLD, OLD))
            (root / 'processed/job.externos').symlink_to(protected[0], target_is_directory=True)
            self.assertEqual(limpieza.clean(root, now=NOW), 2)
            self.assertTrue(old.exists())
            self.assertEqual(limpieza.clean(root, apply=True, now=NOW), 2)
            self.assertFalse(old.exists()); self.assertFalse(duplicate.exists())
            for path in [*protected, recent, failed, extra, linked]:
                self.assertTrue(path.exists())
            self.assertEqual(limpieza.clean(root, apply=True, now=NOW), 0)

    def test_refuses_symlinked_processed_and_short_retention(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / 'rejected'; target.mkdir()
            (root / 'processed').symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                limpieza.clean(root, apply=True, now=NOW)
            with self.assertRaises(ValueError):
                limpieza.clean(root, days=0)


if __name__ == '__main__':
    unittest.main()
