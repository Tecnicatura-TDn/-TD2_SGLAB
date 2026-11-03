<?php
$id=$labId??(is_string($_GET['id']??null)?$_GET['id']:'0');$lab=Access::lab($id);
[$scope,$params]=Access::equipmentScope();
$pcs=query('SELECT e.* FROM equipo e WHERE e.id_laboratorio=? AND '.$scope.' ORDER BY e.hostname,e.id_equipo',[$id,...$params])->fetchAll();
?>
<?php if(manage()): ?><a class="text-link back" href="<?= e(url('laboratorios')) ?>">← Volver a laboratorios</a><?php endif ?>
<div class="page-heading"><div><h1><?= manage()?'Laboratorio':'Mi laboratorio actual' ?></h1><p class="muted">Estado de las PC y comentarios de la sala.</p></div></div>
<section class="device-resources" aria-label="Laboratorio asignado">
    <div class="device-status">
        <img class="device-image" src="/assets/img/device.webp" alt="Equipos del laboratorio" width="220" height="220">
        <strong><?= e($lab['nombre']) ?></strong>
        <span class="status-text"><?= count($pcs) ?> <?= count($pcs)===1?'equipo activo':'equipos activos' ?></span>
    </div>
    <div class="table-wrap device-table lab-devices"><table><caption>Equipos</caption><thead><tr><th>Equipo</th><th>Estado administrativo</th><th>Último diagnóstico</th><th>Último registro (UTC)</th></tr></thead><tbody>
    <?php foreach($pcs as $pc): $last=query('SELECT estado,fecha,ip FROM registro WHERE id_equipo=? AND id_laboratorio_observado=? ORDER BY fecha DESC,id_registro DESC LIMIT 1',[$pc['id_equipo'],$id])->fetch(); ?>
        <tr><td><div class="equipment-cell"><img src="/assets/svg/device.svg" alt="" width="40" height="40"><div><a class="table-link" href="<?= e(url('equipo',['id'=>$pc['id_equipo']])) ?>"><?= e($pc['hostname']?:'PC #'.$pc['id_equipo']) ?></a><span class="cell-sub">IP: <?= e($last['ip']??'Sin capturas') ?></span></div></div></td><td><span class="badge <?= $pc['estado_administrativo']==='OPERATIVA'?'good':'warn' ?>"><?= e(Inventory::STATES[$pc['estado_administrativo']]) ?></span></td><td><?= e($last['estado']??'Sin capturas') ?></td><td><?= e($last['fecha']??'—') ?></td></tr>
    <?php endforeach ?>
    <?php if(!$pcs): ?><tr><td colspan="4">No hay PC activas asignadas.</td></tr><?php endif ?>
    </tbody></table></div>
</section>
<?php view('comments',['kind'=>'laboratorio','id'=>$id]); ?>
