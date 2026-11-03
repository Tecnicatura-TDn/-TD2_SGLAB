
#!/bin/bash

# SGLAB - Respaldo automático MariaDB
set -Eeuo pipefail
umask 077

# Directorio del proyecto
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Archivos de configuración
ENV_FILE="$PROJECT_DIR/.env"
COMPOSE_FILE="$PROJECT_DIR/compose.yaml"

# Validaciones iniciales
if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: No existe el archivo .env"
    echo "Copiá .env.example como .env y configurá las credenciales."
    exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "ERROR: No se encontró compose.yaml"
    exit 1
fi

# Base de datos SGLAB
DB_NAME="sglab"

# Directorio y nombres del respaldo
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

FINAL_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"
TEMP_SQL="$BACKUP_DIR/.backup_${TIMESTAMP}.sql"
TEMP_GZ="$BACKUP_DIR/.backup_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Limpiar archivos temporales ante cualquier error
trap 'rm -f "$TEMP_SQL" "$TEMP_GZ"' EXIT

echo "======================================"
echo " SGLAB - RESPALDO DE BASE DE DATOS"
echo "======================================"
echo "Base de datos: $DB_NAME"
echo "Fecha: $TIMESTAMP"
echo ""

# Ejecutar respaldo desde MariaDB
if ! docker compose \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    exec -T \
    -e DB_NAME="$DB_NAME" \
    db sh -c '
        set -eu

        : "${DB_BACKUP_USER:?Usuario de respaldo no definido}"
        : "${DB_BACKUP_PASSWORD:?Contraseña de respaldo no definida}"

        MYSQL_PWD="$DB_BACKUP_PASSWORD" mariadb-dump \
            --user="$DB_BACKUP_USER" \
            --single-transaction \
            --quick \
            --routines \
            --triggers \
            --events \
            --hex-blob \
            "$DB_NAME"
    ' > "$TEMP_SQL"; then

    echo "ERROR: Falló la generación del respaldo."
    exit 1
fi

# Comprobar que el archivo contiene información
if [[ ! -s "$TEMP_SQL" ]]; then
    echo "ERROR: El respaldo está vacío."
    exit 1
fi

# Comprimir
if ! gzip -c "$TEMP_SQL" > "$TEMP_GZ"; then
    echo "ERROR: Falló la compresión."
    exit 1
fi

# Verificar integridad
if ! gzip -t "$TEMP_GZ"; then
    echo "ERROR: El archivo comprimido está dañado."
    exit 1
fi

# Publicar el respaldo definitivo
mv "$TEMP_GZ" "$FINAL_FILE"

echo ""
echo "RESPALDO COMPLETADO CORRECTAMENTE"
echo "Archivo: $FINAL_FILE"
echo "Tamaño: $(du -h "$FINAL_FILE" | cut -f1)"
echo "======================================"
