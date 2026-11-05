import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('ingesta', Path(__file__).resolve().parents[1]/'infra/configurar-ingesta.py')
ingesta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingesta)


class ConfiguracionIngesta(unittest.TestCase):
    def config(self, host='127.0.0.1'):
        return {'services': {'db': {'ports': [{'target': 3306, 'published': '3307', 'host_ip': host}],
            'environment': {'DB_INGEST_USER': 'sglab_ingest', 'DB_INGEST_PASSWORD': 'a"b\\c#d',
                            'DB_APP_PASSWORD': 'NO_EXPORTAR', 'MARIADB_ROOT_PASSWORD': 'NO_EXPORTAR'}}}}

    def test_exporta_solo_ingesta_y_escapa_opciones(self):
        result = ingesta.client_config(self.config())
        self.assertIn('port="3307"', result)
        self.assertIn('password="a\\"b\\\\c#d"', result)
        self.assertNotIn('NO_EXPORTAR', result)
        self.assertNotIn('root', result)

    def test_rechaza_publicacion_externa(self):
        with self.assertRaises(ValueError):
            ingesta.client_config(self.config('0.0.0.0'))
