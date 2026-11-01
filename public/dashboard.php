<?php
declare(strict_types=1);

session_start();

require_once __DIR__ . '/../app/controllers/DashboardController.php';

(new DashboardController())->mostrar();