"""Filtros, CSV, actividad y permisos sobre HTTPS/MariaDB reales."""
import csv
import io
import json
import os
import re
import secrets
import subprocess
import unittest
from test_reports import root_sql, compose
from test_web_integration import Browser


@unittest.skipUnless(os.environ.get('SGLAB_TEST_WEB')=='1','SGLAB_TEST_WEB=1 para HTTPS real')
class HistoryHttp(unittest.TestCase):
    def test_history_exports_scopes_and_activity(self):
        tag='TEST-WEB-HISTORY-'+secrets.token_hex(6)
        password=secrets.token_urlsafe(24)
        existing=[int(x) for x in root_sql('SELECT ci FROM usuarios').split()]
        users=[x for x in range(4294966500,4294966400,-1) if x not in existing][:3]
        try:
            code="require '/var/www/html/src/bootstrap.php';$d=json_decode(stream_get_contents(STDIN),true);foreach($d['users'] as $i=>$ci){query('INSERT INTO usuarios(ci,nombre,apellido,password_hash,tipo_usuario) VALUES (?,?,?,?,?)',[$ci,$d['tag'],'Temporal',password_hash($d['password'],PASSWORD_DEFAULT),['ASISTENTE','DOCENTE','ALUMNO'][$i]]);}"
            subprocess.run(compose('exec','-T','web','php','-r',code),input=json.dumps(dict(users=users,tag=tag,password=password)),text=True,capture_output=True,check=True)
            setup=f"""
START TRANSACTION;
INSERT INTO laboratorio(nombre) VALUES ('{tag}');SET @lab=LAST_INSERT_ID();
INSERT INTO laboratorio(nombre) VALUES ('{tag}-otra');SET @foreign=LAST_INSERT_ID();
INSERT INTO equipo(hostname,id_laboratorio) VALUES ('=FORMULA-{tag}',@lab);SET @recent=LAST_INSERT_ID();
INSERT INTO equipo(hostname,id_laboratorio) VALUES ('{tag}-vieja',@lab);SET @stale=LAST_INSERT_ID();
INSERT INTO equipo(hostname,id_laboratorio) VALUES ('{tag}-nunca',@lab);SET @never=LAST_INSERT_ID();
INSERT INTO equipo(hostname,id_laboratorio) VALUES ('{tag}-ajena',@foreign);SET @other=LAST_INSERT_ID();
INSERT INTO asignacion_docente(usuario_ci,id_laboratorio,asignado_por_ci) VALUES ({users[1]},@lab,{users[0]});
INSERT INTO registro(id_equipo,id_laboratorio_observado,nombre,fecha,fecha_recepcion,estado) VALUES
(@recent,@lab,'{tag}','2020-01-02 00:00:00',UTC_TIMESTAMP(),'OK'),
(@recent,@lab,'{tag}','2020-01-02 23:59:59',UTC_TIMESTAMP(),'ERROR'),
(@recent,@foreign,'{tag}','2020-01-03 00:00:00',UTC_TIMESTAMP(),'OK'),
(@stale,@lab,'{tag}','2020-01-01 00:00:00',DATE_SUB(UTC_TIMESTAMP(),INTERVAL 20 DAY),'OK'),
(@other,@foreign,'{tag}','2020-01-02 00:00:00',UTC_TIMESTAMP(),'OK');
"""
            for _ in range(51):
                setup+=f"INSERT INTO registro(id_equipo,id_laboratorio_observado,nombre,fecha,fecha_recepcion,estado) VALUES (@recent,@lab,'{tag}','2020-01-04 00:00:00',UTC_TIMESTAMP(),'OK');\n"
            setup+='COMMIT; SELECT @lab,@foreign,@recent,@stale,@never,@other;'
            lab,foreign,recent,stale,never,other=map(int,root_sql(setup).split())
            manager=Browser();self.assertEqual(manager.login(users[0],password)[0],200)
            teacher=Browser();self.assertEqual(teacher.login(users[1],password)[0],200)
            student=Browser();self.assertEqual(student.login(users[2],password)[0],200)
            def exported(browser, **filters):
                status,body,headers=browser.request('historial',exportar='csv',**filters)
                self.assertEqual(status,200,body[:500]);self.assertIn('text/csv',headers['Content-Type'])
                return list(csv.DictReader(io.StringIO(body.lstrip('\ufeff'))))
            def chart(browser, **filters):
                status,html,_=browser.request('historial',**filters)
                self.assertEqual(status,200)
                return {label:(int(value),int(total)) for total,value,label in re.findall(r'<meter[^>]*max="(\d+)"[^>]*value="(\d+)"[^>]*aria-label="([^"]+)"',html)}
            self.assertEqual(chart(manager,lab=lab,desde='2020-01-02',hasta='2020-01-02'),{'Lecturas OK':(1,2),'Lecturas con error':(1,2)})
            self.assertEqual(chart(teacher,equipo=recent,desde='2020-01-03',hasta='2020-01-03'),{})
            self.assertEqual(chart(teacher,vista='sin_recientes',lab=lab,dias='7'),{'Nunca recibió capturas':(1,2),'Última recepción antigua':(1,2)})
            self.assertEqual(chart(manager,lab=lab,desde='2020-01-04',hasta='2020-01-04',n='2')['Lecturas OK'],(51,51))
            rows=exported(manager,lab=lab,desde='2020-01-02',hasta='2020-01-02')
            self.assertEqual(len(rows),2);self.assertTrue(all(r['hostname'].startswith("'=") for r in rows))
            self.assertEqual(len(exported(manager,lab=lab,desde='2020-01-02',hasta='2020-01-02',estado='ERROR')),1)
            self.assertEqual(len(exported(manager,equipo=recent,desde='2020-01-03',hasta='2020-01-03')),1)
            # La captura del laboratorio anterior de la misma PC no se expone al docente.
            self.assertEqual(exported(teacher,equipo=recent,desde='2020-01-03',hasta='2020-01-03'),[])
            self.assertEqual(exported(teacher,lab=foreign),[])
            stale_rows=exported(teacher,vista='sin_recientes',lab=lab,dias='7')
            self.assertEqual({int(r['id_equipo']) for r in stale_rows},{stale,never})
            self.assertEqual(next(r for r in stale_rows if int(r['id_equipo'])==never)['ultima_recepcion'],'')
            status,html,_=manager.request('historial',lab=lab,desde='2020-01-04',hasta='2020-01-04',n='2')
            self.assertEqual(status,200);self.assertIn('51 resultados',html);self.assertIn('Página 2',html)
            self.assertEqual(len(exported(manager,lab=lab,desde='2020-01-04',hasta='2020-01-04',n='2')),51)
            for filters in [dict(desde='2020-02-30'),dict(equipo='1 OR 1=1'),dict(dias='0'),dict(exportar='otro')]:
                self.assertEqual(manager.request('historial',**filters)[0],400)
            self.assertEqual(student.request('historial')[0],403)
            self.assertEqual(student.request('historial',exportar='csv')[0],403)
            # Revocar la asignación debe quitar también los datos de la exportación.
            root_sql(f'UPDATE asignacion_docente SET hasta=UTC_TIMESTAMP() WHERE usuario_ci={users[1]};')
            self.assertEqual(exported(teacher,lab=lab),[])
            self.assertEqual(chart(teacher,lab=lab),{})
            self.assertEqual(exported(teacher,vista='sin_recientes',lab=lab),[])
        finally:
            root_sql(f"""
DELETE r FROM registro r JOIN equipo e ON e.id_equipo=r.id_equipo JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio WHERE l.nombre IN ('{tag}','{tag}-otra');
DELETE a FROM asignacion_docente a JOIN usuarios u ON u.ci=a.usuario_ci WHERE u.nombre='{tag}';
DELETE e FROM equipo e JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio WHERE l.nombre IN ('{tag}','{tag}-otra');
DELETE FROM laboratorio WHERE nombre IN ('{tag}','{tag}-otra');
DELETE FROM usuarios WHERE nombre='{tag}';
""")


if __name__=='__main__':
    unittest.main()
