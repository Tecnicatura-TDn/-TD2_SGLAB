<?php

declare(strict_types=1);

echo '<h1>SGLAB</h1>';
echo '<p>Apache + PHP funcionando.</p>';

$host = getenv('DB_HOST');
$port = getenv('DB_PORT');
$db   = getenv('DB_NAME');
$user = getenv('DB_USER');
$pass = getenv('DB_PASSWORD');

try {
    $pdo = new PDO(
        "mysql:host={$host};port={$port};dbname={$db};charset=utf8mb4",
        $user,
        $pass,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        ]
    );

    echo '<p>Conexión PHP → MariaDB: <strong>OK</strong></p>';

    $version = $pdo->query('SELECT VERSION()')->fetchColumn();

    echo '<p>Servidor BD: '
        . htmlspecialchars((string) $version, ENT_QUOTES, 'UTF-8')
        . '</p>';

} catch (PDOException $e) {
    echo '<p>Conexión PHP → MariaDB: <strong>ERROR</strong></p>';
}
