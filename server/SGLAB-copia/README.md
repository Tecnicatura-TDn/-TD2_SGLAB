# SGLAB

Sistema de inventario y diagnóstico de PC de laboratorio. Este proyecto reúne el
cliente Windows/Linux, la recepción de capturas TOML, la ingesta mediante Bash y
la aplicación web PHP de acceso e inventario.

Esta copia trabaja como proyecto Docker **`sglab`**, con la base actualizada conservada en el volumen externo `sglab_db_data`.

## Funcionamiento previsto y estado actual

El administrador inicia sesión en la web, crea laboratorios, registra PC por
número de serie o UUID SMBIOS y las asigna a un laboratorio. Cada PC genera
capturas técnicas; el servidor las guarda como historial del equipo.

```text
Administrador → Web PHP → Alta de laboratorio y equipos en MariaDB

PC Windows/Linux
  → recopilar.py genera SGLAB-<UUID>.toml
  → SCP sube el archivo como .toml.part
  → SSH lo publica como .toml
  → var/incoming/
  → spawn.sh valida e identifica el equipo
  → MariaDB dentro de Docker
  → var/processed/ o var/rejected/, con resultado.log
```

**La recolección, la ingesta y la primera versión web están implementadas.**
La web incluye login, sesiones, roles de administración/consulta, laboratorios,
alta/edición de PC, filtros y últimas capturas. El equipo debe existir en la BD
antes de importar una captura; ahora puede registrarse desde la web.

Para crear el primer administrador: `docker compose exec web php bin/crear-admin.php`.
No hay credenciales predeterminadas. Ver [la guía de la web](docs/WEB.md).
La dirección actual es **https://192.168.50.83**. Para acceder sin advertencias
hay que instalar el certificado público local en Windows: [guía HTTPS](docs/HTTPS.md).
La interfaz toma el diseño de `docs/views.zip` y `docs/public.zip`, con el logo,
colores y recursos originales: [vistas y adaptación](docs/VISTAS.md).
El trabajo restante, contrastado con el PDF y las pruebas reales pendientes,
se detalla en [PENDIENTES.md](docs/PENDIENTES.md).

## Estructura del proyecto

Se omiten archivos compilados de Python y el contenido de dependencias, respaldos
y colas. La estructura PHP implementada se describe en docs/WEB.md.

```text
SGLAB/
├── README.md
├── compose.yaml                 # Proyecto Docker sglab; volumen externo sglab_db_data
├── .env                         # Credenciales y puertos locales
├── .env.example                 # Plantilla
├── .venv/                       # Parser TOML del servidor (no versionar)
├── client/                      # Recolector, configurador, ventana y lanzadores
│   ├── recopilar.py
│   ├── configurar.py
│   ├── ventana.py
│   ├── Instalar-SGLAB.bat
│   ├── Recopilar-SGLAB.bat
│   ├── perfiles/                # Configuración compartida del servidor
│   ├── windows/                 # Instaladores PowerShell
│   └── systemd/                 # Plantillas del cliente Linux
├── server/
│   ├── bin/spawn.sh             # Única ingesta y daemon
│   ├── ingest/                  # Dependencias y documentación
│   ├── systemd/                 # Servicio del servidor
│   └── web/                     # Apache, Dockerfile y app PHP en app/
├── infra/
│   ├── infra.sh                 # Administración Docker
│   ├── configurar-https.py      # CA local, certificado por IP y variables TLS
│   └── provisioning/            # Aprovisionador y resources/ unificados
├── database/
│   ├── init/                    # SQL inicial y cuentas técnicas
│   └── migrations/              # Evolución del esquema
├── var/                         # Datos de ejecución, no código
│   ├── incoming/
│   ├── processing/
│   ├── processed/
│   ├── rejected/
│   ├── backups/
│   ├── pki/                     # CA y clave privada; solo servidor
│   ├── tls/                     # Certificado y clave del servidor; montaje de Apache
│   └── certificados/            # CA pública para instalar en las PC
├── docs/                        # MER y guía del servidor
└── tests/                       # SSH, HTTPS, autenticación, permisos e ingesta
```

`client` se ejecuta en las PC; `server` procesa capturas y aloja el código PHP;
`infra` administra el entorno; `database` define el esquema; `var` contiene datos
de ejecución y respaldos; `docs` documenta el sistema. Los aprovisionadores
idénticos se unificaron en infra/provisioning. Se conservó el archivo de estado
alternativo como memoria-servidor-anterior.txt. El aprovisionamiento histórico
no se ejecutó ni se validó como instalador completo.

## Cliente Python y primera instalación en Windows

`recopilar.py` funciona con Python 3.9 o posterior, sin dependencias Python externas.
La versión 1.1.1 corrige la detección Linux de zram/discos RAM/loop y el marcador
swap de lsblk, conservando el formato TOML 1.1. Ver [la prueba Fedora](docs/PRUEBA-FEDORA.md).
Consulta identidad del equipo, SO, CPU, RAM, discos, red y periféricos mediante
herramientas del sistema. En Windows usa PowerShell/CIM. Las lecturas no disponibles
se registran en `diagnostico.errores_lectura`.

Para esta primera versión se eligió **instalar sin elevación de administrador**:

1. Copiar **toda la carpeta `client`** a la PC Windows.
2. Hacer doble clic en `Instalar-SGLAB.bat`.
3. El asistente instala Python 3.13 para el usuario actual con WinGet.
4. Ingresar servidor, usuario SSH, puerto, carpeta remota y laboratorio.
5. Verificar la huella SSH del servidor y escribir la contraseña SSH inicial.
6. El configurador autoriza la clave pública, prueba la conexión y registra tareas.

Si la instalación falla, el detalle queda en `%LOCALAPPDATA%\SGLAB-instalacion.log`.
El instalador actualizado permite reintentar conservando la configuración y las
claves existentes. Ver [recuperación de instalación](client/README.md#si-no-aparece-clientejson-o-falla-la-instalación).

Se necesita Internet, WinGet y OpenSSH instalado previamente (`ssh`, `scp` y
`ssh-keygen`). El instalador actual no instala componentes de Windows que requieran
elevación. Las políticas de las PC de la institución pueden limitar estas acciones.

Ubicaciones en la PC:

```text
%LOCALAPPDATA%\Programs\Python\Python313\   # Python por usuario
%LOCALAPPDATA%\SGLAB\
├── cliente.json                          # Servidor, rutas, etiqueta, CI, etc.
├── id_ed25519                            # Clave privada: permanece en esta PC
├── id_ed25519.pub                        # Pública, si se generó una clave nueva
├── known_hosts                          # Identidad verificada del servidor
├── client/
│   ├── recopilar.py
│   ├── ventana.py
│   └── windows/instalar-tareas.ps1
└── pendientes/
    ├── SGLAB-<UUID>.toml                 # Capturas aún no entregadas
    └── enviados/                        # Copias de capturas entregadas por SSH
```

El `.bat` es un lanzador, no un ejecutable autónomo: usa Python instalado.
`Recopilar-SGLAB.bat` se puede copiar solo al Escritorio después de instalar el
cliente, porque utiliza las rutas de la instalación. `Instalar-SGLAB.bat`, en
cambio, necesita los demás archivos de `client` junto a él.

### Claves SSH

Sin `--clave`, `configurar.py` genera una Ed25519 por PC. Abre una primera conexión
SSH con contraseña y agrega **solo la pública** al `~/.ssh/authorized_keys` del
usuario receptor, evitando repetirla. Comprueba después el acceso por clave.
La contraseña se introduce en la terminal de OpenSSH y no se guarda; la privada
no se envía al servidor. Verificar la huella antes de aceptar la primera conexión.

El receptor debe permitir inicialmente autenticación SSH por contraseña y ejecutar
comandos. La carpeta incoming debe estar preparada: el configurador no la crea.
La contraseña SSH del receptor es independiente de las futuras credenciales web.

Se puede reutilizar una clave existente con `--clave`; agregar `--autorizar-clave`
si hay que autorizarla por contraseña. Para una clave ya autorizada, usar `--clave`
y `--known-hosts`. El instalador conserva los archivos si falla; revisar una
instalación incompleta antes de repetirla, porque no sobrescribe destinos no vacíos.

### Formulario provisional y automatización

`Recopilar-SGLAB.bat` abre `ventana.py` mediante `pythonw.exe`. Pide:

- Cédula: números sin puntos ni guion. Se valida formato/rango, no identidad ni
  dígito verificador.
- Laboratorio: etiqueta de entre 1 y 20 caracteres.

El botón **Recopilar y enviar** pasa los valores a `recopilar.py`, que los guarda
en `meta.ci_reportada` y `meta.codigo_laboratorio`. No cambia permanentemente
`cliente.json`. La ventana muestra el resultado de la ejecución.

Las tareas automáticas **no abren el formulario**: usan `cliente.json`. En el modo
actual funcionan al iniciar sesión del usuario y reenvían pendientes cada dos
minutos mientras su sesión está abierta. La configuración inicial usa CI 0 para
estas capturas automáticas; no se deduce todavía la identidad de Windows.

Se dejó disponible un modo administrativo explícito, pero no es el utilizado por
el `.bat` actual: permite tareas SYSTEM al arrancar, con Python instalado para
todo el sistema. La captura anterior al login y su asociación con quien inicia
sesión quedan pendientes de definir. Nunca se capturan contraseñas de Windows.

## Ingesta y almacenamiento

**`server/bin/spawn.sh` es la única implementación de ingesta.** Se eliminaron
`spawn.py`, el validador Python separado, `procesar_toml.sh` y las dependencias
exclusivas de esa alternativa. La validación que necesita la ingesta está en Bash
con `jq`; el parser `tomlq` del paquete yq sí requiere Python en el servidor.

El daemon revisa la cola cada cinco segundos. Toma archivos finales `.toml`,
valida sus campos e inserta la captura y sus discos en una misma transacción.
Usa UUID y SHA-256 para reconocer reenvíos iguales (`YA_PROCESADO`) y rechazar
un UUID reutilizado con contenido diferente. El bloqueo `.spawn.lock` evita
consumidores simultáneos sobre la misma cola.

Cada trabajo conserva el archivo y `resultado.log`. Los fallos de validación,
identidad, Docker o BD terminan en `rejected`. Tras resolver la causa, devolver
el TOML a incoming. Los trabajos interrumpidos en processing se recuperan al
arrancar el daemon. El límite es 1 MiB por TOML y 65535 bytes de JSON de captura.

**Entregado al servidor no equivale a importado en la BD:** el cliente confirma
SCP y publicación por SSH; el resultado de la ingesta se consulta en el servidor.
Los pendientes locales conservan bytes y UUID entre reintentos.

La cola está dentro de var/ en el proyecto. Las rutas antiguas `/srv/sglab/incoming`,
`processing`, `processed` y `rejected` son enlaces de compatibilidad hacia las
carpetas de `var`; no contienen otra copia de los datos.

## Base de datos y MER

El esquema actual tiene nueve tablas:

| Tabla | Responsabilidad |
|---|---|
| `usuarios` | Personas con CI, datos, hash de contraseña y rol. |
| `laboratorio` | Laboratorios disponibles. |
| `equipo` | Identidad de cada PC, asignación y estado administrativo. |
| `registro` | Captura histórica, equipo, usuario opcional, fecha, UUID/hash y diagnóstico. |
| `comentario` | Comentario de un alumno o personal autorizado sobre un equipo. |
| `comentario_laboratorio` | Comentarios de docentes y personal sobre una sala. |
| `asignacion_docente` | Laboratorio del docente, con inicio y fin opcional. |
| `registro_disco` | Discos físicos observados por captura. |
| `registro_sistema_archivos` | Modelo para volúmenes/sistemas de archivos; pendiente de captura. |

Roles: `ALUMNO`, `DOCENTE`, `ASISTENTE`, `ADMINISTRADOR`. El rol administrador se
agregó tanto al SQL inicial como a la BD original activa durante el trabajo, con
respaldo de usuarios. La BD independiente de esta copia se creó posteriormente
con el esquema actualizado. La web permite administración a ADMINISTRADOR;
ASISTENTE es el administrador: gestiona inventario, usuarios de todos los roles y asignaciones.
DOCENTE consulta y comenta su laboratorio vigente; ALUMNO solo el estado y
comentarios de la PC detectada por IP. Ver docs/WEB.md para las condiciones.

Relaciones principales:

- Un laboratorio puede tener varias PC; la BD también admite PC sin laboratorio.
- Cada registro pertenece a una PC; una PC puede tener muchas capturas.
- Un usuario puede asociarse a varias capturas; una captura puede no tener usuario.
- Cada comentario tiene un autor y un equipo; ambos pueden tener muchos comentarios.
- Una captura puede tener varios discos y sistemas de archivos.
- Un volumen puede asociarse a un disco de la misma captura mediante FK compuesta.

El laboratorio oficial se obtiene de `equipo.id_laboratorio`. La etiqueta enviada
por el cliente se conserva en el documento de captura, sin reasignar el equipo.
Si la CI reportada no existe en usuarios, permanece en el documento, pero
`registro.usuario_ci` queda NULL. El cliente no crea usuarios ni equipos.

`registro.estado` indica errores de lectura (`OK`/`ERROR`), mientras
`equipo.estado_administrativo` indica OPERATIVA, EN_REPARACION o FUERA_DE_SERVICIO.
La ingesta no cambia el estado administrativo. La IP se guarda por captura.

El JSON completo se conserva en `registro.descripcion`, incluidos periféricos,
red y espacio libre que no se distribuyen en columnas propias. El contrato actual
no distingue sistemas de archivos y no se llena `registro_sistema_archivos`.

Ver [MER editable](docs/MER-SGLAB.drawio), [MER SVG](docs/MER-SGLAB.svg) y
[condiciones de migración](database/migrations/README.md). Los SQL de init se
aplican solo al crear un volumen vacío: recrear contenedores no migra una BD
existente. No aplicar 001 otra vez sobre el esquema actual de nueve tablas.

## Dónde desarrollar la aplicación PHP

**Toda la app va en `server/web/app/`.** Docker copia su contenido a
`/var/www/html/`; Apache publica solamente `/var/www/html/public`.

Estructura implementada:

```text
server/web/app/
├── public/index.php     # Entrada pública y control de solicitudes
├── public/assets/       # Estilos
├── src/                 # PDO, Auth e Inventory
├── views/               # Pantallas PHP/HTML
└── bin/crear-admin.php  # Alta inicial por terminal
```

Login/logout, sesiones, roles, laboratorios, PC y consulta de capturas están
implementados. Están implementados usuarios, asignaciones docentes y comentarios por alcance.
Quedan pendientes importaciones masivas, gráficos y exportaciones. El backend accede a MariaDB con PDO.
Las PC recolectoras no se conectan a la BD directamente.

En el contenedor web, usar las variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`
y `DB_PASSWORD`, ya suministradas por Compose. **El host de BD es `db` y el puerto
3306**, usando la red interna de Compose. La cuenta de aplicación tiene permisos de
lectura y de administración de usuarios, laboratorios, equipos y comentarios;
la ingesta utiliza otra cuenta con permisos de inserción de capturas.

Los archivos PHP se copian al construir la imagen; no hay un bind mount de app.
Después de editar la aplicación:

```bash
docker compose up -d --build web
```

## Servidor preparado en este entorno

| Elemento | Valor actual |
|---|---|
| Proyecto Compose | `sglab` |
| Directorio | `/home/facu/-TD2_SGLAB/SGLAB` |
| Web | `https://192.168.50.83` (el acceso HTTP anterior redirige aquí) |
| MariaDB desde el host | `127.0.0.1:3306` |
| MariaDB entre contenedores | `db:3306`, base `sglab` |
| Volumen de datos | `sglab_db_data` |
| SSH de pruebas | `facu@192.168.50.83`, puerto 22 |
| Recepción | `/home/facu/-TD2_SGLAB/SGLAB/var/incoming` |
| Servicio permanente | `sglab-spawn.service`, habilitado y activo al configurarlo |
| Usuario del daemon | `facu`, grupos suplementarios docker y sglab-ingest |

La IP es la observada, no una dirección garantizada por el proyecto. Si cambia,
actualizar clientes/perfil o usar DNS estable. El lanzador sin perfil pregunta
los datos: no lee automáticamente pruebas.json. La copia reutiliza el volumen de la BD original actualizado; conserva las altas
y los datos existentes. No hay un segundo despliegue activo.

Se instalaron dependencias del servidor en `.venv` y se configuraron permisos:
incoming 2770 con grupo sglab-ingest, y carpetas de trabajo/resultados 0700.
La cuenta de carga también necesita acceso a las carpetas superiores. La unidad
systemd contiene rutas y usuario propios de este host; adaptarlos si se traslada.

Los valores de Compose se definen en `.env`, incluyendo `COMPOSE_PROJECT_NAME`,
`APP_PORT`, `DB_BIND_PORT` y credenciales de cuentas técnicas. No publicar `.env`,
claves privadas, respaldos ni capturas con datos personales.

Comandos desde la raíz:

```bash
docker compose ps
docker compose up -d
sudo systemctl status sglab-spawn
sudo journalctl -u sglab-spawn -n 50 --no-pager
sudo systemctl restart sglab-spawn
```

Detalles adicionales: [SERVIDOR.md](docs/SERVIDOR.md) e
[instrucciones de ingesta](server/ingest/README.md).

## Verificaciones realizadas y pendientes

Verificado durante este trabajo:

- Sintaxis Python y Bash; unidad systemd y servicio activo.
- Recolección Linux real y captura representativa de Windows insertadas en MariaDB
  temporal con permisos reales de la cuenta de ingesta.
- Daemon permanente: inserción de captura/disco y deduplicación en la BD de la copia.
  Los datos sintéticos de prueba se retiraron después.
- Web PHP con login e inventario; integración HTTP y BD real comprobada.
- Dos pruebas locales del alta de claves: permisos, no duplicación y fallo de acceso.
- Validación del formulario y presencia de CI/laboratorio en el TOML.

El recolector fue probado por el usuario en PC Windows de la UTU. **Todavía falta
probar allí el conjunto nuevo de instalación, ventana, SSH, tareas y envío**.
No se ejecutaron las interfaces Windows/PowerShell en este entorno Linux.

Pruebas locales disponibles:

```bash
python3 -m unittest discover -s tests -v
bash -n server/bin/spawn.sh
```

La integración web/BD/daemon está en tests/test_web_integration.py. Se activa con
SGLAB_TEST_WEB=1 y retira los datos sintéticos. Ver docs/WEB.md para condiciones.

Próximos pasos:

1. Probar una instalación Windows completa y verificar su registro en la BD.
2. Completar importaciones masivas, gráficos y exportaciones de la aplicación PHP.
3. Definir cómo se asocia la identidad de Windows o la sesión web con la CI.
4. Decidir más adelante el modo con administrador y ejecución anterior al login.
5. Ampliar el contrato para sistemas de archivos y definir retención de capturas.

## Ubicación del repositorio

El proyecto está en `/home/facu/-TD2_SGLAB/SGLAB`, directamente en la raíz del
repositorio. El proyecto Compose activo se llama `sglab`. La BD conserva el
volumen externo `sglab_db_data`; las carpetas antiguas no se necesitan.

El cambio de carpeta requiere actualizar cliente.json en las PC ya configuradas:
`directorio_remoto` debe ser `/home/facu/-TD2_SGLAB/SGLAB/var/incoming`.
Los perfiles y valores predeterminados del cliente ya incluyen la ruta nueva.
Los scripts usan rutas relativas a su ubicación, salvo las rutas del servicio y
los perfiles específicos de este servidor. No mover .venv entre máquinas: recrearlo.

## Web de administración

Ver [WEB.md](docs/WEB.md) para crear el primer administrador, permisos,
funcionalidades implementadas, sesiones y pruebas de integración.

## Permisos actualizados

La migración 003 agrega bajas lógicas, asignaciones docentes y comentarios de
laboratorio. El asistente tiene administración del inventario y de cuentas de
usuarios de todos los roles; administrador y asistente son el mismo actor. La PC del
alumno se identifica por IP y captura reciente (ocho horas por defecto), sin
asignación manual. El docente solo accede al laboratorio que tiene vigente.
Detalles, limitaciones de red y pruebas: [WEB.md](docs/WEB.md).
El MER se actualiza desde la BD activa con `python3 infra/generar-mer.py`.

## Login por rol y Google Authenticator

Administrador: cédula/contraseña y código TOTP; la primera vez configura el QR.
Docente: acceso local directo. Asistente: mismo acceso con MFA que el administrador. Estudiante: Continuar con GitHub y email
principal verificado coincidente. GitHub está preparado pero deshabilitado hasta
registrar la OAuth App y configurar sus credenciales en .env.
Guía, recuperación de MFA y respaldo de su clave: [AUTENTICACION.md](docs/AUTENTICACION.md).

## Sistema de referencia del profesor

El análisis de roles y diferencias de SGLAB-main.zip está en
[REFERENCIA_PROFESOR.md](docs/REFERENCIA_PROFESOR.md). La revisión es estática:
no se ejecutó ni reemplazó nuestra aplicación con el contenido del ZIP.

## Nombre definitivo del administrador

En el ejemplo del profesor, Administrador corresponde a nuestro ASISTENTE.
Los perfiles son ASISTENTE (administración y MFA), DOCENTE y ALUMNO. Las cuentas
antiguas ADMINISTRADOR siguen funcionando como alias de ASISTENTE y conservan
sus credenciales; la web no ofrece ese alias como un perfil adicional.

## Logs Docker y acciones de infraestructura

Se conservan los scripts y el servicio del commit `0a015f7`. El registro de acciones
está integrado en `infra/infra.sh`; la ruta anterior `server/bin/infra.sh` sigue
funcionando. Ver [LOGS-DOCKER.md](docs/LOGS-DOCKER.md).
