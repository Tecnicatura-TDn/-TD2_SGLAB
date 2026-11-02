<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ingresar · SGLAB</title><link rel="stylesheet" href="/assets/app.css"></head>
<body class="login-page">
<?php view('institutional-header'); ?>
<main id="contenido" class="login-content"><div class="login-card">
<h1>Ingresar al sistema</h1>
<?php if ($error): ?><div class="alert error" role="alert"><?= e($error) ?></div><?php endif ?>
<?php if (isset($_SESSION['flash'])): ?><div class="alert" role="status"><?= e($_SESSION['flash']) ?></div><?php unset($_SESSION['flash']); endif ?>
<p class="login-section-label">Asistente (administrador) o docente</p>
<form method="post" action="<?= e(url('login')) ?>">
<?= csrf() ?><input type="hidden" name="action" value="login">
<label for="ci">Cédula</label><input id="ci" name="ci" inputmode="numeric" pattern="[0-9]{1,10}" maxlength="10" autocomplete="username" placeholder="Sin puntos ni guion" required value="<?= e(input('ci')) ?>">
<label for="password">Contraseña</label><input id="password" name="password" type="password" autocomplete="current-password" required>
<button class="button full" type="submit">Ingresar</button>
</form><div class="login-divider"><span>Estudiantes</span></div><form method="post" action="<?= e(url('login')) ?>"><?= csrf() ?><input type="hidden" name="action" value="github_start"><button class="button github-button full" type="submit" <?= GithubAuth::configured()?'':'disabled' ?>>Continuar con GitHub</button></form><p class="small muted">El email principal verificado de GitHub debe coincidir con el registrado en SGLAB.</p><?php if(!GithubAuth::configured()): ?><p class="small muted">GitHub está pendiente de configuración por el administrador.</p><?php endif ?><p class="small muted login-note">Acceso con cuenta SGLAB. Si no tenés credenciales, consultá al administrador.</p>
</div></main><?php view('institutional-footer'); ?></body></html>
