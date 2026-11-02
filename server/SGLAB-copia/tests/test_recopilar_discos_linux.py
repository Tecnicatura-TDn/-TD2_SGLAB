"""Regresiones de inventario Linux: zram, particiones y volúmenes montados."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'recopilar_discos_linux', Path(__file__).resolve().parents[1] / 'client/recopilar.py')
recopilar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recopilar)


def dispositivo(nombre, tipo='disk', size=512_110_190_592, rota=False,
                mountpoints=None, children=None):
    nodo = dict(name=nombre, type=tipo, size=size, rota=rota,
                mountpoints=mountpoints or [None])
    if children is not None:
        nodo['children'] = children
    return nodo


class DiscosLinux(unittest.TestCase):
    def capturar(self, devices, mounts):
        captura = recopilar.Captura('PRUEBA', 0)

        def stat(path):
            if path not in mounts:
                raise FileNotFoundError(path)
            value = mounts[path]
            if isinstance(value, OSError):
                raise value
            return SimpleNamespace(st_dev=value[0])

        def statvfs(path):
            return SimpleNamespace(f_bavail=mounts[path][1] // 4096, f_frsize=4096)

        with patch.object(recopilar, 'ejecutar', return_value=json.dumps({'blockdevices': devices})), \
                patch.object(recopilar.os, 'stat', side_effect=stat) as read_stat, \
                patch.object(recopilar.os, 'statvfs', side_effect=statvfs, create=True) as read_free:
            captura.leer('hardware', 'discos', captura.discos_linux, 'hardware.discos')
        return captura, read_stat, read_free

    def test_fedora_zram_y_nvme_dual_boot(self):
        # Windows sin montar y Linux en el mismo SSD: no son discos adicionales.
        devices = [
            dispositivo('zram0', size=8_589_934_592, mountpoints=['[SWAP]']),
            dispositivo('nvme0n1', children=[
                dispositivo('nvme0n1p1', 'part'),
                dispositivo('nvme0n1p2', 'part'),
                dispositivo('nvme0n1p3', 'part', mountpoints=['/']),
            ]),
        ]
        captura, stat, _ = self.capturar(devices, {'/': (10, 134_960_000_000)})
        self.assertEqual(captura.datos['hardware']['discos'], [dict(
            orden=0, capacidad_total_gb=512.11, tipo='SSD', espacio_libre_gb=134.96)])
        self.assertEqual(captura.errores, [])
        stat.assert_called_once_with('/')
        # El formato del archivo que recibe spawn.sh conserva la misma tabla.
        captura.datos['diagnostico']['errores_lectura'] = captura.errores
        toml = recopilar.serializar(captura.datos)
        self.assertEqual(toml.count('[[hardware.discos]]'), 1)
        self.assertIn('version_formato = "1.1"', toml)
        self.assertIn('errores_lectura = []', toml)

    def test_excluye_virtuales_y_conserva_nvme_sata_y_virtio(self):
        devices = [dispositivo(name, size=8_589_934_592, mountpoints=['[SWAP]'])
                   for name in ('zram0', '/dev/zram12', 'ram0', '/dev/ram9', 'loop0')]
        devices += [
            dispositivo('sda', rota=True, mountpoints=['/datos']),
            dispositivo('sda1', 'part', mountpoints=['/datos']),
            dispositivo('mapper-volumen', 'lvm', mountpoints=['/datos']),
            dispositivo('sr0', 'rom'),
            dispositivo('nvme0n1', mountpoints=['/']),
            dispositivo('vda', mountpoints=['/vm']),
        ]
        captura, stat, _ = self.capturar(devices, {
            '/datos': (11, 20_000_000_000), '/': (12, 30_000_000_000), '/vm': (13, 40_000_000_000)})
        disks = captura.datos['hardware']['discos']
        self.assertEqual([disk['orden'] for disk in disks], [0, 1, 2])
        self.assertEqual([disk['tipo'] for disk in disks], ['HDD', 'SSD', 'SSD'])
        self.assertEqual([disk['espacio_libre_gb'] for disk in disks], [20.0, 30.0, 40.0])
        self.assertEqual(captura.errores, [])
        self.assertEqual([call.args[0] for call in stat.call_args_list], ['/datos', '/', '/vm'])

    def test_swap_y_lvm_no_invalidan_espacio_libre_del_disco(self):
        devices = [dispositivo('nvme0n1', children=[
            dispositivo('nvme0n1p1', 'part'),
            dispositivo('nvme0n1p2', 'part', children=[
                dispositivo('luks-volumen', 'crypt', children=[
                    dispositivo('fedora-root', 'lvm', mountpoints=['/']),
                    dispositivo('fedora-swap', 'lvm', mountpoints=['[SWAP]']),
                ]),
            ]),
        ])]
        captura, stat, _ = self.capturar(devices, {'/': (20, 31_000_000_000)})
        self.assertEqual(len(captura.datos['hardware']['discos']), 1)
        self.assertEqual(captura.datos['hardware']['discos'][0]['espacio_libre_gb'], 31.0)
        self.assertEqual(captura.errores, [])
        stat.assert_called_once_with('/')

    def test_bind_mount_no_duplica_el_espacio_libre(self):
        devices = [dispositivo('sda', mountpoints=['/', '/mnt/raiz'])]
        captura, _, free = self.capturar(devices, {
            '/': (30, 25_000_000_000), '/mnt/raiz': (30, 25_000_000_000)})
        self.assertEqual(captura.datos['hardware']['discos'][0]['espacio_libre_gb'], 25.0)
        self.assertEqual(captura.errores, [])
        free.assert_called_once_with('/')

    def test_disco_real_sin_montajes_conserva_la_lectura_no_disponible(self):
        captura, _, _ = self.capturar([
            dispositivo('zram0', mountpoints=['[SWAP]']), dispositivo('sda', rota=True)], {})
        self.assertEqual(captura.datos['hardware']['discos'], [dict(
            orden=0, capacidad_total_gb=512.11, tipo='HDD')])
        self.assertEqual([error['campo'] for error in captura.errores],
                         ['hardware.discos[0].espacio_libre_gb'])

    def test_no_oculta_un_error_real_al_leer_un_montaje(self):
        captura, _, _ = self.capturar([dispositivo('nvme0n1', mountpoints=['/'])],
                                     {'/': PermissionError('Sin acceso')})
        self.assertEqual(len(captura.datos['hardware']['discos']), 1)
        self.assertNotIn('espacio_libre_gb', captura.datos['hardware']['discos'][0])
        self.assertEqual([error['campo'] for error in captura.errores],
                         ['hardware.discos[0].espacio_libre_gb'])


if __name__ == '__main__':
    unittest.main()
