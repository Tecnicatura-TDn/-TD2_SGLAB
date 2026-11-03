# Pendientes de SGLAB

Revisión del 29/10/2026 contra `Proyecto_Ejemplo_SGLAB_Completo.pdf`, el código y
la configuración local. El PDF es un documento modelo; sus resultados de ejemplo
(48/65 requisitos y mediciones de rendimiento) no son resultados de nuestro sistema.
Esta lista no crea ni modifica tareas de GitHub.

## Base implementada

- Recolector Python, generación TOML, envío SCP/SSH, cola e ingesta con spawn.sh
  hacia MariaDB en Docker; pruebas sintéticas de integración aprobadas.
- Web PHP con sesiones, permisos, MFA del asistente, laboratorios, equipos,
  usuarios, asignaciones docentes, comentarios y bajas lógicas.
- Alumno limitado a su PC detectada por IP; docente a su laboratorio vigente;
  asistente como administrador. La integración de GitHub está preparada.
- Diseño adaptado a las maquetas; revisión en Chromium de escritorio y móvil.
- HTTPS con CA local. El usuario confirmó acceso sin advertencias en Brave
  después de reiniciar el navegador. No es una prueba desde todas las PC de la UTU.

## Pendientes prioritarios

| Tarea | Situación y resultado esperado | Referencia del PDF |
|---|---|---|
| Respaldos automáticos y recuperación | Implementado respaldo diario systemd, paquete privado con BD/MFA/CA/TLS/.env y retención de siete días. Restauración SQL aislada comprobada el 02/11/2026. Falta destino externo semanal y ensayo integral de recuperación con MFA/HTTPS en otro servidor. Ver RESPALDOS.md. | RF-LNX-11, RF-NET-08; páginas 10–11 |
| Limpieza programada | Implementada y activada la limpieza diaria de trabajos confirmados en var/processed con retención de 30 días. Conserva pendientes, processing, rechazados y contenido inesperado. Ver LIMPIEZA.md. Pendiente acordar retención local de enviados en las PC cliente. | RF-LNX-14, RF-NET-06 |
| Login real de estudiantes | Registrar la OAuth App, configurar Client ID/Secret localmente y probar el flujo con un estudiante cuyo email principal verificado coincida. Las pruebas actuales de OAuth usan un proveedor simulado. | Login/perfiles del PDF y flujo acordado a partir de la referencia del profesor |
| Estado funcional reportado | Implementado el 02/11/2026: el estudiante reporta funciona/no funciona sobre su PC detectada por IP, con descripción obligatoria del problema. Historial propio para estudiantes y consulta según alcance para docentes/asistentes. Separado del diagnóstico y del estado administrativo; probado contra PHP/MariaDB reales. | RF-WEB-04/05 |
| Importación masiva | Implementadas las importaciones CSV de estudiantes/docentes en Usuarios y de PC en Equipos. La carga de PC asigna todo el archivo a un laboratorio activo, valida identidades y duplicados (incluidos archivados) y revierte completa ante errores. Ver WEB.md. | RF-PHP-10, RF-WEB-06 |
| Consultas y reportes | Implementados historial con filtros por fecha UTC/equipo/laboratorio/lectura, paginación, CSV de resultados filtrados y PC sin capturas recientes (última recepción). Probados por HTTPS con permisos por rol. Implementados gráficos de distribución sobre todos los resultados filtrados (OK/ERROR y nunca/recepción antigua), comprobados por HTTPS. Pendientes mediciones de rendimiento y revisión del alcance de endpoints del modelo. Ver WEB.md. | RF-PHP-11 a 15, RF-WEB-08, RNF-02 |
| Prueba real en UTU | El recolector ya fue probado allí. Falta probar instalación por usuario, inicio de sesión, envío SSH, recepción, ingesta y consulta en la web; guardar evidencias. Validar además que la IP que recibe Apache permita identificar correctamente la PC. | RF-NET-01/09 y validación del flujo completo |
| Receptor SSH con permisos mínimos | Implementada configuración en provision: BASE-TD2 reutilizado como dueño del repositorio, receptor y usuario de spawn, con grupos docker y sglab-ingest y permisos de la cola. Permisos probados en contenedor aislado. Falta aplicar la configuración en el servidor institucional y comprobar el envío real; el perfil activo sigue usando facu. Ver PROVISION-SGLAB.md. | RF-LNX-09 y seguridad de infraestructura |

La frecuencia de respaldo del modelo es inconsistente: la página 10 menciona cada
hora y la 11 cada 24 horas. Se eligió una copia diaria a las 03:00, hora local del servidor, documentada en RESPALDOS.md.

## Completar o validar después

- Captura de espacio libre por sistemas de archivos: el esquema contempla los
  datos, pero la captura/ingesta completa todavía requiere ampliación.
- Diagnóstico de latencia y aviso por email cuando falta la serie, si se mantienen
  en el alcance final (RF-NET-07/11). Ya se recopilan IP, gateway y DNS; existe la
  alternativa de identidad por UUID SMBIOS.
- Implementados verificación previa del directorio remoto y diagnósticos SSH/SCP por etapa (02/11/2026). Falta validar los mensajes en una PC Windows real de UTU con su cuenta receptora institucional.
- Medición de listados con 10.000 equipos, exportaciones con 50.000 registros,
  disponibilidad y auditoría de accesibilidad. Las pruebas funcionales y visuales
  actuales no acreditan esos objetivos (RNF-02/03/04).
- Revisar el script de aprovisionamiento con un despliegue limpio en otro entorno;
  el servidor activo no prueba por sí solo que todo el instalador sea reproducible.
- ESRE propio, matriz requisito/prueba/evidencia, actualización de diagramas de
  clases/casos de uso/despliegue/red, cronograma y responsables. Hay diagramas
  históricos en `../doc`; necesitan contrastarse con la implementación actual.
- Documentar las diferencias respecto del modelo: Python autorizado por el
  profesor, MariaDB/Docker/Rocky, fechas DATETIME UTC frente a epoch y daemon de
  ingesta cada cinco segundos frente a la carga horaria del ejemplo. Confirmar
  qué infraestructura Proxmox/AD/GPO/DNS debe demostrar el equipo y cuál ya provee
  la institución. No modificar esos servicios institucionales por esta revisión.

Prioridad de trabajo sugerida: respaldos y recuperación, limpieza, GitHub y
reportes funcionales/importaciones. La prueba física en UTU puede quedar en el
backlog hasta disponer de los equipos.
