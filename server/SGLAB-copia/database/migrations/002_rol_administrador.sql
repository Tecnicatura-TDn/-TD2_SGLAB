-- Agrega el rol sin modificar los roles ni usuarios existentes.
-- Compatible con instalaciones actuales y repetible.
USE sglab;
ALTER TABLE usuarios
    MODIFY tipo_usuario ENUM('ALUMNO', 'DOCENTE', 'ASISTENTE', 'ADMINISTRADOR') NOT NULL;
