# Usuario BASE-TD2, repositorio y recepción

El aprovisionamiento reutiliza **BASE-TD2**, el usuario que ya creaba provision.
Ese mismo usuario es dueño del repositorio, recibe capturas por SSH y ejecuta
spawn. No se crea una cuenta adicional llamada sglab.

BASE-TD2 pertenece a **docker** para ejecutar la ingesta mediante Compose y a
**sglab-ingest** para la carpeta de recepción. La cuenta de MariaDB
`DB_INGEST_USER` sigue siendo distinta: es la que inserta los registros en la base.
Al compartir la cuenta Linux, las claves SSH autorizadas para BASE-TD2 tienen los
permisos de esa cuenta, incluido acceso a Docker y a su configuración local.

## Instalar y clonar

La opción Docker instala las herramientas y clona el repositorio como BASE-TD2,
en su carpeta personal: normalmente `/home/BASE-TD2/SGLAB`.
También se puede clonar desde la opción **5** o ejecutar:

```bash
sudo sh infra/provision/provision.sh --clonar-sglab
```

Pide la URL GitHub, por defecto:
`https://github.com/Tecnicatura-TDn/-TD2_SGLAB.git`. Reutiliza BASE-TD2 y lo crea solo
si todavía no existe. Git se ejecuta como ese usuario, no como root.
Detecta la raíz SGLAB tanto directamente como en SGLAB, server/SGLAB o
server/SGLAB-copia y muestra la ruta encontrada.

Si ya está clonado desde el mismo origen, conserva todos los archivos sin pull ni
sobrescrituras. Rechaza otra carpeta, origen distinto o enlace simbólico.
Para repositorios privados configurar el acceso Git de BASE-TD2; no incluir tokens
ni contraseñas en la URL. Las claves GitHub de root no autorizan automáticamente
a BASE-TD2. La clonación obtiene lo publicado en GitHub, no cambios locales sin subir.

## Preparar infraestructura y spawn

Entrar como el usuario existente mediante `sudo -iu BASE-TD2`, ir a la raíz SGLAB
que mostró la clonación y preparar `.env`, HTTPS y los contenedores con infra.sh.
Después, desde una cuenta administradora, usar la opción **3** o:

```bash
sudo sh infra/provision/provision.sh --configurar-sglab
```

Pide la ruta del proyecto, pero ya no pide crear/elegir otro usuario: usa BASE-TD2.
Desde el mismo menú sugiere la ruta recién clonada. Comprueba Docker Compose,
MariaDB saludable y el acceso de DB_INGEST_USER antes de activar la ingesta.

Prepara `.ssh` (0700) y `authorized_keys` (0600) conservando claves existentes.
Si BASE-TD2 no tiene contraseña, pide definirla con `passwd`, sin guardarla ni
imprimirla en logs. Si ya tiene contraseña se conserva. Para cambiarla después:

```bash
sudo passwd BASE-TD2
```

BASE-TD2 es propietario de var y de la cola: incoming tiene grupo sglab-ingest y
setgid (2770); processing, processed y rejected quedan 0700; `.env` queda 0600.
No se abren permisos del home a otros usuarios ni se necesitan ACL de recorrido
para una segunda cuenta. Se rechazan enlaces en la cola y archivos SSH.

Instala el parser en `.venv`, genera la unidad de spawn con `User=BASE-TD2`, la
instala en systemd, habilita SSH y reinicia la ingesta. No modifica firewall,
políticas SSH institucionales ni SELinux. Si falta .env o MariaDB no está lista,
informa lo pendiente sin afirmar que terminó la configuración.

## Autorizar clientes

Usar **BASE-TD2** y la ruta exacta de incoming que muestra provision en el perfil
cliente. El instalador puede agregar su clave pública mediante la contraseña del
receptor; los envíos posteriores usan la clave, sin guardar esa contraseña.

Si SSH no admite contraseñas, copiar solo el `.pub` al servidor y usar la opción
**4** o:

```bash
sudo sh infra/provision/provision.sh --autorizar-cliente
```

Valida una sola clave pública y la agrega sin duplicarla, con `restrict` para
impedir reenvíos y PTY; permite los comandos no interactivos y SCP/SFTP necesarios.
No copia claves privadas ni desactiva la comprobación de huella. Revisar también
AllowUsers/AllowGroups, firewall y SELinux si una política bloquea la conexión.

## Verificación

```bash
id BASE-TD2
sudo systemctl status sglab-spawn --no-pager
sudo journalctl -u sglab-spawn -n 30 --no-pager
```

La prueba aislada usa cuentas Linux reales en un contenedor descartable. Comprueba
contraseña inicial/repetición, grupos docker y sglab-ingest, permisos de claves,
publicación y movimiento de capturas por BASE-TD2, .env privado y rechazo de
claves privadas/enlaces. Git se simula sin red: prueba propiedad del checkout por
BASE-TD2 existente, que no se crea sglab y que no se pierden cambios locales.

Desde la raíz del repositorio que contiene server/SGLAB-copia:

```bash
docker build -t sglab-provision-prueba -f server/SGLAB-copia/tests/provision/Dockerfile .
docker run --rm --network none -v "$PWD/server/SGLAB-copia/infra/provision/resources/setup_sglab.sh:/prueba/setup_sglab.sh:ro,Z" -v "$PWD/server/SGLAB-copia/tests/provision/receptor.sh:/prueba/receptor.sh:ro,Z" sglab-provision-prueba sh /prueba/receptor.sh
```

No ejecutar el script de prueba directamente en el host. No se ejecutó el provision
completo ni se migró el usuario del servidor activo. Faltan validación de systemd,
SELinux y un envío real desde Windows en el servidor de destino.
