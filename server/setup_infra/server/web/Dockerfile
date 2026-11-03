FROM composer:2 AS vendor
WORKDIR /app
COPY app/composer.json app/composer.lock ./
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --optimize-autoloader

FROM php:8.3-apache
RUN docker-php-ext-install pdo pdo_mysql mysqli
RUN a2enmod rewrite ssl
COPY 000-default.conf /etc/apache2/sites-available/000-default.conf
WORKDIR /var/www/html
COPY app/ /var/www/html/
COPY --from=vendor /app/vendor/ /var/www/html/vendor/
RUN install -d -m 0700 -o www-data -g www-data /var/lib/sglab-web
EXPOSE 80 443
