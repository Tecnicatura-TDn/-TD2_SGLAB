"""Diagnóstico SSH y conservación de pendientes, sin conexión de red."""
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('recopilar_envio',Path(__file__).resolve().parents[1]/'client/recopilar.py')
client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
NAME='SGLAB-12345678-1234-1234-1234-123456789abc.toml'


class EnvioSsh(unittest.TestCase):
    def args(self, root):
        return SimpleNamespace(salida=Path(root),usuario='carga',servidor='servidor.example',puerto_ssh=22,
            directorio_remoto='/srv/sglab/incoming',clave=None,known_hosts=None,reintentos=2,espera=0)

    def test_known_errors_do_not_expose_remote_output(self):
        for detail, expected in [
            ('Permission denied (publickey).','Autenticación'),
            ('REMOTE HOST IDENTIFICATION HAS CHANGED!','identidad'),
            ('Connection refused','rechazada'),('Could not resolve hostname','DNS'),
            ('Connection timed out','inaccesible'),('SGLAB_DESTINO_NO_EXISTE','no existe'),
            ('SGLAB_DESTINO_SIN_PERMISOS','permisos'),('Permission denied','permisos'),
            ('No space left on device','espacio'),('subsystem request failed','SFTP'),
            ('UNPROTECTED PRIVATE KEY FILE','clave'),('Connection reset','interrumpió'),
        ]:
            error=subprocess.CalledProcessError(255,['ssh','SECRETO-ARG'],stderr=(detail+'\nSECRETO-REMOTO').encode())
            message=client.diagnostico_envio(error)
            self.assertIn(expected,message);self.assertNotIn('SECRETO',message)
        message=client.diagnostico_envio(subprocess.CalledProcessError(42,['SECRETO'],stderr=b'DATO PRIVADO'))
        self.assertIn('42',message);self.assertNotIn('PRIVADO',message)
        self.assertIn('espera',client.diagnostico_envio(subprocess.TimeoutExpired(['SECRETO'],10)))
        self.assertNotIn('SECRETO',client.diagnostico_envio(FileNotFoundError('SECRETO')))

    def test_preflight_failure_keeps_capture_and_skips_scp(self):
        with tempfile.TemporaryDirectory() as root:
            args=self.args(root);capture=Path(root)/NAME;capture.write_text('captura')
            error=subprocess.CalledProcessError(40,['ssh'],stderr=b'SGLAB_DESTINO_NO_EXISTE\nSECRETO')
            output=io.StringIO()
            with patch.object(client.subprocess,'run',side_effect=error) as run, contextlib.redirect_stderr(output):
                self.assertEqual(client.enviar_pendientes(args),1)
            self.assertEqual(run.call_count,2)
            self.assertTrue(all(call.args[0][0]=='ssh' for call in run.call_args_list))
            self.assertTrue(capture.exists());self.assertFalse((Path(root)/'enviados'/NAME).exists())
            self.assertIn('Verificación del destino',output.getvalue());self.assertNotIn('SECRETO',output.getvalue())

    def test_success_and_failed_publication(self):
        with tempfile.TemporaryDirectory() as root:
            args=self.args(root);args.reintentos=1
            capture=Path(root)/NAME;capture.write_text('captura')
            with patch.object(client.subprocess,'run') as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(client.enviar_pendientes(args),0)
            self.assertEqual([call.args[0][0] for call in run.call_args_list],['ssh','scp','ssh'])
            self.assertTrue((Path(root)/'enviados'/NAME).exists());self.assertFalse(capture.exists())
            capture.write_text('otra captura')
            error=subprocess.CalledProcessError(1,['ssh'],stderr=b'Permission denied\nSECRETO')
            output=io.StringIO()
            with patch.object(client.subprocess,'run',side_effect=[None,None,error]), contextlib.redirect_stderr(output):
                self.assertEqual(client.enviar_pendientes(args),1)
            self.assertTrue(capture.exists());self.assertIn('Publicación de la captura',output.getvalue())
            self.assertNotIn('SECRETO',output.getvalue())


if __name__=='__main__':unittest.main()
