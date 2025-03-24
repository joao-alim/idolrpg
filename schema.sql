CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS musicas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    nome VARCHAR(255) NOT NULL,
    streams INT DEFAULT 0,
    downloads INT DEFAULT 0,
    data_lancamento DATE NOT NULL,
    buzz INT DEFAULT 0,
    pontos FLOAT DEFAULT 0,
    uls FLOAT DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
);

CREATE TABLE IF NOT EXISTS compras (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    musica_id INT NOT NULL,
    tipo_buzz VARCHAR(50) NOT NULL,
    custo INT NOT NULL,
    uls INT NOT NULL,
    streams INT NOT NULL,
    data DATE NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    FOREIGN KEY (musica_id) REFERENCES musicas (id)
);