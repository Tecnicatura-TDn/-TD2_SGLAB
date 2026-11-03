-- Reportes manuales, separados del diagnóstico y del estado administrativo.
USE sglab;
CREATE TABLE IF NOT EXISTS reporte_funcionamiento (
    id_reporte BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_equipo INT UNSIGNED NOT NULL,
    autor_ci INT UNSIGNED NOT NULL,
    estado ENUM('FUNCIONA', 'NO_FUNCIONA') NOT NULL,
    descripcion TEXT NOT NULL,
    fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_reporte),
    KEY idx_reporte_equipo_fecha (id_equipo, fecha_hora, id_reporte),
    CONSTRAINT fk_reporte_equipo FOREIGN KEY (id_equipo) REFERENCES equipo(id_equipo),
    CONSTRAINT fk_reporte_autor FOREIGN KEY (autor_ci) REFERENCES usuarios(ci)
) ENGINE=InnoDB;
