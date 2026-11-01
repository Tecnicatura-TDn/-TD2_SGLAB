# TD2 SGLAB Programación Web

Aplicación de ejemplo en PHP y MySQL, sin frameworks, con login, registro y dashboard. Todo corre en contenedores Docker.

## Tabla de contenidos

- [Requisitos](#requisitos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Puesta en marcha](#puesta-en-marcha)
- [Usuarios de prueba](#usuarios-de-prueba)
- [Rutas](#rutas)
- [Arquitectura](#arquitectura)
- [Comandos útiles](#comandos-útiles)
- [Notas de seguridad](#notas-de-seguridad)
- [Solución de problemas](#solución-de-problemas)
- [Licencia](#licencia)

## Requisitos

- Docker y Docker Compose (plugin `docker compose`)
- Git (opcional, para clonar el repositorio)

## Estructura del proyecto

```text
.
├── .env                         # Credenciales (no subir a git)
├── docker-compose.yml           # Servicios: db (MySQL) y web (PHP + Apache)
├── docker/
│   ├── mysql/
│   │   ├── Dockerfile
│   │   ├── my.cnf
│   │   └── init/01-init.sql     # Tabla y datos de prueba
│   └── php/
│       └── Dockerfile
├── app/                         # Código no accesible desde el navegador
│   ├── controllers/
│   │   ├── UsuarioController.php
│   │   └── DashboardController.php
│   ├── models/
│   │   ├── Usuario.php
│   │   └── Dashboard.php
│   └── views/
│       ├── login.html
│       ├── registro.html
│       └── dashboard.html
└── public/                      # Raíz web (/var/www/html)
    ├── index.php
    ├── login.php
    ├── registro.php
    ├── dashboard.php
    ├── logout.php
    ├── css/
    ├── img/
    ├── js/
    └── svg/
```

## Puesta en marcha

1. Crea el archivo `.env` en la raíz, a partir de `.env.example`:

   ```env
   MYSQL_ROOT_PASSWORD=rootsecreta
   MYSQL_DATABASE=miapp
   MYSQL_USER=appuser
   MYSQL_PASSWORD=apppassword
   ```

2. Levanta los contenedores:

   ```bash
   docker compose up -d --build
   ```

3. Comprueba que MySQL esté listo. `db` debe aparecer como `healthy`:

   ```bash
   docker compose ps
   ```

4. Abre la aplicación en el navegador:

   - Login: http://localhost:8080/login.php
   - Registro: http://localhost:8080/registro.php

## Usuarios de prueba

Todos los usuarios de `01-init.sql` usan la contraseña `clave123`:

| Correo              | Contraseña |
|---------------------|------------|
| admin@ejemplo.com   | clave123   |
| ana@ejemplo.com     | clave123   |
| carlos@ejemplo.com  | clave123   |
| maria@ejemplo.com   | clave123   |

También puedes crear una cuenta nueva desde la página de registro.

## Rutas

| URL              | Descripción                                                     |
|------------------|-----------------------------------------------------------------|
| `/`              | Redirige a `dashboard.php` si hay sesión, o a `login.php` si no |
| `/login.php`     | Inicio de sesión                                                |
| `/registro.php`  | Creación de cuenta                                              |
| `/dashboard.php` | Panel principal (requiere sesión)                               |
| `/logout.php`    | Cierra la sesión                                                |

## Arquitectura

```text
Navegador → public/*.php → Controlador → Modelo (PDO) → MySQL
                               ↓
                      app/views/*.html (marcadores {{...}} reemplazados)
                               ↓
                           Navegador
```

Solo los archivos de `public/` son accesibles por URL. Las vistas y la lógica viven en `app/`, fuera de la raíz web.

## Comandos útiles

```bash
docker compose logs -f web                                   # Logs de PHP/Apache
docker compose logs -f db                                    # Logs de MySQL
docker compose exec web php -m                               # Extensiones PHP
docker compose exec db mysql -u appuser -papppassword miapp  # Consola MySQL

docker compose down        # Detiene los contenedores (conserva los datos)
docker compose down -v     # Detiene y BORRA la base de datos
```

Para volver a ejecutar `01-init.sql`, el volumen debe estar vacío. Usa `docker compose down -v` antes de levantar de nuevo.

## Notas de seguridad

- Las contraseñas se guardan con `password_hash()` (bcrypt), nunca en texto plano.
- Las consultas usan PDO con sentencias preparadas.
- Los formularios tienen protección CSRF y la sesión se regenera al iniciar sesión.
- Las credenciales de `.env` y los datos de prueba son solo para desarrollo. Cámbialos antes de usar el proyecto en un entorno real.
- No expongas el puerto 3306 fuera de tu equipo en producción.
- Añade `.env` al `.gitignore` para no subir credenciales al repositorio.

## Solución de problemas

| Problema                                          | Causa probable                                 | Solución                                                                 |
|---------------------------------------------------|------------------------------------------------|--------------------------------------------------------------------------|
| `permission denied` en el socket de Docker        | Tu usuario no está en el grupo `docker`        | `sudo usermod -aG docker $USER` y volver a iniciar sesión                |
| `could not find driver`                           | Falta `pdo_mysql` en la imagen PHP            | `docker compose build --no-cache web`                                    |
| 404 en `/login.php`                               | El archivo no está en `public/`                | Revisa la estructura y el volumen `./public:/var/www/html`               |
| El login no acepta `clave123`                     | El hash en la base de datos no es válido       | `docker compose down -v` y volver a levantar                             |
| `service "web" is not running`                    | `db` no está `healthy` o falló el build        | Revisa `docker compose logs web` y `docker compose logs db`              |

## Licencia

Proyecto educativo de uso libre para prácticas de la materia.