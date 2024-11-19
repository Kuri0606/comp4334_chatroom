CREATE DATABASE IF NOT EXISTS chatroomdb;
USE chatroomdb;

DROP TABLE IF EXISTS users;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

INSERT INTO users (username, password) VALUES ('Alice', 'password123');
INSERT INTO users (username, password) VALUES ('Bob', 'password456');