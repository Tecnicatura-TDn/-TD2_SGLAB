#!/usr/bin/env bash

set -Eeuo pipefail

# Directorios del proyecto
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"

# Usuario que ejecuta la instalación
USUARIO="${SUDO_USER:-$(id -un)}"

# Archivos del servicio
PLANTILLA="$PROJECT_ROOT/server/systemd/sglab-logs-docker.service.example"
SERVICIO="sglab-logs-docker.service"
DESTINO="/etc/systemd/system/$SERVICIO"

error() {
    printf '[ERROR] %s\n' "$*" >&2
}

comprobar_requisitos() {
    if [[ "$EUID" -ne 0 ]]; then
        error "Ejecutá este instalador con sudo."
        return 1
    fi

    if [[ ! -f "$PLANTILLA" ]]; then
        error "No se encontró la plantilla del servicio."
        return 1
    fi

    if [[ ! -x "$PROJECT_ROOT/server/bin/logsparadocker.sh" ]]; then
        error "El script logsparadocker.sh no existe o no es ejecutable."
        return 1
    fi

    if ! id "$USUARIO" >/dev/null 2>&1; then
        error "No se encontró el usuario $USUARIO."
        return 1
    fi

    if ! getent group docker >/dev/null; then
        error "No existe el grupo docker."
        return 1
    fi

    return 0
}

generar_servicio() {
    local archivo_temporal

    archivo_temporal="$(mktemp --suffix=.service)"

    sed \
        -e "s|USUARIO|$USUARIO|g" \
        -e "s|RUTA_PROYECTO|$PROJECT_ROOT|g" \
        "$PLANTILLA" > "$archivo_temporal"

    if ! systemd-analyze verify "$archivo_temporal"; then
        error "La configuración generada no es válida."
        rm -f "$archivo_temporal"
        return 1
    fi

    install -m 644 "$archivo_temporal" "$DESTINO"

    rm -f "$archivo_temporal"

    printf '[INFO] Servicio generado e instalado correctamente.\n'
}

activar_servicio() {
    systemctl daemon-reload

    systemctl enable "$SERVICIO"

    printf '[INFO] Servicio habilitado para iniciar con el sistema.\n'
}

main() {
    comprobar_requisitos
    generar_servicio
    activar_servicio
}

main "$@"
