# Instala paquetes básicos
#    install_basic_tools() {
#        log "Instalando herramientas básicas..."
#        case "$OS" in
#            ubuntu|debian)
#                sudo apt-get install -y -qq git curl wget rsync openssh-client openssh-server \
#                    software-properties-common apt-transport-https ca-certificates \
#                   gnupg-agent unzip make nano htop vim
#                ;;
#            centos|rhel|fedora)
#                sudo yum install -y -q git curl wget rsync openssh-clients openssh-server \
#                    unzip nano htop vim
#                ;;
#        esac
#    }

install_basic_tools() {
    log "Instalando herramientas básicas..."
    case "$OS" in
        ubuntu|debian|kali|zorin|mint)
            sudo apt-get install -y -qq git curl wget rsync openssh-client openssh-server \
                ca-certificates gnupg unzip make nano htop vim python3 python3-pip
            ;;
        centos|rhel|fedora|rocky)
            # Detecta automáticamente si existe dnf, sino usa yum como respaldo
            if command -v dnf > /dev/null 2>&1; then
                PKG_MANAGER="dnf"
            else
                PKG_MANAGER="yum"
            fi
            
            sudo "$PKG_MANAGER" install -y -q git curl wget rsync openssh-clients openssh-server \
                unzip nano vim dnf-plugins-core python3 python3-pip

            # Para instalar top y htop si es estrictamente necesario:
            # paquete que contiene top: sudo dnf install procps-ng
            # paquete que contiene htop:
            # sudo dnf install epel-release -y
            # sudo dnf install htop -y 
            ;;
    esac
}