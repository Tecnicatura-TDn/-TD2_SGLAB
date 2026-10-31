# Imagen oficial de MySQL (última versión).
# Para entornos estables conviene fijarla, por ejemplo: mysql:8.4 (LTS)
FROM mysql:latest


# Configuración personalizada del servidor (utf8mb4, caché, logs lentos, etc.)
COPY my.cnf /etc/mysql/conf.d/custom.cnf

# Scripts SQL de inicialización: se ejecutan en orden alfabético
# únicamente la primera vez, cuando el volumen de datos está vacío
COPY init/ /docker-entrypoint-initdb.d/

# Permisos correctos para el archivo de configuración
RUN chmod 644 /etc/mysql/conf.d/custom.cnf

# Puerto de MySQL
EXPOSE 3306

# Healthcheck: verifica que el servidor responde
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=10 \
  CMD mysqladmin ping -h localhost -u root -p"$MYSQL_ROOT_PASSWORD" --silent || exit 1