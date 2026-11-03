<?php
declare(strict_types=1);
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
require __DIR__.'/../src/bootstrap.php';
try{
    $ci=$argv[1]??'';
    if(!ctype_digit($ci)){throw new InvalidArgumentException('Uso: docker compose exec web php bin/reset-mfa.php CEDULA');}
    if(!stream_isatty(STDIN)){throw new RuntimeException('Usá una terminal interactiva para confirmar.');}
    if(!query("SELECT 1 FROM usuarios WHERE ci=? AND tipo_usuario IN ('ASISTENTE','ADMINISTRADOR')",[$ci])->fetchColumn()){throw new InvalidArgumentException('No existe ese asistente administrador.');}
    echo "Esto invalida sus sesiones y obliga a vincular nuevamente Google Authenticator.\nConfirmá escribiendo la cédula: ";
    if(trim((string)fgets(STDIN))!==$ci){throw new RuntimeException('Operación cancelada.');}
    query('UPDATE usuarios SET totp_secret=NULL,totp_enabled=0,totp_last_step=NULL,auth_version=auth_version+1 WHERE ci=?',[$ci]);
    echo "MFA restablecido. La próxima vez deberá ingresar su contraseña y configurar un nuevo autenticador.\n";
}catch(Throwable $exc){fwrite(STDERR,$exc instanceof PDOException?"No se pudo restablecer MFA.\n":$exc->getMessage()."\n");exit(1);}
