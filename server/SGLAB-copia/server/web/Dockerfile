FROM php:8.3-apache

# Driver necesario para que PHP se conecte a MariaDB mediante PDO.
RUN docker-php-ext-install pdo pdo_mysql mysqli

# Habilita mod_rewrite para futuras rutas de la aplicación.
RUN a2enmod rewrite

# Configuración del VirtualHost de SGLAB.
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf

WORKDIR /var/www/html

# Copia la aplicación PHP dentro del contenedor.
COPY app/ /var/www/html/

EXPOSE 80
