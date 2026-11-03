# Configura la recepción de los clientes y el servicio de ingesta de SGLAB.

preparar_receptor() {
    receptor="BASE-TD2"
    if ! getent group sglab-ingest >/dev/null 2>&1; then
        sudo groupadd sglab-ingest || return 1
    fi
    if ! id "$receptor" >/dev/null 2>&1; then
        sudo useradd -m -s /bin/bash "$receptor" || return 1
    fi
    sudo usermod -aG sglab-ingest "$receptor" || return 1
    # El mismo usuario recibe las capturas y ejecuta spawn.
    if getent group docker >/dev/null 2>&1; then
        sudo usermod -aG docker "$receptor" || return 1
    fi
    home_receptor="$(getent passwd "$receptor" | cut -d: -f6)"
    if [ -z "$home_receptor" ] || [ "$home_receptor" = / ] ||
       [ -L "$home_receptor/.ssh" ] || [ -L "$home_receptor/.ssh/authorized_keys" ]; then
        warn "Revisá el directorio personal y .ssh del receptor"
        return 1
    fi
    grupo_receptor="$(id -gn "$receptor")"
    sudo install -d -m 0700 -o "$receptor" -g "$grupo_receptor" "$home_receptor/.ssh" || return 1
    sudo touch "$home_receptor/.ssh/authorized_keys" || return 1
    sudo chown "$receptor:$grupo_receptor" "$home_receptor/.ssh/authorized_keys" || return 1
    sudo chmod 0600 "$home_receptor/.ssh/authorized_keys" || return 1
    # No guardar ni imprimir contraseñas en memoria.txt, perfiles o logs.
    estado_password="$(sudo passwd -S "$receptor" | awk '{print $2}')"
    if [ "$estado_password" != P ] && [ "$estado_password" != PS ]; then
        info "Definí la contraseña de $receptor para registrar las claves de los clientes"
        sudo passwd "$receptor" || return 1
    else
        info "El receptor ya tiene contraseña; se conserva la existente"
    fi
    log "Receptor $receptor preparado con el grupo sglab-ingest"
}

permisos_cola() {
    # BASE-TD2 es dueño del proyecto y de todas las carpetas de la cola.
    if [ -L "$proyecto/var" ]; then
        warn "var no puede ser un enlace simbólico"
        return 1
    fi
    sudo install -d -m 0700 -o "$operador" -g "$grupo_operador" "$proyecto/var" || return 1
    for carpeta in incoming processing processed rejected; do
        if [ -L "$proyecto/var/$carpeta" ]; then
            warn "La carpeta $carpeta no puede ser un enlace simbólico"
            return 1
        fi
    done
    sudo install -d -m 2770 -o "$operador" -g sglab-ingest "$proyecto/var/incoming" || return 1
    for carpeta in processing processed rejected; do
        sudo install -d -m 0700 -o "$operador" -g "$grupo_operador" "$proyecto/var/$carpeta" || return 1
    done
    sudo -u "$receptor" -- test -w "$proyecto/var/incoming" || return 1
    if [ -L "$proyecto/.env" ]; then
        warn ".env no puede ser un enlace simbólico"
        return 1
    fi
    sudo chmod 0600 "$proyecto/.env" || return 1
    sudo -u "$operador" -- test -r "$proyecto/.env" || return 1
    log "Permisos de la cola preparados"
}

verificar_bd_sglab() {
    if ! sudo docker compose --project-directory "$proyecto" --env-file "$proyecto/.env" -f "$proyecto/compose.yaml" exec -T db healthcheck.sh --connect --innodb_initialized >/dev/null; then
        warn "MariaDB no está lista. Levantá la infraestructura con infra.sh antes de activar spawn"
        return 1
    fi
    if ! sudo docker compose --project-directory "$proyecto" --env-file "$proyecto/.env" -f "$proyecto/compose.yaml" exec -T db sh -c '
        export MYSQL_PWD="$DB_INGEST_PASSWORD"
        exec mariadb --protocol=tcp -h127.0.0.1 -u"$DB_INGEST_USER" --batch --skip-column-names -e "SELECT id_equipo FROM sglab.equipo LIMIT 0"
    ' >/dev/null 2>&1; then
        warn "La cuenta técnica de ingesta no puede acceder a MariaDB. Revisá .env y las cuentas de la base"
        return 1
    fi
}

configurar_sglab() {
    info "Configurando el receptor SSH y spawn de SGLAB"
    proyecto_defecto="${proyecto_clonado:-$(cd "$DIR_ACTUAL/../.." && pwd)}" || return 1
    printf 'Carpeta del proyecto SGLAB [%s]: ' "$proyecto_defecto"
    read -r proyecto || return 1
    proyecto="${proyecto:-$proyecto_defecto}"
    proyecto="$(cd "$proyecto" && pwd -P)" || return 1
    for archivo in compose.yaml .env server/bin/spawn.sh infra/configurar-spawn.py server/ingest/requirements-bash.txt; do
        if [ ! -f "$proyecto/$archivo" ]; then
            warn "Falta $archivo. Prepará primero el proyecto y su .env con infra.sh"
            return 1
        fi
    done
    operador=BASE-TD2
    for comando in docker python3 jq ssh-keygen; do
        if ! command -v "$comando" >/dev/null 2>&1; then
            warn "Falta $comando. Instalá las herramientas básicas y Docker"
            return 1
        fi
    done
    sudo docker compose version >/dev/null || return 1
    sudo docker info >/dev/null || return 1
    verificar_bd_sglab || return 1
    preparar_receptor || return 1
    grupo_operador="$(id -gn "$operador")"
    sudo usermod -aG docker,sglab-ingest "$operador" || return 1
    permisos_cola || return 1
    if [ ! -x "$proyecto/.venv/bin/python" ]; then
        sudo -u "$operador" -- python3 -m venv "$proyecto/.venv" || return 1
    fi
    sudo -u "$operador" -- "$proyecto/.venv/bin/python" -m pip install -r "$proyecto/server/ingest/requirements-bash.txt" || return 1
    sudo -u "$operador" -- python3 "$proyecto/infra/configurar-spawn.py" --usuario "$operador" --proyecto "$proyecto" || return 1
    sudo install -m 0644 "$proyecto/var/systemd/sglab-spawn.service" /etc/systemd/system/sglab-spawn.service || return 1
    case "$OS" in
        ubuntu|debian|kali|zorin|mint) servicio_ssh=ssh ;;
        *) servicio_ssh=sshd ;;
    esac
    sudo systemctl enable --now "$servicio_ssh" || return 1
    sudo systemctl daemon-reload || return 1
    sudo systemctl enable sglab-spawn || return 1
    sudo systemctl restart sglab-spawn || return 1
    sudo systemctl is-active --quiet sglab-spawn || return 1
    log "Recepción e ingesta configuradas"
    info "Usuario SSH de los clientes: $receptor"
    info "Directorio remoto: $proyecto/var/incoming"
    info "El cliente registra su clave pública usando la contraseña del receptor"
    info "Si SSH no permite contraseñas, usá la opción de autorizar clave desde este servidor"
    info "Revisá firewall y SELinux de este servidor si la conexión desde otra PC falla"
}

autorizar_cliente_sglab() {
    receptor=BASE-TD2
    if ! id "$receptor" >/dev/null 2>&1; then
        warn "Configurá primero el receptor SGLAB"
        return 1
    fi
    printf 'Ruta del archivo de clave pública del cliente (.pub): '
    read -r archivo_publica || return 1
    if [ ! -f "$archivo_publica" ] || ! ssh-keygen -lf "$archivo_publica" >/dev/null 2>&1; then
        warn "La clave pública no es válida"
        return 1
    fi
    # Solo admitir una clave pública, nunca copiar una privada.
    if [ "$(awk 'NF {n++} END {print n+0}' "$archivo_publica")" != 1 ] ||
       ! grep -Eq '^(ssh-ed25519|ssh-rsa|ecdsa-sha2-nistp(256|384|521)) [A-Za-z0-9+/=]+( .*)?$' "$archivo_publica"; then
        warn "El archivo debe contener una sola clave pública SSH"
        return 1
    fi
    home_receptor="$(getent passwd "$receptor" | cut -d: -f6)"
    if [ -L "$home_receptor/.ssh" ] || [ -L "$home_receptor/.ssh/authorized_keys" ] ||
       [ ! -f "$home_receptor/.ssh/authorized_keys" ]; then
        warn "Revisá .ssh del receptor antes de autorizar clientes"
        return 1
    fi
    publica="$(awk '{print $1 " " $2}' "$archivo_publica")"
    if sudo grep -qF -- "$publica" "$home_receptor/.ssh/authorized_keys"; then
        info "La clave ya estaba autorizada"
    else
        printf '\nrestrict %s\n' "$publica" | sudo tee -a "$home_receptor/.ssh/authorized_keys" >/dev/null || return 1
        log "Clave del cliente autorizada, sin permisos de reenvío SSH"
    fi
}

clonar_repo_sglab() {
    repo_defecto="https://github.com/Tecnicatura-TDn/-TD2_SGLAB.git"
    printf 'Repositorio GitHub de SGLAB [%s]: ' "$repo_defecto"
    read -r repositorio || return 1
    repositorio="${repositorio:-$repo_defecto}"
    if ! printf '%s\n' "$repositorio" | grep -Eq '^(https://github\.com/|git@github\.com:)[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$'; then
        warn "Indicá una URL de GitHub HTTPS o SSH, sin contraseñas ni tokens"
        return 1
    fi
    # Reutilizar el usuario que ya crea provision, sin agregar otra cuenta.
    operador=BASE-TD2
    if ! id "$operador" >/dev/null 2>&1; then
        sudo useradd -m -s /bin/bash "$operador" || return 1
        log "Usuario base $operador creado"
    fi
    if getent group docker >/dev/null 2>&1; then
        sudo usermod -aG docker "$operador" || return 1
    fi
    home_operador="$(getent passwd "$operador" | cut -d: -f6)"
    if [ -z "$home_operador" ] || [ "$home_operador" = / ]; then
        warn "El usuario necesita un directorio personal válido"
        return 1
    fi
    destino_repo="$home_operador/SGLAB"
    if [ -L "$destino_repo" ]; then
        warn "La carpeta del repositorio no puede ser un enlace simbólico"
        return 1
    fi
    if [ -e "$destino_repo" ]; then
        if ! sudo -H -u "$operador" -- git -C "$destino_repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            warn "La carpeta $destino_repo ya existe y no es un repositorio. No se modificó"
            return 1
        fi
        origen_actual="$(sudo -H -u "$operador" -- git -C "$destino_repo" remote get-url origin)" || return 1
        if [ "$origen_actual" != "$repositorio" ]; then
            warn "La carpeta existente corresponde a otro repositorio. No se modificó"
            return 1
        fi
        info "El repositorio ya existe; se conserva sin hacer pull ni sobrescribir cambios"
    else
        info "Clonando SGLAB para $operador"
        sudo -H -u "$operador" -- git clone -- "$repositorio" "$destino_repo" || return 1
    fi
    # El repositorio puede contener SGLAB en su raíz o dentro de server.
    proyecto=""
    for subcarpeta in . SGLAB server/SGLAB server/SGLAB-copia; do
        if [ -f "$destino_repo/$subcarpeta/compose.yaml" ] && [ -f "$destino_repo/$subcarpeta/server/bin/spawn.sh" ]; then
            proyecto="$(cd "$destino_repo/$subcarpeta" && pwd -P)" || return 1
            break
        fi
    done
    if [ -z "$proyecto" ]; then
        warn "Se clonó el repositorio, pero no se encontró compose.yaml junto al servidor SGLAB"
        return 1
    fi
    proyecto_clonado="$proyecto"
    operador_clonado="$operador"
    log "Repositorio preparado para $operador"
    info "Raíz de SGLAB: $proyecto"
    info "Prepará .env, HTTPS y contenedores con infra.sh usando este usuario"
    info "Después completá recepción y spawn con la opción 3 de provision"
}
