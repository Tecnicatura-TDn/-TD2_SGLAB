<?php
declare(strict_types=1);
require __DIR__.'/../server/web/app/src/Inventory.php';
require __DIR__.'/../server/web/app/src/EquipmentCsv.php';
function textLength(string $s): int{return preg_match_all('/./us',$s)?:strlen($s);}
function check(bool $ok): void{if(!$ok){throw new RuntimeException('Prueba fallida');}}
$header="hostname,num_serie,smbios_uuid,estado_administrativo\n";
$uuid='12345678-1234-1234-1234-123456789abc';
$csv=$header."PC1,serie-1,,\nPC2,,$uuid,EN_REPARACION\n";
$rows=EquipmentCsv::parse($csv);
check(count($rows)===2&&$rows[0]['serial']==='SERIE-1'&&$rows[0]['state']==='OPERATIVA'&&$rows[1]['uuid']===strtoupper($uuid));
check(count(EquipmentCsv::parse("\xEF\xBB\xBF".str_replace(',',';',$csv)))===2);
check(EquipmentCsv::parse($header.'"PC, uno",SERIE-1,,'."\n")[0]['hostname']==='PC, uno');
$invalid=[
 $header,$header."PC,,,\n",$header."PC,UNKNOWN,,\n",$header."PC,,invalido,\n",
 $header."PC,,00000000-0000-0000-0000-000000000000,\n",$header."PC,SERIE,,ERROR\n",
 $header."PC,SERIE,,\nPC2,serie,,\n",$header."PC,,$uuid,\nPC2,,$uuid,\n",
 $header."PC,solo\n",$header.str_repeat('x',256).",SERIE,,\n",$header."PC,".str_repeat('x',101).",,\n",
 str_repeat('x',1048577),$header."\xff",$header."PC,SERIE\0,,\n"
];
$many=$header;for($i=0;$i<501;$i++){$many.="PC$i,SERIE$i,,\n";}$invalid[]=$many;
foreach($invalid as $csv){$rejected=false;try{EquipmentCsv::parse($csv);}catch(InvalidArgumentException $e){$rejected=true;}check($rejected);}
echo "CSV PC: formatos, normalización, identidades, duplicados y límites OK\n";
