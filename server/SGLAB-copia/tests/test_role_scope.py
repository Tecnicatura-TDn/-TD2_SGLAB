"""Pruebas de alcance por rol en el despliegue de pruebas activo."""
import importlib.util
import json
import os
import secrets
import shutil
import subprocess
import time
import unittest
from pathlib import Path
from test_web_integration import Browser, database, ROOT


def root_sql(sql):
    r = subprocess.run(['docker','compose','exec','-T','db','sh','-c',
                        'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb -uroot --batch --skip-column-names sglab'],
                       cwd=ROOT,input="SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;\n"+sql,
                       text=True,capture_output=True,check=True)
    return r.stdout.strip()


def literal(value):
    return "(CONVERT(X'"+str(value).encode().hex()+"' USING utf8mb4) COLLATE utf8mb4_unicode_ci)"


@unittest.skipUnless(os.environ.get('SGLAB_TEST_WEB')=='1','SGLAB_TEST_WEB=1 para integración por roles')
class RoleScope(unittest.TestCase):
    def test_roles_assignments_comments_and_ip(self):
        name='TEST-ROLES-'+secrets.token_hex(6)
        pwd=secrets.token_urlsafe(24)
        accounts={}; browsers={}; files=[]; labs=[]; pcs=[]
        try:
            free=[ci for ci in range(4294967100,4294967000,-1) if not database('SELECT 1 FROM usuarios WHERE ci=?',[ci])][:5]
            self.assertEqual(len(free),5)
            for key,ci in zip(['admin','assistant','teacher','student','new'],free):accounts[key]=ci
            code="require '/var/www/html/src/bootstrap.php'; $a=json_decode(stream_get_contents(STDIN),true); query('INSERT INTO usuarios(ci,nombre,apellido,password_hash,tipo_usuario) VALUES (?,?,?,?,?)',[$a['ci'],$a['name'],'Temporal',password_hash($a['password'],PASSWORD_DEFAULT),$a['role']]);"
            for key,role in [('admin','ADMINISTRADOR'),('assistant','ASISTENTE'),('teacher','DOCENTE'),('student','ALUMNO')]:
                subprocess.run(['docker','compose','exec','-T','web','php','-r',code],cwd=ROOT,
                               input=json.dumps(dict(ci=accounts[key],name=name,password=pwd,role=role)),text=True,capture_output=True,check=True)
                browsers[key]=Browser()
                status,html,_=browsers[key].login(accounts[key],pwd)
                self.assertEqual(status,200)
            def post(key,page,data,**params):
                _,html,_=browsers[key].request('inicio')
                return browsers[key].request(page,dict(csrf=Browser.csrf(html),**data),**params)
            # Asistente: mismo perfil administrativo que el alias ADMINISTRADOR.
            for suffix in ['-A','-B']:
                status,html,_=post('assistant','laboratorios',dict(action='save_lab',id='',nombre=name+suffix))
                self.assertEqual(status,200);self.assertIn('Laboratorio guardado',html)
                labs.append(database('SELECT id_laboratorio FROM laboratorio WHERE nombre=?',[name+suffix])[0]['id_laboratorio'])
            for i,lab in enumerate(labs):
                status,html,_=post('assistant','equipos',dict(action='save_equipment',id='',num_serie=name+str(i),smbios_uuid='',hostname=name+'-PC'+str(i),id_laboratorio=lab,estado_administrativo='OPERATIVA'))
                self.assertEqual(status,200);self.assertIn('PC guardada',html)
                pcs.append(database('SELECT id_equipo FROM equipo WHERE num_serie=?',[name+str(i)])[0]['id_equipo'])
            _,html,_=browsers['student'].request('inicio');self.assertIn('No pudimos identificar',html)
            for page,params in [('equipo',{'id':pcs[0]}),('usuarios',{}),('laboratorios',{})]:
                status,_,_=browsers['student'].request(page,**params);self.assertIn(status,[403,404])
            _,html,_=browsers['teacher'].request('equipos');self.assertNotIn(name+'-PC',html)
            status,html,_=post('assistant','usuarios',dict(action='assign_user',usuario_ci=accounts['teacher'],recurso=labs[0],desde='',hasta=''))
            self.assertEqual(status,200);self.assertIn('Asignación guardada',html)
            _,html,_=browsers['teacher'].request('equipos');self.assertIn(name+'-PC0',html);self.assertNotIn(name+'-PC1',html)
            # Filtros y URLs no amplían el alcance del docente.
            _,html,_=browsers['teacher'].request('equipos',q=name,lab=labs[1]);self.assertNotIn(name+'-PC1',html)
            self.assertEqual(browsers['teacher'].request('equipo',id=pcs[1])[0],404)
            self.assertEqual(browsers['teacher'].request('laboratorio',id=labs[1])[0],404)
            status,html,_=post('teacher','laboratorio',dict(action='save_comment',kind='laboratorio',id=labs[0],contenido='Observación de la sala <script>x</script>'),id=labs[0])
            self.assertEqual(status,200);self.assertIn('&lt;script&gt;x&lt;/script&gt;',html)
            self.assertEqual(post('teacher','laboratorio',dict(action='save_comment',kind='laboratorio',id=labs[1],contenido='No debe entrar'),id=labs[1])[0],404)
            self.assertEqual(post('teacher','equipo',dict(action='save_comment',kind='equipo',id=pcs[0],contenido='No permitido'),id=pcs[0])[0],403)
            # Captura real a través de spawn.sh: la IP debe ser la observada por Apache.
            network=json.loads(subprocess.check_output(['docker','network','inspect','sglab_sglab_network'],text=True))
            gateway=network[0]['IPAM']['Config'][0]['Gateway']
            spec=importlib.util.spec_from_file_location('role_collector',ROOT/'client/recopilar.py')
            collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
            def capture(i,ip,expect=True):
                data=collector.Captura('PRUEBA',accounts['student']).datos
                data.update(equipo={'serial':name+str(i),'hostname':name+'-PC'+str(i)},hardware={'cpu':'CPU restringida','discos':[]},red={'ipv4':ip+'/24'},perifericos={},diagnostico={'errores_lectura':[]})
                file=collector.guardar_captura(ROOT/'var/incoming',data);file.chmod(0o640);files.append(file)
                for _ in range(150):
                    exists=database('SELECT 1 FROM registro WHERE id_ejecucion=?',[data['meta']['id_ejecucion']])
                    if expect and exists:return
                    if not expect and list((ROOT/'var/rejected').glob('job.*/'+file.name)):
                        self.assertFalse(exists);return
                    time.sleep(.1)
                self.fail('El daemon no importó la captura de prueba')
            capture(0,gateway);capture(1,'192.0.2.123')
            status,html,_=browsers['student'].request('inicio')
            self.assertEqual(status,200);self.assertIn(name+'-PC0',html);self.assertNotIn(name+'-PC1',html);self.assertNotIn('CPU restringida',html)
            self.assertEqual(browsers['student'].request('equipo',id=pcs[1])[0],404)
            status,html,_=post('student','equipo',dict(action='save_comment',kind='equipo',id=pcs[0],contenido='El teclado de mi PC falla'),id=pcs[0])
            self.assertEqual(status,200);self.assertIn('El teclado de mi PC falla',html)
            self.assertEqual(post('student','equipo',dict(action='save_comment',kind='equipo',id=pcs[1],contenido='No debe entrar'),id=pcs[1])[0],404)
            self.assertEqual(post('student','laboratorio',dict(action='save_comment',kind='laboratorio',id=labs[0],contenido='No debe entrar'),id=labs[0])[0],403)
            # IP ambiguas: denegar, sin elegir arbitrariamente una PC.
            capture(1,gateway)
            _,html,_=browsers['student'].request('inicio');self.assertIn('No pudimos identificar',html)
            self.assertEqual(browsers['student'].request('equipo',id=pcs[0])[0],404)
            capture(1,'192.0.2.123')
            root_sql('UPDATE registro SET fecha_recepcion=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 9 HOUR) WHERE id_equipo='+str(pcs[0])+';')
            _,html,_=browsers['student'].request('inicio');self.assertIn('No pudimos identificar',html)
            capture(0,gateway)
            # Las cabeceras del cliente no pueden elegir otra PC.
            browsers['student'].opener.addheaders=[('X-Forwarded-For','192.0.2.123')]
            _,html,_=browsers['student'].request('inicio');self.assertIn(name+'-PC0',html);self.assertNotIn(name+'-PC1',html)
            # Vigencia y revocación se evalúan en cada solicitud, sin volver a entrar.
            self.assertEqual(post('assistant','usuarios',dict(action='revoke_assignment',usuario_ci=accounts['teacher']))[0],200)
            self.assertEqual(browsers['teacher'].request('equipo',id=pcs[0])[0],404)
            tomorrow=time.strftime('%Y-%m-%dT%H:%M',time.gmtime(time.time()+86400))
            post('assistant','usuarios',dict(action='assign_user',usuario_ci=accounts['teacher'],recurso=labs[0],desde=tomorrow,hasta=''))
            self.assertEqual(browsers['teacher'].request('laboratorio',id=labs[0])[0],404)
            post('assistant','usuarios',dict(action='assign_user',usuario_ci=accounts['teacher'],recurso=labs[0],desde='',hasta=''))
            root_sql('UPDATE asignacion_docente SET desde=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 2 HOUR),hasta=DATE_SUB(UTC_TIMESTAMP(),INTERVAL 1 HOUR) WHERE usuario_ci='+str(accounts['teacher'])+';')
            self.assertEqual(browsers['teacher'].request('equipo',id=pcs[0])[0],404)
            # El asistente administra todas las cuentas: ADMINISTRADOR es un alias, no otro nivel.
            user_data=dict(action='save_user',id='',ci=accounts['new'],nombre=name,apellido='Temporal',correo='',tipo_usuario='DOCENTE',activo='1',password=pwd)
            self.assertEqual(post('assistant','usuarios',user_data)[0],200)
            for role in ['ASISTENTE','ADMINISTRADOR']:
                forbidden=dict(user_data,id=str(accounts['new']),tipo_usuario=role)
                self.assertEqual(post('assistant','usuarios',forbidden)[0],200)
            self.assertEqual(browsers['assistant'].request('usuarios',edit=accounts['admin'])[0],200)
            self.assertEqual(database('SELECT tipo_usuario FROM usuarios WHERE ci=?',[accounts['new']])[0]['tipo_usuario'],'ASISTENTE')
            forbidden=dict(user_data,id=str(accounts['admin']),ci=accounts['admin'],tipo_usuario='DOCENTE')
            self.assertEqual(post('assistant','usuarios',forbidden)[0],200)
            # Cambiar estado y archivar preserva capturas y corta acceso al alumno.
            post('assistant','equipos',dict(action='save_equipment',id=pcs[0],num_serie=name+'0',smbios_uuid='',hostname=name+'-PC0',id_laboratorio=labs[0],estado_administrativo='EN_REPARACION'))
            _,html,_=browsers['student'].request('inicio');self.assertIn('En reparación',html)
            _,html,_=post('assistant','laboratorios',dict(action='archive_lab',id=labs[0],restore='0'))
            self.assertIn('PC activas',html)
            post('assistant','equipos',dict(action='archive_equipment',id=pcs[0],restore='0'))
            self.assertEqual(browsers['student'].request('equipo',id=pcs[0])[0],404)
            self.assertTrue(database('SELECT 1 FROM registro WHERE id_equipo=?',[pcs[0]]))
            capture(0,gateway,expect=False)
            post('assistant','usuarios',dict(action='revoke_assignment',usuario_ci=accounts['teacher']))
            _,html,_=post('assistant','laboratorios',dict(action='archive_lab',id=labs[0],restore='0'))
            self.assertIn('historial se conserva',html)
            self.assertEqual(database('SELECT activo FROM laboratorio WHERE id_laboratorio=?',[labs[0]])[0]['activo'],0)
            # Desactivar una cuenta invalida también su sesión abierta.
            inactive=dict(user_data,id=str(accounts['student']),ci=accounts['student'],tipo_usuario='ALUMNO',activo='0',password='',correo=name+'-student@example.test')
            post('assistant','usuarios',inactive)
            _,html,_=browsers['student'].request('inicio');self.assertIn('name="password"',html)
        finally:
            ns=literal(name)
            # Nombres/series de esta prueba únicamente; no tocar otras cuentas.
            q="START TRANSACTION; DELETE FROM asignacion_docente WHERE usuario_ci IN (SELECT ci FROM usuarios WHERE nombre="+ns+");"
            q+='DELETE FROM comentario_laboratorio WHERE id_laboratorio IN (SELECT id_laboratorio FROM laboratorio WHERE nombre LIKE '+literal(name+'%')+');'
            q+='DELETE FROM comentario WHERE id_equipo IN (SELECT id_equipo FROM equipo WHERE num_serie LIKE '+literal(name+'%')+');'
            for table in ['registro_sistema_archivos','registro_disco']:
                q+='DELETE d FROM '+table+' d JOIN registro r ON r.id_registro=d.id_registro JOIN equipo e ON e.id_equipo=r.id_equipo WHERE e.num_serie LIKE '+literal(name+'%')+';'
            q+='DELETE r FROM registro r JOIN equipo e ON e.id_equipo=r.id_equipo WHERE e.num_serie LIKE '+literal(name+'%')+';'
            q+='DELETE FROM equipo WHERE num_serie LIKE '+literal(name+'%')+'; DELETE FROM laboratorio WHERE nombre LIKE '+literal(name+'%')+'; DELETE FROM usuarios WHERE nombre='+ns+" AND apellido='Temporal'; COMMIT;"
            root_sql(q)
            for f in files:
                if f.exists():f.unlink()
                for folder in ['processed','rejected']:
                    for file in (ROOT/'var'/folder).glob('job.*/'+f.name):shutil.rmtree(file.parent)


if __name__=='__main__':unittest.main()
