# Recolector de PC y entrega al servidor

`recopilar.py` funciona en Linux y Windows con Python 3.9 o posterior, sin paquetes
Python adicionales. Recopila una captura TOML v1.1, la guarda en la cola local y,
si se configura un servidor, la envía mediante SCP. Se eligió SCP porque OpenSSH
está disponible en ambos sistemas; no requiere rsync en Windows.

El servidor Linux ejecuta `server/bin/spawn.sh`. Cada cinco segundos
revisa incoming, importa los archivos completos y vuelve a dormir. El recolector
no se conecta directamente a MariaDB.

## Configurar cada PC

Copiar `config.example.json` (Linux) o `windows/config.example.json` (Windows)
a una ubicación estable y editar servidor, usuario, rutas y etiqueta de laboratorio.
Las rutas de clave, known_hosts y salida deben ser absolutas para las tareas de
arranque. No colocar contraseñas en el JSON.

Linux:

```bash
python3 client/recopilar.py --config /etc/sglab/cliente.json
```

Windows:

```powershell
python C:\SGLAB\client\recopilar.py --config C:\ProgramData\SGLAB\cliente.json
```

También se pueden pasar opciones directamente, sin JSON:

```bash
python3 client/recopilar.py --laboratorio LAB01 --salida ./salida \
  --servidor 192.168.1.10 --usuario sglab_upload \
  --clave /ruta/id_ed25519 --known-hosts /ruta/known_hosts
```

La CLI prevalece sobre el JSON. Sin servidor se limita a generar el TOML local.
`--solo-enviar` procesa la cola pendiente sin recopilar ni generar otro UUID.
`--reintentos` (3) y `--espera` (10 segundos) controlan los intentos inmediatos.
No enviar dos procesos a la misma cola: el bloqueo evita ejecuciones simultáneas.

Se requiere `scp` y `ssh` del cliente OpenSSH en PATH, también para la cuenta que
use la tarea automática. Windows necesita además Windows PowerShell y los módulos
CIM, NetTCPIP, NetAdapter y Storage. Linux necesita iproute2 y util-linux (`ip`,
`lsblk`), además de `/proc` y `/sys`.

## Autenticación y permisos de recepción

Preparar una clave SSH por equipo y autorizar su clave pública para el usuario
receptor del servidor. La cuenta que ejecuta el recolector debe poder usarla sin
preguntas interactivas (agente SSH o una clave de servicio protegida por permisos).
Verificar la huella del servidor y preparar known_hosts para esa misma cuenta.
El script exige `StrictHostKeyChecking=yes` y `BatchMode=yes`: no acepta claves
de host desconocidas ni pide contraseñas mientras arranca la PC.

El receptor necesita SCP/SFTP, SSH y permiso para ejecutar `chmod` y `mv` en
incoming. No funciona con una cuenta limitada exclusivamente a internal-sftp.
El host remoto configurado debe ser un hostname o IPv4 y el directorio remoto
una ruta absoluta sin espacios. El servidor debe tener incoming creado previamente.
La ruta predeterminada es `/srv/sglab/incoming`; ajustarla con
`--directorio-remoto`, `directorio_remoto` en el JSON o el perfil para que coincida
con la carpeta de recepción real del servidor. Esta ruta pertenece al servidor,
no a la PC que ejecuta el recolector.

El usuario de carga y el del daemon pueden ser distintos, compartiendo un grupo.
Por ejemplo, con usuarios `sglab_upload` y `sglab` ya creados y un grupo compartido
`sglab-ingest`, preparar el servidor una vez:

```bash
sudo usermod -aG sglab-ingest sglab_upload
sudo usermod -aG sglab-ingest sglab
sudo install -d -m 0750 -o sglab -g sglab-ingest /srv/sglab
sudo install -d -m 2770 -o sglab -g sglab-ingest /srv/sglab/incoming
```

Crear previamente el grupo si no existe. Reiniciar el daemon y abrir una nueva
sesión SSH después de cambiar grupos. El bit setgid de incoming hace que los
archivos recibidos hereden el grupo; el emisor les asigna 0640 antes de publicarlos.
El usuario de carga no necesita pertenecer al grupo docker.

## Entrega, archivos pendientes e importación

1. Genera `SGLAB-<UUID>.toml` localmente con escritura temporal y renombrado.
2. Transfiere a `incoming/SGLAB-<UUID>.toml.part` mediante SCP.
3. Ajusta permisos y renombra por SSH a `.toml` al terminar.
4. Mueve la copia local a `salida/enviados/` solo cuando SSH confirma la publicación.
5. Spawn detecta el nombre final e importa en una transacción.

Si falla SCP o SSH, el archivo permanece pendiente con sus mismos bytes y UUID.
Los reintentos no crean otra captura. Si el servidor recibió el archivo pero se
perdió la confirmación, la deduplicación de spawn evita repetir la inserción.
**Entregado** significa publicado en incoming, no confirmado por la BD: revisar
processed/rejected y resultado.log en el servidor para conocer la importación.

El Asistente debe registrar el equipo previamente por serie o UUID SMBIOS y
asignarle laboratorio. La asignación oficial se obtiene de la BD; la etiqueta
laboratorio del cliente se conserva como dato reportado. Si no se logra identificar
el equipo, spawn conserva el archivo en rejected para resolverlo y reintentar.

## Ejecutar al arrancar en Linux

Copiar el recolector a `/opt/sglab/client/recopilar.py` y la configuración a
`/etc/sglab/cliente.json`. Ajustar las rutas de las plantillas si son otras.
Instalar una sola vez con permisos administrativos:

```bash
sudo cp client/systemd/sglab-* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sglab-recopilar.service
sudo systemctl enable --now sglab-enviar.timer
```

El servicio recopila una vez por arranque. El timer reenvía pendientes cada dos
minutos sin generar nuevas capturas. Ejecutan como root para leer DMI sin pedir
sudo cada vez. Para probar sin reiniciar: `sudo systemctl start sglab-recopilar`.
Ver resultados con `journalctl -u sglab-recopilar -u sglab-enviar`.
No hay reinicio automático del recolector: un fallo de red lo atiende el emisor.

## Ejecutar al arrancar en Windows

Usar Python y OpenSSH instalados para el sistema. Guardar configuración y claves
en `C:\ProgramData\SGLAB`, accesibles para SYSTEM y administradores.
Desde PowerShell como administrador, ejecutar una sola vez:

```powershell
.\client\windows\instalar-tareas.ps1 `
  -Python 'C:\Program Files\Python313\python.exe' `
  -Config 'C:\ProgramData\SGLAB\cliente.json'
```

Reemplazar Python por su ruta real. Crea `SGLAB-Recopilar` al arranque y
`SGLAB-EnviarPendientes` cada dos minutos, como SYSTEM, sin guardar una contraseña
de Windows. El known_hosts del usuario interactivo no sirve automáticamente para
SYSTEM: usar el archivo explícito de la configuración. Probar las tareas desde
el Programador de tareas y revisar LastTaskResult (0 indica éxito).

## Servidor y alcance de la captura

Configurar `spawn.sh` usando `server/systemd/sglab-spawn.service`;
ver `server/ingest/README.md`. No se activan servicios ni se configuran credenciales
SSH automáticamente al ejecutar el recolector.

La captura contiene identidad, hostname, SO, CPU, RAM, discos, red y periféricos.
Los datos que no se puedan leer se omiten y se registran en errores_lectura.
Sin privilegios puede faltar la serie/UUID; si faltan ambos, el servidor no podrá
asociar el equipo. Las tareas administrativas evitan pedir permisos en cada arranque.
Por defecto se prueba conectividad al puerto SSH del servidor; puede cambiarse
con `--probar-host` y `--probar-puerto`.

Se mantienen las limitaciones del contrato v1.1: espacio libre agregado por disco,
sin detalle de particiones; LVM/RAID puede impedir atribuirlo correctamente.
Ampliar la captura de sistemas de archivos queda pendiente. No se altera el estado
administrativo del equipo. Las copias enviadas se conservan localmente; definir
una política de retención según el espacio disponible.

### Discos Linux: Fedora y dual boot

Desde la versión del script **1.1.1**, se excluyen `zramN`, `ramN` y `loopN`
aunque `lsblk` los presente como `TYPE=disk`. Se conservan los discos reportados
por el sistema (NVMe, SATA y virtio en máquinas virtuales); las particiones,
LVM y dispositivos cifrados se recorren para encontrar sus montajes, sin contarlos
como discos independientes. El marcador `[SWAP]` no se trata como una ruta.

`zram` almacena datos comprimidos en memoria: no es un SSD adicional. El dual boot
no es la causa de esa detección. Referencias: [documentación de zram](https://docs.kernel.org/admin-guide/blockdev/zram.html)
y [lsblk](https://man7.org/linux/man-pages/man8/lsblk.8.html).

El espacio libre sigue correspondiendo a sistemas de archivos montados y legibles;
no representa necesariamente el espacio libre completo de Windows y Linux juntos.
Si un disco real no tiene montajes accesibles, se conserva en el inventario y se
informa la lectura no disponible. No se ocultan fallos reales para obtener cero
errores. El formato TOML continúa en **1.1**, compatible con `spawn.sh`.

Prueba de Fedora y pasos para repetirla: [PRUEBA-FEDORA.md](../docs/PRUEBA-FEDORA.md).

## Verificación

```bash
python3 -m unittest discover -s tests -v
```

Incluye Linux real, consultas Windows simuladas, transferencia parcial, fallo en
rename, reintentos, conservación de archivos y bloqueo de cola. La integración
MariaDB optativa se documenta en `server/ingest/README.md`. La tarea Windows y el
envío SSH requieren además una prueba en los equipos y servidor reales.

## Instalador unificado y configuración automática

`client/configurar.py` detecta Windows/Linux y permite ingresar servidor, usuario,
puerto, laboratorio y rutas una sola vez. No cambia el recolector para cada PC.
El perfil `client/perfiles/pruebas.json` ya contiene el servidor de pruebas
192.168.50.83, usuario facu, puerto 22 y carpeta /home/facu/-TD2_SGLAB/SGLAB/var/incoming. Se puede
reutilizar en varias PC; los argumentos de CLI prevalecen sobre el perfil.
Para producción crear otro perfil con el nombre DNS del servidor cuando exista.
Un nombre DNS estable evita cambiar las PC si luego cambia la IP.

El instalador copia el recolector y genera cliente.json en una carpeta protegida.
Si se omite `--clave`, genera una clave Ed25519 exclusiva para esa PC, sin
passphrase para permitir las tareas automáticas. La privada permanece en la PC.

En la primera conexión OpenSSH muestra la huella del servidor: compararla con
la que proporcione el administrador antes de aceptarla. Luego pide la contraseña
SSH del usuario receptor en la terminal (no la contraseña de la web).
El servidor Linux debe permitir autenticación SSH por contraseña y ejecutar comandos.
No se guarda la contraseña ni se pasa como argumento. No requiere sshpass.

El instalador agrega la pública a ~/.ssh/authorized_keys del usuario receptor,
evita duplicar esa clave y ajusta permisos: .ssh a 0700 y authorized_keys a 0600.
La configuración local `cliente.json` y los scripts de captura se preparan antes
de la conexión SSH. Después se comprueba el acceso por clave en modo no interactivo.
Solo si tiene éxito continúa con el registro de tareas. Si falla SSH, se conserva
la configuración y se puede generar una captura manual; el envío queda pendiente
hasta resolver la conexión. No crea incoming ni cambia sus permisos; el servidor
debe tener la recepción preparada previamente.

Windows, PowerShell como administrador:

```powershell
python C:\SGLAB\client\configurar.py `
  --perfil C:\SGLAB\client\perfiles\pruebas.json `
  --instalar
```

Linux, desde el repositorio del equipo cliente:

```bash
sudo python3 client/configurar.py \
  --perfil client/perfiles/pruebas.json \
  --instalar
```

Ejecutar desde una terminal interactiva para responder a OpenSSH. En Windows
Python y OpenSSH deben estar disponibles para todo el sistema; no usar el alias
de WindowsApps. En Linux instala en /opt/sglab-cliente; en Windows, en
C:\ProgramData\SGLAB. Las tareas recopilan en el próximo arranque y el timer
reintenta pendientes cada dos minutos.

Para autorizar una clave existente agregar `--clave /ruta/clave --autorizar-clave`.
Para usar una clave ya autorizada, indicar `--clave` y `--known-hosts`; sin
`--autorizar-clave` no se modifica el servidor ni se pide contraseña.
`--known-hosts` también permite proporcionar identidades verificadas previamente
en el flujo de primera conexión. Sin ese argumento, ese flujo guarda las huellas
aceptadas en el known_hosts de la instalación.

Sin `--instalar` prepara los archivos en ./sglab-cliente (o --destino) sin
registrar tareas; la autorización SSH se realiza igualmente si corresponde.
Si falla la conexión, los archivos preparados se conservan para diagnóstico y se
puede completar la instalación con `--reanudar`. El BAT de Windows ya utiliza
esa opción. También recupera instalaciones del configurador anterior que quedaron
solo con la clave SSH y known_hosts, antes de poder escribir el JSON.

Sin `--reanudar` no reemplaza una carpeta de instalación no vacía. Al reanudar se
conservan la configuración, las claves y los hosts conocidos; se actualizan los
scripts copiados y se vuelve a comprobar SSH y registrar las tareas. No cambia
automáticamente el servidor de una configuración existente ni elimina archivos
de carpetas desconocidas. Para cambiar IP, usuario, puerto o laboratorio, editar cliente.json
como administrador; no reinstalar ni editar recopilar.py. Un cambio de identidad
SSH del servidor requiere actualizar también known_hosts tras verificar la huella.
La autorización de la clave pública debe existir para el usuario receptor nuevo.

La dirección del servidor se aprovisiona con un perfil o se ingresa durante la
instalación: no se deduce automáticamente a partir de la red. En este despliegue
el laboratorio del cliente sigue siendo una etiqueta; la asignación oficial se
administra en la BD.

## Instalacion actual de Windows sin administrador

Copiar toda la carpeta client y hacer doble clic en `Instalar-SGLAB.bat`.
No solicita elevacion. Requiere Internet, WinGet y OpenSSH previamente instalado.
Instala Python para el usuario actual en `%LOCALAPPDATA%\Programs\Python\Python313`
y el cliente en `%LOCALAPPDATA%\SGLAB`. Pregunta los datos del servidor, autoriza
la clave por contrasena SSH y registra tareas con permisos limitados del usuario.

La captura automatica ocurre al iniciar sesion, con reenvios cada dos minutos
mientras la sesion este abierta. No se ejecuta antes del login. Las tareas tienen
un sufijo con el SID para separar usuarios. Las politicas de la institucion pueden
impedir instalar programas o registrar tareas incluso sin elevacion.

Para instalar solo Python, abrir `windows/instalar-python.ps1` con PowerShell.
El .bat ejecuta tanto la instalacion de Python como la configuracion del cliente.

El comando equivalente del configurador es `python configurar.py --instalar --por-usuario`.
El modo anterior con SYSTEM sigue disponible explicitamente sin `--por-usuario`,
usando una consola administrativa y Python instalado para todo el sistema.

### Si no aparece cliente.json o falla la instalación

La ruta del modo por usuario es **%LOCALAPPDATA%\SGLAB\cliente.json**. Ejecutar el
instalador con el mismo usuario que luego abrirá Recopilar-SGLAB.bat.
El instalador ahora muestra la etapa del error y guarda un registro en:

```text
%LOCALAPPDATA%\SGLAB-instalacion.log
```

Se puede pegar esa ruta en el Explorador de Windows y abrir el archivo de texto.
Revisar las líneas **ERROR en ...** y **No se completó la configuración**. La
consola queda abierta al terminar y el BAT conserva el código de error; no anuncia
éxito cuando falla el configurador. El registro queda fuera de la carpeta SGLAB
para no bloquear una instalación nueva por encontrarla no vacía.

Copiar la carpeta `client` actualizada y ejecutar Instalar-SGLAB.bat otra vez.
No borrar las claves ni la carpeta de instalación para reintentar. Las carpetas
desconocidas o configuraciones con rutas personalizadas requieren revisar el
mensaje concreto; no se reemplazan automáticamente.

Si el fallo ocurre antes de preparar el cliente (por ejemplo, falta Python u
OpenSSH, o Windows rechaza los permisos), todavía puede faltar el JSON. Si falla
SSH después de prepararlo, el JSON queda disponible pero la instalación de tareas
no se considera completada. Obtener el mensaje exacto del registro para resolver
la dependencia que falta. La versión actual sigue sin solicitar elevación.

La recuperación se verificó con pruebas de orquestación y fallos simulados en
Windows, además de las pruebas locales de autorización SSH. La ejecución completa
en el Windows afectado continúa pendiente.

## Ejecutar una captura con doble clic

Despues de instalar el cliente, hacer doble clic en `Recopilar-SGLAB.bat`.
El lanzador usa Python y cliente.json del usuario actual, ejecuta una captura y
el envio de pendientes, y deja la ventana abierta para leer el resultado.
No pide permisos administrativos. Se puede copiar solo este lanzador al Escritorio
porque utiliza las rutas de la instalacion, no archivos junto al .bat.

## Ventana provisional de captura manual

`Recopilar-SGLAB.bat` ahora abre `ventana.py` con Pythonw: muestra campos para
cedula (solo numeros) y laboratorio, y un boton Recopilar y enviar. El formulario
pasa esos valores al recolector para guardarlos en `meta.ci_reportada` y
`meta.codigo_laboratorio`. Muestra el resultado y mantiene la interfaz disponible
mientras trabaja. No cambia cliente.json ni autentica al usuario.

Las nuevas instalaciones copian ventana.py automaticamente. Si el cliente ya
estaba instalado, copiar `client/ventana.py` a `%LOCALAPPDATA%\SGLAB\client\`
y reemplazar el lanzador del Escritorio por la nueva version del .bat.
Las tareas automaticas siguen usando cliente.json sin mostrar formularios.
Una cedula inexistente en usuarios se conserva en el TOML/descripcion, pero el
importador deja registro.usuario_ci en NULL. El laboratorio oficial sigue siendo
el asignado al equipo en la BD.


## Diagnóstico de envío SSH/SCP

El cliente verifica por SSH que la carpeta remota exista y permita escritura y
acceso antes de enviar el `.part`. Luego transfiere por SCP y finalmente publica
el TOML por SSH mediante chmod/mv. Un error indica la etapa: **Verificación del
destino**, **Transferencia SCP** o **Publicación de la captura**.

Los mensajes distinguen huella desconocida/cambiada, autenticación rechazada,
clave local inválida, servidor/DNS/puerto inaccesible, permisos o carpeta de destino,
espacio/cuota y falta de SFTP. Los fallos desconocidos informan el código de salida.
Se clasifican firmas conocidas de OpenSSH; si el servidor devuelve otro idioma o
formato puede aparecer el diagnóstico genérico. No se vuelca stderr remoto ni los
argumentos, rutas sensibles o contenido de claves. No se desactiva la verificación
de huella ni se instala automáticamente una identidad nueva del servidor.

Se mantienen los reintentos configurados y los archivos pendientes. Solo después
de confirmar SCP y publicación se mueve la captura a `enviados`. El envío no
confirma que la ingesta haya aceptado el TOML; revisar `rejected` si no aparece en
la web. La comprobación de permisos es preventiva: ACL, cuotas u otros cambios
pueden hacer fallar la transferencia aunque esa comprobación haya sido correcta.

### Actualizar clientes ya instalados

El ZIP actualizado está en `var/distribucion/SGLAB-cliente-Windows.zip` del servidor.
Las PC que ya recibieron un ZIP anterior no se actualizan solas. Cerrar el cliente
y reemplazar únicamente `client/recopilar.py` de la instalación local
(`%LOCALAPPDATA%\SGLAB\client\recopilar.py`) por la versión del paquete nuevo.
Conservar `cliente.json`, claves SSH, known_hosts y las carpetas pendientes/enviados.
También se puede reanudar el instalador del paquete nuevo con la configuración
existente. No editar las claves para corregir un problema de permisos del servidor.

Pruebas sin conexiones reales:

```bash
python3 -m unittest discover -s tests -p test_envio_ssh.py -v
```

Comprueban clasificación, ocultamiento de datos remotos, fallo previo sin SCP,
publicación fallida conservando la captura y envío confirmado a `enviados`.
Queda pendiente una prueba con OpenSSH real en una PC Windows de UTU.
