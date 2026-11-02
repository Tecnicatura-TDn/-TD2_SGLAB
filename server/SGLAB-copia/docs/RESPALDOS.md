# Respaldos y recuperación

El respaldo diario de este entorno está programado mediante `sglab-backup.timer`
a las 03:00, hora local del servidor, con hasta cinco minutos de demora aleatoria.
`Persistent=true` recupera una ejecución perdida cuando el servidor vuelve a estar
encendido. No depende de una sesión de usuario abierta.

## Contenido y retención

Cada `var/backups/automaticos/sglab-*.tar.gz` contiene:

- `database.sql`: base sglab, incluyendo rutinas, eventos y triggers.
- `web-state.tar`: estado persistente de la web, incluida `totp-key.bin` de MFA.
- `.env`: configuración y credenciales locales.
- `var/pki` y `var/tls`: CA, claves privadas y certificados de HTTPS.
- `manifest.json`: fecha UTC y hashes SHA-256 de los componentes.

Se usa `mariadb-dump --single-transaction` con la cuenta root dentro del contenedor,
sin imprimir ni pasar la contraseña en argumentos. No realizar migraciones/DDL
mientras se ejecuta un respaldo. Las tablas actuales son InnoDB. No se detienen la
web ni la ingesta. El estado de archivos se copia después del dump: evitar rotar
las claves MFA/CA durante la copia. El respaldo no incluye el código del proyecto
ni la cola TOML; conservar código/versiones y definir su retención por separado.

La carpeta usa permisos 0700 y los paquetes 0600. **Contienen secretos y datos
personales; no subirlos a Git ni dejarlos en carpetas públicas.** No están cifrados:
una copia externa necesita un destino privado/cifrado y acceso restringido.
Los hashes detectan corrupción accidental, no prueban autenticidad frente a un
atacante que pueda reemplazar todo el paquete.

Solo se eliminan archivos `sglab-*.tar.gz` con más de siete días en esta carpeta,
y únicamente después de publicar una nueva copia correcta. Respaldos manuales de
otros directorios no se eliminan. Los archivos temporales se retiran si falla.

## Operación

Desde la raíz de SGLAB:

```bash
python3 infra/respaldos.py crear
python3 infra/respaldos.py verificar var/backups/automaticos/ARCHIVO.tar.gz
systemctl list-timers sglab-backup.timer
journalctl -u sglab-backup.service -n 30 --no-pager
sudo systemctl start sglab-backup.service
```

`verificar` comprueba hashes de todos los componentes y restaura el SQL en un
contenedor MariaDB 11.4 temporal, sin red ni puertos y con datos en tmpfs. Vuelve a
exportarlo y compara su hash con el original. El contenedor se elimina al terminar,
incluso si falla. Requiere memoria para esa base y la imagen local. No restaura ni
modifica la base real. Esto verifica la restauración SQL; no sustituye una prueba
completa de acceso MFA/HTTPS tras recuperar un servidor.

## Instalar en otro servidor

Preparar Docker, Compose, el proyecto, `.env`, HTTPS y acceso a Docker para el
usuario del proyecto. Luego:

```bash
python3 infra/configurar-respaldos.py --usuario USUARIO_DEL_PROYECTO
sudo install -m 0644 var/systemd/sglab-backup.service var/systemd/sglab-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sglab-backup.timer
sudo systemctl start sglab-backup.service
```

Las unidades contienen la ruta real de esta copia: regenerarlas si se mueve el
proyecto. Revisar la zona horaria del servidor con `timedatectl`. Supervisar los
fallos del servicio en journal; no hay notificaciones por correo implementadas.

## Recuperación de un servidor perdido

Este procedimiento reemplaza datos. Ejecutarlo en el servidor de recuperación,
con un paquete propio de confianza y después de comprobarlo con `verificar`.
Si existe una instalación previa, conservar una copia adicional antes de reemplazarla.

1. Recuperar la misma versión del código y preparar Docker/Compose. Detener el
   timer, la ingesta y la web si ya funcionan en el destino.
2. Extraer el paquete en una carpeta privada (0700). Conservar sus claves y `.env`
   fuera de cualquier carpeta pública; no imprimirlos en terminal/logs.
3. Copiar `.env`, `var/pki` y `var/tls` a la raíz del proyecto, preservando permisos.
   Si cambia la IP, emitir el certificado del servidor con la CA recuperada y
   actualizar la configuración OAuth; no crear una CA distinta sin necesidad.
4. Preparar un volumen **nuevo** para la recuperación. No iniciar dos MariaDB sobre
   el mismo volumen. Iniciar solo `db` con `docker compose up -d --wait db`; su
   inicialización prepara las cuentas técnicas de `.env`.
5. Restaurar `database.sql` con la web y la ingesta aún detenidas:

   ```bash
   docker compose exec -T db sh -c 'export MYSQL_PWD="$MARIADB_ROOT_PASSWORD"; exec mariadb -uroot' < /RUTA_PRIVADA/database.sql
   ```

6. Recuperar el estado web antes de arrancarla, conservando propietario y permisos:

   ```bash
   docker compose run --rm -T --no-deps --user root --entrypoint tar web -C /var/lib/sglab-web -xf - < /RUTA_PRIVADA/web-state.tar
   docker compose up -d web
   ```

7. Probar HTTPS, acceso del asistente con MFA, datos de inventario y una ingesta.
   Recuperar el servicio spawn con sus rutas y permisos. Regenerar/reactivar el
   timer de respaldos y ejecutar una nueva copia.

## Estado de verificación

El 02/11/2026 se creó una copia real y se restauró en un contenedor aislado. El SQL
exportado después de restaurar coincidió con el original. También se ejecutó el
servicio systemd correctamente y se probaron permisos, integridad, retención y
fallo de dump sin eliminación de copias anteriores con pruebas automatizadas.

**Pendiente institucional:** acordar un destino externo y hacer una copia semanal
fuera de este servidor, protegerla y comprobar su lectura. Una copia en el mismo
disco no cubre pérdida del equipo. Falta ensayar recuperación integral en otro
servidor con MFA y HTTPS; no se afirma haber probado ese escenario.
