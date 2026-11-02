<?php
declare(strict_types=1);
final class People {
    public static function roles(): array {
        return ['ALUMNO'=>'Estudiante','DOCENTE'=>'Docente','ASISTENTE'=>'Asistente (administrador)'];
    }
    public static function save(): void {
        Access::requireManager();$id=input('id');$ci=input('ci');$role=Access::normalize(input('tipo_usuario'));$name=input('nombre');$surname=input('apellido');$email=input('correo');$active=input('activo')==='1'?1:0;
        $password=is_string($_POST['password']??null)?$_POST['password']:'';
        if(!ctype_digit($ci)||(int)$ci<1||(int)$ci>4294967295){throw new InvalidArgumentException('Cédula inválida: usá solo números, sin puntos ni guion.');}
        if($name===''||$surname===''||textLength($name)>100||textLength($surname)>100){throw new InvalidArgumentException('Nombre y apellido son obligatorios y admiten hasta 100 caracteres.');}
        if($email!==''&&(!filter_var($email,FILTER_VALIDATE_EMAIL)||strlen($email)>254)){throw new InvalidArgumentException('Correo inválido.');}
        if($role==='ALUMNO'&&$email===''){throw new InvalidArgumentException('El estudiante necesita el email principal verificado de GitHub.');}
        if(!isset(self::roles()[$role])){throw new HttpError(403,'No podés crear ni asignar ese rol.');}
        if((($id===''&&$role!=='ALUMNO')||$password!=='')&&(strlen($password)<12||strlen($password)>72)){throw new InvalidArgumentException('La contraseña debe tener entre 12 y 72 bytes.');}
        if($id!==''&&$id!==$ci){throw new InvalidArgumentException('No se cambia la cédula de una cuenta existente.');}
        db()->beginTransaction();
        try{
            // Serializar cambios que puedan quitar el último administrador activo.
            $admins=query("SELECT ci FROM usuarios WHERE tipo_usuario IN ('ASISTENTE','ADMINISTRADOR') AND activo=1 FOR UPDATE")->fetchAll();
            if($id!==''){
                $target=query('SELECT * FROM usuarios WHERE ci=? FOR UPDATE',[$id])->fetch();
                if(!$target){throw new InvalidArgumentException('El usuario no existe.');}
                if(!isset(self::roles()[Access::normalize($target['tipo_usuario'])])){throw new HttpError(403,'Rol de usuario no admitido.');}
                if(Access::isManagerRole($target['tipo_usuario'])&&$target['activo']&&(!Access::isManagerRole($role)||!$active)&&count($admins)<=1){throw new InvalidArgumentException('Debe quedar al menos un asistente administrador activo.');}
                query('UPDATE usuarios SET nombre=?,apellido=?,correo=?,tipo_usuario=?,activo=? WHERE ci=?',[$name,$surname,$email?:null,$role,$active,$ci]);
                if($password!==''){query('UPDATE usuarios SET password_hash=? WHERE ci=?',[password_hash($password,PASSWORD_DEFAULT),$ci]);}
                if($password!==''||(int)$target['activo']!==$active||$target['tipo_usuario']!==$role||strtolower($target['correo']??'')!==strtolower($email)){query('UPDATE usuarios SET auth_version=auth_version+1 WHERE ci=?',[$ci]);}
                if(!$active||$target['tipo_usuario']!==$role){
                    foreach(['asignacion_docente'] as $table){query("UPDATE $table SET desde=LEAST(desde,UTC_TIMESTAMP()),hasta=UTC_TIMESTAMP() WHERE usuario_ci=?",[$ci]);}
                }
            }else{
                if(query('SELECT 1 FROM usuarios WHERE ci=?',[$ci])->fetchColumn()){throw new InvalidArgumentException('La cédula ya tiene una cuenta.');}
                query('INSERT INTO usuarios(ci,nombre,apellido,correo,tipo_usuario,password_hash,activo) VALUES (?,?,?,?,?,?,?)',[$ci,$name,$surname,$email?:null,$role,password_hash($password!==''?$password:bin2hex(random_bytes(32)),PASSWORD_DEFAULT),$active]);
            }
            db()->commit();
        }catch(Throwable $e){if(db()->inTransaction()){db()->rollBack();}throw $e;}
        flash('Usuario guardado.');redirect('usuarios');
    }
    private static function date(string $value): string {
        $date=DateTimeImmutable::createFromFormat('!Y-m-d\TH:i',$value,new DateTimeZone('UTC'));
        if(!$date||$date->format('Y-m-d\TH:i')!==$value){throw new InvalidArgumentException('Fecha inválida. Las asignaciones usan UTC.');}
        return $date->format('Y-m-d H:i:s');
    }
    public static function assign(bool $revoke=false): void {
        Access::requireManager();$ci=input('usuario_ci');
        if(!ctype_digit($ci)){throw new InvalidArgumentException('Seleccioná una persona.');}
        db()->beginTransaction();
        try{
            $user=query('SELECT * FROM usuarios WHERE ci=? FOR UPDATE',[$ci])->fetch();
            if(!$user||!$user['activo']||$user['tipo_usuario']!=='DOCENTE'){throw new InvalidArgumentException('Seleccioná un docente activo.');}
            $table='asignacion_docente';$column='id_laboratorio';
            if($revoke){
                query("UPDATE $table SET desde=LEAST(desde,UTC_TIMESTAMP()),hasta=UTC_TIMESTAMP() WHERE usuario_ci=?",[$ci]);
            }else{
                $resource=input('recurso');if(!ctype_digit($resource)){throw new InvalidArgumentException('Seleccioná el destino de la asignación.');}
                if(!query('SELECT 1 FROM laboratorio WHERE id_laboratorio=? AND activo=1 FOR UPDATE',[$resource])->fetchColumn()){
                    throw new InvalidArgumentException('Seleccioná un laboratorio activo.');
                }
                $start=input('desde')!==''?self::date(input('desde')):gmdate('Y-m-d H:i:s');
                $end=input('hasta')!==''?self::date(input('hasta')):null;
                if($end!==null&&($end<=$start||$end<=gmdate('Y-m-d H:i:s'))){throw new InvalidArgumentException('El fin debe ser posterior al inicio y a la fecha actual.');}
                query("INSERT INTO $table(usuario_ci,$column,desde,hasta,asignado_por_ci) VALUES (?,?,?,?,?) ON DUPLICATE KEY UPDATE $column=VALUES($column),desde=VALUES(desde),hasta=VALUES(hasta),asignado_por_ci=VALUES(asignado_por_ci)",[$ci,$resource,$start,$end,$_SESSION['user']['ci']]);
            }
            db()->commit();
        }catch(Throwable $e){if(db()->inTransaction()){db()->rollBack();}throw $e;}
        flash($revoke?'Asignación finalizada.':'Asignación guardada. Los accesos se aplican según su vigencia.');redirect('usuarios');
    }
}
