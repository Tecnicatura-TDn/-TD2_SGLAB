# Limpieza de TOML procesados

El servidor conserva durante **30 días** los trabajos ya importados y confirmados
de `var/processed`. El timer `sglab-limpieza.timer` ejecuta la limpieza diariamente
entre las 04:00 y las 04:05, hora local del servidor. Recupera ejecuciones perdidas
cuando el servidor vuelve a encenderse.

Solo se elimina un directorio `job.*` si contiene exactamente una captura
`SGLAB-UUID.toml` y `resultado.log`, ambos archivos regulares sin enlaces simbólicos,
y el log confirma `INSERTADO` o `YA_PROCESADO`. La fecha más reciente del directorio,
el TOML y el log debe superar la retención. Una captura vieja recién importada se
conserva durante el plazo completo desde su procesamiento.

Se elimina el trabajo completo (TOML y su resultado). Los datos en MariaDB no se
eliminan ni se modifican. Se conservan los trabajos con contenido inesperado.
Nunca se recorre ni elimina `incoming`, `processing` o `rejected`, ni los respaldos.
El bloqueo `.limpieza.lock` impide ejecuciones simultáneas de la limpieza.
`spawn.sh` mueve los trabajos a processed al finalizar la importación; no los sigue
modificando allí. No es necesario detener la ingesta.

## Uso

Desde la raíz de SGLAB:

```bash
# Simular sin eliminar:
python3 infra/limpiar-toml.py

# Aplicar la retención de 30 días:
python3 infra/limpiar-toml.py --aplicar

# Ver la programación y los resultados:
systemctl list-timers sglab-limpieza.timer
journalctl -u sglab-limpieza.service -n 30 --no-pager
```

`--dias N` permite cambiar la retención; se exige un mínimo de siete días. El
valor elegido para el timer se fija al generar las unidades:

```bash
python3 infra/configurar-limpieza.py --usuario USUARIO_DEL_PROYECTO --dias 30
sudo install -m 0644 var/systemd/sglab-limpieza.service var/systemd/sglab-limpieza.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sglab-limpieza.timer
```

Regenerar las unidades cuando se mueve el proyecto o cambia su usuario. En UTU
acordar la retención y revisar la zona horaria antes de activar el timer.
Para detener la programación: `sudo systemctl disable --now sglab-limpieza.timer`.

## Verificación

Pruebas sin tocar datos reales:

```bash
python3 -m unittest discover -s tests -p test_limpieza_toml.py -v
```

Se prueban simulación, borrado de trabajos confirmados vencidos, ejecuciones
repetidas, conservación de logs recientes/TOML antiguos, rechazos, trabajos en
curso, archivos inesperados y enlaces simbólicos. El 02/11/2026 se verificó también
la ejecución real desde systemd: terminó correctamente y no había trabajos
elegibles para eliminar.

## Alcance de clientes

Esta tarea actúa solo en el **servidor**. Las copias `pendientes/enviados` del cliente
Windows permanecen conservadas; su retención local sigue pendiente. Un archivo
entregado por SSH no garantiza que la ingesta haya sido aceptada, por lo que no se
extiende automáticamente esta política a las PC. Los TOML pendientes de envío no
se eliminan por antigüedad.
