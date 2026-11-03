-- Índices para historial y última recepción por PC. Repetible en MariaDB.
USE sglab;
CREATE INDEX IF NOT EXISTS idx_registro_fecha ON registro(fecha,id_registro);
CREATE INDEX IF NOT EXISTS idx_registro_equipo_recepcion ON registro(id_equipo,fecha_recepcion,id_registro);
