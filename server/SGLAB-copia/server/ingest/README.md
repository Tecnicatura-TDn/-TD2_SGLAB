# Ingesta con spawn.sh

`server/bin/spawn.sh` es el único daemon e importador de reportes TOML.
Usa `tomlq` para parsear TOML y `jq` para validar los campos y generar SQL.
El comando `tomlq` pertenece al paquete yq y requiere Python.
Para comprobar un archivo real ya recibido desde Windows, seguir
[la prueba paso a paso](../../docs/PRUEBA-SPAWN.md).

Importa en el esquema actual de nueve tablas mediante el servicio `db` de Compose,
con la cuenta DB_INGEST_USER. El SQL utiliza bloques anónimos de MariaDB.

El equipo debe existir previamente, creado por el Asistente. Se identifica por
serie o UUID SMBIOS; si no existe o hay conflicto entre ambas identidades, se
rechaza la importación. Se toma el laboratorio asignado al equipo en la BD:
`meta.codigo_laboratorio` se conserva en la captura, sin modificar la asignación.
El estado administrativo no se modifica. El estado observado es ERROR si la
captura declara errores de lectura; en otro caso es OK.

## Ejecutar Bash

Requiere Bash, Docker Compose, jq, flock y utilidades GNU (coreutils).
Instalar jq mediante el gestor de paquetes del host. Desde la raíz de la aplicación SGLAB (donde está compose.yaml):

```bash
python3 -m venv .venv
.venv/bin/pip install -r server/ingest/requirements-bash.txt
SGLAB_TOMLQ="$PWD/.venv/bin/tomlq" SGLAB_DATA_DIR="$PWD/var" bash server/bin/spawn.sh
```

`spawn.sh` valida el nombre/UUID, versión, fecha con zona horaria, tipos y
rangos de los campos importados, discos y diagnósticos. Conserva el documento
completo en `registro.descripcion`. No exige un error de lectura por cada campo omitido.

Admite `--once` para procesar la cola y salir. El intervalo predeterminado es
cinco segundos, configurable con `SGLAB_INTERVALO`. La carpeta predeterminada
es `var/` dentro del proyecto, configurable mediante `SGLAB_DATA_DIR`.

## Entrega y recuperación

El emisor debe subir `SGLAB-<UUID>.toml.part` y renombrarlo a
`SGLAB-<UUID>.toml` en incoming al terminar. El renombrado debe ocurrir en el mismo
filesystem. No publicar el nombre final mientras se escribe el archivo.
Los enlaces simbólicos y archivos de otras extensiones no se procesan.

Cada archivo pasa a `processing/job.XXXXXXXX/`, después a `processed/` o
`rejected/`, junto con `resultado.log`. `spawn.sh` recupera trabajos
pendientes de processing al arrancar. Usa `.spawn.lock` para impedir que varias
instancias consuman la misma cola simultáneamente. No borrar ese archivo con un daemon activo.

Los fallos de Docker, BD o identidad también quedan en rejected. Tras resolverlos,
se puede devolver el TOML a incoming. UUID y hash permiten reconocer reenvíos sin
insertar dos veces y rechazar un UUID con contenido diferente. La captura y sus
discos se insertan en una misma transacción. No se guardan SQL ni credenciales en
los logs de errores de MariaDB.

## Límites actuales

- Solo TOML v1.1; CSV queda pendiente de definir.
- Máximo 1 MiB por archivo y 65535 bytes de JSON de captura, por el campo TEXT.
- Los discos se insertan en registro_disco. El documento completo preserva el
  espacio libre agregado y otros datos del contrato que no tienen columna propia.
- TOML v1.1 no distingue sistemas de archivos. No se inventan filas en
  registro_sistema_archivos; ampliar el recolector y el contrato es trabajo pendiente.
- Los TOML antiguos de LAB6 no cumplen este contrato.
- El daemon requiere Linux para flock y systemd.

## Servicio permanente

Generar la unidad en el servidor donde se ejecutará el daemon, desde la raíz del
proyecto. `infra/configurar-spawn.py` toma la ruta real de SGLAB y el usuario Linux
actual, comprueba que el usuario exista y que `.venv/bin/tomlq` funcione. Se puede
indicar otro usuario con `--usuario`. No se ejecuta como root por defecto.
El archivo generado queda en `var/systemd/sglab-spawn.service`; no instala ni
reinicia servicios automáticamente. La plantilla de `server/systemd` es un ejemplo
del servidor de desarrollo y no debe copiarse directamente a otra máquina.
El usuario necesita leer `.env`, escribir la carpeta de ingesta y acceder a Docker.
El acceso al grupo docker otorga control administrativo sobre el host.

```bash
python3 infra/configurar-spawn.py
cat var/systemd/sglab-spawn.service
sudo install -m 0644 var/systemd/sglab-spawn.service /etc/systemd/system/sglab-spawn.service
sudo systemctl daemon-reload
sudo systemctl reset-failed sglab-spawn
sudo systemctl enable sglab-spawn
sudo systemctl restart sglab-spawn
sudo systemctl status sglab-spawn --no-pager
journalctl -u sglab-spawn -f
```

## Comprobación de sintaxis

```bash
bash -n server/bin/spawn.sh
```

`tests/test_web_integration.py` y `tests/test_role_scope.py` incluyen integración
con el daemon real, activada mediante `SGLAB_TEST_WEB=1`; generan y retiran datos
sintéticos. La prueba desde una PC real requiere además comprobar el envío y
el archivo/registro concreto según la guía anterior.

## Despliegue actual

Ver `docs/SERVIDOR.md` para rutas, puertos y servicio instalados en este host.
El proyecto Compose es `sglab` y usa el volumen externo `sglab_db_data`.

## Operación del servicio

El servicio ya está instalado en este servidor. No ejecutar otra instancia manual
sobre la misma cola mientras esté activo.

```bash
sudo systemctl status sglab-spawn
sudo systemctl is-enabled sglab-spawn
sudo systemctl restart sglab-spawn
sudo journalctl -u sglab-spawn -n 50 --no-pager
sudo systemctl stop sglab-spawn
sudo systemctl start sglab-spawn
```

`enable --now` inicia el proceso y lo habilita para los próximos arranques.
`stop` lo detiene solo hasta el próximo inicio; para deshabilitarlo también:

```bash
sudo systemctl disable --now sglab-spawn
```

Después de editar la unidad, copiarla de nuevo y ejecutar `daemon-reload` y
`restart`. Si solo se modifica spawn.sh, basta con reiniciar el servicio.
Para probar una pasada manual, detener antes el servicio:

```bash
sudo systemctl stop sglab-spawn
SGLAB_TOMLQ="$PWD/.venv/bin/tomlq" bash server/bin/spawn.sh --once
sudo systemctl start sglab-spawn
```

Consultar `var/processed/job.*/resultado.log` o `var/rejected/job.*/resultado.log`
para el resultado por archivo. El estado activo del daemon no garantiza que una
captura se haya importado; revisar el log correspondiente.

Los equipos o laboratorios archivados no admiten capturas nuevas. El rechazo
conserva el TOML en var/rejected; restaurar el recurso antes de reintentar.

## Error 217/USER y lectura de rechazos

`Failed to determine user credentials` junto con `status=217/USER` indica que
systemd no pudo establecer las credenciales del usuario de la unidad. En otro
servidor puede ocurrir por copiar la plantilla con `User=facu`. El proceso todavía
no llegó a ejecutar spawn.sh. Comprobar el usuario y el archivo realmente cargados:

```bash
systemctl show sglab-spawn -p User -p WorkingDirectory -p FragmentPath
```

Generar e instalar la unidad local con los comandos anteriores. Editar solo el
archivo del repositorio no actualiza la unidad instalada en `/etc/systemd/system`.
El generador añade el grupo docker si existe, sin exigir un grupo sglab-ingest
inexistente en otra máquina. El usuario debe conservar acceso a `.env` y la cola.

Para leer los rechazos, situarse en la raíz de SGLAB, no en server/bin. Esta forma
de find evita tener que escapar el punto y coma de `-exec`:

```bash
find var/rejected -type f -name resultado.log -print -exec cat {} +
```

Los rechazos previos no se vuelven a importar automáticamente al corregir la
unidad. Revisar su resultado y resolver la causa antes de devolverlos a incoming.
Referencia del código de salida: [systemd.exec](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html#Process%20Exit%20Codes).
