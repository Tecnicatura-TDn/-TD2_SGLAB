<?php $comments=Comments::list($kind,(string)$id); ?>
<section class="comments-section">
<form class="comment-form" method="post" action="<?= e(url($kind,['id'=>$id])) ?>">
    <?= csrf() ?><input type="hidden" name="action" value="save_comment"><input type="hidden" name="kind" value="<?= e($kind) ?>"><input type="hidden" name="id" value="<?= e($id) ?>">
    <fieldset><legend>Comentarios <?= $kind==='equipo'?'sobre esta PC':'sobre este laboratorio' ?></legend>
        <label class="visually-hidden" for="comentario-contenido">Agregar comentario</label>
        <textarea id="comentario-contenido" name="contenido" rows="4" maxlength="4000" required placeholder="Describí el problema o la observación." aria-describedby="comment-limit"></textarea>
        <div class="comment-actions"><span id="comment-limit">Máximo 4000 caracteres</span><button class="button" type="submit">Enviar comentario</button></div>
    </fieldset>
</form>
<div class="comment-history"><h2>Comentarios anteriores</h2><p class="muted small">Últimos 50 comentarios · Fechas UTC</p>
<?php if(!$comments): ?><p class="muted">Todavía no hay comentarios.</p><?php endif ?>
<?php foreach($comments as $comment): ?><article class="comment"><header><strong><?= e($comment['nombre'].' '.$comment['apellido']) ?></strong><span><?= e($comment['fecha_hora']) ?></span></header><p><?= nl2br(e($comment['contenido'])) ?></p></article><?php endforeach ?>
</div></section>
