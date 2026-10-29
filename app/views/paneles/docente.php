<?php
session_start();

$_SESSION["sesion_como"] = "docente";
?>

<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SGLAB - Docente</title>
    <link rel="stylesheet" href="styles/default.css">
    <link rel="stylesheet" href="styles/layout.css">
    <link rel="stylesheet" href="styles/registros.css">
    <link rel="stylesheet" href="styles/docente.css">
</head>

<body>
    <?php include("layouts/header.php"); ?>
    <main>
        <div class="main-div">
            <!-- Visor del registro -->
            <div class="main-header">
                <h1>Laboratorio</h1>
            </div>
            <div class="main-subdiv" id="device-resources">
                <div class="device-status">
                    <div class="device-image">
                        <img src="assets/device.webp" alt="Lab Image">
                    </div>
                    <div class="status-text">
                        <b>LABORATORIO 5</b>
                    </div>
                </div>
                <div class="lab-devices">
                    <table border="0">
                        <thead>
                            <tr>
                                <th colspan="2">
                                    <h2>Equipos</h2>
                                </th>
                                <td>
                                    <b>Responsable</b>
                                </td>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #1</b>
                                    <br>
                                    <div class="status-text" data-status="online">
                                        <div class="status-circle"></div><span>IP: 192.168.2.2</span>
                                    </div>
                                </td>
                                <td>Roberto Clavijo</td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #2</b>
                                    <br>
                                    <div class="status-text" data-status="offline">
                                        <div class="status-circle"></div><span>IP: 192.168.2.3</span>
                                    </div>
                                </td>
                                <td></td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #3</b>
                                    <br>
                                    <div class="status-text" data-status="offline">
                                        <div class="status-circle"></div><span>IP: 192.168.2.4</span>
                                    </div>
                                </td>
                                <td></td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #4</b>
                                    <br>
                                    <div class="status-text" data-status="online">
                                        <div class="status-circle"></div><span>IP: 192.168.2.5</span>
                                    </div>
                                </td>
                                <td>No hay registro</td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #1</b>
                                    <br>
                                    <div class="status-text" data-status="online">
                                        <div class="status-circle"></div><span>IP: 192.168.2.2</span>
                                    </div>
                                </td>
                                <td>Roberto Clavijo</td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #2</b>
                                    <br>
                                    <div class="status-text" data-status="offline">
                                        <div class="status-circle"></div><span>IP: 192.168.2.3</span>
                                    </div>
                                </td>
                                <td></td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #3</b>
                                    <br>
                                    <div class="status-text" data-status="offline">
                                        <div class="status-circle"></div><span>IP: 192.168.2.4</span>
                                    </div>
                                </td>
                                <td></td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #4</b>
                                    <br>
                                    <div class="status-text" data-status="online">
                                        <div class="status-circle"></div><span>IP: 192.168.2.5</span>
                                    </div>
                                </td>
                                <td>No hay registro</td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #1</b>
                                    <br>
                                    <div class="status-text" data-status="online">
                                        <div class="status-circle"></div><span>IP: 192.168.2.2</span>
                                    </div>
                                </td>
                                <td>Roberto Clavijo</td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #2</b>
                                    <br>
                                    <div class="status-text" data-status="offline">
                                        <div class="status-circle"></div><span>IP: 192.168.2.3</span>
                                    </div>
                                </td>
                                <td></td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #3</b>
                                    <br>
                                    <div class="status-text" data-status="offline">
                                        <div class="status-circle"></div><span>IP: 192.168.2.4</span>
                                    </div>
                                </td>
                                <td></td>
                            </tr>
                            <tr>
                                <th>
                                    <img src="assets/svg/device.svg" alt="PC">
                                </th>
                                <td>
                                    <b>Equipo #4</b>
                                    <br>
                                    <div class="status-text" data-status="online">
                                        <div class="status-circle"></div><span>IP: 192.168.2.5</span>
                                    </div>
                                </td>
                                <td>No hay registro</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="main-subdiv" id="comment-div">
                <form id="comment-form">
                    <fieldset>
                        <legend>Comentarios sobre laboratorio</legend>
                        <textarea maxlength=500 name="comentario" id="comentario"></textarea>
                        <div>
                            <span>Máximo 500 caracteres</span>
                            <input type="submit" value="Enviar">
                        </div>
                    </fieldset>
                </form>
                <!-- Añado un script para que no cargue el form !-->
                <script>
                    document.getElementById("comment-form").addEventListener("submit", function (event) {
                        event.preventDefault(true);
                    });
                </script>
            </div>
        </div>
    </main>
    <?php include("layouts/footer.php"); ?>
</body>

</html>