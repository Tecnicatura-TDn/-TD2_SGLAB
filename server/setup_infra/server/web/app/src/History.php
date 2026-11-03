<?php
declare(strict_types=1);
final class History {
    public static function authorize(): void {
        if(!in_array(Access::role(),['ASISTENTE','DOCENTE'],true)){
            throw new HttpError(403,'El historial está disponible para docentes y asistentes. Los estudiantes consultan el último diagnóstico de su PC.');
        }
    }
    public static function filters(array $input): array {
        $defaults=['vista'=>'capturas','desde'=>'','hasta'=>'','equipo'=>'','lab'=>'','estado'=>'','dias'=>'7','n'=>'1'];$filters=[];
        foreach($defaults as $key=>$default){
            if(isset($input[$key])&&!is_string($input[$key])){throw new InvalidArgumentException('Filtro inválido.');}
            $filters[$key]=trim($input[$key]??$default);
        }
        if(!in_array($filters['vista'],['capturas','sin_recientes'],true)){throw new InvalidArgumentException('Vista de historial inválida.');}
        foreach(['desde','hasta'] as $key){
            $value=$filters[$key];
            if($value===''){continue;}
            $date=DateTimeImmutable::createFromFormat('!Y-m-d',$value);
            if(!$date||$date->format('Y-m-d')!==$value||substr($value,0,4)<'1000'){
                throw new InvalidArgumentException('Ingresá fechas válidas con formato año-mes-día.');
            }
        }
        if($filters['desde']!==''&&$filters['hasta']!==''&&$filters['desde']>$filters['hasta']){throw new InvalidArgumentException('La fecha inicial debe ser anterior o igual a la final.');}
        foreach(['equipo','lab'] as $key){
            $value=$filters[$key];
            if($value!==''&&(!ctype_digit($value)||strlen($value)>10||(int)$value<1||(int)$value>4294967295)){throw new InvalidArgumentException('Identificador de equipo o laboratorio inválido.');}
        }
        if($filters['estado']!==''&&!in_array($filters['estado'],['OK','ERROR'],true)){throw new InvalidArgumentException('Resultado de lectura inválido.');}
        foreach(['dias'=>365,'n'=>100000] as $key=>$maximum){
            if(!ctype_digit($filters[$key])||strlen($filters[$key])>6||(int)$filters[$key]<1||(int)$filters[$key]>$maximum){throw new InvalidArgumentException($key==='dias'?'Indicá de 1 a 365 días sin capturas.':'Página inválida.');}
        }
        return $filters;
    }
    private static function source(array $filters): array {
        self::authorize();
        [$scope,$params]=Access::equipmentScope();$where=[$scope];
        $stale=$filters['vista']==='sin_recientes';
        if($stale){
            $from='equipo e LEFT JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio LEFT JOIN registro r ON r.id_registro=(SELECT r0.id_registro FROM registro r0 WHERE r0.id_equipo=e.id_equipo ORDER BY r0.fecha_recepcion DESC,r0.id_registro DESC LIMIT 1)';
            // La recepción mide actividad; una captura antigua reenviada hoy sí cuenta.
            $where[]='(r.id_registro IS NULL OR r.fecha_recepcion<DATE_SUB(UTC_TIMESTAMP(),INTERVAL ? DAY))';$params[]=(int)$filters['dias'];
        }else{
            $from='registro r JOIN equipo e ON e.id_equipo=r.id_equipo LEFT JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio';
            // No exponer al docente capturas de una sala anterior de la PC.
            if(Access::role()==='DOCENTE'){$where[]='r.id_laboratorio_observado=e.id_laboratorio';}
            if($filters['desde']!==''){$where[]='r.fecha>=?';$params[]=$filters['desde'].' 00:00:00';}
            if($filters['hasta']!==''){$where[]='r.fecha<=?';$params[]=$filters['hasta'].' 23:59:59';}
            if($filters['estado']!==''){$where[]='r.estado=?';$params[]=$filters['estado'];}
        }
        foreach(['equipo'=>'e.id_equipo','lab'=>'e.id_laboratorio'] as $key=>$column){
            if($filters[$key]!==''){$where[]=$column.'=?';$params[]=$filters[$key];}
        }
        return [$from.' WHERE '.implode(' AND ',$where),$params];
    }
    public static function results(array $filters,bool $export=false): array {
        [$source,$params]=self::source($filters);
        $total=(int)query('SELECT COUNT(*) FROM '.$source,$params)->fetchColumn();
        if($export&&$total>50000){throw new InvalidArgumentException('La exportación admite hasta 50.000 filas. Acotá los filtros.');}
        $limit=$export?50001:50;$offset=$export?0:((int)$filters['n']-1)*50;
        $stale=$filters['vista']==='sin_recientes';
        $columns=$stale?'e.id_equipo,e.hostname,e.num_serie,e.smbios_uuid,l.nombre laboratorio,r.fecha_recepcion ultima_recepcion':
            'r.id_registro,e.id_equipo,e.hostname,l.nombre laboratorio,r.fecha,r.fecha_recepcion,r.estado';
        $order=$stale?'r.fecha_recepcion ASC,e.id_equipo ASC':'r.fecha DESC,r.id_registro DESC';
        $rows=query('SELECT '.$columns.' FROM '.$source.' ORDER BY '.$order.' LIMIT '.$limit.' OFFSET '.$offset,$params)->fetchAll();
        if($export&&count($rows)>50000){throw new InvalidArgumentException('La exportación supera 50.000 filas. Acotá los filtros.');}
        return [$rows,$total];
    }
    public static function summary(array $filters): array {
        [$source,$params]=self::source($filters);
        $stale=$filters['vista']==='sin_recientes';
        $expression=$stale?"CASE WHEN r.id_registro IS NULL THEN 'NUNCA' ELSE 'ANTIGUA' END":'r.estado';
        $labels=$stale?['NUNCA'=>'Nunca recibió capturas','ANTIGUA'=>'Última recepción antigua']:['OK'=>'Lecturas OK','ERROR'=>'Lecturas con error'];
        $counts=array_fill_keys(array_keys($labels),0);
        foreach(query('SELECT '.$expression.' categoria,COUNT(*) cantidad FROM '.$source.' GROUP BY '.$expression,$params)->fetchAll() as $row){
            $counts[$row['categoria']]=(int)$row['cantidad'];
        }
        $total=array_sum($counts);$result=[];
        foreach($labels as $key=>$label){$result[]=['label'=>$label,'count'=>$counts[$key],'total'=>$total];}
        return $result;
    }
    public static function csvCell(mixed $value): string {
        $text=(string)($value??'');
        // Evitar fórmulas al abrir valores del inventario en una planilla.
        return preg_match('/^(?:\s*[=+@-]|[\t\r\n])/u',$text)?"'".$text:$text;
    }
    public static function export(array $filters): never {
        [$rows]=self::results($filters,true);
        $stale=$filters['vista']==='sin_recientes';
        $columns=$stale?['id_equipo','hostname','num_serie','smbios_uuid','laboratorio','ultima_recepcion']:
            ['id_registro','id_equipo','hostname','laboratorio','fecha','fecha_recepcion','estado'];
        header('Content-Type: text/csv; charset=utf-8');
        header('Content-Disposition: attachment; filename="sglab-'.$filters['vista'].'.csv"');
        $output=fopen('php://output','w');fwrite($output,"\xEF\xBB\xBF");
        fputcsv($output,$columns,',','"','');
        foreach($rows as $row){fputcsv($output,array_map(fn($key)=>self::csvCell($row[$key]??null),$columns),',','"','');}
        fclose($output);exit;
    }
}
