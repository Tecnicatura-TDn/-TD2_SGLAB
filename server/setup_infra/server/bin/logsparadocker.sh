#!/usr/bin/env bash

set -Eeuo pipefail
umask 077

# Directorios del proyecto
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"

# Archivos de configuración
COMPOSE_FILE="$PROJECT_ROOT/compose.yaml"
ENV_FILE="$PROJECT_ROOT/.env"

# Directorio donde se guardarán los registros
LOG_DIR="$PROJECT_ROOT/logs/infra"

info() {
    printf '[INFO] %s\n' "$*"
}

aviso() {
    printf '[AVISO] %s\n' "$*" >&2
}

error() {
    printf '[ERROR] %s\n' "$*" >&2
}

compose() {
    docker compose \
        --project-directory "$PROJECT_ROOT" \
        --env-file "$ENV_FILE" \
        -f "$COMPOSE_FILE" \
        "$@"
}

comprobar_requisitos() {
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        error "No se encontró compose.yaml."
        return 1
    fi

    if [[ ! -f "$ENV_FILE" ]]; then
        error "No se encontró el archivo .env."
        return 1
    fi

    if ! command -v docker >/dev/null 2>&1; then
        error "Docker no está instalado."
        return 1
    fi

    if ! docker info >/dev/null 2>&1; then
        error "No se puede conectar con el servicio Docker."
        return 1
    fi

    if ! compose config --quiet; then
        error "La configuración de Docker Compose no es válida."
        return 1
    fi

    return 0
}

preparar_directorio() {
    mkdir -p -- "$LOG_DIR" || {
        error "No se pudo crear el directorio de registros."
        return 1
    }
}

capturar_logs() {
    info "Iniciando captura de registros de Docker."

    local ultima_limpieza=""

    compose logs \
        --follow \
        --timestamps \
        --no-color \
        web db |
    while IFS= read -r linea; do
        local fecha archivo

        fecha="$(date '+%Y-%m-%d')"
        archivo="$LOG_DIR/sglab-docker-$fecha.log"

        # Limpiar registros antiguos al cambiar el día
        if [[ "$fecha" != "$ultima_limpieza" ]]; then
            limpiar_logs_antiguos
            ultima_limpieza="$fecha"
        fi

        printf '%s\n' "$linea" >> "$archivo"
    done
}

limpiar_logs_antiguos() {
    info "Eliminando registros con más de 30 días."

    find "$LOG_DIR" \
        -maxdepth 1 \
        -type f \
        -name 'sglab-docker-????-??-??.log' \
        -mtime +30 \
        -delete
}

main() {
    info "Iniciando sistema de registros SGLAB."

    comprobar_requisitos
    preparar_directorio
    capturar_logs
}

main "$@"
