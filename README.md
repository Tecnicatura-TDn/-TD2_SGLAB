# Repositorio de TD2 para el Sistema Gestor de Laboratorio

Repo del proyecto SGLAB del grupo TD2 BY Elian-zzz

Enlace a la carpeta de drive para el equipo de Base de Datos: [enlace a drive](https://drive.google.com/drive/folders/1MZuWgNfkVu3Hl370qXv6x-qYt4Yx1MZS?usp=sharing)

## Rutas del proyecto

- `doc/` Documentación, diagramas y desiciónes.
- `server/` Scripts de linux.
- `provision/` : Carpeta contenedora del ``provision.sh`` y sus recursos.

## Provision

__Qué permisos necesita el provision.sh__
__Cómo se ejecuta el provision__

## Servidor

Dentro de la carpeta `/server/`:

* `SGLAB-copia` : __Carpeta principal__ de la configuración del proyecto.
* `docker-resources` : Recursos docker para la __carpeta princilpal__.
---
## Configuración del server

### 🔒 Hardening de SSH: Autenticación Exclusiva por Clave Pública

Para asegurar el servidor contra ataques de fuerza bruta, el servicio SSH se configura para rechazar contraseñas e interfaces interactivas, permitiendo únicamente el acceso mediante claves SSH.

### 1. Configuración del Servidor (`sshd`)

Crea o edita el archivo de configuración en `/etc/ssh/sshd_config.d/01-security.conf`:

```text
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
```

_Validar sintaxis:_
```Bash
sudo sshd -t
``` 
```Bash
Recargar el demonio SSH:
Bash

sudo systemctl reload sshd
```
Prueba de conexión:
```Bash

# Acceso permitido con clave
ssh -i /ruta/a/clave_privada usuario@ip_servidor

# Verificación de rechazo de contraseña -> Permission denied (publickey)
ssh -o PreferredAuthentications=password usuario@ip_servidor
```

## Tareas de la reunion 02/11

1. Cerrar todos los puertos excepto el 80 y el 3306 con ufw.
2. Crear un usuario invitado de solo lectura para los pibe de base de datos (usuario invitado).
3. Logs en provision, centralizar logs.
4. Testear en distros RHEL, CENTOS, UBUNTU, DEBIAN, KALI.
