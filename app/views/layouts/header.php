<header>
    <div class="header-content">
        <div class="header-center">
            <div class="header-item">
                <div class="header-logo">
                    <img src="assets/logo_utu.webp" alt="Logo UTU Brazo Oriental">
                </div>
            </div>
            <div class="header-item">
                <?php if (!isset($_SESSION["sesion_como"])) return; ?>
                <?php switch ($_SESSION["sesion_como"]): 
                    case "ninguno": ?>
                    <span></span>
                <?php break; 
                    case "estudiante": ?>
                    <nav class="header-nav">
                        <ul class="nav-content">
                            <li class="nav-item">Hola Roberto Clavijo</li>
                            <li class="nav-item"><a href="#">Cerrar sesión</a></li>
                        </ul>
                    </nav>
                <?php break;
                    case "docente": ?>
                    <nav class="header-nav">
                        <ul class="nav-content">
                            <li class="nav-item">Hola Damian Pajares</li>
                            <li class="nav-item"><a href="#">Cerrar sesión</a></li>
                        </ul>
                    </nav>
                <?php break;
                     endswitch; ?>
            </div>
        </div>
    </div>
</header>