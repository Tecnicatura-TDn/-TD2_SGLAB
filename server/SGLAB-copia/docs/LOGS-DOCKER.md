# Logs de Docker y acciones de infraestructura

Se conserva el trabajo del commit 0a015f76563f08269a3955b9a7b0d377beb1a614.
Los scripts de captura/instalación y la plantilla del servicio se recuperaron
sin cambios respecto de ese commit.

- `server/bin/logsparadocker.sh`: sigue los logs de web y db y los escribe en
  `logs/infra/sglab-docker-AAAA-MM-DD.log`. Limpia sus logs de más de 30 días al
  cambiar el día cuando recibe líneas nuevas. No elimina registros de acciones.
- `server/bin/instalar-logs-docker.sh`: genera y verifica la unidad systemd usando
  la ruta del proyecto y el usuario invocador de sudo. Instala y habilita el servicio.
- `server/systemd/sglab-logs-docker.service.example`: plantilla original.

Desde la raíz de SGLAB:

```bash
sudo bash server/bin/instalar-logs-docker.sh
sudo systemctl start sglab-logs-docker
sudo systemctl status sglab-logs-docker --no-pager
```

El usuario de la unidad debe tener acceso al proyecto, .env y Docker. El instalador
usa SUDO_USER (o el usuario actual); verificar la cuenta elegida al instalar en otro
servidor. El instalador habilita la unidad; el comando start inicia la captura ahora.

El registro de acciones del menú se integró en `infra/infra.sh`, manteniendo la
creación automática del volumen externo. Registra éxito/error en inicios,
detenciones, exportación, reinicialización y eliminación según el commit original.
Se guarda en `var/logs/infra/sglab-acciones-AAAA-MM-DD.log`, junto a las exportaciones
del administrador. `server/bin/infra.sh` conserva la entrada antigua y delega a
`infra/infra.sh` para no mantener dos administradores distintos.

Tanto logs/ como var/ están excluidos de Git. No se instaló ni inició ningún
servicio real al recuperar este commit.

Pruebas con Docker y operaciones administrativas simulados:

```bash
python3 -m unittest discover -s tests -p test_logs_infra.py -v
```

Verifican éxitos/fallos del menú, archivo diario, permisos privados, retención de
logs Docker y conservación de otros registros. Los tres archivos originales se
compararon byte a byte con el commit.
