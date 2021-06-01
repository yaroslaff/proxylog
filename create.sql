CREATE TABLE response (
    id INT AUTO_INCREMENT PRIMARY KEY,
    path VARCHAR(200),
    code int,
    headers TEXT,
    body TEXT,
    ms INT
);