#!/usr/bin/env bash
# Vigila TOML terminados; systemd administra el proceso en primer plano.
set -euo pipefail
umask 077
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd -P)"
DATA_DIR="${SGLAB_DATA_DIR:-$PROJECT_ROOT/server}"
COMPOSE_DIR="${SGLAB_COMPOSE_DIR:-$PROJECT_ROOT}"
TOMLQ_BIN="${SGLAB_TOMLQ:-tomlq}"
INTERVALO="${SGLAB_INTERVALO:-5}"

if [[ "${1:-}" == --help ]]; then
    echo 'Uso: spawn.sh [--once]'
    echo 'Variables: SGLAB_DATA_DIR, SGLAB_TOMLQ, SGLAB_INTERVALO (segundos).'
    exit 0
fi
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != --once ) ]]; then
    echo 'Uso: spawn.sh [--once]' >&2
    exit 2
fi
[[ "$INTERVALO" =~ ^[1-9][0-9]*$ ]] || { echo 'Intervalo inválido' >&2; exit 2; }
for comando in "$TOMLQ_BIN" jq docker flock find mktemp sha256sum date timeout; do
    command -v "$comando" >/dev/null || { echo "Falta $comando" >&2; exit 2; }
done
mkdir -p -- "$DATA_DIR"/{incoming,processing,processed,rejected}
DATA_DIR="$(cd -- "$DATA_DIR" && pwd -P)"
# Impide que dos instancias procesen simultáneamente la misma cola.
exec 9>"$DATA_DIR/.spawn.lock"
flock -n 9 || { echo 'Ya hay un spawn activo para esta carpeta.' >&2; exit 1; }
log() { printf '%s %s\n' "$(date -Is)" "$*"; }
trap 'exit 0' TERM INT

# Validación e importación de reportes TOML.
importar() (
    local archivo="$1" temporal digest fecha
    [[ -f "$archivo" && ! -L "$archivo" ]] || return 1
    [[ "$(stat -c %s -- "$archivo")" -le 1048576 ]] || { echo 'TOML mayor a 1 MiB'; return 1; }
    temporal="$(mktemp -d)" || return 1
    trap 'rm -rf -- "$temporal"' EXIT
    cp -- "$archivo" "$temporal/original.toml" || return 1
    if ! "$TOMLQ_BIN" '.' "$temporal/original.toml" > "$temporal/datos.json" 2> "$temporal/parser.log"; then
        echo 'TOML inválido'; return 1
    fi
    # Validación de los campos usados por la ingesta.
    if ! jq -e --arg nombre "${archivo##*/}" '
      def texto: type == "string";
      def opcionaltexto: . == null or texto;
      def numero: type == "number" and . >= 0 and . <= 9999999999.99;
      def uuid: texto and test("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$");
      type == "object" and
      ([.meta,.equipo,.hardware,.red,.perifericos,.diagnostico] | all(type == "object")) and
      (.meta.id_ejecucion | uuid) and
      $nombre == ("SGLAB-" + .meta.id_ejecucion + ".toml") and
      .meta.version_formato == "1.1" and
      (.meta.version_script | texto) and (.meta.codigo_laboratorio | texto) and
      (.meta.ci_reportada | type == "number" and . == floor and . >= 0 and . <= 4294967295) and
      (.meta.fecha_evento | texto and test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}([.][0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})$")) and
      (.equipo.serial | opcionaltexto) and (.equipo.smbios_uuid | . == null or uuid) and
      (.equipo.hostname | opcionaltexto) and (.equipo.sistema_operativo | opcionaltexto) and
      (.hardware.cpu | opcionaltexto) and
      (.hardware.ram_total_gb | . == null or (numero and . <= 99999999.99)) and
      (.red.mac | opcionaltexto) and (.red.ipv4 | opcionaltexto) and
      (.diagnostico.errores_lectura | type == "array" and all(type == "object" and (.campo|texto) and (.detalle|texto))) and
      (.hardware.discos | . == null or (type == "array" and all(
        type == "object" and (.orden | type == "number" and . == floor and . >= 0 and . <= 65535) and
        (.tipo | . == null or IN("HDD","SSD","OTRO")) and
        (.capacidad_total_gb | . == null or numero) and
        (.espacio_libre_gb | . == null or numero) and
        (.espacio_libre_gb == null or .capacidad_total_gb == null or .espacio_libre_gb <= .capacidad_total_gb)))) and
      (((.hardware.discos // []) | map(.orden) | unique | length) == ((.hardware.discos // [])|length)) and
      ((tojson | utf8bytelength) <= 65535)
    ' "$temporal/datos.json" > /dev/null 2>&1; then
        echo 'Campos de captura inválidos o nombre de archivo incorrecto'; return 1
    fi
    fecha="$(jq -r '.meta.fecha_evento' "$temporal/datos.json")" || return 1
    fecha="$(date -u -d "$fecha" '+%Y-%m-%d %H:%M:%S')" || { echo 'Fecha inválida'; return 1; }
    digest="$(sha256sum -- "$temporal/original.toml")" || return 1
    digest="${digest%% *}"
    cat > "$temporal/generador.jq" <<'JQ_SQL'
def sql:
  if . == null then "NULL"
  elif type == "number" then tostring
  else "(CONVERT(FROM_BASE64('" + (tostring | @base64) + "') USING utf8mb4) COLLATE utf8mb4_unicode_ci)" end;
def ident:
  if . == null then null else ascii_upcase | gsub("^\\s+|\\s+$"; "") |
  if IN("", "DEFAULT STRING", "TO BE FILLED BY O.E.M.", "TO BE FILLED BY OEM", "UNKNOWN", "NONE", "NOT SPECIFIED", "SYSTEM SERIAL NUMBER", "0", "N/A") then null else . end end;
. as $d |
(.equipo.serial | ident | sql) as $serial |
(.equipo.smbios_uuid | if . == null or . == "00000000-0000-0000-0000-000000000000" or ascii_upcase == "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF" then null else ascii_upcase end | sql) as $uuid |
(.meta.id_ejecucion | sql) as $id |
($digest | sql) as $hash |
"SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET time_zone = '+00:00';
SET SESSION sql_mode = 'STRICT_ALL_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';
DELIMITER $$
BEGIN NOT ATOMIC
 DECLARE EXIT HANDLER FOR SQLEXCEPTION
 BEGIN
  ROLLBACK;
  DO RELEASE_LOCK('sglab_ingesta_v2');
  RESIGNAL;
 END;
 IF COALESCE(GET_LOCK('sglab_ingesta_v2',30),0) <> 1 THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='No se pudo obtener bloqueo';
 END IF;
 START TRANSACTION;
 SET @existente=(SELECT id_registro FROM registro WHERE id_ejecucion=\($id));
 IF @existente IS NOT NULL AND NOT ((SELECT hash_archivo FROM registro WHERE id_registro=@existente) <=> \($hash)) THEN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='UUID repetido con contenido diferente';
 END IF;
 IF @existente IS NULL THEN
  SET @serial=(SELECT id_equipo FROM equipo WHERE UPPER(TRIM(num_serie))=\($serial));
  SET @uuid=(SELECT id_equipo FROM equipo WHERE UPPER(smbios_uuid)=\($uuid));
  IF @serial IS NOT NULL AND @uuid IS NOT NULL AND @serial <> @uuid THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Identidad conflictiva';
  END IF;
  SET @equipo=COALESCE(@serial,@uuid);
  IF @equipo IS NULL THEN
   SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Equipo no registrado por el Asistente';
  END IF;
  SET @usuario=(SELECT ci FROM usuarios WHERE ci=\((if .meta.ci_reportada == 0 then null else .meta.ci_reportada end)|sql));
  SET @laboratorio=(SELECT id_laboratorio FROM equipo WHERE id_equipo=@equipo);
  INSERT INTO registro (id_ejecucion,hash_archivo,id_equipo,usuario_ci,fecha,nombre,descripcion,estado,
   hostname_reportado,sistema_operativo,cpu,ram_gb,mac,ip,id_laboratorio_observado)
  VALUES (\($id),\($hash),@equipo,@usuario,\($fecha|sql),\(("Captura "+.meta.id_ejecucion)|sql),\(($d|tojson)|sql),
   \((if (.diagnostico.errores_lectura|length)>0 then "ERROR" else "OK" end)|sql),
   \(.equipo.hostname|sql),\(.equipo.sistema_operativo|sql),\(.hardware.cpu|sql),\(.hardware.ram_total_gb|sql),
   \(.red.mac|sql),\(.red.ipv4|sql),@laboratorio);
  SET @registro=LAST_INSERT_ID();
  \([.hardware.discos[]? | "INSERT INTO registro_disco (id_registro,orden,tipo,capacidad_total_gb) VALUES (@registro,\(.orden|sql),\(.tipo|sql),\(.capacidad_total_gb|sql));"]|join("\n"))
 END IF;
 COMMIT;
 DO RELEASE_LOCK('sglab_ingesta_v2');
 SELECT IF(@existente IS NULL,'INSERTADO','YA_PROCESADO');
END$$
DELIMITER ;"
JQ_SQL
    jq -r --arg digest "$digest" --arg fecha "$fecha" -f "$temporal/generador.jq" \
        "$temporal/datos.json" > "$temporal/consulta.sql" || return 1
    if ! timeout 90 docker compose --project-directory "$COMPOSE_DIR" \
        --env-file "$COMPOSE_DIR/.env" -f "$COMPOSE_DIR/compose.yaml" \
        exec -T db sh -c '
            export MYSQL_PWD="$DB_INGEST_PASSWORD"
            exec mariadb --protocol=tcp -h127.0.0.1 -u"$DB_INGEST_USER" \
                --batch --skip-column-names --default-character-set=utf8mb4 sglab
        ' < "$temporal/consulta.sql" > "$temporal/salida.log" 2> "$temporal/error.log"; then
        echo 'Falló la ingesta: revisar identidad del equipo, Docker, BD y credenciales.'
        return 1
    fi
    cat -- "$temporal/salida.log"
)

procesar() {
    local archivo="$1" trabajo nombre
    nombre="${archivo##*/}"
    # Un directorio único evita sobrescribir archivos con nombres repetidos.
    trabajo="$(mktemp -d "$DATA_DIR/processing/job.XXXXXXXX")"
    if ! mv -- "$archivo" "$trabajo/$nombre"; then
        rmdir -- "$trabajo"
        return
    fi
    log "Procesando: $nombre"
    if importar "$trabajo/$nombre" >"$trabajo/resultado.log" 2>&1; then
        mv -- "$trabajo" "$DATA_DIR/processed/"
        log "Importado: $nombre"
    else
        # Conserva el original y el motivo; no reintenta indefinidamente un inválido.
        mv -- "$trabajo" "$DATA_DIR/rejected/"
        log "Falló: $nombre; revisar rejected/${trabajo##*/}/resultado.log"
    fi
}

# Una interrupción pudo ocurrir después del COMMIT. La ingesta deduplica por UUID/hash.
while IFS= read -r -d '' pendiente; do
    trabajo="${pendiente%/*}"
    if importar "$pendiente" >"$trabajo/resultado.log" 2>&1; then
        mv -- "$trabajo" "$DATA_DIR/processed/"
    else
        mv -- "$trabajo" "$DATA_DIR/rejected/"
    fi
done < <(find "$DATA_DIR/processing" -mindepth 2 -maxdepth 2 -type f -name '*.toml' -print0)

log "Escuchando en $DATA_DIR/incoming (cada ${INTERVALO}s)"
while true; do
    while IFS= read -r -d '' archivo; do
        procesar "$archivo"
    done < <(find "$DATA_DIR/incoming" -mindepth 1 -maxdepth 1 -type f -name '*.toml' -print0)
    [[ "${1:-}" == --once ]] && break
    sleep "$INTERVALO" &
    wait $! || true
done
