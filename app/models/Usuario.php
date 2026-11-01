<?php
declare(strict_types=1);

class Usuario
{
    private PDO $pdo;

    public function __construct()
    {
        $dsn = sprintf(
            'mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',
            getenv('DB_HOST'),
            getenv('DB_PORT'),
            getenv('DB_NAME')
        );

        $this->pdo = new PDO($dsn, getenv('DB_USER'), getenv('DB_PASS'), [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ]);
    }

    /**
     * Devuelve los datos del usuario si las credenciales son válidas; null si no.
     */
    public function autenticar(string $email, string $password): ?array
    {
        $stmt = $this->pdo->prepare(
            'SELECT id, nombre, email, password_hash
             FROM usuarios
             WHERE email = :email
             LIMIT 1'
        );
        $stmt->execute([':email' => $email]);
        $usuario = $stmt->fetch();

        if (!$usuario || !password_verify($password, $usuario['password_hash'])) {
            return null;
        }

        unset($usuario['password_hash']);
        return $usuario;
    }

    /**
     * Indica si ya existe un usuario con ese correo.
     */
    public function existeEmail(string $email): bool
    {
        $stmt = $this->pdo->prepare('SELECT 1 FROM usuarios WHERE email = :email LIMIT 1');
        $stmt->execute([':email' => $email]);

        return $stmt->fetchColumn() !== false;
    }

    /**
     * Crea un usuario con la contraseña ya cifrada y devuelve su id.
     */
    public function crear(string $nombre, string $email, string $password): int
    {
        $stmt = $this->pdo->prepare(
            'INSERT INTO usuarios (nombre, email, password_hash)
             VALUES (:nombre, :email, :hash)'
        );
        $stmt->execute([
            ':nombre' => $nombre,
            ':email'  => $email,
            ':hash'   => password_hash($password, PASSWORD_DEFAULT),
        ]);

        return (int) $this->pdo->lastInsertId();
    }
}