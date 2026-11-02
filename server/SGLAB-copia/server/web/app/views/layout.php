<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title><?= e(['inicio'=>'Resumen','laboratorios'=>'Laboratorios','equipos'=>'Equipos','equipo'=>'Detalle de PC','laboratorio'=>'Laboratorio','usuarios'=>'Usuarios y asignaciones','historial'=>'Historial','error'=>'Acceso'][$page]??'Página no encontrada') ?> · SGLAB</title><link rel="stylesheet" href="/assets/app.css"></head>
<body class="authenticated-page">
<?php view('institutional-header'); ?>
<nav class="site-navigation" aria-label="Navegación principal">
<?php
$navigation=Access::role()==='ALUMNO'?['inicio'=>'Mi PC']:(manage()?['inicio'=>'Resumen','laboratorios'=>'Laboratorios','equipos'=>'Equipos','historial'=>'Historial','usuarios'=>'Usuarios y asignaciones']:['inicio'=>'Mi laboratorio','equipos'=>'Equipos','historial'=>'Historial']);
foreach ($navigation as $route=>$label):
    $active=$page===$route||($page==='equipo'&&$route===(Access::role()==='ALUMNO'?'inicio':'equipos'))||($page==='laboratorio'&&$route===(manage()?'laboratorios':'inicio'));
?>
<a class="nav-link <?= $active?'active':'' ?>" href="<?= e(url($route)) ?>" <?= $active?'aria-current="page"':'' ?>><?= e($label) ?></a>
<?php endforeach ?></nav>
<main id="contenido" class="content">
<?php if ($error): ?><div class="alert error" role="alert"><?= e($error) ?></div><?php endif ?>
<?php if (isset($_SESSION['flash'])): ?><div class="alert success" role="status"><?= e($_SESSION['flash']) ?></div><?php unset($_SESSION['flash']); endif ?>
<?php if($page==='error'): ?><h1>Acceso no disponible</h1><a href="<?= e(url('inicio')) ?>">Volver a mi espacio</a><?php elseif ($page==='missing'): ?><h1>Página no encontrada</h1><a href="<?= e(url('inicio')) ?>">Volver al resumen</a><?php else: view($page); endif ?>
</main><?php view('institutional-footer'); ?></body></html>
