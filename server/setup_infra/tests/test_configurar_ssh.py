"""Pruebas locales de autorización SSH, sin conectar a servidores reales."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('configurar', Path(__file__).resolve().parents[1]/'client/configurar.py')
configurar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configurar)


class AutorizacionSSH(unittest.TestCase):
    def test_publica_permisos_duplicados_y_autenticacion(self):
        with tempfile.TemporaryDirectory() as carpeta:
            base = Path(carpeta)
            clave = base/'id_ed25519'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(clave)], check=True)
            hosts = base/'known_hosts'
            hosts.touch()
            remoto = base/'home-remoto'
            remoto.mkdir()
            comandos = []
            real_run = subprocess.run

            def ssh_simulado(comando, **kwargs):
                if comando[0] != 'ssh':
                    return real_run(comando, **kwargs)
                comandos.append(comando)
                if comando[-1] != 'true':
                    return real_run(['sh', '-c', comando[-1]], env=dict(os.environ, HOME=str(remoto)), check=True)
                return subprocess.CompletedProcess(comando, 0)

            valores = dict(servidor='servidor.example', usuario='sglab_upload', puerto_ssh=2222)
            with patch.object(configurar.subprocess, 'run', side_effect=ssh_simulado):
                configurar.autorizar_clave(valores, clave, hosts)
                configurar.autorizar_clave(valores, clave, hosts)
            auth = remoto/'.ssh/authorized_keys'
            publica = subprocess.check_output(['ssh-keygen', '-y', '-f', str(clave)], text=True).strip()
            self.assertEqual(auth.read_text().splitlines().count(publica), 1)
            self.assertEqual(auth.stat().st_mode & 0o777, 0o600)
            self.assertEqual(auth.parent.stat().st_mode & 0o777, 0o700)
            self.assertNotIn('PRIVATE KEY', auth.read_text())
            self.assertIn('PreferredAuthentications=password', comandos[0])
            self.assertIn('StrictHostKeyChecking=ask', comandos[0])
            self.assertIn('BatchMode=yes', comandos[1])
            self.assertIn('StrictHostKeyChecking=yes', comandos[1])

    def test_fallo_password_no_prueba_clave(self):
        with patch.object(configurar.subprocess, 'check_output', return_value='ssh-ed25519 AAAATEST'), patch.object(
            configurar.subprocess, 'run', side_effect=subprocess.CalledProcessError(255, 'ssh')) as ejecutar:
            with self.assertRaises(subprocess.CalledProcessError):
                configurar.autorizar_clave(dict(servidor='host',usuario='user',puerto_ssh=22), Path('/clave'), Path('/hosts'))
            self.assertEqual(ejecutar.call_count, 1)


if __name__ == '__main__':
    unittest.main()
