<?php
declare(strict_types=1);

/** TOTP RFC 6238: HMAC-SHA1, seis dígitos, intervalos de 30 segundos. */
final class Totp {
    public static function secret(): string {
        $alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';$raw=random_bytes(20);$bits='';$result='';
        foreach(str_split($raw) as $byte){$bits.=str_pad(decbin(ord($byte)),8,'0',STR_PAD_LEFT);}
        foreach(str_split($bits,5) as $chunk){$result.=$alphabet[bindec(str_pad($chunk,5,'0',STR_PAD_RIGHT))];}
        return $result;
    }
    private static function decode(string $secret): string {
        if(!preg_match('/^[A-Z2-7]{16,128}$/D',$secret)){throw new RuntimeException('Clave TOTP inválida.');}
        $alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';$bits='';$result='';
        foreach(str_split($secret) as $char){$bits.=str_pad(decbin(strpos($alphabet,$char)),5,'0',STR_PAD_LEFT);}
        foreach(str_split($bits,8) as $chunk){if(strlen($chunk)===8){$result.=chr(bindec($chunk));}}
        return $result;
    }
    public static function code(string $secret,int $step,int $digits=6): string {
        if($step<0||!in_array($digits,[6,8],true)){throw new InvalidArgumentException('Parámetros TOTP inválidos.');}
        $digest=hash_hmac('sha1',pack('N2',intdiv($step,4294967296),$step%4294967296),self::decode($secret),true);
        $offset=ord($digest[19])&15;$number=unpack('N',substr($digest,$offset,4))[1]&0x7fffffff;
        return str_pad((string)($number%(10**$digits)),$digits,'0',STR_PAD_LEFT);
    }
    public static function match(string $secret,string $code,?int $lastStep): ?int {
        if(!preg_match('/^[0-9]{6}$/D',$code)){return null;}
        $now=intdiv(time(),30);
        foreach([$now,$now-1,$now+1] as $step){
            if(($lastStep===null||$step>$lastStep)&&hash_equals(self::code($secret,$step),$code)){return $step;}
        }
        return null;
    }
    private static function key(): string {
        $file=(getenv('SGLAB_WEB_STATE')?:'/var/lib/sglab-web').'/totp-key.bin';
        if(!is_file($file)){
            $handle=@fopen($file,'x+b');
            if($handle){
                chmod($file,0600);flock($handle,LOCK_EX);fwrite($handle,random_bytes(32));fflush($handle);flock($handle,LOCK_UN);fclose($handle);
            }
        }
        $handle=@fopen($file,'rb');if(!$handle){throw new RuntimeException('No se pudo acceder a la clave de cifrado MFA.');}
        try{flock($handle,LOCK_SH);$key=stream_get_contents($handle);}finally{fclose($handle);}
        if(strlen($key)!==32){throw new RuntimeException('La clave de cifrado MFA no está disponible.');}
        return $key;
    }
    public static function seal(string $ci,string $secret): string {
        $iv=random_bytes(12);$tag='';
        $cipher=openssl_encrypt($secret,'aes-256-gcm',self::key(),OPENSSL_RAW_DATA,$iv,$tag,$ci);
        if($cipher===false){throw new RuntimeException('No se pudo proteger la clave MFA.');}
        return 'v1:'.base64_encode($iv.$tag.$cipher);
    }
    public static function open(string $ci,string $encrypted): string {
        $raw=str_starts_with($encrypted,'v1:')?base64_decode(substr($encrypted,3),true):false;
        if($raw===false||strlen($raw)<29){throw new RuntimeException('Configuración MFA inválida.');}
        $secret=openssl_decrypt(substr($raw,28),'aes-256-gcm',self::key(),OPENSSL_RAW_DATA,substr($raw,0,12),substr($raw,12,16),$ci);
        if($secret===false){throw new RuntimeException('No se pudo leer la configuración MFA. Consultá al responsable del servidor.');}
        return $secret;
    }
}
