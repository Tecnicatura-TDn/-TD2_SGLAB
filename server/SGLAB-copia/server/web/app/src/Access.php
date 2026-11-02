<?php
declare(strict_types=1);

final class HttpError extends RuntimeException {
    public function __construct(public readonly int $status, string $message) { parent::__construct($message); }
}
final class Access {
    public static function normalize(string $role): string { return $role==='ADMINISTRADOR'?'ASISTENTE':$role; }
    public static function isManagerRole(string $role): bool { return self::normalize($role)==='ASISTENTE'; }
    public static function role(): string { return self::normalize($_SESSION['user']['tipo_usuario'] ?? ''); }
    public static function manager(): bool { return self::isManagerRole(self::role()); }
    public static function requireManager(): void {
        if (!self::manager()) { throw new HttpError(403,'No tenés permiso para administrar estos datos.'); }
    }
    /** Predicados internos: los alias no provienen de solicitudes HTTP. */
    public static function currentEquipmentId(): ?int {
        // Nunca confiar en X-Forwarded-For enviado por el navegador.
        $ip=$_SERVER['REMOTE_ADDR']??'';
        if(str_starts_with($ip,'::ffff:')){$ip=substr($ip,7);}
        if(!filter_var($ip,FILTER_VALIDATE_IP,FILTER_FLAG_IPV4)){return null;}
        $hours=max(1,min(24,(int)(getenv('SGLAB_PC_IP_MAX_AGE_HOURS')?:8)));
        $matches=query("SELECT e.id_equipo FROM equipo e JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio AND l.activo=1 JOIN registro r ON r.id_registro=(SELECT r0.id_registro FROM registro r0 WHERE r0.id_equipo=e.id_equipo ORDER BY r0.fecha DESC,r0.id_registro DESC LIMIT 1) WHERE e.activo=1 AND SUBSTRING_INDEX(r.ip,'/',1)=? AND r.fecha_recepcion>=DATE_SUB(UTC_TIMESTAMP(),INTERVAL $hours HOUR) LIMIT 2",[$ip])->fetchAll();
        return count($matches)===1?(int)$matches[0]['id_equipo']:null;
    }
    public static function equipmentScope(bool $archived = false): array {
        if (self::manager()) { return [$archived ? 'e.activo=0' : 'e.activo=1',[]]; }
        $ci=$_SESSION['user']['ci'];
        $base='e.activo=1 AND EXISTS (SELECT 1 FROM laboratorio l0 WHERE l0.id_laboratorio=e.id_laboratorio AND l0.activo=1)';
        if (self::role()==='ALUMNO') {
            $id=self::currentEquipmentId();
            return $id!==null?[$base.' AND e.id_equipo=?',[$id]]:['1=0',[]];
        }
        if (self::role()==='DOCENTE') {
            return [$base.' AND EXISTS (SELECT 1 FROM asignacion_docente a WHERE a.usuario_ci=? AND a.id_laboratorio=e.id_laboratorio AND a.desde<=UTC_TIMESTAMP() AND (a.hasta IS NULL OR a.hasta>UTC_TIMESTAMP()))',[$ci]];
        }
        return ['1=0',[]];
    }
    public static function labScope(bool $archived=false): array {
        if(self::manager()){ return [$archived?'l.activo=0':'l.activo=1',[]]; }
        if(self::role()==='DOCENTE'){
            return ['l.activo=1 AND EXISTS (SELECT 1 FROM asignacion_docente a WHERE a.usuario_ci=? AND a.id_laboratorio=l.id_laboratorio AND a.desde<=UTC_TIMESTAMP() AND (a.hasta IS NULL OR a.hasta>UTC_TIMESTAMP()))',[$_SESSION['user']['ci']]];
        }
        return ['1=0',[]];
    }
    public static function equipment(string $id): array {
        [$scope,$params]=self::equipmentScope();
        $pc=query('SELECT e.*,l.nombre laboratorio FROM equipo e LEFT JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio WHERE e.id_equipo=? AND '.$scope,[$id,...$params])->fetch();
        if(!$pc){throw new HttpError(404,'PC no disponible para tu usuario.');} return $pc;
    }
    public static function lab(string $id): array {
        [$scope,$params]=self::labScope();
        $lab=query('SELECT l.* FROM laboratorio l WHERE l.id_laboratorio=? AND '.$scope,[$id,...$params])->fetch();
        if(!$lab){throw new HttpError(404,'Laboratorio no disponible para tu usuario.');} return $lab;
    }
    public static function requirePage(string $page): void {
        if($page==='historial'){History::authorize();}
        if($page==='usuarios'){self::requireManager();}
        if(in_array($page,['laboratorios','laboratorio'],true)&&self::role()==='ALUMNO'){
            throw new HttpError(403,'Tu cuenta permite consultar y comentar únicamente tu PC asignada.');
        }
    }
}
