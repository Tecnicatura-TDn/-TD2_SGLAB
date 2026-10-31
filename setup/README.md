# Documentación del código de `provision.sh`


Para probar el script ejecutar en la consola, el script está en estado de desarrollo y review, por lo que el script aún no instala nada, solo es interfaz CLI.
```bash
sudo ./provision.sh
```



Tareas a tener a realizar:

- Instalar sudo, agregar a usuarios a sudoers file
- Instalar dependencias:
  ___install_basic_tools___
  - `rsync` [x] 
  - `ssh server` [x]
  - `git` [x]
  ___provision_docker_laravel___
  - `Docker` [ ]
  - `Docker-compose` [ ]
  - `Clonar el repositorio` [ ]
  - `Configurar las claves publicas y privadas para conectarse mediante ssh` [ ]
  - `Configurar reglas de firewallD` [ ] (opcional)
  - `Setear el sistema de logs` [x]


### Tratamiento de rsync
Comando para sincronizar los cambios de una carpeta y su contenido en el origen y actualizarlo en el destino
```bash
rsync -avz --delete /ruta/de/la/carpeta/origen/ usuario_host@IP_DEL_HOST:/ruta/del/directorio/destino/
```
`-a` --> Recursivo
`-v` --> verbose
`-z` --> Compress (viaje rapido por la red)

### Cambio de `echo -e` a `printf` con `%s`

Para asegurar la compatibilidad con diferentes shells y distribuciones de Linux, se cambió de `echo -e` a `printf` con `%s`. Esto se hizo por las siguientes razones:

1. **Portabilidad**:
   - `echo` puede tener comportamientos diferentes en diferentes shells (como `bash` y `dash`).
   - `printf` es una función POSIX estándar y tiene un comportamiento consistente en todas las shells.

2. **Formato avanzado**:
   - `printf` permite usar especificadores de formato como `%s`, `%d`, `%f`, etc., lo que facilita la impresión de múltiples cadenas de texto con diferentes formatos.
   - `echo` no permite formatear el texto de manera avanzada.

3. **Multi-distro**:
   - Al usar `printf`, el código es más compatible con diferentes distribuciones de Linux, ya que `printf` es una función estándar en todas las shells POSIX.

**Ejemplo de uso**:

- **Uso de `echo`**:
  ```sh
  echo "Hola, $USER. La fecha es $(date +'%Y-%m-%d %H:%M:%S')."
  ```
  - **Salida**:
    ```
    Hola, vmelian. La fecha es 2023-10-09 13:01:25.
    ```

- **Uso de `printf`**:
  ```sh
  printf "Hola, %s. La fecha es %s.\n" "$USER" "$(date +'%Y-%m-%d %H:%M:%S')"
  ```
  - **Salida**:
    ```
    Hola, vmelian. La fecha es 2023-10-09 13:01:25.
    ```

**Conclusión**:

- `echo` es más simple y fácil de usar para imprimir texto en la consola.
- `printf` es más avanzado y permite formatear el texto de manera avanzada.
- `printf` es más portable y compatible con diferentes shells.
- `printf` es mejor para imprimir múltiples cadenas de texto con diferentes formatos.

En el archivo `logs.sh`, usamos `printf` con `%s` para imprimir múltiples cadenas de texto con diferentes formatos, como la fecha y hora actual y el mensaje de log. Esto hace que el código sea más compatible con diferentes shells y más portable.

### Comparación entre `provision.sh` y `ejemplo_provision.sh`

Para mejorar la mantenibilidad y limpieza del código, se decidió reorganizar las funciones entre los archivos `provision.sh` y `ejemplo_provision.sh`. A continuación, se muestra una tabla con las funciones que se movieron y el motivo de estos cambios:

| Función | Archivo Original | Archivo Destino | Motivo |
|---------|------------------|------------------|--------|
| `log`, `error`, `warn`, `info`, `mensaje_warn`, `mensaje` | `provision.sh` | `logs.sh` | Separar las funciones de logging en un archivo dedicado para mejorar la modularidad y reutilización. |
| `setup_ssh`, `setup_github_ssh` | `provision.sh` | `setup_ssh.sh` | Separar las funciones de configuración de SSH en un archivo dedicado para mejorar la modularidad y reutilización. |
| `install_apache`, `install_mysql`, `install_php`, `finalize_lamp_setup`, `provision_lamp_stack` | `provision.sh` | `install_lamp.sh` | Separar las funciones de instalación del entorno LAMP en un archivo dedicado para mejorar la modularidad y reutilización. |
| `install_docker`, `install_docker_compose`, `clone_repository`, `setup_project`, `provision_docker_laravel` | `provision.sh` | `setup-proyect_docker.sh` | Separar las funciones de configuración del entorno Docker + Laravel en un archivo dedicado para mejorar la modularidad y reutilización. |

**Conclusión**:

La reorganización de las funciones entre los archivos `provision.sh` y `ejemplo_provision.sh` ha mejorado la mantenibilidad y limpieza del código. Se ha separado cada conjunto de funciones relacionadas en archivos dedicados para mejorar la modularidad y reutilización. Esto hace que el código sea más fácil de entender, mantener y actualizar.

### Cambio de ubicaciones de funciones

Cambiamos la ubicación de las funciones que anteriormente estaban dentro de `provision.sh`, ahora están dentro de la carpeta `./SGLAB/setup/resources/` para modularizar el script.

### Cambios en herramientas básicas (`provision.sh`) para Debian 13

* **`apt-transport-https` (Eliminado):** Soporte HTTPS integrado de forma nativa en el paquete principal `apt`. No requiere instalación adicional.
* **`gnupg-agent` (Sustituido por `gnupg`):** El agente de cifrado y autenticación ya viene incluido de forma interna en el paquete moderno `gnupg`.
* **`software-properties-common` (Eliminado):** Destinado originalmente a PPAs de Ubuntu. En Debian puro, la gestión de repositorios externos y claves GPG se realiza de forma manual y directa en `/etc/apt/sources.list.d/` y `/etc/apt/keyrings/`.