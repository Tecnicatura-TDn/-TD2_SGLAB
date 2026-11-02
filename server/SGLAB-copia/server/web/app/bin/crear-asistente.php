<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__ . '/../src/bootstrap.php';
function ask(string $label): string { fwrite(STDOUT,$label.': '); return trim((string)fgets(STDIN)); }
function secret(string $label): string {
    if (!stream_isatty(STDIN)) { throw new RuntimeException('Ejecutá este comando en una terminal interactiva (docker compose exec sin -T).'); }
    $mode=trim((string)shell_exec('stty -g'));
    if ($mode==='') { throw new RuntimeException('No se pudo ocultar la contraseña en esta terminal.'); }
    fwrite(STDOUT,$label.': '); shell_exec('stty -echo');
    try { $value=rtrim((string)fgets(STDIN),"\r\n"); }
    finally { shell_exec('stty '.escapeshellarg($mode)); fwrite(STDOUT,"\n"); }
    return $value;
}
try {
    echo "Crear asistente administrador SGLAB (no modifica usuarios existentes)\n";
    $ci=ask('Cédula sin puntos ni guion');$name=ask('Nombre');$surname=ask('Apellido');$email=ask('Correo (opcional)');
    if(!ctype_digit($ci)||(int)$ci<1||(int)$ci>4294967295){throw new InvalidArgumentException('Cédula inválida.');}
    if($name===''||$surname===''||textLength($name)>100||textLength($surname)>100){throw new InvalidArgumentException('Nombre y apellido son obligatorios y admiten hasta 100 caracteres.');}
    if($email!==''&&(!filter_var($email,FILTER_VALIDATE_EMAIL)||strlen($email)>254)){throw new InvalidArgumentException('Correo inválido.');}
    if(query('SELECT 1 FROM usuarios WHERE ci=?',[$ci])->fetchColumn()){throw new InvalidArgumentException('La cédula ya existe. No se modificó su contraseña ni su rol.');}
    $password=secret('Contraseña (mínimo 12 caracteres)');$confirmation=secret('Repetir contraseña');
    if(strlen($password)<12||strlen($password)>72||$password!==$confirmation){throw new InvalidArgumentException('Las contraseñas deben coincidir y tener entre 12 y 72 bytes.');}
    query('INSERT INTO usuarios(ci,nombre,apellido,correo,password_hash,tipo_usuario) VALUES (?,?,?,?,?,?)',[$ci,$name,$surname,$email?:null,password_hash($password,PASSWORD_DEFAULT),'ASISTENTE']);
    echo "Asistente creado. Ya podés ingresar a la web con tu cédula.\n";
} catch(Throwable $exc){fwrite(STDERR,$exc instanceof PDOException?"No se pudo crear el usuario. Revisá conexión y datos duplicados.\n":$exc->getMessage()."\n");exit(1);}
