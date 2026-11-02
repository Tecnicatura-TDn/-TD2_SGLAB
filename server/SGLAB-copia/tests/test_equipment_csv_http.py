"""Carga multipart real: login/MFA, permisos y rollback de importación de PC."""
import json
import os
import secrets
import subprocess
import unittest
import urllib.error
import urllib.parse
import urllib.request
from test_reports import root_sql, compose
from test_web_integration import Browser, BASE


@unittest.skipUnless(os.environ.get('SGLAB_TEST_WEB')=='1','SGLAB_TEST_WEB=1 para HTTPS real')
class EquipmentCsvHttp(unittest.TestCase):
    def upload(self, browser, lab, content, csrf=None):
        if csrf is None:
            _,html,_=browser.request('equipos'); csrf=browser.csrf(html)
        boundary='sglab'+secrets.token_hex(16)
        parts=[]
        for key,value in [('action','import_equipment'),('csrf',csrf),('laboratorio_csv',str(lab))]:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n')
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="csv"; filename="pc.csv"\r\nContent-Type: text/csv\r\n\r\n{content}\r\n--{boundary}--\r\n')
        request=urllib.request.Request(BASE+'/?page=equipos',data=''.join(parts).encode(),headers={'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            response=browser.opener.open(request,timeout=20)
        except urllib.error.HTTPError as error:
            response=error
        return response.status,response.read().decode()

    def test_import_atomicity_and_permissions(self):
        tag='TEST-CSV-PC-'+secrets.token_hex(6)
        password=secrets.token_urlsafe(24)
        existing=[int(x) for x in root_sql('SELECT ci FROM usuarios').split()]
        users=[x for x in range(4294966700,4294966600,-1) if x not in existing][:2]
        header='hostname,num_serie,smbios_uuid,estado_administrativo\n'
        try:
            lab=int(root_sql(f"INSERT INTO laboratorio(nombre) VALUES ('{tag}'); SELECT LAST_INSERT_ID();"))
            inactive=int(root_sql(f"INSERT INTO laboratorio(nombre,activo) VALUES ('{tag}',0); SELECT LAST_INSERT_ID();"))
            code="require '/var/www/html/src/bootstrap.php';$d=json_decode(stream_get_contents(STDIN),true);foreach($d['users'] as $i=>$ci){query('INSERT INTO usuarios(ci,nombre,apellido,password_hash,tipo_usuario) VALUES (?,?,?,?,?)',[$ci,$d['tag'],'Temporal',password_hash($d['password'],PASSWORD_DEFAULT),$i===0?'ASISTENTE':'DOCENTE']);}"
            subprocess.run(compose('exec','-T','web','php','-r',code),input=json.dumps(dict(users=users,tag=tag,password=password)),text=True,capture_output=True,check=True)
            manager=Browser();self.assertEqual(manager.login(users[0],password)[0],200)
            csv=header+f'{tag}-1,{tag}-SERIE1,,\n{tag}-2,{tag}-SERIE2,,EN_REPARACION\n'
            status,html=self.upload(manager,lab,csv)
            self.assertEqual(status,200); self.assertIn('2 PC importadas',html)
            self.assertEqual(root_sql(f'SELECT COUNT(*) FROM equipo WHERE id_laboratorio={lab};').strip(),'2')
            # La segunda fila ya existe: la primera fila nueva también debe revertirse.
            rollback=header+f'{tag}-3,{tag}-SERIE3,,\n{tag}-4,{tag}-SERIE1,,\n'
            status,html=self.upload(manager,lab,rollback)
            self.assertIn('Fila 3:',html);self.assertIn('No se importó ninguna PC',html)
            self.assertEqual(root_sql(f'SELECT COUNT(*) FROM equipo WHERE id_laboratorio={lab};').strip(),'2')
            # Un equipo archivado sigue reservando su identidad.
            root_sql(f"UPDATE equipo SET activo=0 WHERE num_serie='{tag}-SERIE1';")
            self.assertIn('incluso archivada',self.upload(manager,lab,rollback)[1])
            self.assertIn('dejó de estar activo',self.upload(manager,inactive,header+f'{tag}-3,{tag}-SERIE3,,\n')[1])
            self.assertEqual(self.upload(manager,lab,csv,csrf='incorrecto')[0],403)
            teacher=Browser();self.assertEqual(teacher.login(users[1],password)[0],200)
            self.assertEqual(self.upload(teacher,lab,csv)[0],403)
            self.assertEqual(root_sql(f'SELECT COUNT(*) FROM equipo WHERE id_laboratorio={lab};').strip(),'2')
        finally:
            root_sql(f"DELETE e FROM equipo e JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio WHERE l.nombre='{tag}'; DELETE FROM laboratorio WHERE nombre='{tag}'; DELETE FROM usuarios WHERE nombre='{tag}';")


if __name__=='__main__':
    unittest.main()
