# Autenticación por rol

## Uso

### Asistente (administrador)

1. Abrir la web e ingresar cédula y contraseña.
2. La primera vez, escanear el QR con Google Authenticator.
3. Ingresar el código de seis dígitos para confirmar la vinculación y entrar.
4. En los siguientes ingresos se pide contraseña y código; no se vuelve a mostrar el QR.

Hasta validar el código no existe sesión administrativa. La clave manual está
disponible como alternativa al escaneo solo durante el alta inicial. El desafío
vence a los diez minutos. Los códigos cambian cada 30 segundos y se admite un
intervalo de desfase de reloj. Un código ya utilizado no sirve para otro ingreso.
Se limitan los intentos del segundo factor, independientemente de la contraseña.

Si aparece **Verificá tu acceso** y no hay QR, esa cuenta ya tiene MFA activado.
La pantalla muestra la cédula para identificarla. Hay que usar el autenticador
que se vinculó antes; el QR no se vuelve a exponer en los ingresos normales.
Si nunca se vinculó en el teléfono actual o se perdió el acceso, seguir
**Recuperar acceso MFA** para la cuenta concreta. El restablecimiento invalida
las sesiones y el autenticador anterior; después se vuelve a ingresar con
contraseña para recibir un QR nuevo.

La cuenta de prueba administrativa conserva su cédula y contraseña; debe
configurar su propio autenticador al ingresar. No tiene un QR preconfigurado.

### Docente

Ingresar cédula y contraseña. El docente entra directamente a su panel, que muestra
solo el laboratorio que tiene asignado en ese momento, las PC y sus últimos estados.
Puede comentar sobre ese laboratorio. Las asignaciones futuras, vencidas o retiradas
no dan acceso. El asistente ingresa con MFA por ser el administrador del sistema.

### Estudiante

1. El asistente o administrador crea la cuenta de estudiante con el email correcto.
2. El estudiante abre la web y pulsa **Continuar con GitHub**.
3. Autoriza la OAuth App de SGLAB en GitHub.
4. Su **email principal verificado de GitHub** debe coincidir con el registrado en SGLAB.
5. El sistema lo lleva a su PC, detectada por IP como se describe en WEB.md.

No se permite login por contraseña para ALUMNO. No se crean usuarios automáticamente.
Un email público en el perfil no basta: se consulta el listado privado de emails
con el permiso user:email y se exige principal/verificado. Las cuentas inactivas o
de otros roles no pueden ingresar por este flujo. La primera coincidencia vincula
el ID estable de GitHub; otra cuenta GitHub no puede suplantarla aunque use el mismo
email. Si cambia el email, actualizarlo en SGLAB y conservar la misma cuenta GitHub.

## Estado actual de GitHub

**La integración está implementada y preparada, pero no activada:** todavía no hay
una OAuth App registrada ni Client ID/Client Secret configurados. El botón lo indica
y permanece deshabilitado. No existe un login simulado ni un bypass de producción.
La contraseña anterior de la cuenta de estudiante de prueba ya no da acceso.
También hay que completar su email real de GitHub desde Usuarios y asignaciones.

### Probar GitHub con una cuenta personal

La cuenta de estudiante de prueba es **CI 99000004**. Se le asigna el email
principal verificado de la cuenta GitHub que se usará para la prueba. El vínculo
con el ID de GitHub se crea al completar el OAuth real, no por conocer su usuario
público ni por tener una conexión GitHub en una herramienta de desarrollo.

`usuarios.correo` es único: si ese email ya pertenece a una cuenta de asistente,
no puede repetirse en el estudiante. Hay que elegir otra cuenta GitHub o trasladar
el correo al estudiante, dejando vacío el correo opcional de la cuenta de personal.
Ese traslado requiere identificar las dos cuentas; no cambia sus roles ni el MFA.
El cambio de correo invalida las sesiones de las cuentas modificadas, como los
demás cambios de identidad. No se desactiva la unicidad ni se fusionan perfiles.

La herramienta GitHub conectada puede identificar el perfil del usuario, pero no
registra una OAuth App de SGLAB ni aporta automáticamente su Client ID/Secret.
El registro se completa en [New OAuth App](https://github.com/settings/applications/new)
con los valores indicados abajo. Guardar el Client Secret directamente en `.env`,
fuera de Git y sin enviarlo al chat. No usar un token personal en su lugar.

### Registrar y configurar la OAuth App

En GitHub: Settings → Developer settings → OAuth Apps → New OAuth App.
Para este entorno de pruebas:

- Application name: SGLAB.
- Homepage URL: `https://192.168.50.83`.
- Authorization callback URL: `https://192.168.50.83/?page=github_callback`.

La URL debe ser accesible desde el navegador del usuario. Si cambia el servidor,
usar un DNS estable o actualizar la app, el certificado y la configuración.
Completar **localmente** `.env`, sin publicar el secreto ni enviarlo por chat:

```dotenv
GITHUB_CLIENT_ID=valor_del_client_id
GITHUB_CLIENT_SECRET=valor_del_client_secret
GITHUB_REDIRECT_URI=https://192.168.50.83/?page=github_callback
```

Después ejecutar desde SGLAB:

```bash
docker compose up -d web
```

El flujo utiliza state de un solo uso, expiración y PKCE S256. El intercambio del
código por token se realiza en el servidor con TLS verificado. Solo se piden
read:user y user:email, sin acceso a repositorios. El token se utiliza para verificar
la identidad y se descarta: no se almacena en BD, cookies ni sesión.
Los logs Apache no registran la query de las URL para no conservar códigos OAuth.

Referencias: [flujo oficial OAuth de GitHub](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps),
[emails verificados de GitHub](https://docs.github.com/en/rest/users/emails).

## Recuperar acceso MFA

Si un asistente administrador pierde el teléfono, el responsable del servidor puede
restablecer la vinculación desde una terminal interactiva:

```bash
docker compose exec web php bin/reset-mfa.php CEDULA
```

Solicita confirmar escribiendo la cédula. Invalida las sesiones y el desafío anterior.
El siguiente ingreso exige la contraseña existente y vincular un nuevo autenticador.
No elimina usuarios ni cambia la contraseña. No hay restablecimiento público de MFA
ni excepción por rol para omitirlo. El primer administrador se sigue creando con
`docker compose exec web php bin/crear-asistente.php`.

## Almacenamiento y despliegue

La migración 004 añade a usuarios: totp_secret (cifrado), totp_enabled,
totp_last_step (contra reutilización), github_id (único) y auth_version.
El esquema mantiene nueve tablas. El SQL inicial también incorpora estas columnas.
Aplicada con respaldo previo de la BD; es repetible en MariaDB.

El secreto TOTP se cifra con AES-256-GCM y queda vinculado a la cédula. La clave
se crea localmente en `/var/lib/sglab-web/totp-key.bin`, con permisos 0600, dentro
del volumen persistente **sglab_web_state**. No se incluye en la imagen ni en Git.
**Un respaldo de BD por sí solo no permite recuperar MFA: también hay que conservar
la clave del volumen web_state en un respaldo protegido.** Perder ese volumen obliga
a restaurar la clave o restablecer MFA de las cuentas. No borrar volúmenes al desplegar.

Los cambios de contraseña, rol, email o activación incrementan auth_version e
invalidan las sesiones existentes. Una sesión de contraseña no se convierte en
administrativa al cambiar el rol: debe autenticar también con TOTP. Una sesión de
personal tampoco se convierte automáticamente en una sesión GitHub de estudiante.
Las sesiones anteriores a este cambio requieren un nuevo ingreso.

El QR se genera en el propio servidor con [endroid/qr-code](https://github.com/endroid/qr-code/tree/5.1.0),
sin enviar secretos a servicios externos. Dependencias Composer bloqueadas en
composer.lock; Docker las instala en una etapa separada. TOTP sigue
[RFC 6238](https://www.rfc-editor.org/rfc/rfc6238).

## Pruebas y límites de verificación

```bash
SGLAB_TEST_WEB=1 python3 -m unittest discover -s tests -v
```

`test_auth_methods.py` prueba vectores públicos RFC, cifrado, alta MFA, QR SVG,
acceso bloqueado antes del código, rechazo de códigos reutilizados, invalidación
por restablecimiento y login local de docente. OAuth se prueba con respuestas de
proveedor simuladas en CLI: state, expiración, PKCE, email no verificado/incorrecto,
rol no permitido, vínculo de ID y sesión final. No necesita credenciales reales.

Las pruebas de inventario simulan mediante CLI la sesión de un alumno de prueba
posterior a GitHub para verificar permisos. Ese mecanismo es exclusivo del código
de tests con acceso al contenedor y no es accesible por HTTP. No valida el login
real de GitHub, que sigue pendiente de registrar/configurar la OAuth App y de una
prueba manual con una cuenta real. El escaneo con un teléfono real también queda
para la prueba manual; el algoritmo y el QR se verifican automáticamente.

HTTPS funciona en el servidor con una CA local para la red del laboratorio.
Antes de probar desde Windows instalar la CA pública: [HTTPS.md](HTTPS.md).
Las pruebas validan su firma e IP; nunca omiten la verificación del certificado.

## Tres perfiles funcionales

Administrador en el ejemplo del profesor equivale a ASISTENTE en SGLAB. El alias
histórico ADMINISTRADOR y ASISTENTE tienen idénticos permisos y ambos requieren
MFA, incluida cualquier sesión antigua que antes hubiera entrado solo por contraseña.
No se cambiaron ni eliminaron las cuentas existentes. El alias se normaliza a
ASISTENTE en la interfaz. Los docentes siguen con contraseña y alumnos con GitHub.
