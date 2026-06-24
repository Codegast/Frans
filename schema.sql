-- SchoolPortaal Database Schema voor Cloudflare D1

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('docent','leerling')),
    vak TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS toetsen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titel TEXT NOT NULL,
    vak TEXT NOT NULL,
    klas TEXT NOT NULL,
    datum TEXT NOT NULL,
    tijd TEXT NOT NULL,
    duur INTEGER DEFAULT 60,
    docent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (docent_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS quizzen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titel TEXT NOT NULL,
    vak TEXT NOT NULL,
    klas TEXT NOT NULL,
    docent_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (docent_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS vragen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    tekst TEXT NOT NULL,
    optie_a TEXT NOT NULL,
    optie_b TEXT NOT NULL,
    optie_c TEXT NOT NULL,
    optie_d TEXT NOT NULL,
    antwoord INTEGER NOT NULL CHECK(antwoord IN (0,1,2,3)),
    volgorde INTEGER DEFAULT 0,
    FOREIGN KEY (quiz_id) REFERENCES quizzen(id)
);

CREATE TABLE IF NOT EXISTS cijfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    leerling_id INTEGER NOT NULL,
    vak TEXT NOT NULL,
    cijfer REAL NOT NULL CHECK(cijfer >= 1 AND cijfer <= 10),
    type TEXT NOT NULL,
    percentage INTEGER CHECK(percentage >= 0 AND percentage <= 100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (leerling_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS live_quizzen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER NOT NULL,
    pin TEXT UNIQUE NOT NULL,
    docent_id INTEGER NOT NULL,
    status TEXT DEFAULT 'wacht' CHECK(status IN ('wacht','actief','klaar')),
    boss_naam TEXT,
    boss_hp INTEGER DEFAULT 100,
    boss_max_hp INTEGER DEFAULT 100,
    team_hp INTEGER DEFAULT 100,
    team_max_hp INTEGER DEFAULT 100,
    huidige_vraag INTEGER DEFAULT 0,
    gestart_op TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quiz_id) REFERENCES quizzen(id),
    FOREIGN KEY (docent_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS live_deelnemers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pin TEXT NOT NULL,
    naam TEXT NOT NULL,
    klas TEXT DEFAULT 'attacker',
    score INTEGER DEFAULT 0,
    total_damage INTEGER DEFAULT 0,
    heals_done INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pin) REFERENCES live_quizzen(pin)
);

CREATE TABLE IF NOT EXISTS antwoorden (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pin TEXT NOT NULL,
    deelnemer_id INTEGER NOT NULL,
    vraag_id INTEGER NOT NULL,
    antwoord INTEGER NOT NULL,
    correct BOOLEAN DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pin) REFERENCES live_quizzen(pin),
    FOREIGN KEY (deelnemer_id) REFERENCES live_deelnemers(id)
);

CREATE TABLE IF NOT EXISTS berichten (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    afzender_id INTEGER NOT NULL,
    ontvanger_id INTEGER NOT NULL,
    onderwerp TEXT NOT NULL,
    inhoud TEXT NOT NULL,
    gelezen BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (afzender_id) REFERENCES users(id),
    FOREIGN KEY (ontvanger_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS rpg_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pin TEXT NOT NULL,
    bericht TEXT NOT NULL,
    type TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pin) REFERENCES live_quizzen(pin)
);
