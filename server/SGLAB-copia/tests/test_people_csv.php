<?php
declare(strict_types=1);
require __DIR__.'/../server/web/app/src/PeopleCsv.php';
function textLength(string $text): int { return preg_match_all('/./us',$text) ?: strlen($text); }
function check(bool $condition): void { if (!$condition) { throw new RuntimeException('Prueba fallida'); } }
$header="ci,nombre,apellido,correo,tipo_usuario,password\n";
$student="123,Ana,Pérez,ana@example.com,ALUMNO,\n";
$teacher="124,Juan,López,,DOCENTE,UnaClaveLarga123\n";
$rows=PeopleCsv::parse($header.$student.$teacher);
check(count($rows)===2 && $rows[0]['surname']==='Pérez' && $rows[1]['role']==='DOCENTE');
check(count(PeopleCsv::parse("\xEF\xBB\xBF".str_replace(',',';',$header.$student)))===1);
check(PeopleCsv::parse($header.'125,"Ana, María",Pérez,otra@example.com,ALUMNO,'."\n")[0]['name']==='Ana, María');
$invalid=[
    $header,
    $header.$student.$student,
    $header.$student."124,Otra,Persona,ANA@example.com,ALUMNO,\n",
    $header."123,Ana,Pérez,,ALUMNO,\n",
    $header."123,Ana,Pérez,,ASISTENTE,UnaClaveLarga123\n",
    $header."123,Ana,Pérez,,DOCENTE,corta\n",
    $header."123,Ana,Pérez,incorrecto,ALUMNO,\n",
    $header."4294967296,Ana,Pérez,ana@example.com,ALUMNO,\n",
    $header."123,Ana\n",
    str_repeat('x',1048577),
    $header."\xff",
];
$many=$header;
for($i=1;$i<=501;$i++){ $many.="$i,Ana,Pérez,a$i@example.com,ALUMNO,\n"; }
$invalid[]=$many;
foreach($invalid as $csv){
    $rejected=false;
    try { PeopleCsv::parse($csv); } catch(InvalidArgumentException $e){ $rejected=true; }
    check($rejected);
}
echo "CSV: formatos, roles, límites, duplicados y campos inválidos OK\n";
