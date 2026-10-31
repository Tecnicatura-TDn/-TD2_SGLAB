# Repositorio de código fuente

Aquí guardaremos el código `html`, `css`, `js` y `php` de la aplicación web de login de usuarios y las diferentes pantallas.

## Metodología a utilizar
Usaremos la metodología `MVC` para mantener una estructura de código limpia e independiente, de la misma forma empleamos los fundamentos de programación `SOLID` para mantener una lógica de código coherente.

## Roles
- Alumnos.
- Profesores.
- Asistente de coordinación.
- Admin.

## Vistas 
- Login 
    * Alumno : username y contraseña.
    * Profesor : doble factor de autenticación.
    * Asistente de coordinación y Admin : Multiple factor de autenticación (a ver con el scrum master senior)

- Pantalla de interacción con el sistema
    * Alumnos : ver la de computadora, su IP, un badge verde junto al equipo para verificar su estado y la opción de poder agregar un comentario.
    * Profesores : ver las computadoras del laboratorio (IP y badge de estado) y poder agregar un comentario del laboratorio.
    * Asistente de coordinación : Poder dar de alta un usuario con un rol, dar de alta un equipo en un laboratorio, operaciónes CRUD para usuarios y equipos.
    * Admin : Poder acceder con cualquier tipo de rol, dando la posibilidad de entrar con la pantalla de alumno, profesor ó asistente. 
