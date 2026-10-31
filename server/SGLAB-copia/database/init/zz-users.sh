#!/bin/bash

# SGLAB - Cuentas técnicas MariaDB
# Modelo inicial corregido: maestros, registros, discos y sistemas de archivos.
#
# Este script se ejecuta durante la inicialización del contenedor MariaDB.
# Las contraseñas llegan mediante variables de entorno y no se versionan.

set -euo pipefail

: "${MARIADB_ROOT_PASSWORD:?MARIADB_ROOT_PASSWORD no definido}"

: "${DB_APP_USER:?DB_APP_USER no definido}"
: "${DB_APP_PASSWORD:?DB_APP_PASSWORD no definido}"

: "${DB_INGEST_USER:?DB_INGEST_USER no definido}"
: "${DB_INGEST_PASSWORD:?DB_INGEST_PASSWORD no definido}"

: "${DB_BACKUP_USER:?DB_BACKUP_USER no definido}"
: "${DB_BACKUP_PASSWORD:?DB_BACKUP_PASSWORD no definido}"

sql_escape() {
    printf '%s' "$1" |
        sed -e 's/\\/\\\\/g' -e "s/'/''/g"
}

APP_USER="$(sql_escape "$DB_APP_USER")"
APP_PASSWORD="$(sql_escape "$DB_APP_PASSWORD")"

INGEST_USER="$(sql_escape "$DB_INGEST_USER")"
INGEST_PASSWORD="$(sql_escape "$DB_INGEST_PASSWORD")"

BACKUP_USER="$(sql_escape "$DB_BACKUP_USER")"
BACKUP_PASSWORD="$(sql_escape "$DB_BACKUP_PASSWORD")"

mariadb \
    --protocol=socket \
    -uroot \
    -p"${MARIADB_ROOT_PASSWORD}" <<SQL

CREATE USER IF NOT EXISTS '${APP_USER}'@'%'
    IDENTIFIED BY '${APP_PASSWORD}';

CREATE USER IF NOT EXISTS '${INGEST_USER}'@'%'
    IDENTIFIED BY '${INGEST_PASSWORD}';

CREATE USER IF NOT EXISTS '${BACKUP_USER}'@'%'
    IDENTIFIED BY '${BACKUP_PASSWORD}';


-- Aplicación: administración de usuarios, laboratorios, equipos y comentarios.
GRANT SELECT ON sglab.* TO '${APP_USER}'@'%';
GRANT INSERT, UPDATE ON sglab.usuarios TO '${APP_USER}'@'%';
GRANT INSERT, UPDATE ON sglab.laboratorio TO '${APP_USER}'@'%';
GRANT INSERT, UPDATE ON sglab.equipo TO '${APP_USER}'@'%';
GRANT INSERT, UPDATE ON sglab.comentario TO '${APP_USER}'@'%';

-- Ingesta: consulta maestros e inserta capturas, sin alterar estado administrativo.
GRANT SELECT ON sglab.* TO '${INGEST_USER}'@'%';
GRANT INSERT ON sglab.registro TO '${INGEST_USER}'@'%';
GRANT INSERT ON sglab.registro_disco TO '${INGEST_USER}'@'%';
GRANT INSERT ON sglab.registro_sistema_archivos TO '${INGEST_USER}'@'%';

GRANT SELECT, SHOW VIEW, LOCK TABLES ON sglab.* TO '${BACKUP_USER}'@'%';
SQL

echo "Cuentas técnicas de SGLAB configuradas correctamente."
