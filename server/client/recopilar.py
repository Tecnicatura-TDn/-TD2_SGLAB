#!/usr/bin/env python3
"""Captura técnica Linux/Windows en el contrato SGLAB TOML v1.1."""
import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shlex
import time
import socket
import subprocess
import sys
import tempfile
import uuid


def ejecutar(*args):
    resultado = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                               errors='replace', timeout=30, check=True)
    return resultado.stdout.strip()


def powershell(codigo):
    return json.loads(ejecutar('powershell.exe', '-NoProfile', '-NonInteractive',
                              '-Command', "[Console]::OutputEncoding = [Text.UTF8Encoding]::new(); "
                              "$ErrorActionPreference='Stop'; " + codigo + ' | ConvertTo-Json -Depth 8 -Compress'))


def texto(ruta):
    valor = Path(ruta).read_text().strip()
    if not valor:
        raise ValueError('Lectura vacía')
    return valor


def gb(valor):
    # GB decimales, coherentes con las unidades del contrato.
    return round(int(valor) / 1_000_000_000, 2)


def lista(valor):
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


class Captura:
    def __init__(self, laboratorio, ci):
        self.datos = {s: {} for s in ('meta', 'equipo', 'hardware', 'red', 'perifericos', 'diagnostico')}
        self.errores = []
        self.datos['meta'] = dict(id_ejecucion=str(uuid.uuid4()), version_formato='1.1',
                                 version_script='1.1.0', fecha_evento=datetime.now(timezone.utc).isoformat(timespec='seconds'),
                                 codigo_laboratorio=laboratorio, ci_reportada=ci)

    def leer(self, seccion, campo, funcion, error_campo=None):
        try:
            valor = funcion()
            if valor is None or valor == '':
                raise ValueError('No se pudo determinar')
            self.datos[seccion][campo] = valor
        except (OSError, ValueError, KeyError, IndexError, TypeError, StopIteration, subprocess.SubprocessError) as exc:
            self.errores.append(dict(campo=error_campo or campo,
                                     detalle=(str(exc) or 'No se pudo determinar la lectura')[:255]))

    def linux(self):
        self.leer('equipo', 'serial', lambda: texto('/sys/class/dmi/id/product_serial'))
        self.leer('equipo', 'smbios_uuid', lambda: str(uuid.UUID(texto('/sys/class/dmi/id/product_uuid'))).upper())
        self.leer('hardware', 'cpu', lambda: next(line.split(':', 1)[1].strip() for line in texto('/proc/cpuinfo').splitlines()
                                                if line.startswith(('model name', 'Hardware', 'Processor'))))
        self.leer('hardware', 'ram_total_gb', lambda: gb(int(next(line.split()[1] for line in texto('/proc/meminfo').splitlines()
                                                                          if line.startswith('MemTotal:'))) * 1024))
        self.leer('hardware', 'ethernet_presente', lambda: any(p.name != 'lo' and (p / 'device').exists()
                                                                              and not (p / 'wireless').exists()
                                                                              for p in Path('/sys/class/net').iterdir()))
        self.leer('hardware', 'discos', self.discos_linux, 'hardware.discos')
        self.leer('red', 'ipv4', lambda: self.red_linux()['ipv4'])
        self.leer('red', 'mac', lambda: self.red_linux()['mac'])
        self.leer('red', 'gateway', lambda: self.red_linux()['gateway'])
        self.leer('red', 'dns', lambda: sorted({line.split()[1] for line in texto('/etc/resolv.conf').splitlines()
                                              if line.startswith('nameserver ') and isinstance(ipaddress.ip_address(line.split()[1]), ipaddress.IPv4Address)}))
        self.leer('perifericos', 'teclado', lambda: self.entrada_linux('kbd'))
        self.leer('perifericos', 'mouse', lambda: self.entrada_linux('mouse'))
        self.leer('perifericos', 'monitor', self.monitor_linux)

    def entrada_linux(self, tipo):
        contenido = texto('/proc/bus/input/devices')
        for bloque in contenido.split('\n\n'):
            # Los botones ACPI también exponen el handler kbd.
            if tipo == 'kbd' and any(nombre in bloque.lower() for nombre in
                                     ('power button', 'sleep button', 'video bus', 'lid switch')):
                continue
            for line in bloque.splitlines():
                if line.startswith('H: Handlers='):
                    handlers = line.split('=', 1)[1].split()
                    if tipo == 'kbd' and 'kbd' in handlers:
                        return True
                    if tipo == 'mouse' and any(h.startswith('mouse') for h in handlers):
                        return True
        return False

    def monitor_linux(self):
        estados = list(Path('/sys/class/drm').glob('card*-*/status'))
        if not estados:
            raise ValueError('No hay conectores DRM accesibles')
        return any(texto(p) == 'connected' for p in estados)

    def red_linux(self):
        rutas = json.loads(ejecutar('ip', '-j', '-4', 'route', 'show', 'default'))
        if not rutas:
            raise ValueError('No hay ruta IPv4 predeterminada')
        ruta = min(rutas, key=lambda r: r.get('metric', 0))
        interfaz = json.loads(ejecutar('ip', '-j', '-4', 'address', 'show', 'dev', ruta['dev']))[0]
        direccion = next(a for a in interfaz['addr_info'] if a['family'] == 'inet' and a.get('scope') == 'global')
        return dict(ipv4=f"{direccion['local']}/{direccion['prefixlen']}",
                    mac=texto(Path('/sys/class/net') / ruta['dev'] / 'address').upper(), gateway=ruta.get('gateway'))

    def discos_linux(self):
        dispositivos = json.loads(ejecutar('lsblk', '-J', '-b', '-o', 'NAME,TYPE,SIZE,ROTA,MOUNTPOINTS'))['blockdevices']
        discos = []
        def montajes(nodo):
            yield from (p for p in nodo.get('mountpoints', []) if p)
            for hijo in nodo.get('children', []):
                yield from montajes(hijo)
        for dispositivo in dispositivos:
            if dispositivo['type'] != 'disk':
                continue
            indice = len(discos)
            disco = dict(orden=indice, capacidad_total_gb=gb(dispositivo['size']))
            if dispositivo.get('rota') is not None:
                disco['tipo'] = 'HDD' if dispositivo['rota'] else 'SSD'
            else:
                self.errores.append(dict(campo=f'hardware.discos[{indice}].tipo', detalle='Rotación desconocida'))
            # Espacio libre de sistemas de archivos montados, sin duplicar bind mounts.
            puntos = list(montajes(dispositivo))
            vistos = set()
            libre = 0
            for punto in puntos:
                try:
                    identidad = os.stat(punto).st_dev
                    if identidad in vistos:
                        continue
                    vistos.add(identidad)
                    estado = os.statvfs(punto)
                    libre += estado.f_bavail * estado.f_frsize
                except OSError:
                    vistos.clear()
                    break
            if vistos:
                disco['espacio_libre_gb'] = min(gb(libre), disco['capacidad_total_gb'])
            else:
                self.errores.append(dict(campo=f'hardware.discos[{indice}].espacio_libre_gb',
                                        detalle='No se pudo leer espacio libre de volúmenes montados'))
            discos.append(disco)
        return discos

    def windows(self):
        consultas = {
            ('equipo', 'serial'): '(Get-CimInstance Win32_BIOS).SerialNumber.Trim()',
            ('equipo', 'smbios_uuid'): '(Get-CimInstance Win32_ComputerSystemProduct).UUID.ToUpper()',
            ('hardware', 'cpu'): "((Get-CimInstance Win32_Processor | Select-Object -First 1).Name).Trim()",
            ('hardware', 'ram_total_gb'): '[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1e9, 2)',
            ('perifericos', 'teclado'): '@(Get-CimInstance Win32_Keyboard).Count -gt 0',
            ('perifericos', 'mouse'): '@(Get-CimInstance Win32_PointingDevice).Count -gt 0',
        }
        for (seccion, campo), consulta in consultas.items():
            self.leer(seccion, campo, lambda q=consulta, c=campo:
                      float(powershell(q)) if c == 'ram_total_gb' else powershell(q))
        self.leer('perifericos', 'monitor', self.monitor_windows)
        self.leer('hardware', 'ethernet_presente', self.ethernet_windows)
        for campo in ('ipv4', 'mac', 'gateway', 'dns'):
            self.leer('red', campo, lambda c=campo: self.red_windows()[c])
        self.leer('hardware', 'discos', self.discos_windows, 'hardware.discos')

    def monitor_windows(self):
        # Algunos Windows no admiten root/wmi:WmiMonitorID (0x8004100c).
        # Solo contar dispositivos PnP de clase Monitor con estado OK.
        # Ejecutar directamente y leer true/false, sin ConvertTo-Json.
        codigo = (
            "$ErrorActionPreference = 'Stop'; "
            "$activos = @(Get-PnpDevice -Class Monitor -ErrorAction Stop | "
            "Where-Object { $_.Status -eq 'OK' }); "
            "if ($activos.Count -gt 0) { 'true' } else { 'false' }"
        )
        salida = ejecutar('powershell.exe', '-NoProfile', '-NonInteractive',
                          '-Command', codigo).strip().lower()
        if salida not in ('true', 'false'):
            raise ValueError('Respuesta inesperada de deteccion de monitor: ' + salida[:120])
        return salida == 'true'

    def ethernet_windows(self):
        # MediaType es una representación de PowerShell, no el código NDIS.
        # Usar códigos de CIM: InterfaceType=6 o NdisPhysicalMedium=14 (802.3).
        adaptadores = lista(powershell(
            '@(Get-NetAdapter -Physical | Select-Object InterfaceType,NdisPhysicalMedium)'))
        desconocidos = False
        for adaptador in adaptadores:
            interfaz = adaptador.get('InterfaceType')
            medio = adaptador.get('NdisPhysicalMedium')
            if interfaz == 6 or medio == 14:
                return True
            if interfaz in (None, 0) and medio in (None, 0):
                desconocidos = True
        if desconocidos:
            raise ValueError('No se pudo identificar el tipo de uno o más adaptadores físicos')
        return False

    def red_windows(self):
        datos = powershell("$r=Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' | "
                           "Sort-Object RouteMetric | Select-Object -First 1; "
                           "if (!$r) { throw 'No hay ruta predeterminada' }; "
                           "$n=Get-NetIPConfiguration -InterfaceIndex $r.InterfaceIndex; "
                           "[pscustomobject]@{ip=@($n.IPv4Address)[0].IPAddress; "
                           "prefix=@($n.IPv4Address)[0].PrefixLength; mac=$n.NetAdapter.MacAddress; "
                           "gateway=$r.NextHop; dns=@(Get-DnsClientServerAddress -InterfaceIndex $r.InterfaceIndex "
                           "-AddressFamily IPv4 | ForEach-Object {$_.ServerAddresses})}")
        return dict(ipv4=f"{datos['ip']}/{datos['prefix']}", mac=datos['mac'].replace('-', ':').upper(),
                    gateway=datos['gateway'] if datos['gateway'] != '0.0.0.0' else None,
                    dns=list(dict.fromkeys(lista(datos['dns']))))

    def discos_windows(self):
        datos = powershell("@(Get-Disk | Sort-Object Number | ForEach-Object { "
                           "$d=$_; $p=Get-PhysicalDisk | Where-Object { $_.DeviceId -eq [string]$d.Number }; "
                           "$v=@(Get-Partition -DiskNumber $d.Number | Get-Volume -ErrorAction SilentlyContinue); "
                           "[pscustomobject]@{size=$d.Size; type=[string]$p.MediaType; "
                           "free=($v | Measure-Object SizeRemaining -Sum).Sum; volumes=$v.Count} })")
        discos = []
        for indice, dato in enumerate(lista(datos)):
            disco = dict(orden=indice, capacidad_total_gb=gb(dato['size']))
            for campo, valor in (('tipo', dato['type'] if dato['type'] in ('HDD', 'SSD') else None),
                                 ('espacio_libre_gb', gb(dato['free']) if dato['volumes'] and dato['free'] is not None else None)):
                if valor is None:
                    self.errores.append(dict(campo=f'hardware.discos[{indice}].{campo}', detalle='Lectura no disponible'))
                else:
                    disco[campo] = valor
            discos.append(disco)
        return discos

    def recopilar(self, destino_prueba):
        self.leer('equipo', 'hostname', socket.gethostname)
        self.leer('equipo', 'sistema_operativo', lambda: f'{platform.system()} - {platform.release()}')
        if platform.system() == 'Linux':
            self.linux()
        else:
            self.windows()
        if destino_prueba:
            def probar():
                try:
                    with socket.create_connection(destino_prueba, timeout=3):
                        return True
                except (TimeoutError, ConnectionError):
                    return False
            self.leer('red', 'conectividad', probar)
        else:
            self.errores.append(dict(campo='conectividad', detalle='No se configuró destino de prueba TCP'))
        self.datos['diagnostico']['errores_lectura'] = self.errores
        return self.datos


def serializar(datos):
    """Sólo tipos del contrato; JSON escapa strings de forma compatible con TOML."""
    def valor(v):
        return json.dumps(v, ensure_ascii=False, allow_nan=False)
    lineas = []
    for seccion, campos in datos.items():
        lineas.append(f'[{seccion}]')
        for campo, contenido in campos.items():
            if isinstance(contenido, list) and contenido and isinstance(contenido[0], dict):
                continue
            lineas.append(f'{campo} = {valor(contenido)}')
        for campo, contenido in campos.items():
            if isinstance(contenido, list) and contenido and isinstance(contenido[0], dict):
                for elemento in contenido:
                    lineas.append(f'[[{seccion}.{campo}]]')
                    lineas.extend(f'{k} = {valor(v)}' for k, v in elemento.items())
        lineas.append('')
    return '\n'.join(lineas)


def guardar_captura(salida, datos):
    salida.mkdir(parents=True, exist_ok=True)
    ruta = salida / f"SGLAB-{datos['meta']['id_ejecucion']}.toml"
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=salida, delete=False) as archivo:
            temporal = Path(archivo.name)
            archivo.write(serializar(datos))
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, ruta)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    return ruta


def opciones_ssh(args):
    opciones = ['-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=15',
                '-o', 'ServerAliveCountMax=2']
    if args.clave:
        opciones += ['-i', str(Path(args.clave).resolve()), '-o', 'IdentitiesOnly=yes']
    if args.known_hosts:
        # OpenSSH interpreta los valores de -o como configuración, incluso con argv.
        archivo = str(Path(args.known_hosts).resolve())
        if any(c in archivo for c in ('"', '\n', '\r')):
            raise ValueError('Ruta known_hosts inválida')
        opciones += ['-o', 'UserKnownHostsFile="' + archivo + '"']
    return opciones


def enviar_archivo(ruta, args):
    """SCP a nombre temporal y publicación atómica mediante SSH en servidor Linux."""
    if ruta.is_symlink() or not ruta.is_file():
        raise ValueError('Solo se envían archivos regulares')
    if not re.fullmatch(r'SGLAB-[0-9a-fA-F-]{36}\.toml', ruta.name):
        raise ValueError('Nombre de captura inválido')
    destino = f'{args.usuario}@{args.servidor}'
    remoto = args.directorio_remoto.rstrip('/') + '/' + ruta.name
    opciones = opciones_ssh(args)
    # Sin shell local; host, usuario y directorio se validan antes de llegar aquí.
    subprocess.run(['scp', *opciones, '-P', str(args.puerto_ssh), str(ruta.resolve()),
                    destino + ':' + remoto + '.part'], check=True, timeout=120,
                   capture_output=True)
    subprocess.run(['ssh', *opciones, '-p', str(args.puerto_ssh), destino,
                    'chmod 0640 -- ' + shlex.quote(remoto + '.part') + ' && mv -- ' + shlex.quote(remoto + '.part') + ' ' + shlex.quote(remoto)],
                   check=True, timeout=45, capture_output=True)


def enviar_pendientes(args):
    """Reintentar mismos bytes y UUID; no crear una nueva captura para reenviar."""
    enviados = args.salida / 'enviados'
    enviados.mkdir(parents=True, exist_ok=True)
    fallidos = 0
    for ruta in sorted(args.salida.glob('SGLAB-*.toml')):
        if ruta.is_symlink() or not ruta.is_file():
            continue
        for intento in range(args.reintentos):
            try:
                enviar_archivo(ruta, args)
                # SCP+rename confirmados: conservar copia local como enviada.
                ruta.rename(enviados / ruta.name)
                print(f'Entregado al servidor: {ruta.name}', flush=True)
                break
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                # No volcar stderr remoto ni argumentos que pudieran contener datos.
                print(f'No se pudo enviar {ruta.name} (intento {intento + 1}/{args.reintentos}, '
                      f'{type(exc).__name__}). Se conserva localmente.', file=sys.stderr)
                if intento + 1 < args.reintentos:
                    time.sleep(args.espera)
        else:
            fallidos += 1
    return 1 if fallidos else 0


class BloqueoCola:
    """Bloqueo de SO liberado incluso si el proceso se interrumpe."""
    def __init__(self, salida):
        self.ruta = salida / '.recopilar.lock'
        self.archivo = None

    def __enter__(self):
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self.archivo = self.ruta.open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.archivo.seek(0)
                if self.archivo.read(1) == b'':
                    self.archivo.write(b'0')
                    self.archivo.flush()
                self.archivo.seek(0)
                msvcrt.locking(self.archivo.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.archivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.archivo.close()
            raise ValueError('Ya hay otro recolector o emisor usando esta cola')
        return self

    def __exit__(self, *exc):
        self.archivo.close()


def argumentos():
    previo = argparse.ArgumentParser(add_help=False)
    previo.add_argument('--config', type=Path, help='Configuración JSON del equipo')
    config, _ = previo.parse_known_args()
    parser = argparse.ArgumentParser(description=__doc__, parents=[previo])
    parser.add_argument('--laboratorio', default='', help='Etiqueta de laboratorio; la asignación oficial está en la BD')
    parser.add_argument('--ci', type=int, default=0)
    parser.add_argument('--salida', type=Path, default=Path('salida'))
    parser.add_argument('--probar-host')
    parser.add_argument('--probar-puerto', type=int, default=8080)
    parser.add_argument('--servidor', help='Servidor SSH (hostname o IPv4); omitir para solo recopilar')
    parser.add_argument('--usuario', help='Usuario SSH receptor')
    parser.add_argument('--directorio-remoto', default='/srv/sglab/incoming')
    parser.add_argument('--puerto-ssh', type=int, default=22)
    parser.add_argument('--clave', help='Ruta de la clave privada SSH; nunca guardar contraseñas')
    parser.add_argument('--known-hosts', help='Archivo con clave de host verificada previamente')
    parser.add_argument('--reintentos', type=int, default=3)
    parser.add_argument('--espera', type=int, default=10, help='Segundos entre reintentos')
    parser.add_argument('--solo-enviar', action='store_true', help='Reenviar pendientes sin recopilar otra vez')
    if config.config:
        try:
            valores = json.loads(config.config.read_text(encoding='utf-8'))
            permitidos = {a.dest for a in parser._actions} - {'help', 'config', 'solo_enviar'}
            if not isinstance(valores, dict) or set(valores) - permitidos:
                raise ValueError('Configuración desconocida')
            parser.set_defaults(**valores)
        except (OSError, ValueError) as exc:
            parser.error(f'No se pudo leer la configuración: {exc}')
    args = parser.parse_args()
    # argparse no convierte defaults JSON que no son strings: validarlos explícitamente.
    for nombre in ('ci', 'probar_puerto', 'puerto_ssh', 'reintentos', 'espera'):
        if type(getattr(args, nombre)) is not int:
            parser.error(f'{nombre} debe ser entero')
    for nombre in ('laboratorio', 'directorio_remoto'):
        if not isinstance(getattr(args, nombre), str):
            parser.error(f'{nombre} debe ser texto')
    for nombre in ('servidor', 'usuario', 'clave', 'known_hosts', 'probar_host'):
        if getattr(args, nombre) is not None and not isinstance(getattr(args, nombre), str):
            parser.error(f'{nombre} debe ser texto')
    if not isinstance(args.salida, (str, Path)):
        parser.error('salida debe ser una ruta')
    args.salida = Path(args.salida).resolve()
    if platform.system() not in ('Linux', 'Windows'):
        parser.error('Este recolector soporta Linux y Windows')
    if not args.solo_enviar and not 1 <= len(args.laboratorio.strip()) <= 20:
        parser.error('Laboratorio: 1 a 20 caracteres')
    if not 0 <= args.ci <= 4294967295 or not 1 <= args.probar_puerto <= 65535 or not 1 <= args.puerto_ssh <= 65535:
        parser.error('CI o puerto fuera de rango')
    if not 1 <= args.reintentos <= 100 or not 0 <= args.espera <= 3600:
        parser.error('Reintentos: 1 a 100; espera: 0 a 3600 segundos')
    if args.servidor:
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]*', args.servidor):
            parser.error('Servidor debe ser un hostname o IPv4')
        if not args.usuario or not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.-]*', args.usuario):
            parser.error('Usuario SSH inválido')
        if not re.fullmatch(r'/[a-zA-Z0-9_./-]+', args.directorio_remoto) or '..' in args.directorio_remoto.split('/'):
            parser.error('Directorio remoto absoluto sin espacios ni ..')
    elif args.solo_enviar:
        parser.error('--solo-enviar requiere --servidor')
    return args


def main():
    args = argumentos()
    try:
        with BloqueoCola(args.salida):
            if not args.solo_enviar:
                captura = Captura(args.laboratorio.strip(), args.ci)
                # Si hay servidor, probar su puerto SSH sin necesitar otro destino.
                prueba = ((args.probar_host, args.probar_puerto) if args.probar_host else
                          (args.servidor, args.puerto_ssh) if args.servidor else None)
                datos = captura.recopilar(prueba)
                ruta = guardar_captura(args.salida, datos)
                print(f'Captura guardada: {ruta} ({len(captura.errores)} lecturas no disponibles)', flush=True)
            return enviar_pendientes(args) if args.servidor else 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Error del recolector: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
