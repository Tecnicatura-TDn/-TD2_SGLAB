<?php
declare(strict_types=1);

function db(): PDO {
    static $pdo;
    if ($pdo) { return $pdo; }
    $pdo = new PDO(
        sprintf('mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4', getenv('DB_HOST'), getenv('DB_PORT') ?: '3306', getenv('DB_NAME')),
        getenv('DB_USER'), getenv('DB_PASSWORD'),
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC, PDO::ATTR_EMULATE_PREPARES => false]
    );
    $pdo->exec("SET time_zone = '+00:00'");
    return $pdo;
}
function query(string $sql, array $params = []): PDOStatement {
    $stmt = db()->prepare($sql); $stmt->execute($params); return $stmt;
}
function e(mixed $value): string { return htmlspecialchars((string)($value ?? ''), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function input(string $key): string {
    $value = $_POST[$key] ?? ''; return is_string($value) ? trim($value) : '';
}
function url(string $page, array $params = []): string { return '/?' . http_build_query(['page' => $page] + $params); }
function redirect(string $page, array $params = []): never { header('Location: ' . url($page, $params), true, 303); exit; }
function flash(string $text): void { $_SESSION['flash'] = $text; }
function csrf(): string { return '<input type="hidden" name="csrf" value="' . e($_SESSION['csrf']) . '">'; }
// Compatibilidad: en SGLAB el administrador es el asistente.
function admin(): bool { return Access::manager(); }
function manage(): bool { return Access::manager(); }
function authorizeAdmin(): void { Access::requireManager(); }
function view(string $name, array $data = []): void { extract($data, EXTR_SKIP); require __DIR__ . '/../views/' . $name . '.php'; }
function textLength(string $text): int { return preg_match_all('/./us', $text) ?: strlen($text); }

if(is_file(__DIR__.'/../vendor/autoload.php')){require __DIR__.'/../vendor/autoload.php';}
require __DIR__ . '/Totp.php';
require __DIR__ . '/Mfa.php';
require __DIR__ . '/GithubAuth.php';
require __DIR__ . '/Access.php';
require __DIR__ . '/Auth.php';
require __DIR__ . '/Inventory.php';

require __DIR__ . '/People.php';
require __DIR__ . '/Comments.php';

require __DIR__ . '/PeopleCsv.php';

require __DIR__ . '/Reports.php';

require __DIR__ . '/EquipmentCsv.php';

require __DIR__ . '/History.php';
