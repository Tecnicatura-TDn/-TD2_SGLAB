#!/usr/bin/env bash

# =============================================================================
# SGLAB - Script para desplegar y administrar la infraestructura Docker
#
# Este script se encarga de:
# - verificar que Docker y Docker Compose funcionen;
# - crear el .env cuando se configura SGLAB por primera vez;
# - crear y levantar los contenedores web y db usando compose.yaml;
# - levantar o detener servicios, consultar su estado y ver/exportar logs.
#
# No instala Docker ni paquetes del sistema: eso le corresponde a provision.sh.
# No importa si el host es Debian, Ubuntu, Rocky o RHEL, siempre que tenga
# Bash, Docker Engine y Docker Compose disponibles.
# =============================================================================

# Termina si usamos una variable que no fue definida.
set -u

# Detecta errores cuando usamos comandos unidos con pipes.
set -o pipefail

# Los archivos nuevos, sobre todo .env y los logs, no deben ser públicos.
umask 077


# -----------------------------------------------------------------------------
# Rutas del proyecto
# -----------------------------------------------------------------------------

# Obtengo el directorio donde se encuentra este script (server/bin).
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1

# Subo dos niveles para llegar a la raíz del repositorio SGLAB.
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)" || exit 1

# Defino todas las rutas usando PROJECT_ROOT, no una ruta de mi VM.
COMPOSE_FILE="$PROJECT_ROOT/compose.yaml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE_FILE="$PROJECT_ROOT/.env.example"
DOCKERFILE_WEB="$PROJECT_ROOT/docker/web/Dockerfile"
SQL_INIT="$PROJECT_ROOT/database/init/sglab.sql"
USERS_INIT="$PROJECT_ROOT/database/init/zz-users.sh"

# Archivo que indica que el despliegue inicial ya terminó correctamente.
# No se borra al detener los contenedores.
MARCA_DESPLIEGUE="$PROJECT_ROOT/.sglab-infra.done"

# Directorio predeterminado para guardar los logs exportados.
DIR_LOGS="$PROJECT_ROOT/logs/infra"


# -----------------------------------------------------------------------------
# Mensajes para mostrar en la terminal
# -----------------------------------------------------------------------------

info() {
    printf '[INFO] %s\n' "$*"
}

aviso() {
    printf '[AVISO] %s\n' "$*" >&2
}

error() {
    printf '[ERROR] %s\n' "$*" >&2
}


# -----------------------------------------------------------------------------
# Verificar requisitos antes de usar Docker
# -----------------------------------------------------------------------------

verificar_requisitos() {
    # Compruebo que existan los archivos principales del proyecto.
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "No se encontró el archivo Compose: $COMPOSE_FILE"
        return 1
    fi

    if [[ ! -f "$DOCKERFILE_WEB" ]]; then
        error "No se encontró el Dockerfile: $DOCKERFILE_WEB"
        return 1
    fi

    if [[ ! -f "$SQL_INIT" || ! -f "$USERS_INIT" ]]; then
        error "Faltan los archivos de inicialización de MariaDB en database/init/."
        return 1
    fi

    # Este script usa comandos de Docker, no instala nada con apt o dnf.
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker no está instalado o no está en el PATH. Ejecutá provision.sh."
        return 1
    fi

    if ! docker compose version >/dev/null 2>&1; then
        error "Docker Compose no está disponible. Ejecutá provision.sh."
        return 1
    fi

    # Compruebo que Docker esté funcionando y que este usuario tenga acceso.
    if ! docker info >/dev/null 2>&1; then
        error "No se puede acceder al daemon de Docker. Revisá el servicio y los permisos."
        return 1
    fi

    return 0
}


# -----------------------------------------------------------------------------
# Comando Docker Compose para no repetir toda la ruta en cada opción
# -----------------------------------------------------------------------------

compose() {
    # -p mantiene el mismo nombre de proyecto aunque cambie la carpeta del repo.
    # --env-file usa el .env correcto incluso si ejecuto el script desde /tmp.
    docker compose \
        -p sglab \
        --project-directory "$PROJECT_ROOT" \
        --env-file "$ENV_FILE" \
        -f "$COMPOSE_FILE" \
        "$@"
}


# -----------------------------------------------------------------------------
# Validación de las contraseñas que se piden en la primera instalación
# -----------------------------------------------------------------------------

validar_password() {
    local clave="$1"
    local clave_minuscula="${clave,,}"

    # Validaciones que hicimos mientras aprendíamos Bash.
    if [[ -z "$clave" ]]; then
        error "La contraseña no puede estar vacía."
    elif [[ ${#clave} -lt 8 ]]; then
        error "La contraseña debe tener al menos 8 caracteres."
    elif [[ ! "$clave" =~ [A-Z] ]]; then
        error "La contraseña debe tener al menos una mayúscula."
    elif [[ ! "$clave" =~ [a-z] ]]; then
        error "La contraseña debe tener al menos una minúscula."
    elif [[ ! "$clave" =~ [0-9] ]]; then
        error "La contraseña debe tener al menos un número."
    elif [[ ! "$clave" =~ [[:punct:]] ]]; then
        error "La contraseña debe tener al menos un carácter especial."
    elif [[ "$clave" =~ [[:space:]] ]]; then
        error "La contraseña no puede contener espacios ni saltos de línea."
    elif [[ "$clave_minuscula" == *root* || "$clave_minuscula" == *sglab* ]]; then
        error "La contraseña no puede contener las palabras root o sglab."
    elif [[ "$clave" == *"'"* || "$clave" == *'\'* ]]; then
        # Estas dos clases de caracteres requieren escapes adicionales en .env.
        # Las rechazamos para no generar un archivo ambiguo.
        error "La contraseña no puede contener comilla simple ni barra invertida."
    else
        return 0
    fi

    return 1
}


# -----------------------------------------------------------------------------
# Solicitar contraseña, confirmarla y permitir como máximo tres intentos
# -----------------------------------------------------------------------------

pedir_password() {
    local nombre_cuenta="$1"
    local variable_destino="$2"
    local clave=""
    local confirmacion=""
    local intentos=0
    local max_intentos=3

    while [[ "$intentos" -lt "$max_intentos" ]]; do
        printf '\n'
        info "Configurando la contraseña de $nombre_cuenta."

        # -s oculta lo que escribimos. Cada contraseña + confirmación es 1 intento.
        if ! read -r -s -p "Ingresá la contraseña: " clave; then
            printf '\n'
            error "No se pudo leer la contraseña."
            return 1
        fi
        printf '\n'

        if ! read -r -s -p "Confirmá la contraseña: " confirmacion; then
            printf '\n'
            error "No se pudo leer la confirmación."
            return 1
        fi
        printf '\n'

        intentos=$((intentos + 1))

        if [[ "$clave" != "$confirmacion" ]]; then
            error "Las contraseñas no coinciden."
        elif validar_password "$clave"; then
            # Guardo el valor en la variable que me pasó la función que llamó.
            printf -v "$variable_destino" '%s' "$clave"
            info "Contraseña validada."
            return 0
        fi

        if [[ "$intentos" -ge "$max_intentos" ]]; then
            error "Se agotaron los 3 intentos para $nombre_cuenta."
            return 1
        fi

        aviso "Intentos restantes: $((max_intentos - intentos))"
    done

    return 1
}


# -----------------------------------------------------------------------------
# Crear .env solo cuando todavía no existe
# -----------------------------------------------------------------------------

crear_env() {
    # Si existe .env, NO volvemos a pedir datos ni sobrescribimos las claves.
    if [[ -f "$ENV_FILE" ]]; then
        info "Se encontró .env. Se va a usar la configuración existente."
        return 0
    fi

    # Elegimos la opción B: .env.example solo es obligatorio si falta .env.
    if [[ ! -f "$ENV_EXAMPLE_FILE" ]]; then
        error "No existe .env y tampoco se encontró .env.example."
        return 1
    fi

    info "No existe .env. Vamos a preparar la configuración inicial."
    info "Se encontró la plantilla: $ENV_EXAMPLE_FILE"

    local APP_PORT=""
    local DB_ROOT_PASSWORD=""
    local DB_APP_PASSWORD=""
    local DB_INGEST_PASSWORD=""
    local DB_BACKUP_PASSWORD=""
    local archivo_temporal=""

    # El nombre de la BD es fijo porque sglab.sql crea y usa la base sglab.
    local DB_NAME="sglab"
    local DB_APP_USER="sglab_app"
    local DB_INGEST_USER="sglab_ingest"
    local DB_BACKUP_USER="sglab_backup"

    # Pedimos el puerto HTTP. Si presiona Enter, usamos 8080.
    if ! read -r -p "Puerto HTTP para la web [8080]: " APP_PORT; then
        error "No se pudo leer el puerto HTTP."
        return 1
    fi
    APP_PORT="${APP_PORT:-8080}"

    # El puerto debe ser numérico y estar entre 1 y 65535.
    if [[ ! "$APP_PORT" =~ ^[0-9]{1,5}$ ]] ||
       (( 10#$APP_PORT < 1 || 10#$APP_PORT > 65535 )); then
        error "El puerto HTTP debe ser un número entre 1 y 65535."
        return 1
    fi

    # Pedimos una contraseña diferente para cada cuenta técnica de MariaDB.
    pedir_password "root de MariaDB" DB_ROOT_PASSWORD || return 1
    pedir_password "$DB_APP_USER (web)" DB_APP_PASSWORD || return 1
    pedir_password "$DB_INGEST_USER (ingesta)" DB_INGEST_PASSWORD || return 1
    pedir_password "$DB_BACKUP_USER (respaldos)" DB_BACKUP_PASSWORD || return 1

    # No reutilizar contraseñas entre cuentas técnicas.
    if [[ "$DB_ROOT_PASSWORD" == "$DB_APP_PASSWORD" ||
          "$DB_ROOT_PASSWORD" == "$DB_INGEST_PASSWORD" ||
          "$DB_ROOT_PASSWORD" == "$DB_BACKUP_PASSWORD" ||
          "$DB_APP_PASSWORD" == "$DB_INGEST_PASSWORD" ||
          "$DB_APP_PASSWORD" == "$DB_BACKUP_PASSWORD" ||
          "$DB_INGEST_PASSWORD" == "$DB_BACKUP_PASSWORD" ]]; then
        error "Las cuatro cuentas deben tener contraseñas diferentes."
        return 1
    fi

    # Primero escribimos un archivo temporal y luego lo renombramos a .env.
    # Así evitamos dejar un .env incompleto si hay un error de escritura.
    archivo_temporal="$(mktemp "$PROJECT_ROOT/.env.tmp.XXXXXX")" || {
        error "No se pudo crear el archivo temporal de configuración."
        return 1
    }

    # Usamos comillas simples: Docker Compose no interpola $ ni # dentro de ellas.
    # La validación anterior no permite comillas simples ni barras invertidas.
    if ! {
        printf '# SGLAB - Configuración generada por infra.sh\n'
        printf 'APP_PORT=%s\n' "$APP_PORT"
        printf 'DB_NAME=%s\n' "$DB_NAME"
        printf "DB_ROOT_PASSWORD='%s'\n" "$DB_ROOT_PASSWORD"
        printf 'DB_APP_USER=%s\n' "$DB_APP_USER"
        printf "DB_APP_PASSWORD='%s'\n" "$DB_APP_PASSWORD"
        printf 'DB_INGEST_USER=%s\n' "$DB_INGEST_USER"
        printf "DB_INGEST_PASSWORD='%s'\n" "$DB_INGEST_PASSWORD"
        printf 'DB_BACKUP_USER=%s\n' "$DB_BACKUP_USER"
        printf "DB_BACKUP_PASSWORD='%s'\n" "$DB_BACKUP_PASSWORD"
    } > "$archivo_temporal"; then
        rm -f -- "$archivo_temporal"
        error "No se pudo escribir el archivo .env."
        return 1
    fi

    chmod 600 -- "$archivo_temporal" || {
        rm -f -- "$archivo_temporal"
        error "No se pudieron proteger los permisos de .env."
        return 1
    }

    # Si apareció un .env durante las preguntas, no lo pisamos.
    if [[ -e "$ENV_FILE" ]]; then
        rm -f -- "$archivo_temporal"
        error "Ya existe .env; no se va a sobrescribir."
        return 1
    fi

    mv -- "$archivo_temporal" "$ENV_FILE" || {
        rm -f -- "$archivo_temporal"
        error "No se pudo guardar .env."
        return 1
    }

    info "Archivo .env creado con permisos 600."
    return 0
}


# -----------------------------------------------------------------------------
# Revisar la configuración antes de desplegar
# -----------------------------------------------------------------------------

validar_configuracion() {
    if [[ ! -f "$ENV_FILE" || ! -r "$ENV_FILE" ]]; then
        error "No existe .env o no tengo permiso para leerlo."
        return 1
    fi

    # Nuestro SQL usa específicamente la BD sglab.
    if ! grep -Eq '^[[:space:]]*DB_NAME[[:space:]]*=[[:space:]]*sglab[[:space:]]*$' "$ENV_FILE"; then
        error "DB_NAME debe ser sglab porque database/init/sglab.sql usa esa base."
        return 1
    fi

    # Verifico que Docker Compose pueda leer el YAML y sus variables.
    if ! compose config --quiet; then
        error "La configuración de Docker Compose tiene errores. Revisá .env."
        return 1
    fi

    return 0
}


# -----------------------------------------------------------------------------
# Primer despliegue: solo se ejecuta si no existe la marca
# -----------------------------------------------------------------------------

despliegue_inicial() {
    local respuesta=""

    info "Todavía no hay un despliegue inicial registrado para este proyecto."
    aviso "Si esta BD ya se utilizaba, el volumen MariaDB no se inicializa de nuevo."

    # Pedimos confirmación para no crear contenedores por accidente.
    if ! read -r -p "¿Querés realizar el primer despliegue de SGLAB? [s/N]: " respuesta; then
        return 1
    fi

    if [[ ! "$respuesta" =~ ^[sS]$ ]]; then
        info "No se realizó ningún despliegue."
        return 1
    fi

    crear_env || return 1

    # Si el archivo ya existía con permisos amplios, intentamos protegerlo.
    chmod 600 -- "$ENV_FILE" || {
        error "No se pudieron ajustar los permisos de .env."
        return 1
    }

    validar_configuracion || return 1

    info "Construyendo la imagen web y levantando los servicios web y db..."
    # --build construye la imagen PHP/Apache del Dockerfile.
    # Compose descarga MariaDB si la imagen todavía no está disponible.
    # --wait espera que los servicios estén ejecutándose y, si tienen
    # healthcheck, que se reporten saludables.
    if ! compose up -d --build --wait; then
        error "Falló el despliegue. No se va a marcar como completado."
        return 1
    fi

    # Solo creamos la marca después de que Compose terminó correctamente.
    if ! printf 'Despliegue inicial completado: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" > "$MARCA_DESPLIEGUE"; then
        error "Los contenedores se levantaron, pero no se pudo guardar la marca."
        error "Revisá el estado antes de volver a ejecutar el despliegue inicial."
        return 1
    fi

    info "Despliegue inicial completado correctamente."
    compose ps
    return 0
}


# -----------------------------------------------------------------------------
# Ver logs o copiarlos a un directorio
# -----------------------------------------------------------------------------

# Esta función pregunta si queremos logs de web, db o de ambos.
seleccionar_servicio_logs() {
    local seleccion=""

    printf '\nLogs disponibles:\n'
    printf '1) Todos los servicios\n'
    printf '2) Web (Apache / PHP)\n'
    printf '3) Base de datos (MariaDB)\n'

    if ! read -r -p "Elegí una opción [1-3]: " seleccion; then
        return 1
    fi

    case "$seleccion" in
        1) SERVICIO_LOGS=""; NOMBRE_LOGS="todos" ;;
        2) SERVICIO_LOGS="web"; NOMBRE_LOGS="web" ;;
        3) SERVICIO_LOGS="db";  NOMBRE_LOGS="db" ;;
        *) error "Opción inválida."; return 1 ;;
    esac

    return 0
}

ver_logs() {
    local SERVICIO_LOGS=""
    local NOMBRE_LOGS=""

    seleccionar_servicio_logs || return 1

    info "Mostrando las últimas 15 líneas de los logs de $NOMBRE_LOGS."
    if [[ -z "$SERVICIO_LOGS" ]]; then
        compose logs --no-color --timestamps --tail=15
    else
        compose logs --no-color --timestamps --tail=15 "$SERVICIO_LOGS"
    fi
}

exportar_logs() {
    local SERVICIO_LOGS=""
    local NOMBRE_LOGS=""
    local destino=""
    local archivo=""

    seleccionar_servicio_logs || return 1

    # Permitimos elegir la carpeta; si se deja vacío usamos logs/infra.
    if ! read -r -p "Directorio para guardar los logs [$DIR_LOGS]: " destino; then
        return 1
    fi
    destino="${destino:-$DIR_LOGS}"

    if ! mkdir -p -- "$destino"; then
        error "No pude crear el directorio: $destino"
        return 1
    fi

    archivo="$destino/sglab-$NOMBRE_LOGS-$(date '+%Y%m%d-%H%M%S').log"

    # Exportamos las últimas 15 líneas por servicio, con fecha y hora.
    if [[ -z "$SERVICIO_LOGS" ]]; then
        if ! compose logs --no-color --timestamps --tail=15 > "$archivo"; then
            rm -f -- "$archivo"
            error "No se pudieron exportar los logs."
            return 1
        fi
    else
        if ! compose logs --no-color --timestamps --tail=15 "$SERVICIO_LOGS" > "$archivo"; then
            rm -f -- "$archivo"
            error "No se pudieron exportar los logs."
            return 1
        fi
    fi

    info "Logs guardados en: $archivo"
    return 0
}


# -----------------------------------------------------------------------------
# Menú de administración, disponible después del primer despliegue
# -----------------------------------------------------------------------------

menu() {
    local opcion=""
    local continuar=""

    while true; do
        printf '\n===========================================\n'
        printf '          SGLAB - Infraestructura\n'
        printf '===========================================\n'
        printf '1) Levantar toda la infraestructura\n'
        printf '2) Levantar el contenedor web\n'
        printf '3) Levantar el contenedor de MariaDB\n'
        printf '4) Detener el contenedor web\n'
        printf '5) Detener el contenedor de MariaDB\n'
        printf '6) Detener toda la infraestructura\n'
        printf '7) Ver estado de los contenedores\n'
        printf '8) Ver logs\n'
        printf '9) Exportar logs\n'
        printf '0) Salir\n'
        printf '===========================================\n'

        if ! read -r -p "Elegí una opción: " opcion; then
            printf '\n'
            info "Saliendo del menú."
            return 0
        fi

        # Limpio el menú antes de mostrar el resultado de la opción elegida.
        # No intento limpiar si la salida está redirigida o no hay terminal.
        if [[ -t 1 && -n "${TERM:-}" && "${TERM:-}" != dumb ]]; then
            clear || true
        fi

        # Ninguna opción vuelve a ejecutar el SETUP inicial.
        # Cada acción ocurre solamente si el usuario elige una opción.
        case "$opcion" in
            1)
                info "Levantando toda la infraestructura..."
                compose up -d || error "No se pudieron levantar los servicios."
                ;;
            2)
                info "Levantando únicamente web..."
                compose up -d --no-deps web || error "No se pudo levantar web."
                ;;
            3)
                info "Levantando MariaDB..."
                compose up -d --no-deps db || error "No se pudo levantar db."
                ;;
            4)
                compose stop web || error "No se pudo detener web."
                ;;
            5)
                aviso "La web puede perder conexión mientras la DB esté detenida."
                compose stop db || error "No se pudo detener db."
                ;;
            6)
                info "Deteniendo ambos servicios (sin borrar los datos)..."
                compose stop || error "No se pudieron detener los servicios."
                ;;
            7)
                compose ps --all || error "No se pudo consultar el estado."
                ;;
            8)
                ver_logs || error "No se pudieron mostrar los logs."
                ;;
            9)
                exportar_logs || error "No se pudieron exportar los logs."
                ;;
            0)
                info "Saliendo de infra.sh."
                return 0
                ;;
            *)
                aviso "Opción inválida. Elegí un número del menú."
                ;;
        esac

        # Mantengo el resultado visible hasta que el usuario quiera volver.
        printf '\n'
        if ! read -r -p "Presioná Enter para volver al menú..." continuar; then
            printf '\n'
            return 0
        fi
        if [[ -t 1 && -n "${TERM:-}" && "${TERM:-}" != dumb ]]; then
            clear || true
        fi
    done
}


# -----------------------------------------------------------------------------
# Función principal
# -----------------------------------------------------------------------------

main() {
    info "Proyecto: $PROJECT_ROOT"

    verificar_requisitos || exit 1

    # Si ya hubo un despliegue inicial, nunca volvemos a correrlo solos.
    if [[ ! -f "$MARCA_DESPLIEGUE" ]]; then
        despliegue_inicial || exit 1
    else
        info "La infraestructura ya fue desplegada anteriormente."
        info "No se va a repetir el setup inicial."
    fi

    # Para administrar la infraestructura necesitamos el .env real.
    validar_configuracion || exit 1
    menu
}

main "$@"
