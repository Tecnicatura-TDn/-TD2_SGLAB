# Configurar acceso SSH a GitHub de forma dinámica y segura
setup_github_ssh() {
    log "Configurando acceso SSH a GitHub..."
    
    info "Ingrese el correo de la cuenta de GitHub a sincronizar (correo/NO):"
    read configurar

    case "$configurar" in
        [Nn][Oo])
            warn "Cancelando configuración de GitHub"
            mensaje_saliendo
            return 0
            ;;
        *)
            if [ -n "$configurar" ]; then
                email_github="$configurar"
            fi
            ;;
    esac

    # Asegurar que el directorio .ssh existe con los permisos correctos
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"

    # Ruta absoluta explícita para la clave de GitHub
    ssh_key_path="$HOME/.ssh/id_ed25519_github"
    
    # 1. Verificar si ya existe la llave específica para GitHub
    if [ ! -f "$ssh_key_path" ]; then
        log "Generando nueva clave SSH ed25519 para GitHub..."
        # Quitamos el silenciamiento de errores para detectar cualquier fallo de escritura
        ssh-keygen -t ed25519 -C "$email_github" -f "$ssh_key_path" -N ""
        
        if [ $? -eq 0 ]; then
            log "Llave SSH generada con éxito en $ssh_key_path."
        else
            error "Hubo un error al generar la clave SSH."
            return 1
        fi
    else
        info "Ya existe una llave SSH para GitHub en $ssh_key_path. Omitiendo generación."
    fi
    
    # 2. Iniciar el agente SSH en segundo plano y añadir la llave
    eval "$(ssh-agent -s)" > /dev/null 2>&1
    ssh-add "$ssh_key_path" 2>/dev/null
    
    # 3. Configurar el archivo ~/.ssh/config para que use el archivo correcto para GitHub
    ssh_config="$HOME/.ssh/config"
    touch "$ssh_config"
    chmod 600 "$ssh_config"
    
    # Verificar si ya existe el bloque para github.com para no duplicarlo
    if ! grep -q "Host github.com" "$ssh_config"; then
        printf "\nHost github.com\n  AddKeysToAgent yes\n  IdentityFile %s\n" "$ssh_key_path" >> "$ssh_config"
        log "Configuración de GitHub añadida a ~/.ssh/config"
    else
        info "El bloque para github.com ya existe en ~/.ssh/config. Verificando IdentityFile..."
        sed -i "s|IdentityFile.*|IdentityFile $ssh_key_path|g" "$ssh_config"
    fi
    
    # 4. Mostrar la clave pública por pantalla para que el usuario la agregue a GitHub
    printf "\n%s\n" "--------------------------------------------------"
    mensaje_warn "Copia la siguiente clave pública y agrégala en tu GitHub (Settings -> SSH and GPG keys -> New SSH key):"
    printf "\n%s\n" "--------------------------------------------------"
    cat "${ssh_key_path}.pub"
    printf "\n%s\n" "--------------------------------------------------"
    
    log "Configuración de GitHub SSH completada."
}