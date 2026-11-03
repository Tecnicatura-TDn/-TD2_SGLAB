# Servidor activo: SGLAB

Todo el despliegue activo se opera desde `/home/facu/-TD2_SGLAB/SGLAB`.
El proyecto está ubicado en la raíz del repositorio, no dentro de server/.

| Recurso | Configuración |
|---|---|
| Proyecto Compose | sglab |
| Contenedores | sglab-web-1 y sglab-db-1 |
| Web | https://192.168.50.83 |
| Dirección anterior | http://192.168.50.83:8080 redirige a HTTPS |
| BD desde el host | 127.0.0.1:3306 |
| BD desde PHP | db:3306, base sglab |
| Volumen externo activo | sglab_db_data |
| Aplicación PHP | server/web/app/ |
| SSH | facu@192.168.50.83, puerto 22 |
| Recepción | /home/facu/-TD2_SGLAB/SGLAB/var/incoming |
| Daemon | sglab-spawn.service |

El volumen mantiene su nombre histórico, pero no depende de la carpeta SGLAB.
Se reutilizó para conservar la BD actualizada. El volumen sglab-copia_db_data del
montaje temporal anterior no está conectado. No borrar volúmenes para migrar.
Hay un respaldo previo a la centralización en var/backups.

La unidad systemd ejecuta server/bin/spawn.sh como facu, con los grupos docker y
sglab-ingest. Usa el Compose y .env de SGLAB y .venv/bin/tomlq como parser.
Está habilitada para arrancar con el host. Las rutas son específicas de este servidor.

La cola completa está en var/incoming, processing, processed y rejected.
Incoming usa permisos 2770/grupo sglab-ingest; las carpetas de resultados son 0700.
El receptor necesita acceso a las carpetas superiores. Las rutas antiguas de
/srv/sglab son enlaces de compatibilidad hacia la cola del proyecto.

El cliente publica .toml.part y renombra a .toml. El daemon revisa cada cinco
segundos, mueve cada archivo a un trabajo y deja resultado.log. Los fallos de
BD o equipos desconocidos quedan en rejected: resolver y reenviar a incoming.
El equipo debe existir por serie o UUID antes de importar. El laboratorio oficial
lo determina la BD, no la etiqueta del cliente.

Desde la raíz de SGLAB:

```bash
docker compose ps
docker compose up -d
# Tras editar PHP:
docker compose up -d --build web
sudo systemctl status sglab-spawn
sudo journalctl -u sglab-spawn -n 50 --no-pager
sudo systemctl restart sglab-spawn
```

La IP es la actual; actualizar clientes o usar DNS si cambia. No ejecutar Compose
desde el proyecto antiguo ni iniciar dos MariaDB sobre el mismo volumen.
infra.sh crea el volumen externo si falta antes de levantar servicios. En una
nueva máquina, restaurar el respaldo antes del arranque si se necesitan los datos
anteriores. Al ejecutar docker compose up directamente, preparar el volumen
externo previamente con docker volume create sglab_db_data.
También preparar el certificado con `python3 infra/configurar-https.py IP_DEL_SERVIDOR`
antes de iniciar la web. Ver [HTTPS.md](HTTPS.md): incluye confianza en Windows,
renovación y las rutas de certificados y claves.

## Acceso a la web

La web tiene login e inventario. Crear el primer administrador con
`docker compose exec web php bin/crear-admin.php`. No hay contraseña por defecto.
Ver [WEB.md](WEB.md) para los pasos y permisos de cada rol.

## Roles y detección de PC

Se aplicó la migración 003 con respaldo previo. La BD tiene nueve tablas.
El asistente es el administrador: gestiona inventario, asignaciones docentes y
cuentas de todos los roles. Requiere MFA. El docente accede al laboratorio que tiene asignado en ese
momento. El alumno ve la PC cuya última captura reciente coincide con la IP que
recibe Apache. La detección no confía en cabeceras de IP del navegador y rechaza
coincidencias ambiguas. El valor de frescura por defecto es ocho horas.
Configurar SGLAB_PC_IP_MAX_AGE_HOURS en .env y recrear web si se cambia.
Ver WEB.md para condiciones de NAT/DHCP, comentarios y permisos exactos.

## Respaldos automáticos

Configuración, operación y recuperación en [RESPALDOS.md](RESPALDOS.md).
El timer `sglab-backup.timer` ejecuta una copia diaria a las 03:00 con retención
de siete días. Regenerar las unidades si cambia la ruta del proyecto o su usuario.

## Limpieza automática

`sglab-limpieza.timer` limpia trabajos confirmados de `var/processed` con más de
30 días, diariamente a las 04:00 (hasta cinco minutos de demora). No elimina
pendientes, rechazados ni datos de MariaDB. Ver [LIMPIEZA.md](LIMPIEZA.md).

## Preparar el receptor desde provision

Ver [PROVISION-SGLAB.md](PROVISION-SGLAB.md): opción 3 para configurar BASE-TD2,
contraseña inicial, grupos docker/sglab-ingest, permisos de incoming y servicio spawn
bajo el mismo BASE-TD2; opción 4 para
autorizar una clave pública manualmente. El servidor activo todavía no se migró
a ese receptor y la prueba institucional sigue pendiente.
