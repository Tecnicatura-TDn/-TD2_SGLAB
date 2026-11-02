<?php
History::authorize();$filters=History::filters($_GET);[$rows,$total]=History::results($filters);
$summary=History::summary($filters);
$stale=$filters['vista']==='sin_recientes';$pageNumber=(int)$filters['n'];
[$labScope,$labParams]=Access::labScope();$labs=query('SELECT l.id_laboratorio,l.nombre FROM laboratorio l WHERE '.$labScope.' ORDER BY l.nombre',$labParams)->fetchAll();
?>
<div class="page-heading"><div><p class="eyebrow">SEGUIMIENTO</p><h1>Historial y actividad</h1><p class="muted">Consultá las capturas y las PC sin actividad reciente dentro de tu alcance. Fechas expresadas en UTC.</p></div></div>
<section class="panel form-panel"><form method="get" action="/">
<input type="hidden" name="page" value="historial">
<div class="form-grid"><div><label for="history_view">Consulta</label><select id="history_view" name="vista"><option value="capturas" <?= !$stale?'selected':'' ?>>Historial de capturas</option><option value="sin_recientes" <?= $stale?'selected':'' ?>>PC sin capturas recientes</option></select></div>
<div><label for="history_lab">Laboratorio actual</label><select id="history_lab" name="lab"><option value="">Todos los permitidos</option><?php foreach($labs as $lab): ?><option value="<?= e($lab['id_laboratorio']) ?>" <?= $filters['lab']===(string)$lab['id_laboratorio']?'selected':'' ?>><?= e($lab['nombre']) ?></option><?php endforeach ?></select></div>
<div><label for="history_pc">ID del equipo (opcional)</label><input id="history_pc" name="equipo" type="number" min="1" max="4294967295" value="<?= e($filters['equipo']) ?>"><small>El ID figura en la ficha o en los resultados.</small></div>
<div><label for="history_from">Capturas desde (UTC)</label><input id="history_from" name="desde" type="date" value="<?= e($filters['desde']) ?>"></div>
<div><label for="history_until">Capturas hasta (UTC, inclusive)</label><input id="history_until" name="hasta" type="date" value="<?= e($filters['hasta']) ?>"></div>
<div><label for="history_state">Resultado de lectura</label><select id="history_state" name="estado"><option value="">Todos</option><?php foreach(['OK','ERROR'] as $state): ?><option value="<?= e($state) ?>" <?= $filters['estado']===$state?'selected':'' ?>><?= e($state) ?></option><?php endforeach ?></select></div>
<div><label for="history_days">Días sin recibir capturas</label><input id="history_days" name="dias" type="number" min="1" max="365" value="<?= e($filters['dias']) ?>"></div></div>
<p class="small muted">Fechas y resultado se aplican al historial. Los días se aplican a PC sin capturas recientes y se cuentan desde la última recepción; incluye equipos que nunca enviaron capturas.</p>
<div class="form-actions"><button class="button" type="submit">Consultar</button><a href="<?= e(url('historial')) ?>">Limpiar filtros</a></div></form></section>
<section class="panel form-panel" aria-labelledby="resumen-historial"><h2 id="resumen-historial">Distribución de los resultados</h2>
<p class="muted">Todos los resultados filtrados, incluyendo las otras páginas. <?= $stale?'Se cuentan equipos.':'Se cuentan capturas, no equipos distintos.' ?></p>
<?php if(array_sum(array_column($summary,'count'))===0): ?><p>No hay datos para representar con estos filtros.</p><?php else: ?>
<div class="history-chart"><?php foreach($summary as $bar): ?><div class="history-bar"><label><?= e($bar['label']) ?>: <strong><?= e($bar['count']) ?></strong> de <?= e($bar['total']) ?> (<?= e(number_format(100*$bar['count']/max(1,$bar['total']),1,',','.')) ?> %)
<meter min="0" max="<?= e(max(1,$bar['total'])) ?>" value="<?= e($bar['count']) ?>" aria-label="<?= e($bar['label']) ?>"><?= e($bar['count']) ?> de <?= e($bar['total']) ?></meter></label></div><?php endforeach ?></div>
<?php endif ?></section>
<section class="panel"><div class="panel-heading"><div><h2><?= $stale?'PC sin capturas recientes':'Capturas recibidas' ?></h2><p><?= e($total) ?> resultados · <?= $stale?'No implica que el equipo no funcione.':'OK/ERROR describe la lectura del recolector, no el funcionamiento reportado.' ?></p></div><a class="button secondary" href="<?= e(url('historial',array_merge($filters,['exportar'=>'csv','n'=>'1']))) ?>">Exportar CSV</a></div>
<?php if(!$rows): ?><div class="empty"><h3>No hay resultados para estos filtros</h3></div><?php else: ?>
<div class="table-wrap"><table><thead><tr><th>Equipo / ID</th><th>Laboratorio actual</th><?php if($stale): ?><th>Última recepción (UTC)</th><?php else: ?><th>Fecha de captura (UTC)</th><th>Recepción (UTC)</th><th>Lectura</th><?php endif ?></tr></thead><tbody>
<?php foreach($rows as $row): ?><tr><td><a href="<?= e(url('equipo',['id'=>$row['id_equipo']])) ?>"><?= e($row['hostname']?:'PC #'.$row['id_equipo']) ?></a><small class="cell-sub">ID <?= e($row['id_equipo']) ?></small></td><td><?= e($row['laboratorio']??'Sin laboratorio') ?></td>
<?php if($stale): ?><td><?= e($row['ultima_recepcion']??'Nunca recibió capturas') ?></td><?php else: ?><td><?= e($row['fecha']) ?></td><td><?= e($row['fecha_recepcion']) ?></td><td><span class="badge <?= $row['estado']==='OK'?'good':'warn' ?>"><?= e($row['estado']) ?></span></td><?php endif ?></tr><?php endforeach ?>
</tbody></table></div><?php endif ?>
<div class="pagination"><span>Página <?= e($pageNumber) ?> · 50 filas por página</span><div><?php if($pageNumber>1): ?><a href="<?= e(url('historial',array_merge($filters,['n'=>(string)($pageNumber-1)]))) ?>">← Anterior</a><?php endif ?><?php if($pageNumber*50<$total): ?><a href="<?= e(url('historial',array_merge($filters,['n'=>(string)($pageNumber+1)]))) ?>">Siguiente →</a><?php endif ?></div></div><p class="small form-panel muted">El CSV incluye todos los resultados filtrados, hasta 50.000 filas. Solo se consultan equipos activos.</p></section>
