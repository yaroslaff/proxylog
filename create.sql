CREATE TABLE response (
    id INT AUTO_INCREMENT PRIMARY KEY,
    method VARCHAR(10),
    path VARCHAR(200),
    code int,
    headers TEXT,
    body TEXT,
    ms INT,
    created TIMESTAMP,
);
