-- ============================================================
-- IoT Sensor Network — MySQL Database Setup
-- Run this script on VM3 as root (or a privileged user):
--   mysql -u root -p < setup_db.sql
--
-- IMPORTANT: Replace 'your_secure_password_here' below with
-- the same password you set in your .env file.
-- ============================================================

CREATE DATABASE IF NOT EXISTS iot_db;
USE iot_db;

-- Sensor measurements table
CREATE TABLE IF NOT EXISTS measurements (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    sensor_id VARCHAR(50) NOT NULL,
    type      VARCHAR(50) NOT NULL,
    value     FLOAT       NOT NULL,
    unit      VARCHAR(10),
    timestamp TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_type      (type),
    INDEX idx_timestamp (timestamp)
);

-- Alerts table
-- (api.py also creates this on startup, but it is listed here
--  for a clean initial setup or manual inspection.)
CREATE TABLE IF NOT EXISTS alerts (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    type      VARCHAR(50) NOT NULL,
    value     FLOAT       NOT NULL,
    unit      VARCHAR(10),
    location  VARCHAR(50),
    message   TEXT,
    timestamp TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp)
);

-- Create application user with network-wide access (192.168.56.0/24)
-- Replace 'your_secure_password_here' with your actual password.
CREATE USER IF NOT EXISTS 'iot_user'@'%' IDENTIFIED BY 'your_secure_password_here';
GRANT ALL PRIVILEGES ON iot_db.* TO 'iot_user'@'%';
FLUSH PRIVILEGES;
