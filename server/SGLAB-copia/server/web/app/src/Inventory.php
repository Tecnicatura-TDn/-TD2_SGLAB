<?php
declare(strict_types=1);

final class Inventory {
    public const STATES = ['OPERATIVA'=>'Operativa','EN_REPARACION'=>'En reparación','FUERA_DE_SERVICIO'=>'Fuera de servicio'];
    public static function saveLab(): void {
        authorizeAdmin(); $name = input('nombre'); $id = input('id');
        if ($name === '' || textLength($name)>100) { throw new InvalidArgumentException('El nombre del laboratorio debe tener entre 1 y 100 caracteres.'); }
        if ($id !== '') {
            if (!ctype_digit($id) || !query('SELECT 1 FROM laboratorio WHERE id_laboratorio=? AND activo=1',[$id])->fetchColumn()) { throw new InvalidArgumentException('El laboratorio no existe.'); }
            query('UPDATE laboratorio SET nombre=? WHERE id_laboratorio=?',[$name,$id]);
        } else { query('INSERT INTO laboratorio(nombre) VALUES (?)',[$name]); }
        flash('Laboratorio guardado.'); redirect('laboratorios');
    }
    public static function equipmentValues(string $serial,string $uuid,string $hostname,string $state): array {
        $serial=strtoupper(trim($serial));$uuid=strtoupper(trim($uuid));$hostname=trim($hostname);
        $invalid=['DEFAULT STRING','TO BE FILLED BY O.E.M.','TO BE FILLED BY OEM','UNKNOWN','NONE','NOT SPECIFIED','SYSTEM SERIAL NUMBER','0','N/A'];
        if ($serial !== '' && (textLength($serial)>100 || in_array($serial,$invalid,true))) { throw new InvalidArgumentException('Ingresá un número de serie real de hasta 100 caracteres.'); }
        if ($uuid !== '' && (!preg_match('/^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$/D',$uuid) || in_array($uuid,['00000000-0000-0000-0000-000000000000','FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF'],true))) { throw new InvalidArgumentException('Ingresá un UUID SMBIOS válido.'); }
        if ($serial==='' && $uuid==='') { throw new InvalidArgumentException('Indicá al menos la serie o el UUID SMBIOS para que spawn.sh pueda identificar la PC.'); }
        if (textLength($hostname)>255) { throw new InvalidArgumentException('El nombre de la PC admite hasta 255 caracteres.'); }
        if (!isset(self::STATES[$state])) { throw new InvalidArgumentException('Seleccioná un estado válido.'); }
        return [$serial,$uuid,$hostname,$state];
    }
    public static function saveEquipment(): void {
        authorizeAdmin();
        $id=input('id'); $serial=strtoupper(input('num_serie')); $uuid=strtoupper(input('smbios_uuid')); $hostname=input('hostname'); $lab=input('id_laboratorio'); $state=input('estado_administrativo');
        [$serial,$uuid,$hostname,$state]=self::equipmentValues($serial,$uuid,$hostname,$state);
        if (!ctype_digit($lab) || !query('SELECT 1 FROM laboratorio WHERE id_laboratorio=? AND activo=1',[$lab])->fetchColumn()) { throw new InvalidArgumentException('Seleccioná un laboratorio existente.'); }
        // Evitar que serie y UUID queden asignados a equipos distintos.
        if (query('SELECT id_equipo FROM equipo WHERE (UPPER(TRIM(num_serie))=? OR UPPER(smbios_uuid)=?) AND id_equipo<>?',[$serial ?: null,$uuid ?: null,$id ?: 0])->fetch()) { throw new InvalidArgumentException('La serie o el UUID ya pertenecen a otra PC.'); }
        $params=[$serial ?: null,$uuid ?: null,$hostname ?: null,$lab,$state];
        db()->beginTransaction();
        try {
            // Mismo bloqueo que el archivado: no dar altas en una sala eliminada.
            if(!query('SELECT 1 FROM laboratorio WHERE id_laboratorio=? AND activo=1 FOR UPDATE',[$lab])->fetchColumn()){
                throw new InvalidArgumentException('El laboratorio dejó de estar activo.');
            }
            if ($id!=='') {
                if (!ctype_digit($id) || !query('SELECT 1 FROM equipo WHERE id_equipo=? AND activo=1 FOR UPDATE',[$id])->fetchColumn()) { throw new InvalidArgumentException('La PC no existe.'); }
                query('UPDATE equipo SET num_serie=?,smbios_uuid=?,hostname=?,id_laboratorio=?,estado_administrativo=? WHERE id_equipo=?',[...$params,$id]);
            } else { query('INSERT INTO equipo(num_serie,smbios_uuid,hostname,id_laboratorio,estado_administrativo) VALUES (?,?,?,?,?)',$params); }
            db()->commit();
        } catch(Throwable $e){if(db()->inTransaction()){db()->rollBack();}throw $e;}
        flash('PC guardada. Ya puede recibir capturas del recolector.'); redirect('equipos');
    }
    public static function archive(string $kind): void {
        Access::requireManager(); $id=input('id'); $restore=input('restore')==='1';
        if(!ctype_digit($id)){throw new InvalidArgumentException('Identificador inválido.');}
        db()->beginTransaction();
        try {
            if($kind==='lab'){
                $lab=query('SELECT * FROM laboratorio WHERE id_laboratorio=? FOR UPDATE',[$id])->fetch();
                if(!$lab){throw new InvalidArgumentException('El laboratorio no existe.');}
                if(!$restore){
                    if(query('SELECT 1 FROM equipo WHERE id_laboratorio=? AND activo=1 LIMIT 1',[$id])->fetchColumn()){
                        throw new InvalidArgumentException('Reasigná o archivá las PC activas antes de eliminar el laboratorio.');
                    }
                    if(query('SELECT 1 FROM asignacion_docente a JOIN usuarios u ON u.ci=a.usuario_ci WHERE a.id_laboratorio=? AND u.activo=1 AND u.tipo_usuario=\'DOCENTE\' AND (a.hasta IS NULL OR a.hasta>UTC_TIMESTAMP()) LIMIT 1',[$id])->fetchColumn()){
                        throw new InvalidArgumentException('Finalizá las asignaciones docentes antes de eliminar el laboratorio.');
                    }
                }
                query('UPDATE laboratorio SET activo=? WHERE id_laboratorio=?',[$restore?1:0,$id]);
            } else {
                $pc=query('SELECT * FROM equipo WHERE id_equipo=? FOR UPDATE',[$id])->fetch();
                if(!$pc){throw new InvalidArgumentException('La PC no existe.');}
                if($restore && !query('SELECT 1 FROM laboratorio WHERE id_laboratorio=? AND activo=1',[$pc['id_laboratorio']])->fetchColumn()){
                    throw new InvalidArgumentException('Restaurá primero el laboratorio de esta PC.');
                }
                query('UPDATE equipo SET activo=? WHERE id_equipo=?',[$restore?1:0,$id]);
            }
            db()->commit();
        } catch(Throwable $e){if(db()->inTransaction()){db()->rollBack();}throw $e;}
        flash($restore?'Registro restaurado.':'Registro eliminado del inventario activo; su historial se conserva.');
        redirect($kind==='lab'?'laboratorios':'equipos');
    }

}
