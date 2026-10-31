# Servidor activo: SGLAB-copia

Todo el despliegue activo se opera desde `/home/facu/SGLAB-copia`.
El proyecto `/home/facu/SGLAB` está desactivado; sus contenedores fueron retirados.

| Recurso | Configuración |
|---|---|
| Proyecto Compose | sglab-copia |
| Contenedores | sglab-copia-web-1 y sglab-copia-db-1 |
| Web | http://192.168.50.83:8080 |
| BD desde el host | 127.0.0.1:3306 |
| BD desde PHP | db:3306, base sglab |
| Volumen externo activo | sglab_db_data |
| Aplicación PHP | server/web/app/ |
| SSH | facu@192.168.50.83, puerto 22 |
| Recepción | /home/facu/SGLAB-copia/server/incoming |
| Daemon | sglab-spawn.service |

El volumen mantiene su nombre histórico, pero no depende de la carpeta SGLAB.
Se reutilizó para conservar la BD actualizada. El volumen sglab-copia_db_data del
montaje temporal anterior no está conectado. No borrar volúmenes para migrar.
Hay un respaldo previo a la centralización en database/backups.

La unidad systemd ejecuta server/bin/spawn.sh como facu, con los grupos docker y
sglab-ingest. Usa el Compose y .env de SGLAB-copia y .venv/bin/tomlq como parser.
Está habilitada para arrancar con el host. Las rutas son específicas de este servidor.

La cola completa está en server/incoming, processing, processed y rejected.
Incoming usa permisos 2770/grupo sglab-ingest; las carpetas de resultados son 0700.
El receptor necesita acceso a las carpetas superiores. Las rutas antiguas de
/srv/sglab son enlaces de compatibilidad hacia la cola del proyecto.

El cliente publica .toml.part y renombra a .toml. El daemon revisa cada cinco
segundos, mueve cada archivo a un trabajo y deja resultado.log. Los fallos de
BD o equipos desconocidos quedan en rejected: resolver y reenviar a incoming.
El equipo debe existir por serie o UUID antes de importar. El laboratorio oficial
lo determina la BD, no la etiqueta del cliente.

Desde la raíz de SGLAB-copia:

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
En una nueva máquina hay que preparar/restaurar el volumen externo antes de up.
