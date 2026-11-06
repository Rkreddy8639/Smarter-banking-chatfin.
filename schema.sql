CREATE DATABASE IF NOT EXISTS chatfin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'chatfin_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON chatfin.* TO 'chatfin_user'@'localhost';
FLUSH PRIVILEGES;
USE chatfin;
-- Tables are created automatically by database/db.py when the app starts.
