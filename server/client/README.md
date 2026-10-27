# Recolector de PC y entrega al servidor

`recopilar.py` funciona en Linux y Windows con Python 3.9 o posterior, sin paquetes
Python adicionales. Recopila una captura TOML v1.1, la guarda en la cola local y,
si se configura un servidor, la envía mediante SCP. Se eligió SCP porque OpenSSH
está disponible en ambos sistemas; no requiere rsync en Windows.

El servidor Linux ejecuta una de las alternativas de spawn. Cada cinco segundos
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

Configurar una sola alternativa usando `server/systemd/sglab-spawn.service`;
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
192.168.50.38, usuario facu, puerto 22 y carpeta /srv/sglab/incoming. Se puede
reutilizar en varias PC; los argumentos de CLI prevalecen sobre el perfil.
Para producción crear otro perfil con el nombre DNS del servidor cuando exista.
Un nombre DNS estable evita cambiar las PC si luego cambia la IP.

El instalador copia recolector, clave privada y known_hosts a una carpeta
protegida y genera cliente.json. No genera ni autoriza claves nuevas en el servidor
ni acepta una huella de host sin verificar. Para la instalación de arranque usar
una clave de servicio ya autorizada, sin passphrase: SYSTEM/root no reutilizan el
agente SSH ni el perfil interactivo. Cada PC debe tener su propia clave privada.
No compartir claves privadas mediante perfiles JSON ni Git.

Preparar primero los archivos de clave y known_hosts existentes. Para identificar
las claves de Windows: `Get-ChildItem "$env:USERPROFILE\.ssh"`. No copiar el archivo
`.pub` como clave privada. Si la clave existente requiere passphrase, preparar una
clave de servicio por PC y autorizar su pública antes de instalar.

Windows, PowerShell como administrador, desde una copia completa de client:

```powershell
python C:\SGLAB\client\configurar.py `
  --perfil C:\SGLAB\client\perfiles\pruebas.json `
  --clave "$env:USERPROFILE\.ssh\id_ed25519" `
  --known-hosts "$env:USERPROFILE\.ssh\known_hosts" `
  --instalar
```

Reemplazar id_ed25519 por el nombre real de la clave autorizada. Instala en
C:\ProgramData\SGLAB y registra las dos tareas Windows. Usa RemoteSigned únicamente
en el proceso PowerShell de instalación; no cambia la política global. Python debe
ser accesible para SYSTEM: se rechazan los alias de WindowsApps.

Linux, desde el repositorio del equipo cliente:

```bash
sudo python3 client/configurar.py \
  --perfil client/perfiles/pruebas.json \
  --clave /home/facu/.ssh/id_ed25519 \
  --known-hosts /home/facu/.ssh/known_hosts \
  --instalar
```

Instala en /opt/sglab-cliente y registra systemd. No ejecutar esto en el servidor
salvo que también se quiera recopilar ese equipo. Las tareas quedan habilitadas
para el próximo arranque; el timer de pendientes se activa inmediatamente.
Sin `--instalar`, solo prepara archivos en ./sglab-cliente (o --destino) y no
registra servicios. Sin perfil, pregunta los valores que falten.

Por seguridad no reemplaza una carpeta de instalación no vacía. Si ya se configuró
C:\ProgramData\SGLAB manualmente, revisar esa configuración antes de instalar de
nuevo. Para cambiar IP, usuario, puerto o laboratorio después, editar cliente.json
como administrador; no reinstalar ni editar recopilar.py. Un cambio de identidad
SSH del servidor requiere actualizar también known_hosts tras verificar la huella.
La autorización de la clave pública debe existir para el usuario receptor nuevo.

La dirección del servidor se aprovisiona con un perfil o se ingresa durante la
instalación: no se deduce automáticamente a partir de la red. En este despliegue
el laboratorio del cliente sigue siendo una etiqueta; la asignación oficial se
administra en la BD.
