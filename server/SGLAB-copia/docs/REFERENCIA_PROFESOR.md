# Roles del sistema de referencia del profesor

Fuente: [SGLAB-main.zip](SGLAB-main.zip). Revisión estática del contenido realizada
el 29/10/2026: 117 archivos. No se ejecutaron su código, scripts, SQL ni pruebas,
y no se importó su BD en nuestro despliegue.

## Conclusión

El ZIP contiene una aplicación PHP con una base funcional de tres roles, no solo
una maqueta. Sirve para identificar funcionalidades, pero sus permisos son más
amplios que los acordados para nuestro SGLAB. No debe tomarse como especificación
única ni reemplazar automáticamente las decisiones ya aceptadas.

En el ZIP el rol se llama Administrador. El usuario aclaró que ese actor es
nuestro ASISTENTE: es el mismo perfil, no un cuarto actor. Nuestras asignaciones
temporales de docentes y la identificación automática de la PC del alumno por IP
tampoco están implementadas allí.

## Permisos observados en el código

| Función | Administrador | Docente | Estudiante |
|---|---|---|---|
| Ingresar con usuario/contraseña | Sí, más TOTP | Sí, directo | No; usa GitHub |
| Consultar panel administrativo global | Sí | No | No |
| Consultar equipos para reportar | Sí | No mediante RegistroController | Sí, todos los activos |
| Crear/editar/baja/reactivación de PC | Sí | No | No |
| Importar PC por CSV | Sí | No | No |
| Crear/editar/baja de usuarios | Sí | No | No |
| Importar/exportar estudiantes CSV | Sí | No | No |
| Consultar y filtrar registros globales | Sí | No por esas acciones | No |
| Consultar panel de laboratorios | Sí | Sí, todos los activos | No |
| Actualizar comentario de laboratorio | Sí | Sí, sin asignación de laboratorio | No |
| Enviar reporte funciona/no funciona + descripción | No por crearReporte | No | Sí, sobre el equipo seleccionado |
| Detectar la PC propia por IP | No implementado | No aplica | No implementado |
| Asignar docente por turno/laboratorio | No implementado | No aplica | No aplica |

El administrador puede consultar el panel docente además de sus propias pantallas.
La API de reportes automáticos usa una clave técnica; no es otro rol de usuario.
Los permisos de las cuentas MySQL no equivalen a los permisos funcionales de la web.

## Evidencias dentro del ZIP

Todas las rutas siguientes son relativas a `SGLAB-main/`, dentro del archivo.

- `app/Core/acceso.php`, líneas 9–11: solo ROL_ADMIN=1, ROL_DOCENTE=2 y
  ROL_ESTUDIANTE=3. Líneas 22–37: comprobación del rol de vistas/API.
- `app/Models/TipoUsuario.php`, líneas 7–24: mismos tres roles y descripciones.
- `app/Controllers/loginController.php`, líneas 90–155: administrador con TOTP,
  docente directo y estudiante remitido a GitHub.
- `app/Controllers/githubAuthController.php`, líneas 135–175: vínculo existente
  por GitHub ID y primera vinculación por email de estudiante activo.
- `app/Controllers/EquipoController.php`, línea 3: controlador solo para admin;
  acciones en líneas 14–149: listar, obtener, crear, actualizar, baja, reactivar,
  control de reportes ausentes e importación masiva.
- `app/Controllers/usuariosController.php`, línea 3 y líneas 20–120: solo admin;
  consulta, creación, edición, baja, roles, importación y exportación CSV.
- `app/Controllers/RegistroController.php`, líneas 5–9: obtenerEquipos para admin
  y estudiante; crearReporte solo para estudiante; el resto solo para admin.
- `app/Controllers/RegistroController.php`, líneas 85–96: el equipo llega desde
  el formulario; la identidad del autor procede de la sesión.
- `app/views/menu_estudiante.php`, líneas 50–75: selector de equipo, indicador
  funciona/no funciona, comentario y botón Enviar Reporte.
- `public/assets/js/menu_estudiante.js`, líneas 5–19: carga todos los equipos que
  devuelve la API; líneas 48–73: envía idEquipo, estado y descripción.
- `app/Models/Equipo.php`, líneas 180–185: devuelve todos los equipos activos,
  sin un vínculo de PC/alumno ni una comparación de IP.
- `app/Models/Registro.php`, líneas 184–200: el reporte manual del estudiante se
  guarda como un nuevo Registro, con estado/descripción y sin diagnóstico técnico.
- `app/Controllers/DocenteController.php`, líneas 3 y 14–30: admin/docente pueden
  consultar estadísticas, laboratorios y actualizar un comentario por ID.
- `app/Models/LaboratorioDocente.php`, líneas 15–57: consulta todos los laboratorios
  activos y el último registro por PC; no filtra por docente, horario o asignación.
- Ese mismo modelo, líneas 168–181: actualiza Laboratorios.comentario por ID.
  Es un campo que se reemplaza; no un historial separado de comentarios/autores.

## Diferencias con el alcance que acordamos

| Tema | ZIP del profesor | Nuestro alcance vigente |
|---|---|---|
| Nombre del administrador | Administrador | ASISTENTE, equivalente funcional: administra inventario, todos los usuarios y asignaciones |
| PC del alumno | Selección manual entre PC activas | Detección por IP, con coincidencia única y captura reciente |
| Docente | Todos los laboratorios activos | Solo el laboratorio asignado durante su vigencia |
| Comentarios docentes | Un texto por laboratorio, reemplazable | Historial con autor y fecha |
| Reporte del alumno | Funciona/no funciona y descripción, crea Registro | Actualmente comentario sobre su PC y consulta de su estado; sin selector de estado declarado |
| Login de personal | Username | Cédula |
| Fechas | Epoch INT | DATETIME en UTC |
| Estado | Registro.estado numérico, mezcla estados reportados | Estado administrativo separado del resultado técnico de lectura |
| Reporte automático | Script Linux llama una API PHP con clave | spawn.sh valida TOML y ejecuta la transacción en MariaDB |

Las restricciones de PC propia y laboratorio vigente fueron instrucciones expresas
del usuario. La referencia del profesor no las implementa: no corresponde ampliar
los accesos de nuestra aplicación solo para imitar este ZIP.

## ¿Está completo?

Contiene controladores, modelos, vistas, scripts, datos iniciales y pruebas, pero
la revisión estática encuentra al menos una ruta funcional inconsistente:

`app/api/api_registro.php:75` llama a `Equipo::obtenerPorSerial($serialNumber)`,
pero ese método no está definido en `app/Models/Equipo.php`. Tampoco hay un método
mágico `__callStatic` que lo resuelva. Por tanto, esa ruta de ingesta no puede
completarse con el código tal como viene en el ZIP. No se probó el resto en ejecución.

No encontré un controlador web para altas/bajas de laboratorios ni una asignación
de docentes por laboratorio. El modelo Laboratorio ofrece consultas; el panel
Docente modifica su comentario. No hay que confundir el título «gestión de
laboratorios» con un CRUD completo de salas y asignaciones.

Además, su API automática parsea un reporte de texto mediante expresiones regulares,
no nuestro contrato TOML v1.1. El esquema usa nombres y tipos diferentes (por ejemplo,
serie numérica), por lo que copiar sus modelos o SQL directamente rompería la
compatibilidad con la ingesta y los datos de nuestro sistema.

## Funcionalidades aprovechables para el backlog

1. **Reporte manual del alumno (implementado el 02/11/2026):** funciona/no funciona
   y descripción del problema, restringido a su PC detectada. Historial separado
   del diagnóstico automático y del estado administrativo; ver WEB.md.
2. **Importación CSV de estudiantes y PC (implementada):** usuarios con emails
   GitHub y roles validados; PC con serie/UUID y laboratorio activo. Ver WEB.md.
3. **Exportación CSV de estudiantes**, con los permisos acordados.
4. **Filtros y exportación de capturas (implementados el 02/11/2026):** fecha,
   lectura, laboratorio y equipo; consulta de PC sin captura reciente. Gráficos de distribución implementados;
   mediciones de rendimiento siguen pendientes. Ver WEB.md.
5. **Auditoría de autenticación** estructurada: ingresos, fallos y cambios de cuenta.

Este análisis no modifica los permisos, el código PHP de la aplicación activa,
los usuarios, los contenedores ni la BD. El ZIP se conserva como referencia.

## Aclaración posterior del usuario

El administrador de este ejemplo es el asistente de nuestro proyecto. Se unificaron
permisos y MFA para ambos nombres. ADMINISTRADOR queda solo como alias compatible
con cuentas existentes; los perfiles funcionales son asistente, docente y estudiante.
Se mantienen las restricciones específicas acordadas para docente y estudiante.
