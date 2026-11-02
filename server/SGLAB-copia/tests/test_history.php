<?php
declare(strict_types=1);
require __DIR__.'/../server/web/app/src/History.php';
function check(bool $ok): void{if(!$ok){throw new RuntimeException('Prueba fallida');}}
$f=History::filters([]);check($f['vista']==='capturas'&&$f['dias']==='7');
check(History::filters(['desde'=>'2024-02-29','hasta'=>'2024-02-29'])['desde']==='2024-02-29');
foreach([
 ['desde'=>'2023-02-29'],['hasta'=>'2024-13-01'],['desde'=>'2024-02-30'],['desde'=>'2024-03-01','hasta'=>'2024-02-01'],
 ['equipo'=>'1 OR 1=1'],['lab'=>['1']],['estado'=>'FUNCIONA'],['vista'=>'inventada'],['dias'=>'0'],['dias'=>'366'],['n'=>'-1'],['equipo'=>'4294967296']
] as $input){$rejected=false;try{History::filters($input);}catch(InvalidArgumentException $e){$rejected=true;}check($rejected);}
foreach(['=SUM(1,2)','+1','-2','@formula',"\tvalor",'   =1'] as $cell){check(str_starts_with(History::csvCell($cell),"'"));}
check(History::csvCell('PC-01')==='PC-01'&&History::csvCell(null)===''&&History::csvCell('2026-11-02')==='2026-11-02');
echo "Historial: filtros, fechas y protección de fórmulas CSV OK\n";
// El límite se comprueba antes de leer filas o enviar un archivo parcial.
class Access {
    public static function role(): string{return 'ASISTENTE';}
    public static function equipmentScope(): array{return ['e.activo=1',[]];}
}
function query(string $sql,array $params): object {
    if(!str_starts_with($sql,'SELECT COUNT(*)')){throw new RuntimeException('No debe cargar filas si supera el límite');}
    return new class {public function fetchColumn(): int{return 50001;}};
}
$rejected=false;
try{History::results(History::filters([]),true);}catch(InvalidArgumentException $e){$rejected=true;}
check($rejected);echo "Límite de exportación sin resultados parciales OK\n";
