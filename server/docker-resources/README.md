# Imagenes del contenedor web y de base de datos

- `sglab-db.tar` imagen de la base de datos


Si en el futuro quieres levantar estas imágenes en otra computador, los comandos que vas a necesitar usar en la terminal son:

```bash
# Cargar el archivo de vuelta a Docker
docker load -i sglab-web.tar

# Verificar que apareció en tu lista de imagenes locales
docker images
```