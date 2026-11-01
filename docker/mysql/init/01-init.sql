CREATE TABLE IF NOT EXISTS usuarios (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  nombre        VARCHAR(100) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  creado        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Todos los usuarios de prueba usan la contraseña: clave123
INSERT INTO usuarios (nombre, email, password_hash) VALUES
  ('Administrador',    'admin@ejemplo.com',  '$2y$12$ilZEBUP9u.LTwgzXNLOt1u1chJeNYB3md2EjVHeNDmcb6yjvRf.PC'),
  ('Ana Pérez',        'ana@ejemplo.com',    '$2y$12$ilZEBUP9u.LTwgzXNLOt1u1chJeNYB3md2EjVHeNDmcb6yjvRf.PC'),
  ('Carlos Rodríguez', 'carlos@ejemplo.com', '$2y$12$ilZEBUP9u.LTwgzXNLOt1u1chJeNYB3md2EjVHeNDmcb6yjvRf.PC'),
  ('María López',      'maria@ejemplo.com',  '$2y$12$ilZEBUP9u.LTwgzXNLOt1u1chJeNYB3md2EjVHeNDmcb6yjvRf.PC');
