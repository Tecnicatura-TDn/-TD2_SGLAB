<?php
declare(strict_types=1);

class UsuarioController
{
    private const VISTA_LOGIN    = __DIR__ . '/../views/login.html';
    private const VISTA_REGISTRO = __DIR__ . '/../views/registro.html';
    private const MIN_PASSWORD   = 8;

    public function __construct(private Usuario $usuario)
    {
    }

    /* ---------- LOGIN ---------- */

    public function login(): void
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->procesarLogin();
            return;
        }

        if (!empty($_SESSION['usuario'])) {
            $this->redirigir('dashboard.php');
        }

        $this->renderizar(self::VISTA_LOGIN);
    }

    private function procesarLogin(): void
    {
        if (!$this->csrfValido()) {
            $this->renderizar(self::VISTA_LOGIN, ['error' => 'La sesión expiró. Intenta nuevamente.']);
            return;
        }

        $email    = trim($_POST['email'] ?? '');
        $password = $_POST['password'] ?? '';

        if ($email === '' || $password === '') {
            $this->renderizar(self::VISTA_LOGIN, ['error' => 'Completa todos los campos.', 'email' => $email]);
            return;
        }

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $this->renderizar(self::VISTA_LOGIN, ['error' => 'El correo no es válido.', 'email' => $email]);
            return;
        }

        $datos = $this->usuario->autenticar($email, $password);

        if ($datos === null) {
            $this->renderizar(self::VISTA_LOGIN, ['error' => 'Correo o contraseña incorrectos.', 'email' => $email]);
            return;
        }

        session_regenerate_id(true);
        $_SESSION['usuario'] = $datos;

        $this->redirigir('dashboard.php');
    }

    /* ---------- REGISTRO ---------- */

    public function registro(): void
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->procesarRegistro();
            return;
        }

        if (!empty($_SESSION['usuario'])) {
            $this->redirigir('dashboard.php');
        }

        $this->renderizar(self::VISTA_REGISTRO);
    }

    private function procesarRegistro(): void
    {
        if (!$this->csrfValido()) {
            $this->renderizar(self::VISTA_REGISTRO, ['error' => 'La sesión expiró. Intenta nuevamente.']);
            return;
        }

        $nombre   = trim($_POST['nombre'] ?? '');
        $email    = trim($_POST['email'] ?? '');
        $password = $_POST['password'] ?? '';
        $confirma = $_POST['password_confirm'] ?? '';

        // Valores que se devuelven a la vista si hay error (sin contraseñas)
        $valores = ['nombre' => $nombre, 'email' => $email];

        $error = match (true) {
            $nombre === '' || $email === '' || $password === ''
                => 'Completa todos los campos.',
            mb_strlen($nombre) > 100
                => 'El nombre no puede tener más de 100 caracteres.',
            mb_strlen($email) > 150 || !filter_var($email, FILTER_VALIDATE_EMAIL)
                => 'El correo no es válido.',
            mb_strlen($password) < self::MIN_PASSWORD
                => 'La contraseña debe tener al menos ' . self::MIN_PASSWORD . ' caracteres.',
            $password !== $confirma
                => 'Las contraseñas no coinciden.',
            $this->usuario->existeEmail($email)
                => 'Ya existe una cuenta con ese correo.',
            default => null,
        };

        if ($error !== null) {
            $this->renderizar(self::VISTA_REGISTRO, ['error' => $error] + $valores);
            return;
        }

        try {
            $id = $this->usuario->crear($nombre, $email, $password);
        } catch (PDOException $e) {
            // 23000 = violación de clave única (dos registros con el mismo correo al mismo tiempo)
            if ($e->getCode() === '23000') {
                $this->renderizar(self::VISTA_REGISTRO, ['error' => 'Ya existe una cuenta con ese correo.'] + $valores);
                return;
            }
            throw $e;
        }

        // Inicia sesión automáticamente tras el registro
        session_regenerate_id(true);
        $_SESSION['usuario'] = [
            'id'     => $id,
            'nombre' => $nombre,
            'email'  => $email,
        ];

        $this->redirigir('dashboard.php');
    }

    /* ---------- AUXILIARES ---------- */

    private function csrfValido(): bool
    {
        return hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? '');
    }

    private function redirigir(string $destino): void
    {
        header('Location: ' . $destino);
        exit;
    }

    /**
     * Carga una vista HTML y reemplaza los marcadores {{...}} con valores escapados.
     */
    private function renderizar(string $archivo, array $datos = []): void
    {
        if (empty($_SESSION['csrf'])) {
            $_SESSION['csrf'] = bin2hex(random_bytes(32));
        }

        $e = fn(string $valor): string => htmlspecialchars($valor, ENT_QUOTES, 'UTF-8');

        $html = file_get_contents($archivo);
        $html = strtr($html, [
            '{{error}}'  => $e($datos['error']  ?? ''),
            '{{nombre}}' => $e($datos['nombre'] ?? ''),
            '{{email}}'  => $e($datos['email']  ?? ''),
            '{{csrf}}'   => $_SESSION['csrf'],   // token generado por nosotros, no necesita escape
        ]);

        header('Content-Type: text/html; charset=UTF-8');
        echo $html;
    }
}