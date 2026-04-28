-- user_ai_configs table: user-level AI model configuration
-- SQLite version

CREATE TABLE IF NOT EXISTS user_ai_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    config_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL,
    service_type VARCHAR(30) NOT NULL,
    api_base_url VARCHAR(500),
    encrypted_api_key VARCHAR(500),
    api_key_hint VARCHAR(100),
    is_enabled BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    extra_config TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_user_ai_configs_user_id ON user_ai_configs(user_id);
CREATE INDEX IF NOT EXISTS ix_user_ai_configs_user_service ON user_ai_configs(user_id, service_type);

-- MySQL version (run manually if using MySQL):
--
-- CREATE TABLE IF NOT EXISTS user_ai_configs (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     user_id INT NOT NULL,
--     config_name VARCHAR(100) NOT NULL,
--     provider VARCHAR(50) NOT NULL,
--     model_id VARCHAR(100) NOT NULL,
--     service_type VARCHAR(30) NOT NULL,
--     api_base_url VARCHAR(500) DEFAULT NULL,
--     encrypted_api_key VARCHAR(500) DEFAULT NULL,
--     api_key_hint VARCHAR(100) DEFAULT NULL,
--     is_enabled TINYINT(1) DEFAULT 1,
--     is_default TINYINT(1) DEFAULT 0,
--     extra_config TEXT DEFAULT NULL,
--     created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
--     updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
--     INDEX ix_user_ai_configs_user_id (user_id),
--     INDEX ix_user_ai_configs_user_service (user_id, service_type),
--     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
