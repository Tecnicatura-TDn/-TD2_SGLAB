-- Solo para el esquema inicial de cinco tablas. Ejecutar una sola vez.
-- Hacer respaldo antes de aplicar. El DDL de MariaDB hace COMMIT implícito.
-- No ejecutar contra el esquema anterior de 15 tablas.
USE sglab;
ALTER TABLE equipo
    MODIFY num_serie VARCHAR(100) NULL,
    ADD smbios_uuid CHAR(36) NULL,
    ADD estado_administrativo ENUM('OPERATIVA','EN_REPARACION','FUERA_DE_SERVICIO')
        NOT NULL DEFAULT 'OPERATIVA',
    ADD UNIQUE KEY uq_equipo_smbios_uuid (smbios_uuid);
ALTER TABLE registro
    ADD id_ejecucion CHAR(36) NULL,
    ADD hash_archivo CHAR(64) NULL,
    ADD fecha_recepcion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD hostname_reportado VARCHAR(255) NULL,
    ADD sistema_operativo VARCHAR(255) NULL,
    ADD cpu VARCHAR(255) NULL,
    ADD ram_gb DECIMAL(10,2) UNSIGNED NULL,
    ADD mac CHAR(17) NULL,
    ADD id_laboratorio_observado INT UNSIGNED NULL,
    ADD UNIQUE KEY uq_registro_id_ejecucion (id_ejecucion),
    ADD CONSTRAINT fk_registro_laboratorio FOREIGN KEY (id_laboratorio_observado)
        REFERENCES laboratorio (id_laboratorio)
        ON DELETE RESTRICT ON UPDATE RESTRICT;

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
