<?php
declare(strict_types=1);

class DashboardController
{
    private const VISTA = __DIR__ . '/../views/dashboard.html';

    public function mostrar(): void
    {
        // Sin sesión no se puede ver el dashboard
        if (empty($_SESSION['usuario'])) {
            header('Location: login.php');
            exit;
        }

        $usuario = $_SESSION['usuario'];

        $this->renderizar(self::VISTA, [
            'nombre' => $usuario['nombre'] ?? '',
            'email'  => $usuario['email'] ?? '',
            'fecha'  => date('d/m/Y H:i'),
        ]);
    }

    /**
     * Carga la vista y reemplaza los marcadores {{...}} con valores escapados.
     */
    private function renderizar(string $archivo, array $datos): void
    {
        $html = file_get_contents($archivo);

        $reemplazos = [];
        foreach ($datos as $clave => $valor) {
            $reemplazos['{{' . $clave . '}}'] = htmlspecialchars((string) $valor, ENT_QUOTES, 'UTF-8');
        }

        header('Content-Type: text/html; charset=UTF-8');
        echo strtr($html, $reemplazos);
    }
}