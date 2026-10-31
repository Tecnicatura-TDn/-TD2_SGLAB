<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Iniciar sesión</title>
    <link rel="stylesheet" href="css/login.css">
</head>
<body>
    <main class="contenedor">
        <form class="tarjeta" action="login.php" method="POST" novalidate>
            <h1>Iniciar sesión</h1>

            <p class="error">{{error}}</p>

            <input type="hidden" name="csrf" value="{{csrf}}">

            <div class="campo">
                <label for="email">Correo electrónico</label>
                <input type="email" id="email" name="email" placeholder="tu@correo.com" required autofocus>
            </div>

            <div class="campo">
                <label for="password">Contraseña</label>
                <input type="password" id="password" name="password" placeholder="••••••••" required>
            </div>

            <button type="submit" class="boton">Entrar</button>
        </form>
    </main>
</body>
</html>