#!/bin/sh

# 1. Obtiene la ruta absoluta de la carpeta donde está ESTE script
DIR_ACTUAL="$(cd "$(dirname "$0")" && pwd)"

. "$DIR_ACTUAL/resources/logs.sh"
# funciones: log, error, warn, info, mensaje_warn, mensaje

. "$DIR_ACTUAL/resources/setup_ssh.sh"
# funciones: setup_ssh, setup_github_ssh

. "$DIR_ACTUAL/resources/install_lamp.sh"
# functions: install_lamp, finalize_lamp_setup, provision_lamp_stack
# Main function: provision_lamp_stack

. "$DIR_ACTUAL/resources/setup-proyect_docker.sh"
# functions: install_docker, install_docker_compose,clone_repository,setup_project, provision_docker_laravel
# Main function: provision_docker_laravel

. "$DIR_ACTUAL/resources/install_basic_tools.sh"
# functions: install_basic_tools

. "$DIR_ACTUAL/resources/config_memoria.sh"
# functions: crear_memoria, agregar_memoria, obtener_memoria, operar_memoria


# Termina el script si un comando falla
set -e

# check_sudoer
check_sudo() {
    if [ 0 -ne $(id -u) ]; then
        error "Requiere superusuario para ejecutar éste script"
    fi
}

detect_os() {
if [ -f /etc/os-release ]; then
. /etc/os-release
OS=$ID
OS_VERSION=$VERSION_ID
fi
}

update_system() {
    log "Actualizando el sistema..."
    case "$OS" in
        ubuntu|debian|mint|zorin|kali)
            sudo apt-get update -y -qq
            sudo apt-get upgrade -y -qq
            ;;
        centos|rhel|fedora|rocky)
        if command -v dnf > /dev/null 2>&1; then
            PKG_MANAGER="dnf"
        else
            PKG_MANAGER="yum"
        fi
            sudo "$PKG_MANAGER" update -y -q
            # eliminará activamente los paquetes viejos que hayan sido declarados obsoletos por el sistema
            sudo "$PKG_MANAGER" upgrade -y -q
            ;;
        *)
            error "Sistema operativo no soportado: $OS"
            ;;
    esac
}

check_system() {
    case "$OS" in
        debian|ubuntu|kali|zorin|mint|rhel|fedora|rocky|centos)
            log "Sistema $OS soportado"
        ;;
        *)
            warn "Sistema operativo $OS aún no integrado"
            error "Procura ejecutar éste script en un sistema: DEBIAN, UBUNTU, KALI, ZORIN, MINT, FEDORA, RHEL, ROCKY o CENTOS"
        ;;
    esac
    
}


menu_provisiones() {
    choice=1
    while [ $choice -ne 0 ]; do
        printf "\n"
        info "Por favor, selecciona el tipo de entorno que deseas aprovisionar:"
        mensaje_warn "1) Entorno de desarrollo Laravel con Docker (Git, Docker, Docker Compose)"
        mensaje_warn "2) Servidor LAMP clásico (Apache, MySQL, PHP en el host)"
        mensaje_warn "0) No instalar nada y salir"
        read -p "[SISTEMA]> Introduce tu elección [0-2]: " choice
        printf "\n"

        case $choice in
            #Agregar memoría ahora están más cerca del exito
            1)
                log "Aprovisionando stack docker-laravel"
                provision_docker_laravel
                choice=0
                ;;
            2)
                log "Aprovisionando stack LAMP local"
                provision_lamp_stack
                choice=0
                ;;
            0)
                operar_memoria
                mensaje_saliendo 
                ;;
            * )
                warn "Opcion no valida"
                ;;
        esac
    done
}

# función principal
main() {
    # Verificar sudo
    check_sudo
    # Ahora comienza la cosa
    echo ""
    mensaje "Comenzando el aprovisionamiento"
    crear_memoria
    detect_os
    info "Tipo de distro: $OS $OS_VERSION"
    check_system
    update_system
    printf "\n"
    install_basic_tools
    operar_memoria
    if [ "$memoria" != "0" ] && [ "$memoria" != "3" ]; then
        mensaje "¿Deseas instalar otro entorno? [ENTER/NO]"
        read otravez
        case "$otravez" in
                "")
                    menu_provisiones
                    ;;
                [Nn][Oo])
                    mensaje_saliendo
                    ;;
                *)
                    warn "Opcion no valida"
                    ;;
            esac
    else
        menu_provisiones
    fi
}

main "$@"
