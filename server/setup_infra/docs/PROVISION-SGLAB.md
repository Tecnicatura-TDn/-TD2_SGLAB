# Administrador, receptor SSH y servicio spawn

El proyecto permanece en el home del administrador, por ejemplo
`/home/facu/-TD2_SGLAB/server/setup_infra`. El administrador conserva la propiedad
del código, `.env`, certificados y entorno `.venv`. No ejecutar la instalación
como `BASE-TD2` ni transferirle el repositorio.

`BASE-TD2` es la cuenta genérica que recibe capturas y ejecuta spawn. No necesita
sudo ni pertenecer a docker. Tiene escritura en `var/incoming`, `var/processing`,
`var/processed`, `var/rejected` y el bloqueo `var/.spawn.lock`. El provisionador
aplica ACL para atravesar las carpetas superiores y leer exclusivamente el script
y el entorno Python necesarios, sin abrir todo `/home/facu` a otros usuarios.
El administrador puede inspeccionar la cola mediante sudo.

## Instalación

Instalar Docker y las herramientas del provisionador. También se requieren
`setfacl` (paquete `acl`), `mariadb` (cliente, normalmente `mariadb-client` en Debian
 o `mariadb` en Rocky/RHEL), Python con venv/pip, jq y OpenSSH.

Desde la raíz SGLAB que contiene compose.yaml:

```bash
sudo bash infra/provision/provision.sh --configurar-sglab
cp .env.example .env  # solo si todavía no existe; configurar sus valores
sudo bash infra/infra.sh
```

Primero provision prepara usuario, dependencias, permisos y la unidad systemd,
sin exigir `.env` ni contenedores creados. La ruta solicitada es la carpeta con
`compose.yaml` (aceptar la sugerencia con Enter); no ingresar `/home`.
Después configurar `.env` y ejecutar infra.sh: prepara HTTPS si falta, levanta
los contenedores y activa spawn una vez comprobada la conexión a MariaDB.
El provisionador crea `BASE-TD2` si falta.
Si no tiene contraseña pide definirla para registrar las claves de los clientes.
No es ninguna de las contraseñas de MariaDB.

El provisionador instala el parser en `.venv` como administrador, aplica permisos,
deja la extracción de credenciales para infra.sh. Este extrae solamente las credenciales `DB_INGEST_USER` y `DB_INGEST_PASSWORD` mediante
la configuración resuelta de Compose y las guarda en `/etc/sglab/ingest.cnf`.
El archivo es root:sglab-ingest con permisos 640; no incluye root, web ni respaldos.
No se imprime su contenido. No agregar otras cuentas al grupo sglab-ingest.

spawn usa el cliente MariaDB local y ese archivo, sin leer `.env` ni invocar
Docker. Compose ya publica MariaDB exclusivamente en `127.0.0.1`, usando
`DB_BIND_PORT` (3306 por defecto). No abrir ese puerto al laboratorio. Se valida
la conexión con la identidad real de BASE-TD2 antes de activar el servicio.
La cuenta SQL conserva sus permisos existentes: consultar e insertar capturas,
sin administrar usuarios ni modificar el estado administrativo de los equipos.

El servicio systemd se instala con `User=BASE-TD2`, sin grupos Docker,
`NoNewPrivileges`, sistema de archivos de solo lectura salvo la cola y un
directorio temporal privado. Reinicia ante fallos y arranca con el servidor.
Las claves SSH de los clientes comparten los permisos de BASE-TD2: la cuenta
puede leer las credenciales de ingesta y todas las capturas de la cola; no hay
separación por cliente dentro de esta cuenta genérica.

## Configurar los clientes

Usar en cliente.json el usuario `BASE-TD2`, la IP del servidor y la ruta exacta
que imprime el provisionador, por ejemplo:

```json
{
  "usuario": "BASE-TD2",
  "servidor": "192.168.2.229",
  "directorio_remoto": "/home/facu/-TD2_SGLAB/server/setup_infra/var/incoming"
}
```

Estos son campos a actualizar en el perfil completo, no un reemplazo de todos
sus campos. El instalador registra la clave pública; la clave privada permanece
en la PC. Si SSH no admite contraseñas, autorizar la pública desde el servidor:

```bash
sudo bash infra/provision/provision.sh --autorizar-cliente
```

## Estado y logs

```bash
sudo systemctl enable --now sglab-spawn
sudo systemctl status sglab-spawn --no-pager
sudo journalctl -u sglab-spawn -n 50 -f
sudo systemctl restart sglab-spawn
sudo systemctl stop sglab-spawn
```

Ctrl+C cierra el seguimiento de logs sin detener el servicio. Los fallos por
captura quedan en `var/rejected/job.*/resultado.log`, junto al original.

## Actualizar una instalación anterior

Guardar un respaldo y detener spawn antes de cambiar sus archivos. El proyecto
y su `.venv` deben pertenecer al administrador, no a BASE-TD2. El provisionador
rechaza un proyecto propiedad del receptor; no cambia recursivamente la propiedad
de una instalación existente. Corregirla con el administrador antes de continuar.

Reejecutar `--configurar-sglab` como administrador. Elimina al receptor del grupo
docker si pertenecía a él, deja preparada la unidad y prepara el
servicio. Después ejecutar infra.sh para actualizar credenciales y activarlo. Cerrar las sesiones SSH antiguas de BASE-TD2: los procesos existentes
conservan sus grupos hasta terminar. Revisar y quitar cualquier permiso sudo que
se le hubiera concedido manualmente. Si conocía las claves del `.env` general,
rotarlas también en la BD: cambiar solo `.env` no cambia usuarios de un volumen
MariaDB existente.

Después de cambiar el puerto o las credenciales de ingesta en Compose y MariaDB,
reejecutar infra.sh para actualizar `/etc/sglab/ingest.cnf`.

## Pruebas

```bash
python3 -m unittest discover -s tests -p 'test_configurar*.py'
bash -n server/bin/spawn.sh
```

La prueba de cuentas/ACL usa usuarios reales exclusivamente dentro de un
contenedor descartable, nunca ejecutar receptor.sh directamente en el servidor:

```bash
docker build -t sglab-provision-prueba -f tests/provision/Dockerfile .
docker run --rm --network none -v "$PWD/infra/provision/resources/setup_sglab.sh:/prueba/setup_sglab.sh:ro,Z" -v "$PWD/tests/provision/receptor.sh:/prueba/receptor.sh:ro,Z" sglab-provision-prueba sh /prueba/receptor.sh
```
