CREATE DATABASE IF NOT EXISTS chatroomdb;
USE chatroomdb;

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS messages;

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    message_content TEXT NOT NULL,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(user_id),
    FOREIGN KEY (receiver_id) REFERENCES users(user_id)
);

INSERT INTO users (username, password) VALUES ('Alice', 'password123');
INSERT INTO users (username, password) VALUES ('Bob', 'password456');