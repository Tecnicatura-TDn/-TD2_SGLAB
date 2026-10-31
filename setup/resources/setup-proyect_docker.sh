
# --- Funciones para el Entorno Docker + Laravel ---

desinstalar_old_docker() {
    # Debian version
    case "$OS" in
            ubuntu|debian|kali|zorin|mint)
                pkgs=$(dpkg -l | grep -E -i 'docker|containerd|runc' | awk '{print $2}')
                ;;
            centos|rhel|fedora|rocky)
                pkgs=$(rpm -qa | grep -E -i 'docker|containerd|runc')
                ;;
        esac
    if [ -n "$pkgs" ]; then
        case "$OS" in
            ubuntu|debian|kali|zorin|mint)
                sudo apt-get purge -y -qq $pkgs
                sudo apt-get autoremove -y -qq
                ;;
            centos|rhel|fedora|rocky)
                sudo dnf remove -y -q $pkgs
                sudo dnf autoremove -y -q
            ;;
        esac
        
                log "Docker eliminado correctamente"
    else
        info "No se encontraron paquetes relacionados con Docker instalados."
    fi
}


install_docker() {
    if command -v docker >/dev/null 2>&1; then
        warn "Docker ya está instalado"
        while [ "$choice" != 0 ]; do
            printf "\n\f"
            info "Si anteriormente instalaste docker desde los paquetes APT sin usar claves GPG probablemente sea una version obsoleta de docker."
            mensaje_warn "1) Eliminar paquetes anteriores e iniciar una instalacion limpia"
            mensaje_warn "0) Cancelar instalacion de Docker"
            read -p "[SISTEMA]> Introduce tu elección [0-1]: " choice
            case "$choice" in
            "1")
                desinstalar_old_docker
                choice=0
            ;;
            "0")
                choice=0
                mensaje "Instalación de docker cancelada"
                return 0
            ;;
            *)
                mensaje_warn "Opcion invalida"
            ;;
            esac
        done
    fi



    log "Instalando Docker..."
    # Creando directorio seguro para llaves y descargar la llave GPG oficial de Docker
    case "$OS" in
        debian)
            sudo install -m 0755 -d /etc/apt/keyrings # Un mkdir más seguro
            curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg 
            sudo chmod a+r /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt update -qq && sudo apt install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && log "Docker instalado con éxito" || warn "Problemas al instalar docker, último código de comando: $?"
        ;;
        ubuntu|kali|zorin|mint)
                    sudo install -m 0755 -d /etc/apt/keyrings
                    
                    # Mapear correctamente la URL de Docker según la distro base (debian o ubuntu)
                    DISTRO_URL="ubuntu"
                    curl -fsSL "https://download.docker.com/linux/$DISTRO_URL/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
                    sudo chmod a+r /etc/apt/keyrings/docker.gpg
                    
                    # Obtener el codename de forma segura compatible con sh
                    . /etc/os-release
                    CODENAME="${VERSION_CODENAME:-$UBUNTU_CODENAME}"
                    
                    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$DISTRO_URL $CODENAME stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                    
                    sudo apt update -qq && sudo apt install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && log "Docker instalado con éxito" || warn "Problemas al instalar docker, último código de comando: $?"
                ;;
        rhel|centos|rocky)
            sudo curl -fsSL https://download.docker.com/linux/centos/docker-ce.repo -o /etc/yum.repos.d/docker-ce.repo
            sudo dnf makecache -q
            sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && log "Docker instalado con éxito" || warn "Problemas al instalar docker, último código de comando: $?"
            sudo systemctl start docker
            sudo systemctl enable docker
            ;;
        fedora)
            sudo curl -fsSL https://download.docker.com/linux/fedora/docker-ce.repo -o /etc/yum.repos.d/docker-ce.repo
            sudo dnf makecache -q
            sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin && log "Docker instalado con éxito" || warn "Problemas al instalar docker, último código de comando: $?"
            sudo systemctl start docker
            sudo systemctl enable docker
        ;;
        *)
            error "El provision no soporta éste sistema operativo: '$OS'"
            ;;
    esac
    
   
    # ... (código de instalación de Docker original)
}

clone_repository() {
    local repo_url=$1
    local target_dir=${2:-"/opt/laravel-app"}
    # ... (código para clonar repositorio original)
}

setup_project() {
    log "Configurando el proyecto Laravel..."
    # ... (código de configuración del proyecto Laravel original)
}

# Funcion main de docker
provision_docker_laravel() {
    log "Iniciando aprovisionamiento para entorno de desarrollo Laravel con Docker..."
    install_docker
    agregar_memoria 1
   # install_docker_compose
   #setup_ssh
   setup_github_ssh
   log "Todo listo, siguiente paso: terminar la programación del proyecto :P saludo a los pibe del equipo FNLabs"
   # read -p "Introduce la URL SSH de tu repositorio GitHub (ej: git@github.com:usuario/repo.git): " repo_url
   # if [ -z "$repo_url" ]; then
   #     error "Debes proporcionar una URL de repositorio válida"
    #fi

    #clone_repository "$repo_url"
    #setup_project

   # log "Provisionamiento completado exitosamente!"
    #info "Acceso a la aplicación: http://localhost"
    #info "Acceso a PHPMyAdmin: http://localhost:8080"
    #warn "Recuerda que has tenido que agregar manualmente la clave SSH a tu cuenta de GitHub."
}
