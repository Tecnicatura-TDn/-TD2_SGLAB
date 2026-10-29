<?php 
session_start();

$_SESSION["sesion_como"] = "estudiante";
?>

<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SGLAB - Estudiante</title>
    <link rel="stylesheet" href="styles/default.css">
    <link rel="stylesheet" href="styles/layout.css">
    <link rel="stylesheet" href="styles/registros.css">
</head>

<body>
    <?php include("layouts/header.php"); ?>
    <main>
        <div class="main-div">
            <!-- Visor del registro -->
            <div class="main-header">
                <h1>Nuevo registro de equipo</h1>
            </div>
            <div class="main-subdiv" id="device-resources">
                <div class="device-status">
                    <div class="device-image">
                        <img src="assets/device.webp" alt="Device Image">
                    </div>
                    <div class="status-text" data-status="online">
                        <div class="status-circle"></div><span>IP: 192.168.2.2</span>
                    </div>
                    <div class="status-text">
                        <span>LABORATORIO 5</span>
                    </div>
                </div>
                <div class="actual-device">
                    <table border="0">
                        <tr>
                            <td colspan="2">
                                <h2>Recursos del sistema</h2>
                            </td>
                        </tr>
                        <tr>
                            <th>Procesador:</th>
                            <td>Intel Core i5-4570 3.20GHz</td>
                        </tr>
                        <tr>
                            <th>Memoria:</th>
                            <td>8GB DDR3 1600MHz</td>
                        </tr>
                        <tr>
                            <th>Almacenamiento:</th>
                            <td>SSD 240GB (155GB disponibles)</td>
                        </tr>
                        <tr>
                            <th>Internet:</th>
                            <td>Ethernet 1 <b>IP</b> 192.168.2.2 <b>MAC</b> 15-5B-AB-20-55-AD</td>
                        </tr>
                    </table>
                </div>
            </div>
            <div class="main-subdiv" id="comment-div">
                <form id="comment-form">
                    <fieldset>
                        <legend>Comentarios sobre dispositivo</legend>
                        <textarea maxlength=500 name="comentario" id="comentario"></textarea>
                        <div>
                            <span>Máximo 500 caracteres</span>
                            <input type="submit" value="Enviar">
                        </div>
                    </fieldset>
                </form>
                <!-- Añado un script para que no cargue el form !-->
                <script>
                    document.getElementById("comment-form").addEventListener("submit", function(event) {
                        event.preventDefault(true);
                    });
                </script>
            </div>
        </div>
    </main>
    <?php include("layouts/footer.php"); ?>
</body>

</html>