<?php
declare(strict_types=1);

class LoginController
{
    private const VISTA = __DIR__ . '/../Views/login.html';

    public function __construct(private LoginModel $model)
    {
    }

    public function handle(): void
    {
        if ($_SERVER['REQUEST_METHOD'] === 'POST') {
            $this->procesarLogin();
            return;
        }

        // Si ya hay sesión iniciada, no mostrar el formulario
        if (!empty($_SESSION['usuario'])) {
            header('Location: index.php');
            exit;
        }

        $this->mostrarVista();
    }

    private function procesarLogin(): void
    {
        // Protección CSRF
        if (!hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf'] ?? '')) {
            $this->mostrarVista('La sesión expiró. Intenta nuevamente.');
            return;
        }

        $email    = trim($_POST['email'] ?? '');
        $password = $_POST['password'] ?? '';

        if ($email === '' || $password === '') {
            $this->mostrarVista('Completa todos los campos.');
            return;
        }

        if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
            $this->mostrarVista('El correo no es válido.');
            return;
        }

        $usuario = $this->model->autenticar($email, $password);

        if ($usuario === null) {
            // Mensaje genérico: no revela si el correo existe
            $this->mostrarVista('Correo o contraseña incorrectos.');
            return;
        }

        // Evita fijación de sesión
        session_regenerate_id(true);
        $_SESSION['usuario'] = $usuario;

        header('Location: index.php');
        exit;
    }

    private function mostrarVista(string $error = ''): void
    {
        if (empty($_SESSION['csrf'])) {
            $_SESSION['csrf'] = bin2hex(random_bytes(32));
        }

        $html = file_get_contents(self::VISTA);
        $html = str_replace(
            ['{{error}}', '{{csrf}}'],
            [htmlspecialchars($error, ENT_QUOTES, 'UTF-8'), $_SESSION['csrf']],
            $html
        );

        header('Content-Type: text/html; charset=UTF-8');
        echo $html;
    }
}