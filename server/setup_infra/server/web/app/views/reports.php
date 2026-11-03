<?php $reports=Reports::list($id); $isStudent=Access::role()==='ALUMNO'; ?>
<section class="panel form-panel" id="funcionamiento"><h2>Funcionamiento reportado</h2>
<p class="muted">Reportes de uso de estudiantes. No modifican el estado administrativo ni el diagnóstico automático. Fechas en UTC.</p>
<?php if($isStudent): ?>
<form method="post" action="<?= e(url('equipo',['id'=>$id])) ?>#funcionamiento"><?= csrf() ?>
<input type="hidden" name="action" value="report_function"><input type="hidden" name="id" value="<?= e($id) ?>">
<label for="estado_funcional">¿Cómo funciona tu PC?</label>
<select id="estado_funcional" name="estado_funcional" required><option value="">Seleccionar</option>
<?php foreach(Reports::STATES as $key=>$label): ?><option value="<?= e($key) ?>" <?= input('action')==='report_function'&&input('estado_funcional')===$key?'selected':'' ?>><?= e($label) ?></option><?php endforeach ?></select>
<label for="descripcion_funcional">Descripción (obligatoria si no funciona)</label>
<textarea id="descripcion_funcional" name="descripcion" maxlength="4000" rows="3"><?= e(input('action')==='report_function'?input('descripcion'):'') ?></textarea>
<button class="button" type="submit">Publicar reporte</button></form>
<p class="small muted">Solo ves los reportes que publicaste sobre esta PC.</p>
<?php endif ?>
<?php if(!$reports): ?><p>No hay reportes de funcionamiento para mostrar.</p><?php else: ?>
<div class="table-wrap"><table><thead><tr><th>Fecha (UTC)</th><th>Funcionamiento</th><?php if(!$isStudent): ?><th>Estudiante</th><?php endif ?><th>Descripción</th></tr></thead><tbody>
<?php foreach($reports as $report): ?><tr><td><?= e($report['fecha_hora']) ?></td><td><span class="badge <?= $report['estado']==='FUNCIONA'?'good':'warn' ?>"><?= e(Reports::STATES[$report['estado']]) ?></span></td><?php if(!$isStudent): ?><td><?= e($report['nombre'].' '.$report['apellido']) ?></td><?php endif ?><td><?= nl2br(e($report['descripcion'])) ?></td></tr><?php endforeach ?>
</tbody></table></div><?php endif ?></section>
