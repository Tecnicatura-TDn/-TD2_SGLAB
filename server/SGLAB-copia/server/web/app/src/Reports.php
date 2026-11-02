<?php
declare(strict_types=1);
final class Reports {
    public const STATES=['FUNCIONA'=>'Funciona','NO_FUNCIONA'=>'No funciona'];

    public static function record(string $id, string $state, string $description): void {
        if(Access::role()!=='ALUMNO'){throw new HttpError(403,'Solo los estudiantes pueden reportar el funcionamiento de su PC.');}
        if(!ctype_digit($id)||!isset(self::STATES[$state])){throw new InvalidArgumentException('Seleccioná Funciona o No funciona.');}
        $description=trim($description);
        if(textLength($description)>4000||($state==='NO_FUNCIONA'&&$description==='')){
            throw new InvalidArgumentException('Describí el problema cuando la PC no funciona (hasta 4000 caracteres).');
        }
        // Revalidar la PC detectada al publicar, sin confiar en el id del formulario.
        Access::equipment($id);
        query('INSERT INTO reporte_funcionamiento(id_equipo,autor_ci,estado,descripcion) VALUES (?,?,?,?)',[$id,$_SESSION['user']['ci'],$state,$description]);
    }
    public static function save(): void {
        $id=input('id');
        self::record($id,input('estado_funcional'),input('descripcion'));
        flash('Reporte de funcionamiento publicado.');redirect('equipo',['id'=>$id]);
    }
    public static function list(string $id): array {
        Access::equipment($id);
        // Cada estudiante ve sus propios reportes; el personal consulta el historial
        // dentro de su alcance habitual de equipos/laboratorios.
        $extra=Access::role()==='ALUMNO'?' AND r.autor_ci=?':'';
        $params=[$id];if($extra){$params[]=$_SESSION['user']['ci'];}
        return query('SELECT r.*,u.nombre,u.apellido FROM reporte_funcionamiento r JOIN usuarios u ON u.ci=r.autor_ci WHERE r.id_equipo=?'.$extra.' ORDER BY r.fecha_hora DESC,r.id_reporte DESC LIMIT 50',$params)->fetchAll();
    }
}
