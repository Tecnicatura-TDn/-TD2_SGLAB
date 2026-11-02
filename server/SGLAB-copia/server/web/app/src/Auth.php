<?php
declare(strict_types=1);
final class Auth {
    public static function start(): void {
        ini_set('session.use_strict_mode','1');ini_set('session.use_only_cookies','1');session_name('sglab_session');
        session_set_cookie_params(['lifetime'=>0,'path'=>'/','secure'=>!empty($_SERVER['HTTPS'])&&$_SERVER['HTTPS']!=='off','httponly'=>true,'samesite'=>'Lax']);session_start();
        if(isset($_SESSION['user'])&&(time()-($_SESSION['last_seen']??0)>900||time()-($_SESSION['started']??0)>28800)){self::logout();flash('Tu sesión venció. Ingresá nuevamente.');}
        $_SESSION['csrf']??=bin2hex(random_bytes(32));
        if(isset($_SESSION['user'])){
            $user=query('SELECT ci,nombre,apellido,tipo_usuario,auth_version,totp_enabled,github_id FROM usuarios WHERE ci=? AND activo=1',[$_SESSION['user']['ci']])->fetch();
            $method=$_SESSION['auth_method']??'';
            $allowed=$user&&(int)$user['auth_version']===($_SESSION['auth_version']??-1);
            if($allowed&&Access::isManagerRole($user['tipo_usuario'])){$allowed=$method==='mfa'&&(bool)$user['totp_enabled'];}
            if($allowed&&$user['tipo_usuario']==='ALUMNO'){$allowed=$method==='github'&&$user['github_id']!==null&&(string)$user['github_id']===($_SESSION['github_id']??'');}
            if(!$allowed){self::logout();}else{$_SESSION['user']=array_intersect_key($user,array_flip(['ci','nombre','apellido','tipo_usuario']));$_SESSION['last_seen']=time();}
        }
    }
    public static function logout(): void {$_SESSION=[];session_regenerate_id(true);$_SESSION['csrf']=bin2hex(random_bytes(32));}
    private static function rate(string $identity,bool $failure): bool {
        $directory=getenv('SGLAB_WEB_STATE')?:'/var/lib/sglab-web';$key=hash('sha256',($_SERVER['REMOTE_ADDR']??'').'|'.$identity);
        $file=fopen($directory.'/login-'.$key.'.json','c+');
        if(!$file||!flock($file,LOCK_EX)){throw new RuntimeException('No se pudo verificar el acceso. Intentá más tarde.');}
        try{
            $data=json_decode(stream_get_contents($file),true);
            if(!is_array($data)||time()-($data['start']??0)>900){$data=['start'=>time(),'attempts'=>0];}
            $blocked=$data['attempts']>=10;if($failure&&!$blocked){++$data['attempts'];}
            rewind($file);ftruncate($file,0);fwrite($file,json_encode($data,JSON_THROW_ON_ERROR));return $blocked;
        }finally{flock($file,LOCK_UN);fclose($file);}
    }
    public static function checkRate(string $identity): void {if(self::rate($identity,false)){throw new InvalidArgumentException('Demasiados intentos. Esperá 15 minutos antes de volver a intentar.');}}
    public static function failure(string $identity): void {self::rate($identity,true);}
    public static function login(string $ci,string $password): void {
        self::checkRate($ci);
        $user=preg_match('/^[0-9]{1,10}$/D',$ci)?query('SELECT * FROM usuarios WHERE ci=?',[$ci])->fetch():false;
        $dummy='$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2uheWG/igi.';
        $valid=password_verify($password,$user?$user['password_hash']:$dummy);
        if(!$user||!$valid||!$user['activo']){self::failure($ci);throw new InvalidArgumentException('Cédula o contraseña incorrectas.');}
        if($user['tipo_usuario']==='ALUMNO'){throw new InvalidArgumentException('Los estudiantes ingresan con «Continuar con GitHub».');}
        if(password_needs_rehash($user['password_hash'],PASSWORD_DEFAULT)){query('UPDATE usuarios SET password_hash=? WHERE ci=?',[password_hash($password,PASSWORD_DEFAULT),$user['ci']]);}
        if(Access::isManagerRole($user['tipo_usuario'])){Mfa::begin($user);return;}
        self::complete($user,'password');
    }
    public static function complete(array $user,string $method): void {
        session_regenerate_id(true);
        $_SESSION=['user'=>array_intersect_key($user,array_flip(['ci','nombre','apellido','tipo_usuario'])),
            'started'=>time(),'last_seen'=>time(),'csrf'=>bin2hex(random_bytes(32)),
            'auth_method'=>$method,'auth_version'=>(int)$user['auth_version']];
        if($method==='github'){$_SESSION['github_id']=(string)$user['github_id'];}
    }
}
