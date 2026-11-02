<?php
declare(strict_types=1);

final class PeopleCsv {
    public static function parse(string $content): array {
        if (strlen($content)>1048576 || !preg_match('//u', $content) || str_contains($content, "\0")) {
            throw new InvalidArgumentException('El CSV debe ser UTF-8 y ocupar hasta 1 MiB.');
        }
        $content=preg_replace('/^\xEF\xBB\xBF/', '', $content);
        $stream=fopen('php://temp', 'r+');
        fwrite($stream, $content); rewind($stream);
        try {
            $first=strtok($content, "\r\n") ?: '';
            $separator=substr_count($first, ';')>substr_count($first, ',')?';':',';
            $header=fgetcsv($stream, 0, $separator, '"', '');
            if ($header===false || array_map('trim', $header)!==['ci','nombre','apellido','correo','tipo_usuario','password']) {
                throw new InvalidArgumentException('Encabezado requerido: ci,nombre,apellido,correo,tipo_usuario,password.');
            }
            $rows=[]; $identities=[]; $emails=[]; $line=1;
            while (($fields=fgetcsv($stream, 0, $separator, '"', ''))!==false) {
                $line++;
                if ($fields===[null]) { continue; }
                if (count($rows)>=500) { throw new InvalidArgumentException('Se admiten hasta 500 cuentas por archivo.'); }
                $fail=static function(string $message) use ($line): never {
                    throw new InvalidArgumentException("Fila $line: $message No se importó ninguna cuenta.");
                };
                if (count($fields)!==6) { $fail('Se esperan seis columnas.'); }
                [$ci,$name,$surname,$email,$role]=array_map('trim', array_slice($fields,0,5));
                $password=$fields[5]; $role=strtoupper($role);
                if (!ctype_digit($ci) || strlen($ci)>10 || (int)$ci<1 || (int)$ci>4294967295) { $fail('Cédula inválida; usá solo números.'); }
                $ci=(string)(int)$ci;
                if ($name==='' || $surname==='' || textLength($name)>100 || textLength($surname)>100) { $fail('Nombre y apellido obligatorios, de hasta 100 caracteres.'); }
                if (!in_array($role,['ALUMNO','DOCENTE'],true)) { $fail('El rol debe ser ALUMNO o DOCENTE.'); }
                if ($email!=='' && (strlen($email)>254 || !filter_var($email,FILTER_VALIDATE_EMAIL))) { $fail('Correo inválido.'); }
                if ($role==='ALUMNO' && $email==='') { $fail('El estudiante necesita su correo principal verificado de GitHub.'); }
                if (($role==='DOCENTE' || $password!=='') && (strlen($password)<12 || strlen($password)>72)) { $fail('La contraseña debe tener entre 12 y 72 bytes.'); }
                if (isset($identities[$ci])) { $fail('Cédula repetida en el archivo.'); }
                $emailKey=strtolower($email);
                if ($email!=='' && isset($emails[$emailKey])) { $fail('Correo repetido en el archivo.'); }
                $identities[$ci]=true;
                if ($email!=='') { $emails[$emailKey]=true; }
                $rows[]=compact('ci','name','surname','email','role','password','line');
            }
            if (!$rows) { throw new InvalidArgumentException('El CSV no contiene cuentas.'); }
            return $rows;
        } finally { fclose($stream); }
    }

    public static function import(): void {
        Access::requireManager();
        $file=$_FILES['csv']??null;
        if (!is_array($file) || ($file['error']??UPLOAD_ERR_NO_FILE)!==UPLOAD_ERR_OK || !is_string($file['tmp_name']??null) || !is_uploaded_file($file['tmp_name'])) {
            throw new InvalidArgumentException('Seleccioná un archivo CSV válido de hasta 1 MiB.');
        }
        $content=file_get_contents($file['tmp_name'], false, null, 0, 1048577);
        if ($content===false) { throw new InvalidArgumentException('No se pudo leer el CSV.'); }
        $rows=self::parse($content);
        db()->beginTransaction();
        try {
            foreach ($rows as $row) {
                if (query('SELECT 1 FROM usuarios WHERE ci=? OR (correo IS NOT NULL AND correo=?)',[$row['ci'],$row['email']?:null])->fetchColumn()) {
                    throw new InvalidArgumentException('Fila '.$row['line'].': la cédula o el correo ya tienen una cuenta. No se importó ninguna cuenta.');
                }
                query('INSERT INTO usuarios(ci,nombre,apellido,correo,tipo_usuario,password_hash,activo) VALUES (?,?,?,?,?,?,1)',[
                    $row['ci'],$row['name'],$row['surname'],$row['email']?:null,$row['role'],
                    password_hash($row['password']!==''?$row['password']:bin2hex(random_bytes(32)),PASSWORD_DEFAULT)
                ]);
            }
            db()->commit();
        } catch (Throwable $exception) {
            if (db()->inTransaction()) { db()->rollBack(); }
            if ($exception instanceof PDOException && $exception->getCode()==='23000') {
                throw new InvalidArgumentException('El archivo contiene una cédula o correo duplicados o ya registrados. No se importó ninguna cuenta.');
            }
            throw $exception;
        }
        flash(count($rows).' cuentas importadas. Los docentes se asignan a laboratorios desde Usuarios.');
        redirect('usuarios');
    }
}
