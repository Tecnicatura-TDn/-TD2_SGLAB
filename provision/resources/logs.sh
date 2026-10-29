
# --- Colores para la salida en la consola ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Código para restaurar el color por defecto

# --- Funciones de Logging ---
log() {
    printf "${GREEN}[%s] INFO: %s${NC}\n" "$(date +'%Y-%m-%d %H:%M:%S')" "$1"
}

error() {
    printf "${RED}[%s] ERROR: %s${NC}\n" "$(date +'%Y-%m-%d %H:%M:%S')" "$1" >&2
    exit 1
}

warn() {
    printf "${YELLOW}[%s] WARN: %s${NC}\n" "$(date +'%Y-%m-%d %H:%M:%S')" "$1"
}

info() {
    printf "${GREEN}[%s] INFO: %s${NC}\n" "$(date +'%Y-%m-%d %H:%M:%S')" "$1"
}
mensaje_warn(){
    printf "${YELLOW}[%s]> %s ${NC}\n" "SISTEMA" "$1"
}
mensaje(){
    printf "${GREEN}[%s]> %s ${NC}\n" "SISTEMA" "$1"
}

mensaje_saliendo(){
    printf "${GREEN}[%s]> %s ${NC}\n" "SISTEMA" "Saliendo."
    exit 1
}
