FROM php:apache

# Dependencias del sistema para compilar las extensiones
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpng-dev \
        libjpeg-dev \
        libfreetype-dev \
        libzip-dev \
        libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Extensiones PHP. pdo_mysql y mysqli NO vienen en la imagen base.
RUN docker-php-ext-install pdo_mysql mysqli \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" gd zip intl bcmath exif

# Módulos de Apache
RUN a2enmod rewrite headers

# Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

EXPOSE 80
