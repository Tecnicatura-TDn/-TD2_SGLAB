FROM php:apache

# Dependencias del sistema para compilar las extensiones que no vienen incluidas
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpng-dev \
        libjpeg-dev \
        libfreetype-dev \
        libzip-dev \
        libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Extensiones PHP (pdo, pdo_mysql, mysqli, mbstring, xml, curl y opcache ya vienen en la imagen)
RUN docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" gd zip intl bcmath exif

# Módulos de Apache
RUN a2enmod rewrite headers

# Composer
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

EXPOSE 80