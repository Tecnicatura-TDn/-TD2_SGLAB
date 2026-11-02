-- Amplía los permisos por alcance sin eliminar capturas ni usuarios.
-- Repetible en MariaDB. El DDL hace COMMIT implícito: respaldar antes.
USE sglab;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS activo TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE laboratorio ADD COLUMN IF NOT EXISTS activo TINYINT(1) NOT NULL DEFAULT 1;
ALTER TABLE equipo ADD COLUMN IF NOT EXISTS activo TINYINT(1) NOT NULL DEFAULT 1;

-- Una asignación actual por docente; hasta NULL significa sin fin programado.
CREATE TABLE IF NOT EXISTS asignacion_docente (
    usuario_ci INT UNSIGNED NOT NULL,
    id_laboratorio INT UNSIGNED NOT NULL,
    desde DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hasta DATETIME NULL,
    asignado_por_ci INT UNSIGNED NOT NULL,
    PRIMARY KEY (usuario_ci),
    KEY idx_asignacion_docente_laboratorio (id_laboratorio),
    CONSTRAINT ck_asignacion_docente_fechas CHECK (hasta IS NULL OR hasta >= desde),
    CONSTRAINT fk_asignacion_docente_usuario FOREIGN KEY (usuario_ci) REFERENCES usuarios(ci),
    CONSTRAINT fk_asignacion_docente_laboratorio FOREIGN KEY (id_laboratorio) REFERENCES laboratorio(id_laboratorio),
    CONSTRAINT fk_asignacion_docente_autor FOREIGN KEY (asignado_por_ci) REFERENCES usuarios(ci)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS comentario_laboratorio (
    id_comentario BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_laboratorio INT UNSIGNED NOT NULL,
    autor_ci INT UNSIGNED NOT NULL,
    contenido TEXT NOT NULL,
    fecha_hora DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_comentario),
    KEY idx_comentario_lab_fecha (id_laboratorio,fecha_hora),
    CONSTRAINT fk_comentario_lab_laboratorio FOREIGN KEY (id_laboratorio) REFERENCES laboratorio(id_laboratorio),
    CONSTRAINT fk_comentario_lab_autor FOREIGN KEY (autor_ci) REFERENCES usuarios(ci)
) ENGINE=InnoDB;
