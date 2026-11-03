"""Flujo del instalador por usuario, sin modificar Windows ni conectar por SSH."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'configurar_instalacion', Path(__file__).resolve().parents[1] / 'client/configurar.py')
configurar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(configurar)


class InstalacionUsuario(unittest.TestCase):
    def instalar(self, carpeta, reanudar=True, error_ssh=False, error_tareas=False,
                 servidor='servidor.example'):
        carpeta = Path(carpeta)
        comandos = []

        def ejecutar(*args):
            comandos.append(args)
            if args[0] == 'ssh-keygen':
                clave = Path(args[-1])
                clave.write_text('CLAVE-DE-PRUEBA\n')
                Path(str(clave)+'.pub').write_text('ssh-ed25519 AAAATEST\n')
            elif args[0] == 'powershell.exe':
                if error_tareas:
                    raise subprocess.CalledProcessError(1, 'powershell.exe')
            else:
                raise AssertionError('Comando inesperado: '+str(args[0]))

        args = ['configurar.py', '--instalar', '--por-usuario', '--destino', str(carpeta),
                '--servidor', servidor, '--usuario', 'receptor', '--puerto-ssh', '22',
                '--directorio-remoto', '/srv/sglab/incoming', '--laboratorio', 'LAB01']
        if reanudar:
            args.append('--reanudar')
        salida, errores = io.StringIO(), io.StringIO()
        with patch.object(sys, 'argv', args), \
                patch.dict(os.environ, {'LOCALAPPDATA': str(carpeta.parent)}), \
                patch.object(configurar.platform, 'system', return_value='Windows'), \
                patch.object(configurar.platform, 'node', return_value='PC-PRUEBA'), \
                patch.object(configurar.shutil, 'which', return_value='/prueba/ssh'), \
                patch.object(configurar, 'proteger') as proteger, \
                patch.object(configurar, 'ejecutar', side_effect=ejecutar), \
                patch.object(configurar, 'autorizar_clave', side_effect=(
                    subprocess.CalledProcessError(255, 'ssh') if error_ssh else None)) as autorizar, \
                patch.object(configurar.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = configurar.main()
        return codigo, comandos, proteger, autorizar, salida.getvalue()+errores.getvalue()

    def test_fallo_ssh_conserva_configuracion_y_permite_captura_local(self):
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            codigo, comandos, _, _, salida = self.instalar(destino, error_ssh=True)
            self.assertEqual(codigo, 1)
            datos = json.loads((destino/'cliente.json').read_text())
            self.assertEqual(datos['servidor'], 'servidor.example')
            self.assertEqual(datos['salida'], str(destino/'pendientes'))
            self.assertTrue((destino/'client/recopilar.py').is_file())
            self.assertTrue((destino/'client/ventana.py').is_file())
            self.assertIn('Se conserva la configuración local', salida)
            self.assertFalse(any(comando[0]=='powershell.exe' for comando in comandos))

    def test_reanuda_sin_regenerar_claves_ni_perder_datos_personalizados(self):
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            self.instalar(destino, error_ssh=True)
            clave = (destino/'id_ed25519').read_bytes()
            hosts = b'servidor.example ssh-ed25519 AAAATEST\n'
            (destino/'known_hosts').write_bytes(hosts)
            config = destino/'cliente.json'
            datos = json.loads(config.read_text())
            datos.update(ci=12345678, espera=7)
            config.write_text(json.dumps(datos))
            original = config.read_bytes()
            codigo, comandos, _, _, _ = self.instalar(destino)
            self.assertEqual(codigo, 0)
            self.assertEqual((destino/'id_ed25519').read_bytes(), clave)
            self.assertEqual((destino/'known_hosts').read_bytes(), hosts)
            self.assertEqual(config.read_bytes(), original)
            self.assertFalse(any(comando[0]=='ssh-keygen' for comando in comandos))
            tareas = [comando for comando in comandos if comando[0]=='powershell.exe']
            self.assertEqual(len(tareas), 1)
            self.assertIn('-PorUsuario', tareas[0])

    def test_recupera_instalacion_anterior_sin_json(self):
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            destino.mkdir()
            (destino/'id_ed25519').write_bytes(b'CLAVE-EXISTENTE')
            (destino/'known_hosts').write_bytes(b'HOST-EXISTENTE')
            codigo, comandos, _, _, _ = self.instalar(destino)
            self.assertEqual(codigo, 0)
            self.assertTrue((destino/'cliente.json').is_file())
            self.assertEqual((destino/'id_ed25519').read_bytes(), b'CLAVE-EXISTENTE')
            self.assertEqual((destino/'known_hosts').read_bytes(), b'HOST-EXISTENTE')
            self.assertFalse(any(comando[0]=='ssh-keygen' for comando in comandos))

    def test_error_de_tareas_se_puede_reintentar_sin_perder_configuracion(self):
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            codigo, _, _, _, _ = self.instalar(destino, error_tareas=True)
            self.assertEqual(codigo, 1)
            config = (destino/'cliente.json').read_bytes()
            codigo, _, _, _, _ = self.instalar(destino)
            self.assertEqual(codigo, 0)
            self.assertEqual((destino/'cliente.json').read_bytes(), config)

    def test_no_cambia_servidor_existente_al_reanudar(self):
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            self.instalar(destino, error_ssh=True)
            config = (destino/'cliente.json').read_bytes()
            clave = (destino/'id_ed25519').read_bytes()
            codigo, comandos, proteger, autorizar, _ = self.instalar(destino, servidor='otro.example')
            self.assertEqual(codigo, 1)
            self.assertEqual((destino/'cliente.json').read_bytes(), config)
            self.assertEqual((destino/'id_ed25519').read_bytes(), clave)
            self.assertEqual(comandos, [])
            proteger.assert_not_called()
            autorizar.assert_not_called()

    def test_rechaza_carpeta_desconocida_y_reinstalacion_sin_reanudar(self):
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            destino.mkdir()
            ajeno = destino/'datos-del-usuario.txt'
            ajeno.write_text('Conservar')
            codigo, comandos, proteger, autorizar, _ = self.instalar(destino)
            self.assertEqual(codigo, 1)
            self.assertEqual(ajeno.read_text(), 'Conservar')
            self.assertEqual(comandos, [])
            proteger.assert_not_called()
            autorizar.assert_not_called()
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            self.instalar(destino)
            codigo, comandos, _, autorizar, _ = self.instalar(destino, reanudar=False)
            self.assertEqual(codigo, 1)
            self.assertEqual(comandos, [])
            autorizar.assert_not_called()

    def test_permisos_windows_incluyen_usuario_en_la_misma_operacion(self):
        with patch.object(configurar.subprocess, 'check_output', return_value='"EQUIPO\\usuario","S-1-5-21-123-456-789-1001"\n'), \
                patch.object(configurar, 'ejecutar') as ejecutar:
            configurar.proteger(Path('carpeta'), True, permitir_usuario=True)
        ejecutar.assert_called_once_with('icacls', Path('carpeta'), '/inheritance:r', '/grant:r',
                                        '*S-1-5-18:(OI)(CI)F', '*S-1-5-32-544:(OI)(CI)F',
                                        '*S-1-5-21-123-456-789-1001:(OI)(CI)F')

    def test_reanudar_rechaza_enlaces_en_los_archivos_del_cliente(self):
        with tempfile.TemporaryDirectory() as temporal:
            destino = Path(temporal)/'SGLAB'
            self.instalar(destino, error_ssh=True)
            externo = Path(temporal)/'archivo-externo.py'
            externo.write_text('conservar')
            script = destino/'client/recopilar.py'
            script.unlink()
            try:
                script.symlink_to(externo)
            except OSError:
                self.skipTest('El sistema no permite crear enlaces simbólicos')
            codigo, comandos, proteger, autorizar, _ = self.instalar(destino)
            self.assertEqual(codigo, 1)
            self.assertEqual(externo.read_text(), 'conservar')
            self.assertEqual(comandos, [])
            proteger.assert_not_called()
            autorizar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
