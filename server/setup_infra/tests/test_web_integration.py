"""HTTP + MariaDB reales. Activar con SGLAB_TEST_WEB=1; crea y retira datos sintéticos."""
import base64
import hashlib
import hmac
import struct
import importlib.util
import http.cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import time
import subprocess
import unittest
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('SGLAB_WEB_URL', 'https://127.0.0.1')
CA = os.environ.get('SGLAB_TEST_CA_FILE', str(ROOT/'var/certificados/SGLAB-CA.crt'))


def tls_context():
    # Confiar explícitamente en la CA local, manteniendo la validación de IP y firma.
    return ssl.create_default_context(cafile=CA)


def database(sql, params=()):
    code = "require '/var/www/html/src/bootstrap.php'; $d=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR); echo json_encode(query($d['sql'],$d['params'])->fetchAll(),JSON_THROW_ON_ERROR);"
    r = subprocess.run(['docker', 'compose', 'exec', '-T', 'web', 'php', '-r', code], cwd=ROOT,
                       input=json.dumps(dict(sql=sql, params=list(params))), text=True, capture_output=True, check=True)
    return json.loads(r.stdout)


class Browser:
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies),
                                                  urllib.request.HTTPSHandler(context=tls_context()))

    def request(self, page='inicio', data=None, **params):
        address = BASE + '/?' + urllib.parse.urlencode(dict(page=page, **params))
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        try:
            r = self.opener.open(address, data=body, timeout=20)
        except urllib.error.HTTPError as exc:
            r = exc
        return r.status, r.read().decode(), r.headers

    @staticmethod
    def csrf(html):
        return re.search(r'name="csrf" value="([a-f0-9]+)"', html).group(1)

    def login(self, ci, password):
        _, html, _ = self.request('login')
        fixture=database('SELECT ci,nombre,apellido,tipo_usuario FROM usuarios WHERE ci=?',[ci])
        if fixture and fixture[0]['tipo_usuario']=='ALUMNO' and fixture[0]['nombre'].startswith(('TEST-WEB-','TEST-ROLES-')) and fixture[0]['apellido']=='Temporal':
            # Fixture de permisos: simular la sesión posterior a OAuth mediante
            # acceso CLI privilegiado. No existe bypass en ningún endpoint web.
            session_id=next(cookie.value for cookie in self.cookies if cookie.name=='sglab_session')
            code="""require '/var/www/html/src/bootstrap.php'; $d=json_decode(stream_get_contents(STDIN),true);
            $u=query('SELECT * FROM usuarios WHERE ci=?',[$d['ci']])->fetch();
            if(!$u||!str_starts_with($u['nombre'],'TEST-')||!password_verify($d['password'],$u['password_hash']))exit(1);
            $gid='9'.$u['ci'];query('UPDATE usuarios SET github_id=? WHERE ci=?',[$gid,$u['ci']]);$u['github_id']=$gid;
            session_name('sglab_session');session_id($d['session']);session_start();
            // Mantener ID solo en la fixture para conservar la cookie de urllib.
            $_SESSION=['user'=>array_intersect_key($u,array_flip(['ci','nombre','apellido','tipo_usuario'])),'started'=>time(),'last_seen'=>time(),'csrf'=>bin2hex(random_bytes(32)),'auth_method'=>'github','auth_version'=>(int)$u['auth_version'],'github_id'=>$gid];session_write_close();"""
            subprocess.run(['docker','compose','exec','-T','--user','www-data','web','php','-r',code],cwd=ROOT,input=json.dumps(dict(ci=ci,password=password,session=session_id)),text=True,capture_output=True,check=True)
            return self.request('inicio')
        status,html,headers=self.request('login',dict(action='login',csrf=self.csrf(html),ci=ci,password=password))
        secret=re.search(r'id="totp-secret">([A-Z2-7]+)</code>',html)
        if secret:
            status,html,headers=self.request('mfa',dict(action='mfa_verify',csrf=self.csrf(html),code=totp_code(secret.group(1))))
        return status,html,headers


def totp_code(secret, step=None):
    step=int(time.time())//30 if step is None else step
    raw=base64.b32decode(secret+'='*((-len(secret))%8))
    digest=hmac.new(raw,struct.pack('>Q',step),hashlib.sha1).digest()
    number=struct.unpack('>I',digest[digest[-1]&15:(digest[-1]&15)+4])[0]&0x7fffffff
    return str(number%1000000).zfill(6)



@unittest.skipUnless(os.environ.get('SGLAB_TEST_WEB') == '1', 'Integración web optativa: SGLAB_TEST_WEB=1')
class WebIntegration(unittest.TestCase):
    def test_inventory_auth_and_permissions(self):
        token = secrets.token_hex(8)
        name = 'TEST-WEB-' + token
        password = secrets.token_urlsafe(24)
        users = []
        capture_file = None
        try:
            # Seleccionar CI libres sin sobrescribir cuentas.
            for ci in range(4294967295, 4294967200, -1):
                if not database('SELECT ci FROM usuarios WHERE ci=?', [ci]):
                    users.append(ci)
                if len(users) == 2:
                    break
            self.assertEqual(len(users), 2)
            code = "require '/var/www/html/src/bootstrap.php'; $d=json_decode(stream_get_contents(STDIN),true); query('INSERT INTO usuarios(ci,nombre,apellido,password_hash,tipo_usuario) VALUES (?,?,?,?,?)',[$d['ci'],$d['name'],'Temporal',password_hash($d['password'],PASSWORD_DEFAULT),$d['role']]);"
            for ci, role in zip(users, ['ADMINISTRADOR', 'ALUMNO']):
                subprocess.run(['docker', 'compose', 'exec', '-T', 'web', 'php', '-r', code], cwd=ROOT,
                               input=json.dumps(dict(ci=ci, name=name, password=password, role=role)),
                               text=True, capture_output=True, check=True)
            guest = Browser()
            status, html, headers = guest.request('equipos')
            self.assertEqual(status, 200)
            self.assertIn('name="password"', html)
            self.assertIn('HttpOnly', headers.get('Set-Cookie', ''))
            self.assertIn('SameSite=Lax', headers.get('Set-Cookie', ''))
            self.assertTrue(next(cookie for cookie in guest.cookies if cookie.name == 'sglab_session').secure)
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
            status, html, _ = guest.request('login', dict(action='login', csrf='invalid', ci=users[0], password=password))
            self.assertEqual(status, 403)
            status, html, _ = guest.login(users[0], 'incorrecta')
            self.assertIn('Cédula o contraseña incorrectas', html)
            status, html, _ = guest.login(users[0], password)
            self.assertEqual(status, 200)
            self.assertIn('Resumen del laboratorio', html)
            _, html, _ = guest.request('laboratorios')
            status, html, _ = guest.request('laboratorios', dict(action='save_lab', csrf=guest.csrf(html), nombre=name, id=''))
            self.assertEqual(status, 200)
            self.assertIn('Laboratorio guardado', html)
            lab = database('SELECT id_laboratorio FROM laboratorio WHERE nombre=?', [name])[0]['id_laboratorio']
            _, html, _ = guest.request('equipos')
            data = dict(action='save_equipment', csrf=guest.csrf(html), id='', num_serie=name,
                        smbios_uuid='', hostname='<script>prueba</script>', id_laboratorio=lab,
                        estado_administrativo='OPERATIVA')
            status, html, _ = guest.request('equipos', data)
            self.assertEqual(status, 200)
            self.assertIn('PC guardada', html)
            self.assertIn('&lt;script&gt;prueba&lt;/script&gt;', html)
            self.assertNotIn('<script>prueba</script>', html)
            pc = database('SELECT * FROM equipo WHERE num_serie=?', [name])[0]
            self.assertEqual(int(pc['id_laboratorio']), int(lab))
            # Alta duplicada e identidad ausente se rechazan sin insertar otras PC.
            data['csrf'] = guest.csrf(html)
            _, html, _ = guest.request('equipos', data)
            self.assertIn('ya pertenecen a otra PC', html)
            data['num_serie'] = ''
            _, html, _ = guest.request('equipos', data)
            self.assertIn('al menos la serie o el UUID', html)
            # Editar la PC y consultar el inventario filtrado.
            data.update(id=pc['id_equipo'], num_serie=name, hostname='PC-'+token, estado_administrativo='EN_REPARACION')
            _, html, _ = guest.request('equipos', data, edit=pc['id_equipo'])
            self.assertIn('PC guardada', html)
            status, html, _ = guest.request('equipos', q=name, lab=lab, estado='EN_REPARACION')
            self.assertEqual(status, 200)
            self.assertIn('PC-'+token, html)
            self.assertIn('En reparación', html)
            _, html, _ = guest.request('equipo', id=pc['id_equipo'])
            self.assertIn('Esta PC todavía no recibió capturas', html)
            # La PC registrada por la web debe ser reconocida por el daemon real.
            spec = importlib.util.spec_from_file_location('web_test_collector', ROOT/'client/recopilar.py')
            collector = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(collector)
            capture = collector.Captura('ETIQUETA-REPORTADA', users[1])
            capture.datos.update(equipo={'serial': name, 'hostname': 'PC-'+token},
                                 hardware={'cpu': 'CPU de prueba', 'ram_total_gb': 8.0,
                                           'discos': [{'orden': 0, 'tipo': 'SSD', 'capacidad_total_gb': 256.0}]},
                                 red={}, perifericos={}, diagnostico={'errores_lectura': []})
            capture_file = collector.guardar_captura(ROOT/'var/incoming', capture.datos)
            capture_file.chmod(0o640)
            for _ in range(100):
                imported = database('SELECT * FROM registro WHERE id_ejecucion=?', [capture.datos['meta']['id_ejecucion']])
                if imported:
                    break
                time.sleep(.1)
            self.assertTrue(imported, 'El daemon debe importar la captura de la PC registrada por PHP')
            self.assertEqual(int(imported[0]['usuario_ci']), users[1])
            self.assertEqual(int(imported[0]['id_laboratorio_observado']), int(lab))
            self.assertEqual(database('SELECT estado_administrativo FROM equipo WHERE id_equipo=?', [pc['id_equipo']])[0]['estado_administrativo'], 'EN_REPARACION')
            _, html, _ = guest.request('equipo', id=pc['id_equipo'])
            self.assertIn('CPU de prueba', html)
            # Usuario de consulta: no ve controles ni puede llamar POST administrativo.
            student = Browser()
            _, html, _ = student.login(users[1], password)
            self.assertNotIn('Registrar PC', html)
            _, html, _ = student.request('laboratorios')
            self.assertNotIn('save_lab', html)
            status, html, _ = student.request('laboratorios', dict(action='save_lab', csrf=student.csrf(html), id='', nombre=name+'-prohibido'))
            self.assertEqual(status, 403)
            self.assertIn('No tenés permiso', html)
            self.assertFalse(database('SELECT 1 FROM laboratorio WHERE nombre=?', [name+'-prohibido']))
            # Retirar rol invalida inmediatamente permisos de una sesión abierta.
            database("UPDATE usuarios SET tipo_usuario='ALUMNO' WHERE ci=?", [users[0]])
            _, html, _ = guest.request('laboratorios')
            status, html, _ = guest.request('laboratorios', dict(action='save_lab', csrf=guest.csrf(html), id='', nombre=name+'-prohibido'))
            self.assertTrue(status==403 or 'name="password"' in html)
            # Cerrar sesión y comprobar acceso protegido.
            _, html, _ = guest.request('inicio')
            _, html, _ = guest.request('inicio', dict(action='logout', csrf=guest.csrf(html)))
            self.assertIn('name="password"', html)
            _, html, _ = guest.request('equipos')
            self.assertIn('name="password"', html)
            status, _, _ = student.request('equipo', id=0)
            self.assertEqual(status, 404)
            # Expiración real de la sesión de consulta.
            session_id = next(cookie.value for cookie in student.cookies if cookie.name == 'sglab_session')
            expire = "session_name('sglab_session'); session_id(trim(stream_get_contents(STDIN))); session_start(); $_SESSION['last_seen']=time()-901; session_write_close();"
            subprocess.run(['docker','compose','exec','-T','--user','www-data','web','php','-r',expire],
                           cwd=ROOT,input=session_id,text=True,capture_output=True,check=True)
            _, html, _ = student.request('inicio')
            self.assertIn('Tu sesión venció', html)
            self.assertIn('name="password"', html)
            # Combinación IP/cédula inexistente aislada para verificar el límite.
            blocked_ci = str(9000000000 + secrets.randbelow(999999999))
            attacker = Browser()
            for _ in range(11):
                _, html, _ = attacker.login(blocked_ci, 'incorrecta')
            self.assertIn('Demasiados intentos', html)
        finally:
            # La cuenta de aplicación no tiene DELETE: limpiar con la cuenta
            # administrativa del contenedor, sin ampliar los permisos de la web.
            name_sql = "CONVERT(X'" + name.encode().hex() + "' USING utf8mb4) COLLATE utf8mb4_unicode_ci"
            forbidden_sql = "CONVERT(X'" + (name+'-prohibido').encode().hex() + "' USING utf8mb4) COLLATE utf8mb4_unicode_ci"
            cleanup = 'SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci; START TRANSACTION; DELETE f FROM registro_sistema_archivos f JOIN registro r ON r.id_registro=f.id_registro JOIN equipo e ON e.id_equipo=r.id_equipo WHERE e.num_serie='+name_sql+'; DELETE d FROM registro_disco d JOIN registro r ON r.id_registro=d.id_registro JOIN equipo e ON e.id_equipo=r.id_equipo WHERE e.num_serie='+name_sql+'; DELETE r FROM registro r JOIN equipo e ON e.id_equipo=r.id_equipo WHERE e.num_serie='+name_sql+'; DELETE FROM equipo WHERE num_serie='+name_sql+'; DELETE FROM laboratorio WHERE nombre IN ('+name_sql+','+forbidden_sql+');'
            for ci in users:
                cleanup += 'DELETE FROM usuarios WHERE ci='+str(ci)+' AND nombre='+name_sql+';'
            cleanup += 'COMMIT;'
            subprocess.run(['docker','compose','exec','-T','db','sh','-c',
                            'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb -uroot sglab'],
                           cwd=ROOT, input=cleanup, text=True, capture_output=True, check=True)
            if capture_file is not None:
                if capture_file.exists():
                    capture_file.unlink()
                for folder in ['processed', 'rejected']:
                    for file in (ROOT/'var'/folder).glob('job.*/'+capture_file.name):
                        shutil.rmtree(file.parent)



if __name__ == '__main__':
    unittest.main()
