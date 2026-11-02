-- Autenticación por rol. Repetible en MariaDB; respaldar antes de aplicar.
USE sglab;
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS totp_secret TEXT NULL,
    ADD COLUMN IF NOT EXISTS totp_enabled TINYINT(1) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS totp_last_step BIGINT NULL,
    ADD COLUMN IF NOT EXISTS github_id BIGINT UNSIGNED NULL,
    ADD COLUMN IF NOT EXISTS auth_version INT UNSIGNED NOT NULL DEFAULT 0;
CREATE UNIQUE INDEX IF NOT EXISTS uq_usuarios_github_id ON usuarios(github_id);
