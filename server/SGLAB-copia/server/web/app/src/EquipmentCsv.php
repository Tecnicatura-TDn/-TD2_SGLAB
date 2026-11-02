<?php
declare(strict_types=1);
final class EquipmentCsv {
    public static function parse(string $content): array {
        if(strlen($content)>1048576||!preg_match('//u',$content)||str_contains($content,"\0")){
            throw new InvalidArgumentException('El CSV debe ser UTF-8 y ocupar hasta 1 MiB.');
        }
        $content=preg_replace('/^\xEF\xBB\xBF/','',$content);
        $stream=fopen('php://temp','r+');fwrite($stream,$content);rewind($stream);
        try{
            $first=strtok($content,"\r\n")?:'';
            $separator=substr_count($first,';')>substr_count($first,',')?';':',';
            $header=fgetcsv($stream,0,$separator,'"','');
            if($header===false||array_map('trim',$header)!==['hostname','num_serie','smbios_uuid','estado_administrativo']){
                throw new InvalidArgumentException('Encabezado requerido: hostname,num_serie,smbios_uuid,estado_administrativo.');
            }
            $rows=[];$serials=[];$uuids=[];$line=1;
            while(($fields=fgetcsv($stream,0,$separator,'"',''))!==false){
                $line++;if($fields===[null]){continue;}
                try{
                    if(count($rows)>=500){throw new InvalidArgumentException('Se admiten hasta 500 PC por archivo.');}
                    if(count($fields)!==4){throw new InvalidArgumentException('Se esperan cuatro columnas.');}
                    [$hostname,$serial,$uuid,$state]=array_map('trim',$fields);
                    [$serial,$uuid,$hostname,$state]=Inventory::equipmentValues($serial,$uuid,$hostname,strtoupper($state?:'OPERATIVA'));
                    if(($serial!==''&&isset($serials[$serial]))||($uuid!==''&&isset($uuids[$uuid]))){
                        throw new InvalidArgumentException('Serie o UUID repetidos en el archivo.');
                    }
                    if($serial!==''){$serials[$serial]=true;}if($uuid!==''){$uuids[$uuid]=true;}
                    $rows[]=compact('serial','uuid','hostname','state','line');
                }catch(InvalidArgumentException $e){throw new InvalidArgumentException("Fila $line: ".$e->getMessage().' No se importó ninguna PC.');}
            }
            if(!$rows){throw new InvalidArgumentException('El CSV no contiene PC.');}
            return $rows;
        }finally{fclose($stream);}
    }
    public static function importContent(string $content,string $lab): int {
        Access::requireManager();
        if(!ctype_digit($lab)){throw new InvalidArgumentException('Seleccioná un laboratorio activo para las PC del archivo.');}
        $rows=self::parse($content);
        db()->beginTransaction();
        try{
            // Mismo bloqueo que las altas individuales y el archivado de salas.
            if(!query('SELECT 1 FROM laboratorio WHERE id_laboratorio=? AND activo=1 FOR UPDATE',[$lab])->fetchColumn()){
                throw new InvalidArgumentException('El laboratorio no existe o dejó de estar activo.');
            }
            foreach($rows as $row){
                if(query('SELECT 1 FROM equipo WHERE UPPER(TRIM(num_serie))=? OR UPPER(smbios_uuid)=?',[$row['serial']?:null,$row['uuid']?:null])->fetchColumn()){
                    throw new InvalidArgumentException('Fila '.$row['line'].': la serie o el UUID ya pertenecen a una PC, incluso archivada. No se importó ninguna PC.');
                }
                query('INSERT INTO equipo(num_serie,smbios_uuid,hostname,id_laboratorio,estado_administrativo) VALUES (?,?,?,?,?)',[
                    $row['serial']?:null,$row['uuid']?:null,$row['hostname']?:null,$lab,$row['state']
                ]);
            }
            db()->commit();
        }catch(Throwable $e){
            if(db()->inTransaction()){db()->rollBack();}
            if($e instanceof PDOException&&$e->getCode()==='23000'){
                throw new InvalidArgumentException('Serie o UUID duplicados o ya registrados. No se importó ninguna PC.');
            }
            throw $e;
        }
        return count($rows);
    }
    public static function import(): void {
        Access::requireManager();
        $file=$_FILES['csv']??null;
        if(!is_array($file)||($file['error']??UPLOAD_ERR_NO_FILE)!==UPLOAD_ERR_OK||!is_string($file['tmp_name']??null)||!is_uploaded_file($file['tmp_name'])){
            throw new InvalidArgumentException('Seleccioná un archivo CSV válido de hasta 1 MiB.');
        }
        $content=file_get_contents($file['tmp_name'],false,null,0,1048577);
        if($content===false){throw new InvalidArgumentException('No se pudo leer el CSV.');}
        $count=self::importContent($content,input('laboratorio_csv'));
        flash($count.' PC importadas y asignadas al laboratorio. Ya pueden recibir capturas.');redirect('equipos');
    }
}
