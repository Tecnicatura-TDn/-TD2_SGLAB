-- SGLAB: modelo inicial corregido. Instalaciones nuevas únicamente.
-- Para una BD existente de cinco tablas usar database/migrations/001_modelo_inicial.sql.
CREATE DATABASE IF NOT EXISTS sglab
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE sglab;

CREATE TABLE usuarios (
    ci INT UNSIGNED NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    correo VARCHAR(254) NULL,
    password_hash VARCHAR(255) NOT NULL,
    tipo_usuario ENUM('ALUMNO', 'DOCENTE', 'ASISTENTE', 'ADMINISTRADOR') NOT NULL,
    PRIMARY KEY (ci),
    UNIQUE KEY uq_usuarios_correo (correo)
) ENGINE=InnoDB;

CREATE TABLE laboratorio (
    id_laboratorio INT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    PRIMARY KEY (id_laboratorio)
) ENGINE=InnoDB;

CREATE TABLE equipo (
    id_equipo INT UNSIGNED NOT NULL AUTO_INCREMENT,
    num_serie VARCHAR(100) NULL,
    smbios_uuid CHAR(36) NULL,
    estado_administrativo ENUM('OPERATIVA', 'EN_REPARACION', 'FUERA_DE_SERVICIO')
        NOT NULL DEFAULT 'OPERATIVA',
    hostname VARCHAR(255) NULL,
    mac CHAR(17) NULL,
    cpu VARCHAR(255) NULL,
    ram_gb DECIMAL(10,2) UNSIGNED NULL,
    disco_tipo VARCHAR(30) NULL,
    disco_total_gb DECIMAL(12,2) UNSIGNED NULL,
    id_laboratorio INT UNSIGNED NULL,
    PRIMARY KEY (id_equipo),
    UNIQUE KEY uq_equipo_num_serie (num_serie),
    UNIQUE KEY uq_equipo_smbios_uuid (smbios_uuid),
    CONSTRAINT fk_equipo_laboratorio FOREIGN KEY (id_laboratorio)
        REFERENCES laboratorio (id_laboratorio)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

-- Se interpreta cada registro como una ejecución de un equipo.
-- Un equipo puede acumular varios registros; un usuario puede realizar varios.
CREATE TABLE registro (
    id_registro BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_equipo INT UNSIGNED NOT NULL,
    usuario_ci INT UNSIGNED NULL,
    id_ejecucion CHAR(36) NULL,
    hash_archivo CHAR(64) NULL,
    fecha_recepcion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hostname_reportado VARCHAR(255) NULL,
    sistema_operativo VARCHAR(255) NULL,
    cpu VARCHAR(255) NULL,
    ram_gb DECIMAL(10,2) UNSIGNED NULL,
    mac CHAR(17) NULL,
    id_laboratorio_observado INT UNSIGNED NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT NULL,
    ip VARCHAR(45) NULL,
    estado ENUM('OK', 'ERROR') NOT NULL,
    disco_libre_gb DECIMAL(12,2) UNSIGNED NULL,
    PRIMARY KEY (id_registro),
    UNIQUE KEY uq_registro_id_ejecucion (id_ejecucion),
    CONSTRAINT fk_registro_laboratorio FOREIGN KEY (id_laboratorio_observado)
        REFERENCES laboratorio (id_laboratorio)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    KEY idx_registro_equipo_fecha (id_equipo, fecha),
    CONSTRAINT fk_registro_equipo FOREIGN KEY (id_equipo)
        REFERENCES equipo (id_equipo)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_registro_usuario FOREIGN KEY (usuario_ci)
        REFERENCES usuarios (ci)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE comentario (
    id_comentario BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_equipo INT UNSIGNED NOT NULL,
    autor_ci INT UNSIGNED NOT NULL,
    contenido TEXT NOT NULL,
    fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_comentario),
    KEY idx_comentario_equipo_fecha (id_equipo, fecha_hora),
    CONSTRAINT fk_comentario_equipo FOREIGN KEY (id_equipo)
        REFERENCES equipo (id_equipo)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_comentario_autor FOREIGN KEY (autor_ci)
        REFERENCES usuarios (ci)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

-- Una fila por disco físico observado en una ejecución.
CREATE TABLE registro_disco (
    id_registro BIGINT UNSIGNED NOT NULL,
    orden SMALLINT UNSIGNED NOT NULL,
    dispositivo VARCHAR(255) NULL,
    modelo VARCHAR(255) NULL,
    num_serie VARCHAR(255) NULL,
    tipo ENUM('HDD', 'SSD', 'OTRO') NULL,
    capacidad_total_gb DECIMAL(12,2) UNSIGNED NULL,
    PRIMARY KEY (id_registro, orden),
    CONSTRAINT fk_disco_registro FOREIGN KEY (id_registro)
        REFERENCES registro (id_registro)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;

-- Se mide espacio libre por sistema de archivos, no por disco físico.
-- La relación con disco es opcional: LVM/RAID puede abarcar varias unidades.
CREATE TABLE registro_sistema_archivos (
    id_registro BIGINT UNSIGNED NOT NULL,
    orden SMALLINT UNSIGNED NOT NULL,
    orden_disco SMALLINT UNSIGNED NULL,
    dispositivo VARCHAR(255) NULL,
    punto_montaje VARCHAR(1024) NULL,
    tipo VARCHAR(50) NULL,
    capacidad_total_gb DECIMAL(12,2) UNSIGNED NULL,
    espacio_libre_gb DECIMAL(12,2) UNSIGNED NULL,
    PRIMARY KEY (id_registro, orden),
    CONSTRAINT ck_fs_espacio CHECK (
        espacio_libre_gb IS NULL OR capacidad_total_gb IS NULL
        OR espacio_libre_gb <= capacidad_total_gb
    ),
    CONSTRAINT fk_fs_registro FOREIGN KEY (id_registro)
        REFERENCES registro (id_registro)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_fs_disco FOREIGN KEY (id_registro, orden_disco)
        REFERENCES registro_disco (id_registro, orden)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB;
