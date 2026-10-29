<?php 
session_start();

$_SESSION["sesion_como"] = "ninguno";
?>

<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SGLAB - Login</title>
    <link rel="stylesheet" href="styles/login.css">
    <link rel="stylesheet" href="styles/default.css">
    <link rel="stylesheet" href="styles/layout.css">
</head>

<body>
    <?php include("layouts/header.php"); ?>
    <main>
        <div class="form-div">
            <h2>Ingresar al sistema</h2>
            <form>
                <div class="form-field">
                    <label for="tipoingreso">Ingresar como</label>
                    <select name="tipoingreso" id="tipoingreso" required>
                        <option value="estudiante">Estudiante</option>
                        <option value="docente">Docente</option>
                        <option value="asistente">Asistente</option>
                    </select>
                </div>

                <div class="form-field">
                    <label for="documento">Documento</label>
                    <input type="text" name="documento" id="documento" placeholder="12345670" inputmode="numeric"
                        autocomplete="username" required>
                </div>

                <div class="form-field">
                    <label for="password">Contraseña</label>
                    <input type="password" name="password" id="password" placeholder="Ingrese su contraseña" autocomplete="current-password" required>
                </div>

                <a href="#">¿Olvidaste tu contraseña?</a>
                <input type="submit" value="Ingresar">
            </form>
        </div>
    </main>
    <?php include("layouts/footer.php"); ?>
</body>

</html>