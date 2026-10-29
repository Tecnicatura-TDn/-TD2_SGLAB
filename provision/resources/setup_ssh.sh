# Configurar SSH

    # Configurar acceso SSH a GitHub
    setup_github_ssh() {
        # Acotación hecha totalmente con IA, tomarla con pinzas
    log "Configurando acceso SSH a GitHub..."
    
        info "Ingrese el correo de la cuenta de github a sincronizar (correo/NO)"
        read configurar
        
        case "$configurar" in
            [Nn][Oo])
                warn "Cancelando configuración de github"
                mensaje_saliendo
                return 0
                ;;
            *)
                if [ -n "$configurar" ]; then
                    email_github="$configurar"
                fi
                ;;
        esac 
        
        ssh_key_path="$HOME/.ssh/id_ed25519"
    
        # 1. Verificar si ya existe una llave SSH para GitHub; si no, crearla de forma desatendida
        if [ ! -f "$ssh_key_path" ]; then
            log "Generando nueva clave SSH Ed25519 para GitHub..."
            ssh-keygen -t ed25519 -C "$email_github" -f "$ssh_key_path" -N "" > /dev/null 2>&1
            log "Llave SSH generada con éxito."
        else
            info "Ya existe una llave SSH en $ssh_key_path. Omitiendo generación."
        fi
    
        # 2. Iniciar el agente SSH en segundo plano y añadir la llave
        eval "$(ssh-agent -s)" > /dev/null 2>&1
        ssh-add "$ssh_key_path" 2>/dev/null
    
        # 3. Configurar el archivo ~/.ssh/config para GitHub automáticamente
        ssh_config="$HOME/.ssh/config"
        touch "$ssh_config"
        chmod 600 "$ssh_config"
    
        # Verificar si ya existe el bloque para github.com para no duplicarlo
        if ! grep -q "Host github.com" "$ssh_config"; then
            printf "\nHost github.com\n  AddKeysToAgent yes\n  IdentityFile %s\n" "$ssh_key_path" >> "$ssh_config"
            log "Configuración de GitHub añadida a ~/.ssh/config"
        fi
    
        # 4. Mostrar la clave pública por pantalla para que el usuario la agregue a GitHub
        printf "\n%s\n" "--------------------------------------------------"
        mensaje_warn "Copia la siguiente clave pública y agrégala en tu GitHub (Settings -> SSH and GPG keys -> New SSH key):"
        printf "\n%s\n" "--------------------------------------------------"
        cat "${ssh_key_path}.pub"
        printf "\n%s\n" "--------------------------------------------------"
    
        log "Configuración de GitHub SSH completada."
    }

