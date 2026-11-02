# Prueba Fedora — Issue #15

## Evidencia aportada

Captura `SGLAB-766fd66b-1685-4d0a-b7df-d6b7c4b7a403.toml`, del 29/10/2026,
generada por `version_script = "1.1.0"` y `version_formato = "1.1"`:

- Serie y UUID SMBIOS disponibles, además de CPU, RAM, red y periféricos.
- `red.conectividad = true` para el destino indicado por el usuario,
  `192.168.50.83:22`. Confirma conexión TCP; no acredita autenticación SSH,
  transferencia del TOML ni inserción en la BD.
- Dos discos registrados: 8,59 GB y 512,11 GB, ambos como SSD.
- Una lectura no disponible: `hardware.discos[0].espacio_libre_gb`.

## Defecto y corrección

El filtro usaba solamente `TYPE=disk`. Un dispositivo de memoria comprimida
`zram0` puede cumplir esa condición y tener `ROTA=false`, por lo que acababa
clasificado como SSD. El dual boot no origina ese dispositivo.

La versión del script **1.1.1** excluye `zramN`, `ramN` y `loopN` por nombre,
conserva los discos reportados por el sistema y sus índices consecutivos, y evita
tratar `[SWAP]` como ruta al calcular espacio libre. Se sigue recorriendo el árbol
de particiones, cifrado y LVM para encontrar los sistemas de archivos montados.
El formato TOML y la ingesta de `spawn.sh` no cambian.

En el caso reproducido, el resultado esperado es un único SSD de 512,11 GB con
`orden = 0`. El espacio libre se calcula nuevamente al capturar: puede variar
respecto de los 134,96 GB observados. La medición se limita a sistemas de archivos
montados y conserva las limitaciones documentadas para LVM/RAID y sistemas con
varios subvolúmenes; no acredita el espacio libre total de todas las particiones.

## Repetir en la laptop

Copiar la versión corregida de `client/recopilar.py` a la laptop. Si se usa el
repositorio completo, desde la raíz de **SGLAB**:

```bash
sudo python3 client/recopilar.py --laboratorio LAB01 --salida salida --probar-host 192.168.50.83 --probar-puerto 22
```

Si se copió solo el archivo a `~/SGLAB/recopilar.py`, reemplazar
`client/recopilar.py` por `recopilar.py`. Se mantiene sudo para reproducir la
prueba anterior y acceder a la identidad DMI; no es un requisito nuevo del filtro.
El comando genera una captura local y prueba TCP, sin enviar archivos.

Revisar el TOML cuyo nombre imprime el comando y guardar como evidencia:

- `meta.version_script = "1.1.1"` y `meta.version_formato = "1.1"`.
- `red.conectividad = true` si el destino sigue accesible.
- Un solo disco para esta laptop, de aproximadamente 512,11 GB y `orden = 0`.
- Sin el error de espacio libre del dispositivo de 8,59 GB.
- Si no aparece ningún otro fallo real, `errores_lectura = []` y el mensaje
  `0 lecturas no disponibles`.

## Validación local y pendiente real

Las regresiones locales reproducen zram + NVMe, particiones de dual boot,
exclusión de dispositivos de memoria/loop, conservación de NVMe/SATA/virtio,
montajes de LVM con swap, deduplicación de bind mounts y fallos legítimos.

```bash
python3 -m unittest discover -s tests -p test_recopilar_discos_linux.py -v
```

Son pruebas con entradas simuladas de lsblk y lecturas de montaje controladas.
Las seis regresiones pasan tras reproducir el fallo con la versión anterior.
También se comprobó la lectura de discos en el servidor Rocky real con LVM/swap:
un disco y cero lecturas de disco no disponibles. El TOML de la reproducción se
parseó correctamente con el mismo `tomlq` que usa spawn.sh. La suite local completa
aprobó ocho pruebas; ocho pruebas de integración web optativas no se ejecutaron
en esta corrección del recolector.
Falta repetir la captura con **1.1.1 en la laptop Fedora**, guardar el TOML nuevo
y documentar el resultado antes de dar la Issue #15 por completada.
