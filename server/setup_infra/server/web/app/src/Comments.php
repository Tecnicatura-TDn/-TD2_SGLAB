<?php
declare(strict_types=1);
final class Comments {
    public static function save(): void {
        $kind=input('kind');$id=input('id');$text=input('contenido');
        if(!ctype_digit($id)||$text===''||textLength($text)>4000){throw new InvalidArgumentException('Escribí un comentario de 1 a 4000 caracteres.');}
        if($kind==='equipo'){
            if(!manage()&&Access::role()!=='ALUMNO'){throw new HttpError(403,'El docente comenta sobre su laboratorio asignado.');}
            Access::equipment($id);
            query('INSERT INTO comentario(id_equipo,autor_ci,contenido) VALUES (?,?,?)',[$id,$_SESSION['user']['ci'],$text]);
        }elseif($kind==='laboratorio'){
            if(!manage()&&Access::role()!=='DOCENTE'){throw new HttpError(403,'No podés comentar laboratorios con este rol.');}
            Access::lab($id);
            query('INSERT INTO comentario_laboratorio(id_laboratorio,autor_ci,contenido) VALUES (?,?,?)',[$id,$_SESSION['user']['ci'],$text]);
        }else{throw new InvalidArgumentException('Tipo de comentario inválido.');}
        flash('Comentario publicado.');redirect($kind,['id'=>$id]);
    }
    public static function list(string $kind,string $id): array {
        if($kind==='equipo'){
            Access::equipment($id);
            // No exponer comentarios personales de alumnos anteriores de la PC.
            $extra=Access::role()==='ALUMNO'?" AND (c.autor_ci=? OR u.tipo_usuario IN ('ADMINISTRADOR','ASISTENTE'))":'';
            $params=[$id];if($extra){$params[]=$_SESSION['user']['ci'];}
            return query('SELECT c.*,u.nombre,u.apellido FROM comentario c JOIN usuarios u ON u.ci=c.autor_ci WHERE c.id_equipo=?'.$extra.' ORDER BY c.id_comentario DESC LIMIT 50',$params)->fetchAll();
        }
        Access::lab($id);
        return query('SELECT c.*,u.nombre,u.apellido FROM comentario_laboratorio c JOIN usuarios u ON u.ci=c.autor_ci WHERE c.id_laboratorio=? ORDER BY c.id_comentario DESC LIMIT 50',[$id])->fetchAll();
    }
}
