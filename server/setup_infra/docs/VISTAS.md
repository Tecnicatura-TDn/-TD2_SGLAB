# Vistas de referencia y adaptación

Referencias entregadas: `views.zip` y `public.zip`, conservadas sin modificar en
`docs/`. Contienen las maquetas de login, docente y estudiante, los estilos, la
fuente Roboto y las imágenes. El archivo `views/paneles/asistente.php` está vacío.

Se adaptó la aplicación PHP existente a esta presentación, utilizando los recursos
originales: azul `#064795`, cabecera con logo UTU, pie institucional, tablas
alternadas y paneles con imagen del equipo y formulario de comentarios.

| Referencia | Implementación activa |
|---|---|
| layouts/header.php y footer.php | views/institutional-header.php y institutional-footer.php |
| login.php | views/login.php; segundo factor en views/mfa.php |
| paneles/docente.php | Inicio muestra el laboratorio asignado mediante views/laboratorio.php |
| paneles/estudiante.php | views/mi-equipo.php, después de identificar la PC por IP |
| paneles/asistente.php vacío | Administración existente con la misma cabecera, colores y tablas |
| public/img, public/svg y fuente | public/assets/img, assets/svg y assets/fonts |
| public/styles/*.css | public/assets/app.css, adaptado a las vistas reales y tamaños de pantalla |

Las rutas de la tabla son relativas a `server/web/app/`. Los ZIP solo sirven como
referencia; no se ejecutan ni se extraen automáticamente durante el despliegue.

## Comportamiento conservado

- El perfil lo determina la cuenta autenticada del servidor. El selector estático
  de la maqueta no concede roles: asistentes y docentes usan cédula/contraseña;
  asistentes requieren además TOTP y estudiantes ingresan mediante GitHub.
- El docente entra directamente a su laboratorio vigente, con todos sus equipos,
  estados y último diagnóstico. Sin asignación vigente se muestra el aviso para
  solicitarla al asistente. Puede comentar únicamente ese laboratorio.
- El estudiante consulta y comenta solamente su PC identificada por IP y captura
  reciente. Conserva la vista limitada a estado e identificación, sin mostrar los
  diagnósticos técnicos completos ni información de otros equipos.
- Los formularios envían POST reales con CSRF. Los comentarios persisten en la BD;
  se retiró el comportamiento de demostración que impedía enviarlos. Se conserva
  el límite existente de 4000 caracteres, indicado junto al formulario, y el
  historial de los últimos 50 comentarios accesibles por el usuario.
- La administración de laboratorios, equipos, usuarios y asignaciones sigue
  disponible para el asistente, con sus controles de autorización actuales.
- El estado administrativo y el resultado del recolector se presentan por separado.
  No se afirma que una PC esté online/offline a partir de una captura ni se atribuye
  un usuario conectado: esos indicadores del ejemplo no cuentan con una medición
  de conexión activa en el sistema actual.

El diseño permite seleccionar texto, mantiene el foco visible para teclado y
adapta las columnas a móvil. El pie no tapa los formularios largos. Las imágenes
y fuentes se sirven desde el propio Apache, sin CDN ni JavaScript adicional.
Se mantienen CSP, HTTPS y cookies de sesión seguras.

## Aplicar cambios

```bash
docker compose up -d --build --no-deps web
```

La web continúa en **https://192.168.50.83**. No requiere cambios de esquema ni
recrear el contenedor de BD. Si el navegador conserva estilos anteriores,
recargar con Ctrl+F5.

## Validación

Se verificó sintaxis PHP y se aprobaron las 10 pruebas de integración existentes:

```bash
SGLAB_TEST_WEB=1 python3 -m unittest discover -s tests -v
```

La revisión visual utiliza Chromium con ventanas de 1440×1000 y 390×844. Se
comparan capturas de las maquetas (HTML estático con las rutas de recursos
resueltas) y de la aplicación real. Las evidencias locales quedan en
`var/verificacion-vistas/`, fuera de Git. El navegador de verificación confía
explícitamente en la clave pública del certificado local; las pruebas HTTPS
validan además la CA y la IP.

Resultado del 29/10/2026: revisión aprobada. Se verificaron login, alta MFA de un
asistente, navegación de administración, laboratorio vigente del docente,
identificación de la PC del estudiante, envío y persistencia de ambos tipos de
comentarios y cierre de sesión. No se detectaron errores de consola, imágenes
rotas ni desborde horizontal de la página en esas ventanas. Las tablas anchas
permiten desplazamiento dentro de su propio contenedor en móvil. Se corrigió un
ID duplicado entre el contenido principal y el campo de comentario.

Las cuentas, asignaciones y registros utilizados para esta revisión son sintéticos
y se eliminan al terminar. El acceso de estudiante se simula por CLI solamente
para revisar su panel autorizado, igual que en las pruebas de permisos: no prueba
el OAuth real de GitHub, que sigue pendiente de registrar y configurar.
El usuario confirmó HTTPS sin advertencias en su navegador Brave el 29/10/2026,
tras cerrarlo y volver a abrirlo. La distribución del certificado y la prueba del
flujo completo en las PC de Windows de la UTU continúan pendientes.
