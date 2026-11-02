<a class="skip-link" href="#contenido">Ir al contenido</a>
<header class="site-header">
    <div class="header-content">
        <a class="header-logo" href="<?= e(url(isset($_SESSION['user'])?'inicio':'login')) ?>" aria-label="SGLAB · Inicio">
            <img src="/assets/img/logo_utu.webp" alt="ANEP UTU · Instituto Superior Brazo Oriental" width="380" height="80">
        </a>
        <?php if(isset($_SESSION['user'])): ?>
        <div class="header-account">
            <div><span>Hola, <?= e($_SESSION['user']['nombre']) ?></span><small><?= e(['ASISTENTE'=>'Asistente','DOCENTE'=>'Docente','ALUMNO'=>'Estudiante'][Access::role()]??'') ?></small></div>
            <form method="post" action="<?= e(url('inicio')) ?>"><?= csrf() ?><input type="hidden" name="action" value="logout"><button class="logout" type="submit">Cerrar sesión</button></form>
        </div>
        <?php endif ?>
    </div>
</header>
