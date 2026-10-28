# SGLAB

Sistema de inventario y diagnóstico de PC de laboratorio. Este proyecto reúne el
cliente Windows/Linux, la recepción de capturas TOML, la ingesta mediante Bash y
la infraestructura de la futura aplicación web PHP.

Esta copia trabaja como proyecto Docker **`sglab-copia`**, con la base actualizada conservada en el volumen externo `sglab_db_data`.
El despliegue anterior de `/home/facu/SGLAB` está desactivado. Toda la operación
activa y el desarrollo PHP se realizan desde `SGLAB-copia`.

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
  → server/incoming/
  → spawn.sh valida e identifica el equipo
  → MariaDB dentro de Docker
  → server/processed/ o server/rejected/, con resultado.log
```

**La recolección y la ingesta están implementadas. La web administrativa todavía
no:** actualmente muestra una página de prueba de Apache/PHP y conexión a MariaDB.
El equipo debe existir en la BD antes de importar una captura. Mientras no exista
la web, esa alta debe hacerse directamente en la BD con una cuenta autorizada.

## Estructura del proyecto

Se omiten archivos compilados de Python y el contenido de dependencias, respaldos
y colas. Las carpetas PHP marcadas como propuestas aún no existen.

```text
SGLAB-copia/
├── README.md                       # Guía general
├── compose.yaml                    # Servicios web/db, puertos, red y volumen
├── .env                            # Configuración y credenciales locales
├── .env.example                    # Plantilla de variables
├── .sglab-infra.done                # Marca usada por infra.sh
├── .venv/                          # Entorno Python del parser TOML del servidor
├── client/                         # Archivos que se llevan a las PC
│   ├── README.md                   # Instrucciones detalladas del cliente
│   ├── recopilar.py                # Captura técnica y envío de pendientes
│   ├── configurar.py               # Configuración, claves y tareas automáticas
│   ├── ventana.py                  # Formulario provisional: cédula/laboratorio
│   ├── Instalar-SGLAB.bat           # Instalación Windows con doble clic
│   ├── Recopilar-SGLAB.bat          # Abre el formulario con doble clic
│   ├── config.example.json         # Ejemplo de configuración del cliente
│   ├── perfiles/
│   │   └── pruebas.json            # Datos comunes del servidor de pruebas
│   ├── windows/
│   │   ├── instalar-cliente.ps1     # Coordina Python y configuración por usuario
│   │   ├── instalar-python.ps1      # Python 3.13 por usuario mediante WinGet
│   │   ├── instalar-tareas.ps1      # Tareas por usuario o SYSTEM explícito
│   │   └── config.example.json     # Ejemplo de rutas para Windows
│   └── systemd/                    # Plantillas de captura/reenvío para Linux
├── database/
│   ├── init/
│   │   ├── sglab.sql               # Esquema para una instalación nueva
│   │   └── zz-users.sh             # Cuentas técnicas y permisos MariaDB
│   ├── migrations/
│   │   ├── README.md               # Alcance y condiciones de las migraciones
│   │   ├── 001_modelo_inicial.sql   # Evolución del esquema antiguo de 5 tablas
│   │   └── 002_rol_administrador.sql # Agrega ADMINISTRADOR al ENUM de usuarios
│   └── backups/                    # Respaldos locales; pueden contener datos
├── doc/
│   ├── SERVIDOR.md                 # Rutas, puertos y operación de este servidor
│   ├── MER-SGLAB.drawio            # MER editable
│   └── MER-SGLAB.svg               # Vista del MER
├── server/
│   ├── bin/
│   │   ├── infra.sh                # Administración de infraestructura Docker
│   │   └── spawn.sh                # Único daemon e importador de TOML
│   ├── incoming/                   # Recepción de archivos finales y .part
│   ├── processing/                 # Trabajos tomados por el daemon
│   ├── processed/                  # Capturas importadas o ya procesadas
│   ├── rejected/                   # Capturas rechazadas; revisar resultado.log
│   ├── .spawn.lock                 # Bloqueo para una sola instancia de ingesta
│   ├── ingest/
│   │   ├── README.md               # Contrato operativo y límites de ingesta
│   │   └── requirements-bash.txt    # yq: proporciona el comando tomlq
│   ├── systemd/
│   │   └── sglab-spawn.service     # Servicio instalado y adaptado a este host
│   ├── web/
│   │   ├── Dockerfile              # Imagen PHP 8.3 + Apache + drivers MariaDB
│   │   ├── 000-default.conf        # VirtualHost: DocumentRoot en public/
│   │   └── app/                    # Aquí va toda la aplicación PHP
│   │       └── public/
│   │           └── index.php       # Página de prueba actual / entrada pública
│   ├── provision.sh                # Copia antigua con rutas pendientes de corregir
│   └── setup/                      # Scripts históricos de aprovisionamiento
│       ├── README.md
│       ├── OBJETIVO.md
│       ├── provision.sh
│       ├── ejemplo_provision.sh
│       ├── memoria.txt
│       └── resources/              # Instalación Docker/LAMP, SSH y utilidades
└── tests/
    └── test_configurar_ssh.py       # Pruebas locales de autorización de claves
```

`client` se ejecuta en las PC; `server` recibe y procesa; `database` define la BD;
`doc` describe el proyecto; `tests` verifica parte del configurador. Los scripts
históricos de `setup` no forman parte del circuito de ingesta activo y no se han
validado como instalador completo. `server/provision.sh` sigue teniendo referencias
a `server/resources`, carpeta inexistente; no usar esa copia para desplegar.

## Cliente Python y primera instalación en Windows

`recopilar.py` funciona con Python 3.9 o posterior, sin dependencias Python externas.
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

La cola está dentro del proyecto. Las rutas antiguas `/srv/sglab/incoming`,
`processing`, `processed` y `rejected` son enlaces de compatibilidad hacia las
carpetas de `server`; no contienen otra copia de los datos.

## Base de datos y MER

El esquema actual tiene siete tablas:

| Tabla | Responsabilidad |
|---|---|
| `usuarios` | Personas con CI, datos, hash de contraseña y rol. |
| `laboratorio` | Laboratorios disponibles. |
| `equipo` | Identidad de cada PC, asignación y estado administrativo. |
| `registro` | Captura histórica, equipo, usuario opcional, fecha, UUID/hash y diagnóstico. |
| `comentario` | Comentario de un usuario sobre un equipo. |
| `registro_disco` | Discos físicos observados por captura. |
| `registro_sistema_archivos` | Modelo para volúmenes/sistemas de archivos; pendiente de captura. |

Roles: `ALUMNO`, `DOCENTE`, `ASISTENTE`, `ADMINISTRADOR`. El rol administrador se
agregó tanto al SQL inicial como a la BD original activa durante el trabajo, con
respaldo de usuarios. La BD independiente de esta copia se creó posteriormente
con el esquema actualizado. Los permisos de los roles web aún deben implementarse
en PHP; un valor ENUM no implementa autorización.

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

Ver [MER editable](doc/MER-SGLAB.drawio), [MER SVG](doc/MER-SGLAB.svg) y
[condiciones de migración](database/migrations/README.md). Los SQL de init se
aplican solo al crear un volumen vacío: recrear contenedores no migra una BD
existente. No aplicar 001 otra vez sobre el esquema actual de siete tablas.

## Dónde desarrollar la aplicación PHP

**Toda la app va en `server/web/app/`.** Docker copia su contenido a
`/var/www/html/`; Apache publica solamente `/var/www/html/public`.

Organización propuesta para desarrollar, todavía no creada:

```text
server/web/app/
├── public/
│   ├── index.php       # Entrada/rutas públicas
│   └── assets/         # CSS, JavaScript e imágenes públicas
├── src/
│   ├── Controllers/    # Solicitudes y acciones
│   ├── Models/         # Acceso a BD con PDO
│   ├── Services/       # Reglas de negocio
│   └── Middleware/     # Sesión y permisos
├── views/              # Plantillas HTML/PHP
└── config/             # Configuración; credenciales desde variables de entorno
```

Los módulos pendientes son login/logout, permisos, usuarios, laboratorios,
registro/asignación de equipos, capturas y comentarios. El frontend consulta al
backend PHP y el backend accede a MariaDB. Las PC recolectoras no se conectan a
la BD directamente.

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
| Proyecto Compose | `sglab-copia` |
| Directorio | `/home/facu/SGLAB-copia` |
| Web | `http://192.168.50.83:8080` |
| MariaDB desde el host | `127.0.0.1:3306` |
| MariaDB entre contenedores | `db:3306`, base `sglab` |
| Volumen de datos | `sglab_db_data` |
| SSH de pruebas | `facu@192.168.50.83`, puerto 22 |
| Recepción | `/home/facu/SGLAB-copia/server/incoming` |
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

Detalles adicionales: [SERVIDOR.md](doc/SERVIDOR.md) e
[instrucciones de ingesta](server/ingest/README.md).

## Verificaciones realizadas y pendientes

Verificado durante este trabajo:

- Sintaxis Python y Bash; unidad systemd y servicio activo.
- Recolección Linux real y captura representativa de Windows insertadas en MariaDB
  temporal con permisos reales de la cuenta de ingesta.
- Daemon permanente: inserción de captura/disco y deduplicación en la BD de la copia.
  Los datos sintéticos de prueba se retiraron después.
- Página PHP conectada a MariaDB. El despliegue original fue desactivado después.
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

La carpeta tests no contiene una suite completa de integración MariaDB; las pruebas
de integración descritas fueron comprobaciones ejecutadas durante el trabajo.

Próximos pasos:

1. Probar una instalación Windows completa y verificar su registro en la BD.
2. Implementar la aplicación PHP de administración y consulta.
3. Definir cómo se asocia la identidad de Windows o la sesión web con la CI.
4. Decidir más adelante el modo con administrador y ejecución anterior al login.
5. Ampliar el contrato para sistemas de archivos y definir retención de capturas.

## Centralización definitiva en SGLAB-copia

Los contenedores originales sglab-web-1 y sglab-db-1 se retiraron. Solo se usan
sglab-copia-web-1 y sglab-copia-db-1, definidos en este compose.yaml. El bind mount
de inicialización y el contexto de construcción PHP pertenecen a esta carpeta.
El daemon tampoco usa el Compose de /home/facu/SGLAB.

El volumen externo `sglab_db_data` conserva su nombre histórico para reutilizar
los datos sin copiarlos ni reinicializarlos; no depende de archivos en SGLAB.
No eliminar ese volumen. Compose lo declara external para no borrarlo con down -v.
Se creó un respaldo previo en database/backups. El volumen antiguo de pruebas
sglab-copia_db_data queda sin conectar y no se usa como base activa.

En otro servidor es necesario crear/restaurar el volumen externo antes de ejecutar
Compose. No levantar simultáneamente el proyecto antiguo contra el mismo volumen.
