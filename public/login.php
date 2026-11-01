<?php
declare(strict_types=1);

session_start();

require_once __DIR__ . '/../app/models/Usuario.php';
require_once __DIR__ . '/../app/controllers/UsuarioController.php';

$controlador = new UsuarioController(new Usuario());
$controlador->login();