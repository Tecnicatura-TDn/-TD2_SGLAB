# Web PHP: login e inventario

La autenticación actual por rol se detalla en [AUTENTICACION.md](AUTENTICACION.md):
MFA para asistente (administrador), GitHub para estudiantes (pendiente de configurar)
y contraseña para docente.
La presentación utiliza las referencias `docs/views.zip` y `docs/public.zip`.
Ver [VISTAS.md](VISTAS.md) para la correspondencia de pantallas y sus adaptaciones.

La aplicación está disponible en https://192.168.50.83, puerto APP_HTTPS_PORT (443).
APP_PORT (8080) redirige las visitas a HTTPS. El backend PHP usa PDO y la cuenta técnica de aplicación;
las credenciales personales se guardan como hash en usuarios.password_hash.

## Crear el primer administrador

Desde `/home/facu/-TD2_SGLAB/SGLAB`, ejecutar en una terminal interactiva:

```bash
docker compose exec web php bin/crear-admin.php
```

Pide cédula (solo números), nombre, apellido, correo opcional y contraseña de 12
a 72 bytes con confirmación. La contraseña no se muestra ni se pasa por argumentos.
No hay una contraseña predeterminada. Si la CI ya existe, el comando se detiene
sin modificar su cuenta. También rechaza correos duplicados. El archivo está
fuera de public y solo se ejecuta por CLI. No usar `exec -T`, porque deshabilita
la terminal necesaria para ocultar la contraseña.

Después, abrir la web con esa cédula y contraseña, y vincular Google Authenticator
con el QR y código de confirmación del primer ingreso. Las credenciales
web son independientes del usuario SSH del receptor y de las cuentas de MariaDB.

## Permisos y alcance

| Rol | Consulta | Comentarios | Administración |
|---|---|---|---|
| ALUMNO | Estado administrativo y último diagnóstico de la PC detectada por IP | Solo su PC | Ninguna |
| DOCENTE | PC y estados del laboratorio asignado actualmente | Solo su laboratorio vigente | Ninguna |
| ASISTENTE (administrador) | Todos los laboratorios, equipos, estados, historial y diagnósticos | PC y laboratorios | Inventario, usuarios de todos los roles y asignaciones docentes |

Las restricciones se aplican en consultas y POST del servidor, también si se
modifican los IDs o filtros de la URL. Sin una PC identificada o una asignación
vigente no se muestran datos de otros recursos. El alumno no accede a listados
globales, usuarios, laboratorios ni detalles técnicos completos de las capturas.

### Identificación automática de la PC del alumno

Se usa exclusivamente REMOTE_ADDR (IP real que recibe Apache), no cabeceras
X-Forwarded-For proporcionadas por el navegador. Se compara con red.ipv4 de la
última captura de cada PC, ordenada por fecha de evento e ID. La PC y su laboratorio
deben estar activos. La captura debe haberse recibido en las últimas ocho horas.
El límite se configura con SGLAB_PC_IP_MAX_AGE_HOURS en .env (de 1 a 24) y se
aplica al recrear la web con Docker Compose.

Si la IP no coincide o coincide con más de una PC, se deniega el acceso y se pide
una captura nueva o asistencia. No se usa la CI declarada en el TOML para ampliar
permisos ni se deduce una PC a partir de registros de uso antiguos del alumno.
Una IP obsoleta por DHCP puede identificar un equipo incorrecto mientras todavía
sea reciente: para esta modalidad conviene reservar IP por PC y enviar capturas
al iniciar sesión. Si hay NAT, proxy o accesos por túnel, Apache puede ver una IP
compartida que no coincide con la captura y la detección no funcionará. Validar
la red real de la UTU antes de confiar en esta identificación; no prueba posesión
de una máquina ni sustituye una vinculación con un identificador de dispositivo.

### Asignación temporal de docentes

En Usuarios y asignaciones, el asistente o administrador selecciona docente,
laboratorio, inicio y fin opcional. Las fechas usan UTC y el formulario lo indica.
Inicio vacío significa ahora; fin vacío dura hasta revocar o reemplazar.
Cada docente tiene una asignación actual (se reemplaza al cambiar de laboratorio).
Las asignaciones futuras o vencidas no dan acceso. Finalizar una asignación corta
el acceso inmediatamente sin exigir un nuevo login. Esta primera versión no guarda
un historial de reemplazos de asignaciones ni soporta reservas de varios turnos.

### Usuarios y bajas

El asistente es el administrador del sistema: puede crear, editar y desactivar
cuentas de todos los perfiles y restablecer sus contraseñas locales. Los alumnos
acceden con GitHub. No puede quitar el último asistente administrador activo. Desactivar o cambiar el rol finaliza la asignación
docente; la cuenta desactivada pierde sus sesiones en la siguiente solicitud.
No se muestran hashes ni contraseñas existentes.

Eliminar PC o laboratorios archiva (activo=0), sin borrar historia. Antes de
archivar un laboratorio hay que retirar sus PC activas y finalizar sus asignaciones
docentes vigentes/futuras. Se pueden consultar eliminados y restaurarlos. Una PC
archivada pierde acceso estudiantil y no recibe nuevas capturas de spawn.sh.

## Uso

1. Ingresar según el rol: MFA para asistente administrador, contraseña para docente, GitHub para estudiante.
2. En Laboratorios, crear la sala con su nombre; se puede renombrar después.
3. En Equipos, registrar la PC y seleccionar el laboratorio y estado administrativo.
4. Informar una serie real o UUID SMBIOS, o ambos; al menos uno es obligatorio.
5. Ejecutar el cliente de esa PC. El daemon la reconoce por esos identificadores.
6. Consultar el resumen y el detalle de la PC para ver hasta 25 capturas recientes.

La serie se normaliza a mayúsculas y el UUID se valida y normaliza. No se admiten
identificadores de relleno ni UUID vacíos/todos F. Las identidades son únicas.
El hostname es opcional. El laboratorio es obligatorio al dar de alta desde la web,
aunque la BD admita NULL para datos históricos.

El inventario tiene búsqueda por nombre/serie/UUID, filtros de laboratorio y estado,
y paginación de 25 PC. La eliminación es lógica y preserva el historial; también se puede marcar una PC
en reparación o fuera de servicio sin archivarla.
El estado administrativo no se cambia al recibir una captura.

Las fechas de captura se muestran en UTC. El laboratorio actual de una PC y la
etiqueta declarada por el cliente son datos distintos. El cliente no reasigna PC.
La cédula declarada por la ventana provisional no autentica a una persona; solo
se vincula a usuarios si la CI ya existe en la BD.

## Sesiones y protección

- Hash de contraseña con password_hash/password_verify; sin contraseñas por defecto.
- Segundo factor TOTP obligatorio para asistentes administradores.
- Estudiantes exclusivamente por GitHub, con email principal verificado y cuenta activa.
- Sesión regenerada al ingresar y salir; vencimiento por 15 minutos de inactividad
  y duración máxima de 8 horas.
- Cookie Secure, HttpOnly y SameSite=Lax en el acceso HTTPS.
- Token CSRF en todos los POST, incluido login/logout.
- Consultas preparadas PDO y salida HTML escapada.
- Límite de 10 intentos fallidos por combinación IP/cédula durante 15 minutos;
  se guarda en el volumen web_state para persistir entre recreaciones de la web.
- Cabeceras CSP, no-store, protección frente a inclusión en frames y nosniff.
- Errores técnicos en logs del servidor; sin mostrar SQL ni credenciales en pantalla.

HTTPS está configurado con una CA local. Instalar su certificado público en las
PC del laboratorio antes de ingresar: [HTTPS.md](HTTPS.md). Apache atiende TLS
directamente y mantiene la IP del cliente para detectar la PC del alumno.
La IP de acceso y el certificado deben revisarse si cambia la red del servidor.

## Estructura y cambios

```text
server/web/app/
├── public/
│   ├── index.php              # Entrada: rutas, POST, sesión y errores
│   └── assets/               # app.css, img/, svg/ y fonts/ (recursos locales)
├── src/
│   ├── bootstrap.php          # PDO y funciones compartidas
│   ├── Auth.php               # Autenticación, sesiones y límite de intentos
│   ├── Inventory.php          # Inventario y bajas lógicas
│   ├── Access.php             # Alcance por rol e identificación por IP
│   ├── People.php             # Cuentas y asignaciones docentes
│   └── Comments.php           # Comentarios autorizados por recurso
├── views/                     # Login, MFA, cabecera/pie, paneles y administración
└── bin/crear-admin.php         # Alta interactiva del administrador
```

Solo public es accesible por Apache. Los archivos PHP se copian en la imagen;
para aplicar cambios hay que reconstruir la web, sin recrear ni borrar la BD:

```bash
docker compose up -d --build web
docker compose logs --tail 50 web
```

Se aplicó la migración 003, con respaldo previo, para asignaciones docentes,
comentarios de laboratorio y bajas lógicas. Se agregaron permisos técnicos
limitados sobre esas dos tablas; no se otorgó DELETE a la web.
El volumen sglab_web_state contiene el límite de intentos y la clave de cifrado MFA;
respaldar esta clave junto con la BD según AUTENTICACION.md. La BD continúa en sglab_db_data y la cola en var/.

## Pruebas

Pruebas locales comunes:

```bash
python3 -m unittest discover -s tests -v
```

La integración HTTP es optativa porque escribe datos sintéticos en el despliegue
activo. Requiere Docker, web, BD y sglab-spawn activos. Ejecutar solo en el entorno
de pruebas. Crea cuentas y registros temporales y luego los elimina:

```bash
SGLAB_TEST_WEB=1 python3 -m unittest discover -s tests -v
```

Cubre login correcto/incorrecto, CSRF, cookies, alta/edición de inventario,
identidades duplicadas, escape HTML, filtros, ingesta real de una PC dada de alta
por PHP, permisos de lectura, retiro de rol, logout, 404 y expiración de sesión. tests/test_role_scope.py verifica además
alumnos por IP (sin coincidencia y con IP ambigua), docentes con vigencia,
comentarios permitidos/prohibidos, gestión restringida de cuentas, archivado y
revocación de accesos.
La limpieza usa root desde el contenedor DB: la cuenta de la web no tiene DELETE.
Se comprobó también sintaxis PHP. La adaptación de las vistas se revisó con
Chromium en escritorio y móvil, usando cuentas sintéticas. Las evidencias y las
diferencias respecto de las maquetas se detallan en [VISTAS.md](VISTAS.md).
La prueba en una PC real de la UTU sigue pendiente.

## Pendientes fuera de este módulo

Importación masiva de PC, recuperación de contraseñas por autoservicio,
gráficos, exportación, consulta ampliada del documento y discos, y pruebas
de rendimiento/accesibilidad. La prueba de envío desde una PC real de la UTU
sigue en el backlog; esta prueba de integración genera el TOML en el servidor.

## Equivalencia con el ejemplo del profesor

El actor Administrador del ZIP es nuestro ASISTENTE. No hay dos niveles de
administración. Los tres perfiles funcionales son ASISTENTE, DOCENTE y ALUMNO.
La BD conserva el valor ADMINISTRADOR como alias compatible para cuentas antiguas;
no se crea como perfil separado en la web. Ambas cuentas de prueba de personal
administrativo conservan sus credenciales y ahora exigen MFA. Las cuentas nuevas
se guardan como ASISTENTE. El comando recomendado es
`docker compose exec web php bin/crear-asistente.php`; crear-admin.php se conserva
como alias del mismo comando.


## Importación CSV de cuentas

En Usuarios, el asistente administrador puede importar hasta 500 estudiantes y
docentes por archivo UTF-8 de hasta 1 MiB. Se admiten coma o punto y coma y BOM.
El encabezado, en este orden, es:

```csv
ci,nombre,apellido,correo,tipo_usuario,password
12345678,Ana,Pérez,ana@example.com,ALUMNO,
23456789,Juan,López,juan@example.com,DOCENTE,UnaClaveLarga123
```

El correo del estudiante debe coincidir con su correo principal verificado en
GitHub. Para docentes se exige contraseña de 12 a 72 bytes. Solo se admiten roles
ALUMNO y DOCENTE. Las cuentas quedan activas; las asignaciones docentes se realizan
por separado. No actualiza cuentas existentes. Ante una fila inválida, cédula o
correo repetidos, se revierte toda la importación y se informa el error. El CSV no
se conserva en la aplicación; proteger y eliminar las copias con contraseñas.

Prueba del lector y las validaciones, con PHP 8.3:

```bash
php tests/test_people_csv.php
```


## Reporte manual de funcionamiento

En Estado de mi PC, el estudiante puede publicar **Funciona** o **No funciona**.
Para No funciona debe describir el problema; admite hasta 4000 caracteres. Para
Funciona la descripción es opcional. Se vuelve a comprobar la PC detectada por IP
al recibir el formulario; no se acepta reportar otra PC ni una detección ambigua o
vencida. Solo los estudiantes publican reportes.

Los reportes son un historial independiente (`reporte_funcionamiento`), no
cambian `equipo.estado_administrativo`, `registro.estado` ni los comentarios.
El estudiante ve únicamente sus propios reportes en su PC actual; el docente ve
los de equipos de su laboratorio vigente y el asistente los de las PC que puede
consultar. Se muestran los últimos 50, ordenados por fecha UTC e identificador.
Un reporte posterior no elimina los anteriores ni representa un cierre de ticket.

### Instalaciones existentes

Respaldar primero y aplicar `database/migrations/005_reportes_funcionamiento.sql`
con la cuenta de administración de MariaDB. Conceder también INSERT sobre
`sglab.reporte_funcionamiento` a la cuenta técnica web. El archivo
`database/init/zz-users.sh` ya contiene ese permiso para instalaciones nuevas;
puede ejecutarse dentro de db para reaplicar sus concesiones sin borrar datos.
Reconstruir la imagen web. El esquema inicial ya incluye la tabla nueva.
La migración y los permisos se aplicaron en este entorno el 02/11/2026.

Prueba de integración con datos sintéticos que se retiran al finalizar:

```bash
SGLAB_TEST_WEB=1 python3 -m unittest discover -s tests -p test_reports.py -v
```

Comprueba publicación, validación, PC detectada, aislamiento entre estudiantes,
consulta docente/asistente, escape HTML y conservación de los estados originales.
El login OAuth real con GitHub sigue pendiente de la configuración institucional;
la prueba invoca la capa de aplicación con sesiones sintéticas, sin habilitar
ningún acceso alternativo en producción.


## Importación CSV de PC

En **Equipos → Importar PC desde CSV**, el asistente administrador selecciona un
laboratorio activo y carga el archivo. Todas las PC quedan asignadas a esa sala.
Para varias salas, cargar un archivo por laboratorio. Docentes y estudiantes no
pueden importar, ni enviando directamente la solicitud.

Se admite UTF-8 con o sin BOM, separador coma o punto y coma, hasta 1 MiB y 500 PC.
Encabezado obligatorio y ejemplo:

```csv
hostname,num_serie,smbios_uuid,estado_administrativo
LAB-PC01,SERIE-REAL-PC01,,OPERATIVA
LAB-PC02,,12345678-1234-1234-1234-123456789abc,EN_REPARACION
```

Reemplazar las identidades de ejemplo por las reales de la captura TOML. La
pantalla permite descargar este ejemplo. Nombre opcional; al menos serie o UUID
SMBIOS reales obligatorios. Se usan las mismas validaciones que el alta individual
(sin series genéricas ni UUID nulos). Las identidades se normalizan a mayúsculas.
El estado vacío equivale a OPERATIVA; también se admiten EN_REPARACION y
FUERA_DE_SERVICIO. Las PC nuevas quedan activas.

No se actualizan ni restauran equipos existentes. Una serie o UUID que ya existe,
incluso en una PC archivada, rechaza la carga. Se detectan duplicados internos y
se indica la fila del error. La importación se ejecuta en una transacción: ante
cualquier error se revierte completa. El laboratorio se bloquea y revalida dentro
de esa transacción para impedir altas en una sala archivada simultáneamente.

No requiere migración de esquema. Las pruebas están en
`tests/test_equipment_csv.php` (lector y validación) y
`tests/test_equipment_csv_http.py` (carga multipart HTTPS con login/MFA reales,
permisos, CSRF, duplicados, equipos archivados y rollback). La prueba HTTP crea y
retira datos sintéticos:

```bash
SGLAB_TEST_WEB=1 SGLAB_WEB_URL=https://IP_DEL_SERVIDOR python3 -m unittest discover -s tests -p test_equipment_csv_http.py -v
```


## Historial, actividad y exportación CSV

**Historial** está disponible en la navegación de asistentes y docentes. También
se puede acceder desde la ficha de una PC con su ID ya filtrado. Los estudiantes
conservan solo el último diagnóstico en su PC; no pueden acceder a este historial
ni exportarlo, tampoco mediante una URL directa.

- **Historial de capturas:** filtrar por fecha inicial/final (UTC e inclusivas),
  ID de equipo, laboratorio actual y resultado de lectura OK/ERROR.
- **PC sin capturas recientes:** filtrar por laboratorio e ID, con un umbral de
  1 a 365 días (predeterminado: 7). Incluye PC sin ninguna captura y compara la
  última fecha de recepción, no la fecha informada por el cliente. Una captura
  vieja recibida hoy cuenta como actividad reciente. No implica una avería.

Solo se incluyen equipos activos. El asistente consulta su inventario activo;
el docente solo equipos de su laboratorio asignado durante la vigencia de esa
asignación. En el historial docente, además, el laboratorio observado de la
captura debe coincidir con el laboratorio actual de la PC: no se exponen capturas
de salas anteriores. En la vista de actividad solo se muestra la última fecha de
recepción; no se muestran detalles de capturas de otras salas. Los filtros no
amplían permisos y no se incluyen IP, CPU ni otros datos técnicos en el CSV.

Se muestran 50 resultados por página. **Exportar CSV** incluye todos los resultados
filtrados, independientemente de la página, hasta 50.000 filas. Si se supera ese
límite, solicita acotar los filtros y no descarga un resultado truncado. Usa UTF-8
con BOM y separador coma; los valores que podrían ejecutar fórmulas en una planilla
se prefijan con un apóstrofo. Los filtros se revalidan y los permisos se aplican
por igual en pantalla y exportación. Fechas/estados/IDs inválidos devuelven HTTP 400.

Columnas de capturas: id_registro, id_equipo, hostname, laboratorio, fecha,
fecha_recepcion y estado. Columnas de actividad: id_equipo, hostname, num_serie,
smbios_uuid, laboratorio y ultima_recepcion (vacía si nunca recibió).

### Instalaciones existentes y pruebas

Respaldar y aplicar `database/migrations/006_indices_historial.sql`; agrega índices
para búsqueda por fecha y última recepción por equipo, sin cambiar los datos.
El esquema inicial ya los incluye. Reconstruir la imagen web. Esta migración y el
despliegue se aplicaron el 02/11/2026.

```bash
php tests/test_history.php
SGLAB_TEST_WEB=1 SGLAB_WEB_URL=https://IP_DEL_SERVIDOR python3 -m unittest discover -s tests -p test_history_http.py -v
```

Se probaron filtros y fechas inválidas, límite de exportación, protección de
fórmulas, descarga CSV por HTTPS, fechas inclusivas, paginación,
exportación completa, capturas del laboratorio anterior, revocación docente,
denegación al estudiante y equipos con recepción vieja/nueva o sin capturas.
Las pruebas HTTP usan login/MFA y datos sintéticos retirados al terminar.
No se realizó una prueba de carga con 50.000 filas; el límite funcional no acredita
por sí solo objetivos de rendimiento del proyecto. Los gráficos de distribución se describen a continuación.


### Gráficos de distribución

El historial muestra barras con cantidades y porcentajes sobre **todos** los
resultados filtrados, no solo la página visible. Para capturas: lecturas OK y ERROR
(contando capturas, no equipos distintos). Para PC sin actividad reciente: nunca
recibieron frente a última recepción antigua (contando equipos). Un resultado
vacío muestra un mensaje, sin porcentajes engañosos ni división por cero.

Los gráficos usan los mismos predicados de permisos y filtros de la tabla/CSV.
Incluyen etiquetas y valores textuales, además de barras HTML nativas, sin requerir
JavaScript. La prueba `test_history_http.py` comprueba las cantidades, otra página,
exclusión de capturas de salas anteriores y revocación del acceso docente.
No representan el estado administrativo ni los reportes manuales de funcionamiento.
