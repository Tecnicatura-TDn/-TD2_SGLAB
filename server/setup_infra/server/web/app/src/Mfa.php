<?php
declare(strict_types=1);
final class Mfa {
    public static function pending(): ?array {
        $pending=$_SESSION['mfa']??null;
        if(!$pending){return null;}
        if(time()-$pending['started']>600){unset($_SESSION['mfa']);return null;}
        $user=query('SELECT * FROM usuarios WHERE ci=? AND activo=1',[$pending['ci']])->fetch();
        if(!$user||!Access::isManagerRole($user['tipo_usuario'])||(int)$user['auth_version']!==$pending['version']){unset($_SESSION['mfa']);return null;}
        return $user;
    }
    public static function begin(array $user): void {
        Auth::logout();
        $_SESSION['mfa']=['ci'=>(string)$user['ci'],'started'=>time(),'version'=>(int)$user['auth_version']];
        if(!$user['totp_enabled']){$_SESSION['mfa']['secret']=Totp::secret();}
    }
    public static function confirm(string $code): void {
        $user=self::pending();if(!$user){throw new InvalidArgumentException('La verificación venció. Ingresá nuevamente con tu contraseña.');}
        $ci=(string)$user['ci'];Auth::checkRate('mfa:'.$ci);
        $valid=false;
        db()->beginTransaction();
        try{
            $user=query("SELECT * FROM usuarios WHERE ci=? AND activo=1 AND tipo_usuario IN ('ASISTENTE','ADMINISTRADOR') FOR UPDATE",[$ci])->fetch();
            if(!$user||(int)$user['auth_version']!==$_SESSION['mfa']['version']){throw new RuntimeException('La cuenta cambió. Ingresá nuevamente.');}
            $secret=$user['totp_enabled']?Totp::open($ci,$user['totp_secret']):($_SESSION['mfa']['secret']??'');
            $step=Totp::match($secret,$code,$user['totp_last_step']===null?null:(int)$user['totp_last_step']);
            if($step!==null){
                query('UPDATE usuarios SET totp_secret=?,totp_enabled=1,totp_last_step=? WHERE ci=?',[Totp::seal($ci,$secret),$step,$ci]);
                $user['totp_enabled']=1;$valid=true;
            }
            db()->commit();
        }catch(Throwable $exc){if(db()->inTransaction()){db()->rollBack();}throw $exc;}
        if(!$valid){Auth::failure('mfa:'.$ci);throw new InvalidArgumentException('Código inválido o ya utilizado. Esperá el próximo código de Google Authenticator.');}
        Auth::complete($user,'mfa');
    }
    public static function qr(): string {
        $user=self::pending();$secret=$_SESSION['mfa']['secret']??null;
        if(!$user||$user['totp_enabled']||!$secret){throw new HttpError(404,'QR no disponible.');}
        $uri='otpauth://totp/'.rawurlencode('SGLAB:'.$user['ci']).'?'.http_build_query(['secret'=>$secret,'issuer'=>'SGLAB','algorithm'=>'SHA1','digits'=>6,'period'=>30],'','&',PHP_QUERY_RFC3986);
        $qr=\Endroid\QrCode\QrCode::create($uri)->setSize(260)->setMargin(12);
        return (new \Endroid\QrCode\Writer\SvgWriter())->write($qr)->getString();
    }
}
