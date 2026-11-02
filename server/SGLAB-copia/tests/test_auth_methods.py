"""MFA real y OAuth GitHub con respuestas simuladas, sin credenciales externas."""
import json
import os
import re
import secrets
import subprocess
import unittest
from test_web_integration import ROOT, Browser, database, totp_code
from test_role_scope import root_sql, literal


def php(code, data=None):
    result=subprocess.run(['docker','compose','exec','-T','web','php','-r',code],cwd=ROOT,input=json.dumps(data or {}),text=True,capture_output=True,check=True)
    return result.stdout


@unittest.skipUnless(os.environ.get('SGLAB_TEST_WEB')=='1','SGLAB_TEST_WEB=1 para autenticación integrada')
class AuthMethods(unittest.TestCase):
    def setUp(self):
        self.name='TEST-AUTH-'+secrets.token_hex(6)
        self.password=secrets.token_urlsafe(24)
        self.users=[]
        self.free=[]
        for ci in range(4294966900,4294966800,-1):
            if not database('SELECT 1 FROM usuarios WHERE ci=?',[ci]):self.free.append(ci)
            if len(self.free)==3:break

    def user(self,role,email=None):
        ci=self.free.pop(0)
        code="require '/var/www/html/src/bootstrap.php'; $d=json_decode(stream_get_contents(STDIN),true); query('INSERT INTO usuarios(ci,nombre,apellido,tipo_usuario,password_hash,correo) VALUES (?,?,?,?,?,?)',[$d['ci'],$d['name'],'Temporal',$d['role'],password_hash($d['password'],PASSWORD_DEFAULT),$d['email']]);"
        php(code,dict(ci=ci,name=self.name,role=role,password=self.password,email=email))
        self.users.append(ci)
        return ci

    def tearDown(self):
        root_sql('DELETE FROM usuarios WHERE nombre='+literal(self.name)+" AND apellido='Temporal';")

    def test_totp_rfc_and_encryption(self):
        code="""require '/var/www/html/src/bootstrap.php';
        $secret='GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ';
        $times=[59,1111111109,1111111111,1234567890,2000000000,20000000000];$out=[];
        foreach($times as $t){$out[]=Totp::code($secret,intdiv($t,30),8);}
        $dir=sys_get_temp_dir().'/sglab-key-test-'.bin2hex(random_bytes(8));mkdir($dir,0700);putenv('SGLAB_WEB_STATE='.$dir);
        try{
          $cipher=Totp::seal('1',$secret);if(Totp::open('1',$cipher)!==$secret||str_contains($cipher,$secret))exit(1);
          try{Totp::open('2',$cipher);exit(2);}catch(RuntimeException $e){}
          $out[]='encrypted';
        }finally{unlink($dir.'/totp-key.bin');rmdir($dir);}
        echo json_encode($out);"""
        self.assertEqual(json.loads(php(code)),['94287082','07081804','14050471','89005924','69279037','65353130','encrypted'])

    def test_admin_requires_enrollment_code_and_blocks_replay(self):
        self._assert_manager_mfa('ADMINISTRADOR')

    def test_assistant_requires_enrollment_code_and_blocks_replay(self):
        self._assert_manager_mfa('ASISTENTE')

    def _assert_manager_mfa(self,role):
        ci=self.user(role)
        browser=Browser()
        _,html,_=browser.request('login')
        status,html,_=browser.request('login',dict(action='login',csrf=browser.csrf(html),ci=ci,password=self.password))
        self.assertEqual(status,200);self.assertIn('Configurá tu autenticador',html)
        self.assertNotIn('Resumen del laboratorio',html)
        secret=re.search(r'id="totp-secret">([A-Z2-7]+)</code>',html).group(1)
        status,qr,headers=browser.request('mfa_qr')
        self.assertEqual(status,200);self.assertIn('image/svg+xml',headers['Content-Type']);self.assertIn('<svg',qr)
        _,html,_=browser.request('equipos');self.assertIn('Configurá tu autenticador',html)
        self.assertEqual(int(database('SELECT totp_enabled FROM usuarios WHERE ci=?',[ci])[0]['totp_enabled']),0)
        _,html,_=browser.request('mfa',dict(action='mfa_verify',csrf=browser.csrf(html),code='bad'))
        self.assertIn('Código inválido',html)
        code=totp_code(secret)
        _,html,_=browser.request('mfa',dict(action='mfa_verify',csrf=browser.csrf(html),code=code))
        self.assertIn('Resumen del laboratorio',html)
        row=database('SELECT totp_enabled,totp_secret FROM usuarios WHERE ci=?',[ci])[0]
        self.assertEqual(int(row['totp_enabled']),1);self.assertNotEqual(row['totp_secret'],secret)
        _,html,_=browser.request('inicio',dict(action='logout',csrf=browser.csrf(html)))
        _,html,_=browser.request('login',dict(action='login',csrf=browser.csrf(html),ci=ci,password=self.password))
        self.assertIn('Verificá tu acceso',html);self.assertNotIn('totp-secret',html)
        self.assertIn('Esta cuenta ya tiene un autenticador vinculado',html)
        self.assertIn('Cédula de la cuenta:',html);self.assertIn(str(ci),html)
        self.assertEqual(browser.request('mfa_qr')[0],404)
        _,html,_=browser.request('mfa',dict(action='mfa_verify',csrf=browser.csrf(html),code=code))
        self.assertIn('ya utilizado',html);self.assertNotIn('Resumen del laboratorio',html)
        # Restablecer MFA invalida un desafío pendiente y fuerza nuevo QR.
        root_sql('UPDATE usuarios SET totp_enabled=0,totp_secret=NULL,totp_last_step=NULL,auth_version=auth_version+1 WHERE ci='+str(ci)+';')
        _,html,_=browser.request('mfa');self.assertIn('name="password"',html)
        _,html,_=browser.request('login',dict(action='login',csrf=browser.csrf(html),ci=ci,password=self.password))
        self.assertIn('Configurá tu autenticador',html)
    def test_student_password_is_disabled_and_oauth_validation(self):
        email='student-'+secrets.token_hex(6)+'@example.test'
        ci=self.user('ALUMNO',email)
        teacher=self.user('DOCENTE','teacher-'+secrets.token_hex(6)+'@example.test')
        browser=Browser()
        _,html,_=browser.request('login')
        _,html,_=browser.request('login',dict(action='login',csrf=browser.csrf(html),ci=ci,password=self.password))
        self.assertIn('Los estudiantes ingresan',html)
        self.assertNotIn('Mi PC ·',html)
        # Sin credenciales reales: el proveedor se simula solo en una llamada CLI.
        # No hay parámetros HTTP ni flags de producción para saltar OAuth.
        code="""require '/var/www/html/src/bootstrap.php';
        $d=json_decode(stream_get_contents(STDIN),true);putenv('GITHUB_CLIENT_ID=test-client');putenv('GITHUB_CLIENT_SECRET=test-secret');putenv('GITHUB_REDIRECT_URI=https://localhost/?page=github_callback');
        session_name('sglab_test_oauth');session_start();$_SERVER['REMOTE_ADDR']='127.0.0.1';
        $out=[];$currentEmail=$d['email'];$verified=true;$gid='8'.$d['ci'];$called=[];
        $fetch=function($url,$headers,$data)use(&$currentEmail,&$verified,&$gid,&$called){
          $called[]=['url'=>$url,'data'=>$data];
          if(str_contains($url,'access_token'))return ['access_token'=>'test_token_123'];
          if(str_contains($url,'/emails?'))return [['email'=>$currentEmail,'primary'=>true,'verified'=>$verified]];
          return ['id'=>$gid,'email'=>'untrusted@example.test'];
        };
        $start=function(){ $url=GithubAuth::begin();parse_str(parse_url($url,PHP_URL_QUERY),$q);return $q; };
        $fail=function($state,$message)use($fetch,&$out){try{GithubAuth::callback(['state'=>$state,'code'=>'test-code'],$fetch);throw new Exception('Acceso indebido');}catch(InvalidArgumentException|HttpError $e){$out[]=$message;}};
        $q=$start();if($q['code_challenge_method']!=='S256'||$q['scope']!=='read:user user:email')exit(2);
        $fail('wrong-state','state');if(count($called)!==0)exit(3);
        $q=$start();$_SESSION['oauth']['started']=time()-601;$fail($q['state'],'expired');
        $q=$start();$verified=false;$fail($q['state'],'unverified');$verified=true;
        $q=$start();$currentEmail='not-registered@example.test';$fail($q['state'],'missing');
        $q=$start();$currentEmail=$d['teacher_email'];$fail($q['state'],'role');
        $q=$start();$currentEmail=$d['email'];$verifier=$_SESSION['oauth']['verifier'];
        GithubAuth::callback(['state'=>$q['state'],'code'=>'test-code'],$fetch);
        if((int)$_SESSION['user']['ci']!==$d['ci']||$_SESSION['auth_method']!=='github'||isset($_SESSION['access_token']))exit(4);
        $last=array_slice($called,-3)[0];if($last['data']['code_verifier']!==$verifier)exit(5);$out[]='github-session';
        $q=$start();$gid='7'.$d['ci'];$fail($q['state'],'different-github-id');
        echo json_encode($out);"""
        teacher_email=database('SELECT correo FROM usuarios WHERE ci=?',[teacher])[0]['correo']
        results=json.loads(php(code,dict(email=email,ci=ci,teacher_email=teacher_email)))
        self.assertEqual(results,['state','expired','unverified','missing','role','github-session','different-github-id'])
        # Docente conserva login local directo, sin MFA.
        status,html,_=Browser().login(teacher,self.password)
        self.assertEqual(status,200);self.assertIn('Mi laboratorio actual',html)


if __name__=='__main__':unittest.main()
