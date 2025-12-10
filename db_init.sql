
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    phone TEXT,
    address TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS prices;

CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    color TEXT,
    storage TEXT,
    image_url TEXT
);

CREATE TABLE stores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    store_id INTEGER,
    price INTEGER,
    FOREIGN KEY (product_id) REFERENCES products (id),
    FOREIGN KEY (store_id) REFERENCES stores (id)
);

INSERT INTO products (name, color, storage, image_url)
VALUES 
('Apple iPhone 17 Pro Max', 'Оранжевый', '256GB', 'iphone17or.jpeg'),
('Apple iPhone 17 Pro Max', 'Темно-синий', '256GB', 'iphone17blue.jpg');

-- If you need to migrate an existing database, run the following ALTER statements:
-- ALTER TABLE users ADD COLUMN phone TEXT;
-- ALTER TABLE users ADD COLUMN address TEXT;

INSERT INTO stores (name)
VALUES ('Kaspi.kz'), ('iSpace Apple'), ('Sulpak');

INSERT INTO prices (product_id, store_id, price)
VALUES 
(1, 1, 925990),   -- Orange Kaspi.kz
(2, 2, 934990),   -- Blue iSpace
(2, 3, 957990);   -- Blue Sulpak

CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_name TEXT NOT NULL,
    balance INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

INSERT INTO cards (user_id, card_name, balance)
VALUES 
(1, 'Kaspi Gold', 4300000),
(1, 'Halyk Bank', 2100000),
(1, 'BCC', 650000);

-- New table for virtual bank cards (kept separate from legacy `cards`)
CREATE TABLE IF NOT EXISTS bank_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    card_name TEXT NOT NULL,
    card_number TEXT NOT NULL,
    balance INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);

INSERT INTO bank_cards (user_id, card_name, card_number, balance)
VALUES
(1, 'Kaspi Gold', '**** 4300', 4300000),
(1, 'Halyk Bank', '**** 2100', 2100000);

-- Order history to record payments
CREATE TABLE IF NOT EXISTS order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_amount INTEGER NOT NULL,
    card_id INTEGER,
    card_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (card_id) REFERENCES bank_cards (id)
);
