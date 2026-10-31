# INSTALACIONES DE LAMP

install_lamp() {
    log "Instalando pila LAMP (Apache, MySQL Server y PHP 8.3)..."

    case "$OS" in
        debian|ubuntu|kali|zorin|mint)
            # 1. Crear directorio seguro para la llave GPG (gracias a coreutils/install)
            sudo install -m 0755 -d /etc/apt/keyrings

            # 2. Descargar y registrar la llave GPG oficial de PHP usando curl y gpg (provistos por install_basic_tools)
            curl -fsSL https://packages.sury.org/php/apt.gpg | sudo gpg --dearmor -o /etc/apt/keyrings/php.gpg
            sudo chmod a+r /etc/apt/keyrings/php.gpg

            # 3. Obtener el codename de forma segura compatible con sh
            . /etc/os-release
            CODENAME="${VERSION_CODENAME:-$UBUNTU_CODENAME}"

            # 4. Añadir el repositorio remoto oficial de PHP a sources.list.d
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/php.gpg] https://packages.sury.org/php/ $CODENAME main" | sudo tee /etc/apt/sources.list.d/php.list > /dev/null

            # 5. Actualizar paquetes e instalar Apache, mariadb y PHP 8.3 con sus módulos clave (incluyendo PDO-MySQL)
            sudo apt-get update -qq
            sudo apt-get install -y -qq apache2 mariadb-server \
                php8.3 \
                libapache2-mod-php8.3 \
                php8.3-mysql \
                php8.3-cli \
                php8.3-common

            # 6. Habilitar y arrancar servicios en Debian/Ubuntu
            sudo systemctl enable --now apache2
            sudo systemctl enable --now mariadb

            log "LAMP con PHP 8.3 instalado con éxito en base Debian/Ubuntu"
            ;;
        rhel|centos|rocky|fedora)
            # Detectar gestor de paquetes de forma segura (por si se ejecuta independiente)
            if command -v dnf > /dev/null 2>&1; then
                PKG_MANAGER="dnf"
            else
                PKG_MANAGER="yum"
            fi

            # 1. Instalar EPEL y el repositorio Remi para habilitar PHP 8.3 en entornos Enterprise Linux
            sudo "$PKG_MANAGER" install -y -q epel-release
            
            # Obtener la versión mayor del sistema (ej: 9) para el repositorio Remi de forma dinámica
            RHEL_VERSION=$(rpm -E %rhel)
            sudo "$PKG_MANAGER" install -y -q "https://rpms.remirepo.net/enterprise/remi-release-${RHEL_VERSION}.rpm"

            # 2. Habilitar el stream/módulo de PHP 8.3 en Remi
            sudo "$PKG_MANAGER" module reset -y php >/dev/null 2>&1 || true
            sudo "$PKG_MANAGER" module enable -y php:remi-8.3

            # 3. Instalar Apache (httpd), MySQL y PHP 8.3 con soporte PDO (php-mysqlnd)
            sudo "$PKG_MANAGER" install -y -q httpd mariadb-server php php-mysqlnd php-cli php-common

            # 4. Habilitar y arrancar servicios en Red Hat/Rocky
            sudo systemctl start httpd
            sudo systemctl enable httpd
            sudo systemctl start mariadb
            sudo systemctl enable mariadb

            log "LAMP con PHP 8.3 instalado con éxito en base RHEL/Rocky"
            ;;
        *)
            error "El provision no soporta éste sistema operativo: '$OS'"
            ;;
    esac

    # Asegurar permisos básicos del directorio web predeterminado
    if [ -d "/var/www/html" ]; then
        sudo chown -R "$USER:$USER" /var/www/html 2>/dev/null || true
    fi

    log "¡Pila LAMP con PHP 8.3 instalada y configurada correctamente!"
}

finalize_lamp_setup() {
    log "Reiniciando el servidor web para aplicar la configuración de PHP..."

    # Determinar el nombre correcto del servicio web según la familia del sistema operativo
    case "$OS" in
        debian|ubuntu|kali|zorin|mint)
            WEB_SERVICE="apache2"
            ;;
        rhel|centos|rocky|fedora)
            WEB_SERVICE="httpd"
            ;;
        *)
            WEB_SERVICE="apache2" # Valor por defecto de respaldo
            ;;
    esac

    # Reiniciar el servicio correspondiente de forma segura
    sudo systemctl restart "$WEB_SERVICE"

    log "Creando una página de prueba de PHP para verificar la instalación..."
    sudo mkdir -p /var/www/html
    echo "<?php phpinfo(); ?>" | sudo tee /var/www/html/info.php > /dev/null
    
    log "¡Configuración final de LAMP completada con éxito!"
}


provision_lamp_stack() {
    log "Iniciando aprovisionamiento de un servidor LAMP clásico..."
    install_lamp
    finalize_lamp_setup
    agregar_memoria 2
    SERVER_IP=$(hostname -I | awk '{print $1}')
    log "¡Aprovisionamiento LAMP completado exitosamente!"
    info "Accede a la página de prueba en tu navegador: http://$SERVER_IP/info.php"
    mensaje "- - - - - - - - - - - -"
    warn "Por seguridad, recuerda asegurar tu instalación de MySQL ejecutando: sudo mariadb-secure-installation"
    mensaje "- - - - - - - - - - - -"
    warn "Una vez verificado todo, elimina el archivo de prueba con: sudo rm /var/www/html/info.php"
}
