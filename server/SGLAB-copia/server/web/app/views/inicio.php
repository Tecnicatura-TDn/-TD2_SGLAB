<?php
[$scope,$params]=Access::equipmentScope();
if(Access::role()==='ALUMNO'){
    $assigned=query('SELECT e.id_equipo FROM equipo e WHERE '.$scope.' LIMIT 1',$params)->fetchColumn();
    if($assigned){redirect('equipo',['id'=>$assigned]);}
    ?><div class="page-heading"><div><p class="eyebrow">MI ESPACIO</p><h1>Mi PC</h1></div></div><section class="panel"><div class="empty"><h3>No pudimos identificar esta PC</h3><p>El recolector debe enviar una captura reciente con la IP de esta PC. Si la IP coincide con más de un equipo, no se muestra ninguno. Consultá al asistente.</p></div></section><?php return;
}
if(Access::role()==='DOCENTE'){
    [$labScope,$labParams]=Access::labScope();
    $assigned=query('SELECT l.id_laboratorio FROM laboratorio l WHERE '.$labScope.' LIMIT 1',$labParams)->fetchColumn();
    if($assigned){view('laboratorio',['labId'=>(string)$assigned,'home'=>true]);return;}
    ?><div class="page-heading"><div><h1>Mi laboratorio actual</h1></div></div><section class="panel"><div class="empty"><h2>No tenés un laboratorio asignado en este momento</h2><p>El asistente debe asignarte un laboratorio con un horario vigente para consultar sus equipos y publicar comentarios.</p></div></section><?php return;
}
[$labScope,$labParams]=Access::labScope();
$stats=['labs'=>query('SELECT COUNT(*) FROM laboratorio l WHERE '.$labScope,$labParams)->fetchColumn(),'pcs'=>query('SELECT COUNT(*) FROM equipo e WHERE '.$scope,$params)->fetchColumn(),'operativas'=>query("SELECT COUNT(*) FROM equipo e WHERE $scope AND e.estado_administrativo='OPERATIVA'",$params)->fetchColumn(),'capturas'=>query('SELECT COUNT(*) FROM registro r JOIN equipo e ON e.id_equipo=r.id_equipo WHERE '.$scope.(Access::role()==='DOCENTE'?' AND r.id_laboratorio_observado=e.id_laboratorio':''),$params)->fetchColumn()];
$latest=query('SELECT r.id_registro,r.fecha,r.estado,e.id_equipo,COALESCE(r.hostname_reportado,e.hostname,e.num_serie,e.smbios_uuid) nombre,l.nombre laboratorio FROM registro r JOIN equipo e ON e.id_equipo=r.id_equipo LEFT JOIN laboratorio l ON l.id_laboratorio=e.id_laboratorio WHERE '.$scope.(Access::role()==='DOCENTE'?' AND r.id_laboratorio_observado=e.id_laboratorio':'').' ORDER BY r.id_registro DESC LIMIT 8',$params)->fetchAll();
?>
<div class="page-heading"><div><p class="eyebrow">TU ESPACIO DE TRABAJO</p><h1><?= manage()?'Resumen del laboratorio':'Mi laboratorio actual' ?></h1><p class="muted"><?= manage()?'Inventario y últimas capturas recibidas.':'Solo se muestran datos del laboratorio que tenés asignado y durante su vigencia.' ?></p></div><?php if(manage()): ?><a class="button" href="<?= e(url('equipos')) ?>#formulario">+ Registrar PC</a><?php endif ?></div>
<div class="stats-grid"><?php foreach(['labs'=>['Laboratorios','Asignaciones visibles'],'pcs'=>['Equipos','PC accesibles'],'operativas'=>['Operativas','Estado administrativo'],'capturas'=>['Capturas','Diagnósticos visibles']] as $key=>[$label,$hint]): ?><section class="stat-card"><p><?= e($label) ?></p><strong><?= e($stats[$key]) ?></strong><span><?= e($hint) ?></span></section><?php endforeach ?></div>
<section class="panel"><div class="panel-heading"><div><h2>Capturas recientes</h2><p class="muted">Datos dentro de tu alcance de acceso.</p></div><a class="text-link" href="<?= e(url('equipos')) ?>">Ver equipos →</a></div>
<?php if(!$latest): ?><div class="empty"><h3>Todavía no hay capturas disponibles</h3><p><?= manage()?'Registrá un laboratorio y sus PC para recibir diagnósticos.':'Si no hay un laboratorio asignado actualmente, el asistente debe asignártelo.' ?></p></div><?php else: ?><div class="table-wrap"><table><thead><tr><th>Equipo</th><th>Laboratorio actual</th><th>Fecha (UTC)</th><th>Lectura</th></tr></thead><tbody><?php foreach($latest as $row): ?><tr><td><a class="table-link" href="<?= e(url('equipo',['id'=>$row['id_equipo']])) ?>"><?= e($row['nombre']??'PC sin nombre') ?></a></td><td><?= e($row['laboratorio']??'Sin asignar') ?></td><td><?= e($row['fecha']) ?></td><td><span class="badge <?= $row['estado']==='OK'?'good':'warn' ?>"><?= e($row['estado']) ?></span></td></tr><?php endforeach ?></tbody></table></div><?php endif ?></section>
