# Modelo inicial corregido

`001_modelo_inicial.sql` actualiza exclusivamente una base `sglab` que ya tenga
las cinco tablas `usuarios`, `laboratorio`, `equipo`, `registro` y `comentario`.
No sirve para transformar el esquema anterior de 15 tablas. No es idempotente:
aplicar una sola vez, con respaldo previo. El DDL de MariaDB no permite revertir
la migración completa mediante ROLLBACK.

Correcciones:

- Estado administrativo del equipo separado del observado OK/ERROR del registro.
- Identificación alternativa por UUID SMBIOS; serie opcional y única si existe.
- UUID de ejecución único y hash para que el importador pueda detectar reenvíos.
- CPU, RAM, MAC, hostname, SO y laboratorio observado preservados por captura.
- Varios discos por registro, con tipo, modelo, serie y capacidad.
- Sistemas de archivos separados, con espacio libre, capacidad y montaje.
  La relación al disco puede quedar vacía para LVM/RAID.

Las columnas nuevas de UUID/hash permiten NULL por compatibilidad con registros
históricos; el importador deberá exigirlas en cada captura nueva. Una restricción
única por sí sola no implementa la comparación de hash ni la deduplicación.
El espacio se mide en GB decimales. Las fechas se deben enviar en UTC.
`registro.estado` expresa si hubo errores de recopilación, no conectividad ni
estado administrativo. La regla exacta OK/ERROR corresponde al recolector.

Los campos originales `equipo.disco_tipo`, `equipo.disco_total_gb` y
`registro.disco_libre_gb` se conservan por compatibilidad; usar las tablas nuevas
para futuras capturas. No se convierten automáticamente datos históricos porque
no se puede deducir a qué disco o sistema de archivos corresponden.

`database/init/sglab.sql` contiene el esquema equivalente para instalaciones nuevas.
`zz-users.sh` contiene permisos para ese esquema y se ejecuta solo al inicializar
un volumen vacío. Los usuarios existentes necesitan actualizar sus permisos al
migrar; no basta con modificar ese archivo.

Recrear un contenedor no reinicializa el volumen db_data. No borrar ese volumen
para intentar aplicar este cambio. Si existen las 15 tablas anteriores, se necesita
una migración distinta y revisar previamente sus datos.

`server/bin/spawn.sh` importa en este esquema. El contrato actual no describe
sistemas de archivos: esa captura requiere ampliar el formato y el recolector.
La aplicación web de administración todavía está pendiente.

## Rol administrador

`002_rol_administrador.sql` agrega `ADMINISTRADOR` a `usuarios.tipo_usuario`,
conservando `ALUMNO`, `DOCENTE` y `ASISTENTE` y sus posiciones en el ENUM.
Se puede aplicar a la BD existente sin recrear el volumen. Es repetible.
Hacer un respaldo antes de aplicarla. No crea usuarios ni cambia sus roles.
Las instalaciones nuevas ya incluyen este rol en `database/init/sglab.sql`.
La autorización de las operaciones deberá implementarse en el backend PHP.
