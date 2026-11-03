# Probar spawn.sh con un TOML recibido de Windows

Todos los comandos se ejecutan en el servidor Linux que recibió el archivo,
con el usuario que puede escribir la cola, leer `.env` y acceder a Docker.
El ejemplo de ruta corresponde al servidor indicado durante la prueba de Windows;
reemplazarla si el proyecto se encuentra en otro lugar.

## 1. Entrar al proyecto y comprobar MariaDB

```bash
cd /home/sebapancho/SGLAB
docker compose ps
```

El servicio `db` debe estar en ejecución y saludable. Para esta prueba manual,
si `sglab-spawn` ya está activo, detenerlo antes de revisar la cola:

```bash
systemctl is-active sglab-spawn
# Ejecutar el siguiente comando solamente si estaba activo:
sudo systemctl stop sglab-spawn
```

Si la unidad no existe, seguir con la prueba manual. No ejecutar dos consumidores
sobre la misma cola ni borrar `.spawn.lock` para intentar forzarlo.

## 2. Preparar el parser y comprobar herramientas

Si todavía no existe un entorno Python de ingesta válido en este servidor:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r server/ingest/requirements-bash.txt
```

No copiar `.venv` desde otra máquina; se crea con el Python del servidor.
Verificar las herramientas:

```bash
.venv/bin/tomlq --version
jq --version
docker compose version
```

Si falta `jq`, instalarlo con el gestor del servidor. En Debian/Ubuntu se usa
`sudo apt install jq`; en Fedora/Rocky, `sudo dnf install jq`. Debian/Ubuntu puede
requerir instalar `python3-venv` antes de crear el entorno. Si falla un requisito,
resolverlo antes de ejecutar la ingesta.

## 3. Revisar el TOML recibido

```bash
ls -lh var/incoming/
```

Debe existir un archivo terminado `SGLAB-<UUID>.toml`. Un `.toml.part` todavía
no está publicado para ingesta: verificar que el cliente haya completado el envío.

Definir el nombre real, conservándolo exactamente:

```bash
SGLAB_PRUEBA_ARCHIVO='SGLAB-PEGAR-UUID-REAL.toml'
.venv/bin/tomlq '{id_ejecucion: .meta.id_ejecucion, serial: .equipo.serial, smbios_uuid: .equipo.smbios_uuid, errores_lectura: .diagnostico.errores_lectura}' "var/incoming/$SGLAB_PRUEBA_ARCHIVO"
```

Anotar `id_ejecucion`, serie y UUID SMBIOS. Si no está en incoming, buscarlo en
`var/processing`, `var/processed` y `var/rejected`: un daemon activo pudo haberlo
procesado antes. En ese caso revisar su resultado y comprobar la BD, sin modificar
su contenido ni inventar otro UUID para reenviarlo.

## 4. Registrar la PC desde la web

Ingresar como asistente en la web de ese mismo servidor:

1. Crear el laboratorio si no existe.
2. Registrar la PC con la serie o UUID SMBIOS que aparece en el TOML.
3. Asignarla al laboratorio y dejar ambos activos.

Si la PC ya existe, comprobar su identidad y asignación. La etiqueta LAB01 del
archivo no crea un laboratorio ni sustituye la asignación de la BD. El importador
requiere una PC preexistente; no la da de alta automáticamente.

## 5. Procesar la cola una vez

Desde la raíz del proyecto:

```bash
SGLAB_TOMLQ="$PWD/.venv/bin/tomlq" SGLAB_DATA_DIR="$PWD/var" bash server/bin/spawn.sh --once
```

Procesa los TOML finalizados de la cola actual y recupera trabajos pendientes de
processing. Después termina. Para el archivo debería aparecer `Procesando:` y
`Importado:`; si falla, indicará el trabajo en rejected. Si aparece `Ya hay un
spawn activo`, resolver la instancia que está ejecutándose antes de repetir.
El código de salida por sí solo no acredita que todos los archivos se importaron.

## 6. Ver el resultado de ese archivo

```bash
find var/processed var/rejected -type f -name "$SGLAB_PRUEBA_ARCHIVO" -print
```

En la carpeta `job.XXXXXXXX` que contiene ese TOML, abrir `resultado.log`:

```bash
cat var/processed/job.XXXXXXXX/resultado.log
```

Reemplazar el nombre del trabajo por el devuelto por find; si está en rejected,
usar esa ruta. Los resultados correctos son `INSERTADO` o `YA_PROCESADO`.
Este último reconoce el mismo UUID/contenido y evita duplicarlo.

Si quedó en rejected, revisar el log y comprobar nombre/UUID del archivo,
TOML v1.1, identidad de la PC, estado activo del laboratorio/equipo, Docker y
credenciales de ingesta. Después de resolver la causa se puede devolver el
original intacto a incoming para repetir, sin editar su UUID ni contenido.

## 7. Confirmar en MariaDB

Abrir una sesión con la cuenta técnica de ingesta, sin imprimir su contraseña:

```bash
docker compose exec db sh -c 'MYSQL_PWD="$DB_INGEST_PASSWORD" exec mariadb --protocol=tcp -h127.0.0.1 -u"$DB_INGEST_USER" sglab'
```

Dentro de MariaDB, sustituir el marcador por `meta.id_ejecucion` del TOML:

```sql
SELECT id_registro, id_ejecucion, id_equipo, hostname_reportado, fecha, estado
FROM registro
WHERE id_ejecucion = 'PEGAR_UUID_REAL_DEL_TOML';
```

Debe devolver una fila correspondiente a esa captura. `estado = ERROR` puede
ser una importación correcta con lecturas no disponibles declaradas por el
colector; el estado administrativo del equipo se conserva.

Salir de la sesión con `exit;`. Ver también la última captura desde Equipos en
la web. Si se detuvo un servicio que estaba funcionando, volver a iniciarlo:

```bash
sudo systemctl start sglab-spawn
```

## Resultado de la prueba

La prueba se considera exitosa cuando el archivo está en processed, su resultado
es INSERTADO/YA_PROCESADO, y existe una única fila en registro para su UUID.
Guardar el nombre/UUID del TOML, la salida del procesamiento y la consulta SQL
como evidencia. Esta guía no afirma que la prueba física ya se haya ejecutado.

Para dejar el daemon permanente, seguir `server/ingest/README.md` y adaptar
usuario, grupos y rutas de la unidad systemd a este servidor. Generar la unidad
con `python3 infra/configurar-spawn.py` y copiar el archivo generado a
`/etc/systemd/system/sglab-spawn.service`. La plantilla del repositorio contiene
rutas del servidor de desarrollo; no copiarla directamente sin adaptarla.
