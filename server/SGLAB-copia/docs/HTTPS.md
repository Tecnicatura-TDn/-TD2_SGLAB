# HTTPS dentro del laboratorio

La web activa es **https://192.168.50.83**, puerto 443. La IP debe ser fija o tener
reserva DHCP. `http://192.168.50.83:8080` redirige las visitas GET/HEAD a HTTPS;
los POST por HTTP se rechazan y no llegan a PHP. Usar siempre la dirección HTTPS
para ingresar credenciales.

El archivo de configuración de Apache activa HTTPS, pero necesita además un
certificado del servidor y su clave privada. Para esta IP interna se creó una
autoridad local (CA). Su certificado público se instala una vez por usuario de
Windows, para que el navegador reconozca los certificados que firma.

## Qué archivo va en cada lugar

| Archivo | Uso | Distribución |
|---|---|---|
| server/web/000-default.conf | VirtualHost TLS y redirección HTTP | Código del proyecto |
| var/pki/SGLAB-CA.crt | Certificado público de la CA | Conservar con la CA |
| var/pki/SGLAB-CA.key | Clave privada de la CA | Solo servidor; 0600; fuera del contenedor |
| var/tls/server.crt | Certificado para la IP y localhost | Apache, montaje de solo lectura |
| var/tls/server.key | Clave privada del servidor | Solo servidor y Apache; 0600 |
| var/certificados/SGLAB-CA.crt | Copia pública para Windows | Este es el archivo que se entrega a las PC |

`var/` está excluido de Git. Las claves no se incluyen en la imagen Docker ni se
publican en la web. Apache usa TLS 1.2/1.3 y termina el cifrado directamente:
PHP recibe HTTPS y la IP del navegador; la detección de PC conserva su funcionamiento.
Las cookies de sesión llevan Secure, HttpOnly y SameSite=Lax.

## Instalar la CA en Windows sin terminal

El error **NET::ERR_CERT_AUTHORITY_INVALID** indica que el navegador no reconoce
la autoridad emisora. En este despliegue la CA es local: configurar HTTPS en el
servidor no instala automáticamente esa confianza en las PC.

El script `infra/configurar-https.py` también genera
**var/certificados/Instalar-certificado-SGLAB.zip**. Copiarlo a Windows, extraer
todo y abrir **Instalar-certificado-SGLAB.bat** con doble clic. El instalador
verifica la huella SHA-256 incluida, importa la CA en **Cert:\CurrentUser\Root**
y comprueba su presencia. Si Windows pide confirmar la instalación de la autoridad,
confirmar **SGLAB Autoridad Local**. Cerrar todas las ventanas del navegador y
abrirlo otra vez. Se puede repetir: si la CA ya existe, conserva la instalación.
El ZIP contiene únicamente el certificado público, su huella, las instrucciones
y los dos lanzadores; no incluye claves privadas. La huella del paquete sirve
para comprobar su consistencia; obtener el ZIP por un medio de confianza.
La ejecución del instalador en una PC Windows real queda pendiente de comprobar.
Se validaron la sintaxis PowerShell, la lectura del certificado DER, su huella
y el contenido del ZIP sin claves privadas. Esto no sustituye comprobar la
importación en el almacén de Windows y volver a abrir el navegador allí.

Alternativa manual:

1. Copiar **solo** `var/certificados/SGLAB-CA.crt` del servidor a la PC mediante
   un medio de confianza (por ejemplo, SCP o un pendrive preparado por el asistente).
2. Abrir el archivo con doble clic y elegir **Instalar certificado**.
3. Elegir **Usuario actual**.
4. Elegir **Colocar todos los certificados en el siguiente almacén** y seleccionar
   **Entidades de certificación raíz de confianza**.
5. Confirmar la instalación de **SGLAB Autoridad Local**, cerrar y abrir el navegador.
6. Entrar a **https://192.168.50.83** y comprobar que reconoce el certificado.

Esta instalación corresponde al usuario actual y no necesita elevar a administrador
en Windows con configuración normal. En equipos administrados las políticas de la
institución pueden restringirla. Para todos los usuarios de una PC se requiere
distribución institucional o el almacén del equipo. Edge/Chrome usan el almacén
de Windows; verificar la confianza por separado si se usa otro navegador.
No se modifica automáticamente el instalador del recolector.

Si el error persiste, abrir `certmgr.msc` desde el mismo usuario de Windows y
revisar **Entidades de certificación raíz de confianza → Certificados**. Debe
aparecer **SGLAB Autoridad Local**. Instalar `server.crt` en Personal no añade
confianza en la CA. Si la CA está en el almacén correcto y sigue fallando, revisar
el navegador concreto y el emisor/huella del certificado que recibe: podría tener
un almacén propio o estar recibiendo otro certificado.

El asistente puede comparar la huella SHA-256 pública con el servidor:

```bash
openssl x509 -in var/certificados/SGLAB-CA.crt -noout -fingerprint -sha256
```

Alternativa PowerShell, en el usuario actual:

```powershell
Import-Certificate -FilePath .\SGLAB-CA.crt -CertStoreLocation Cert:\CurrentUser\Root
```

## Preparar otro servidor o cambiar la IP

Desde la raíz de SGLAB, con `.env` configurado y OpenSSL/Python 3 instalados:

```bash
python3 infra/configurar-https.py 192.168.50.83
docker compose config --quiet
docker compose up -d --build --force-recreate web
```

El script conserva la CA existente. Si falta, la crea con validez de diez años;
emite un certificado del servidor válido por un año con SAN para la IP indicada,
127.0.0.1 y localhost. Si el certificado sigue válido para la IP y le queda más de
un mes, lo reutiliza. Si la CA está incompleta o no corresponde a su clave,
se detiene y pide restaurarla.

Actualiza `.env`: APP_HTTPS_PORT (443) y SGLAB_HTTPS_ORIGIN. APP_PORT sigue siendo el
puerto HTTP de redirección (8080). Se puede elegir `--puerto 8443` para HTTPS;
el origen y la redirección incluirán ese puerto. Ambos puertos deben ser distintos.
Abrir el puerto HTTPS correspondiente en el firewall; en el servidor actual se
habilitó el servicio https en la zona public de firewalld (runtime y permanente).

Para usar otra red, reemplazar la IP del comando por la IP real del servidor allí.
Se conserva la misma CA, por lo que las PC que ya confían en ella no necesitan
importarla otra vez. Actualizar además los clientes SSH y la OAuth App de GitHub
si estaba registrada. Mientras GITHUB_CLIENT_ID está vacío, el script prepara
GITHUB_REDIRECT_URI con la URL HTTPS actual. No crea una OAuth App ni sus credenciales.

## Renovación y recuperación

El certificado del servidor emitido el 29/10/2026 vence el 29/10/2027. La renovación
todavía es manual: ejecutar el script durante el último mes o forzarla antes:

```bash
python3 infra/configurar-https.py 192.168.50.83 --renovar
docker compose up -d --force-recreate web
openssl x509 -in var/tls/server.crt -noout -dates
```

Respaldar `var/pki` y `var/tls` en almacenamiento protegido, junto con la BD y la
clave MFA de web_state. Perder la clave de la CA exige crear otra autoridad y
volver a distribuir su certificado. No regenerarla en cada despliegue ni borrar
volúmenes. Conservar también los ajustes de `.env` para recuperar el servicio.

## Verificación

```bash
curl --cacert var/certificados/SGLAB-CA.crt -I https://192.168.50.83/
curl -I http://192.168.50.83:8080/
SGLAB_TEST_WEB=1 python3 -m unittest discover -s tests -v
```

La prueba HTTPS valida certificado, cookies Secure, redirección a un origen fijo,
rechazo de formularios HTTP y rechazo de una CA desconocida. Las demás pruebas
ejercitan login, MFA, permisos por rol, inventario e ingesta sobre HTTPS. Permiten
SGLAB_WEB_URL, SGLAB_HTTP_URL y SGLAB_TEST_CA_FILE para otro despliegue de pruebas.
El 29/10/2026 el usuario confirmó que HTTPS quedó sin advertencias en Brave después
de cerrar completamente el navegador y volver a abrirlo. La prueba desde las PC
de la UTU y la distribución de confianza a esos usuarios siguen pendientes.

Referencias: [configuración TLS de Apache](https://httpd.apache.org/docs/2.4/ssl/ssl_howto.html),
[certificados de una CA local](https://letsencrypt.org/docs/certificates-for-localhost/),
[almacén de certificados de Windows](https://learn.microsoft.com/en-us/powershell/module/pki/import-certificate?view=windowsserver2025-ps).
