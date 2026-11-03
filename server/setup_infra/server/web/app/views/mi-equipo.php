<?php $last=$captures[0]??null; ?>
<div class="page-heading"><div><h1>Estado de mi PC</h1><p class="muted">Podés consultar y comentar únicamente el equipo desde el que ingresaste.</p></div></div>
<section class="device-resources" aria-label="Equipo identificado">
    <div class="device-status">
        <img class="device-image" src="/assets/img/device.webp" alt="Equipo de laboratorio" width="220" height="220">
        <strong><?= e($pc['hostname']?:'PC #'.$pc['id_equipo']) ?></strong>
        <span class="status-text"><?= e($pc['laboratorio']??'Sin laboratorio asignado') ?></span>
        <span class="status-text">IP: <?= e($last['ip']??'Sin informar') ?></span>
    </div>
    <div class="table-wrap device-table"><table>
        <caption>Estado del equipo</caption>
        <tbody>
            <tr><th scope="row">Estado administrativo</th><td><?= e(Inventory::STATES[$pc['estado_administrativo']]) ?></td></tr>
            <tr><th scope="row">Último diagnóstico</th><td><?= e($last['estado']??'Sin capturas') ?></td></tr>
            <tr><th scope="row">Último registro (UTC)</th><td><?= e($last['fecha']??'Sin capturas') ?></td></tr>
        </tbody>
    </table><p class="small muted table-note">El diagnóstico indica si el recolector pudo leer los datos del equipo.</p></div>
</section>
<?php view('comments',['kind'=>'equipo','id'=>$id]); ?>

<?php view('reports',['id'=>$id]); ?>
