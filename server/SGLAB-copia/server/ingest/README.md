# Ingesta con spawn.sh

`server/bin/spawn.sh` es el único daemon e importador de reportes TOML.
Usa `tomlq` para parsear TOML y `jq` para validar los campos y generar SQL.
El comando `tomlq` pertenece al paquete yq y requiere Python.

Importa en el esquema de siete tablas mediante el servicio `db` de Compose,
con la cuenta DB_INGEST_USER. El SQL utiliza bloques anónimos de MariaDB.

El equipo debe existir previamente, creado por el Asistente. Se identifica por
serie o UUID SMBIOS; si no existe o hay conflicto entre ambas identidades, se
rechaza la importación. Se toma el laboratorio asignado al equipo en la BD:
`meta.codigo_laboratorio` se conserva en la captura, sin modificar la asignación.
El estado administrativo no se modifica. El estado observado es ERROR si la
captura declara errores de lectura; en otro caso es OK.

## Ejecutar Bash

Requiere Bash, Docker Compose, jq, flock y utilidades GNU (coreutils).
Instalar jq mediante el gestor de paquetes del host. Desde la raíz del repo:

```bash
python3 -m venv .venv
.venv/bin/pip install -r server/ingest/requirements-bash.txt
SGLAB_TOMLQ="$PWD/.venv/bin/tomlq" SGLAB_DATA_DIR="$PWD/var/ingesta" server/bin/spawn.sh
```

`spawn.sh` valida el nombre/UUID, versión, fecha con zona horaria, tipos y
rangos de los campos importados, discos y diagnósticos. Conserva el documento
completo en `registro.descripcion`. No exige un error de lectura por cada campo omitido.

Admite `--once` para procesar la cola y salir. El intervalo predeterminado es
cinco segundos, configurable con `SGLAB_INTERVALO`. La carpeta predeterminada
es `server/` dentro del proyecto, configurable mediante `SGLAB_DATA_DIR`.

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

Adaptar `server/systemd/sglab-spawn.service` al usuario y rutas reales.
La plantilla ejecuta `server/bin/spawn.sh`; configurar SGLAB_TOMLQ con la ruta
al comando `tomlq`.
El usuario necesita leer `.env`, escribir la carpeta de ingesta y acceder a Docker.
El acceso al grupo docker otorga control administrativo sobre el host.

```bash
sudo cp server/systemd/sglab-spawn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sglab-spawn
journalctl -u sglab-spawn -f
```

## Comprobación de sintaxis

```bash
bash -n server/bin/spawn.sh
```

Esta copia no incluye una suite de pruebas automatizadas de ingesta.

## Despliegue actual

Ver `doc/SERVIDOR.md` para rutas, puertos y servicio instalados en este host.
El proyecto Compose es `sglab-copia` y tiene su propio volumen de BD.
