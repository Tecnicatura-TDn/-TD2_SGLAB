"""Reporte manual contra MariaDB/PHP reales; usa y retira datos sintéticos."""
import os
from pathlib import Path
import secrets
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def compose(*args):
    return ['docker','compose','--project-directory',str(ROOT),'--env-file',str(ROOT/'.env'),'-f',str(ROOT/'compose.yaml'),*args]


def root_sql(sql):
    return subprocess.run(compose('exec','-T','db','sh','-c',
        'export MYSQL_PWD="$MARIADB_ROOT_PASSWORD"; exec mariadb -uroot --batch --skip-column-names sglab'),
        input=sql,text=True,capture_output=True,check=True).stdout


@unittest.skipUnless(os.environ.get('SGLAB_TEST_WEB')=='1','SGLAB_TEST_WEB=1 para prueba real')
class Reports(unittest.TestCase):
    def test_scope_validation_history_and_render(self):
        tag='TEST-REPORT-'+secrets.token_hex(6)
        cis=[int(n) for n in root_sql('SELECT ci FROM usuarios').split()]
        ids=[n for n in range(4294966900,4294966800,-1) if n not in cis][:3]
        a,b,t=ids
        lab=pc=other=None
        try:
            result=root_sql(f"""
START TRANSACTION;
INSERT INTO usuarios(ci,nombre,apellido,tipo_usuario,password_hash) VALUES
({a},'{tag}','A','ALUMNO','sin-login'),({b},'{tag}','B','ALUMNO','sin-login'),({t},'{tag}','T','DOCENTE','sin-login');
INSERT INTO laboratorio(nombre) VALUES ('{tag}'); SET @lab=LAST_INSERT_ID();
INSERT INTO equipo(hostname,id_laboratorio) VALUES ('{tag}',@lab); SET @pc=LAST_INSERT_ID();
INSERT INTO equipo(hostname,id_laboratorio) VALUES ('{tag}-otra',@lab); SET @other=LAST_INSERT_ID();
INSERT INTO registro(id_equipo,nombre,ip,estado,fecha,fecha_recepcion) VALUES (@pc,'{tag}','192.0.2.211','OK',UTC_TIMESTAMP(),UTC_TIMESTAMP());
INSERT INTO asignacion_docente(usuario_ci,id_laboratorio,asignado_por_ci) VALUES ({t},@lab,{t});
COMMIT;
SELECT @lab,@pc,@other;
""")
            lab,pc,other=map(int,result.split())
            code=r'''<?php
require '/var/www/html/src/bootstrap.php';
function check($value){if(!$value){throw new RuntimeException('Prueba fallida');}}
function denied($operation,$class){try{$operation();}catch(Throwable $e){check($e instanceof $class);return;}throw new RuntimeException('Se permitió una acción inválida');}
$_SERVER['REMOTE_ADDR']='192.0.2.211'; $_SESSION=['user'=>['ci'=>STUDENT_A,'tipo_usuario'=>'ALUMNO'],'csrf'=>'test'];
$pc='PC_ID';$other='OTHER_ID';
db()->beginTransaction();
try{
    Reports::record($pc,'NO_FUNCIONA','<script>pantalla</script>');
    Reports::record($pc,'FUNCIONA','');
    check(count(Reports::list($pc))===2);
    denied(fn()=>Reports::record($other,'FUNCIONA',''),HttpError::class);
    denied(fn()=>Reports::record($pc,'ERROR',''),InvalidArgumentException::class);
    denied(fn()=>Reports::record($pc,'NO_FUNCIONA','  '),InvalidArgumentException::class);
    denied(fn()=>Reports::record($pc,'FUNCIONA',str_repeat('á',4001)),InvalidArgumentException::class);
    $_SESSION['user']['ci']=STUDENT_B;
    check(count(Reports::list($pc))===0);
    Reports::record($pc,'FUNCIONA','Mi reporte');
    check(count(Reports::list($pc))===1);
    $_SESSION['user']=['ci'=>TEACHER,'tipo_usuario'=>'DOCENTE'];
    check(count(Reports::list($pc))===3);
    denied(fn()=>Reports::record($pc,'FUNCIONA',''),HttpError::class);
    $_SESSION['user']['tipo_usuario']='ASISTENTE';
    check(count(Reports::list($pc))===3);
    denied(fn()=>Reports::record($pc,'FUNCIONA',''),HttpError::class);
    ob_start();view('reports',['id'=>$pc]);$html=ob_get_clean();
    check(str_contains($html,'&lt;script&gt;')&&!str_contains($html,'<script>'));
    check(query('SELECT estado_administrativo FROM equipo WHERE id_equipo=?',[$pc])->fetchColumn()==='OPERATIVA');
    check(query('SELECT estado FROM registro WHERE id_equipo=?',[$pc])->fetchColumn()==='OK');
    $_SESSION['user']=['ci'=>STUDENT_A,'tipo_usuario'=>'ALUMNO'];
    $_SERVER['REMOTE_ADDR']='192.0.2.212';
    denied(fn()=>Reports::record($pc,'FUNCIONA',''),HttpError::class);
    db()->rollBack();echo "Reportes: permisos, PC detectada, privacidad, validación, historial y escape HTML OK\n";
}catch(Throwable $e){if(db()->inTransaction()){db()->rollBack();}throw $e;}
'''
            for old,new in [('STUDENT_A',a),('STUDENT_B',b),('TEACHER',t),('PC_ID',pc),('OTHER_ID',other)]:
                code=code.replace(old,str(new))
            result=subprocess.run(compose('exec','-T','web','php'),input=code,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            print(result.stdout.strip())
        finally:
            root_sql(f"""
DELETE r FROM reporte_funcionamiento r JOIN usuarios u ON u.ci=r.autor_ci WHERE u.nombre='{tag}';
DELETE r FROM registro r JOIN equipo e ON e.id_equipo=r.id_equipo WHERE e.hostname IN ('{tag}','{tag}-otra');
DELETE a FROM asignacion_docente a JOIN usuarios u ON u.ci=a.usuario_ci WHERE u.nombre='{tag}';
DELETE FROM equipo WHERE hostname IN ('{tag}','{tag}-otra');
DELETE FROM laboratorio WHERE nombre='{tag}';
DELETE FROM usuarios WHERE nombre='{tag}';
""")


if __name__=='__main__':
    unittest.main()
