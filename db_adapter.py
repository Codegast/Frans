# Database Adapter - Ondersteunt zowel SQLite (lokaal) als D1 (Cloudflare)
import os
import sqlite3
from flask import g

# Detecteer omgeving
IS_CLOUDFLARE = os.getenv('CLOUDFLARE') == 'true' or os.getenv('WORKERS') == 'true'

class DatabaseAdapter:
    """Adapter die werkt met zowel SQLite als Cloudflare D1"""
    
    def __init__(self):
        self.is_cloudflare = IS_CLOUDFLARE
        if self.is_cloudflare:
            self.db = None  # Wordt gezet door Cloudflare binding
        else:
            self.db_path = os.path.join(os.path.dirname(__file__), 'schoolportaal.db')
    
    def get_connection(self):
        """Haal database connectie op basis van omgeving"""
        if self.is_cloudflare:
            # Cloudflare D1 binding
            if 'db' not in g:
                g.db = g.get('DB')  # Cloudflare D1 binding
            return g.db
        else:
            # SQLite voor lokaal ontwikkeling
            if 'db' not in g:
                conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
                conn.row_factory = sqlite3.Row
                g.db = conn
            return g.db
    
    def execute(self, query, params=None):
        """Voer query uit met parameters"""
        db = self.get_connection()
        if self.is_cloudflare:
            # D1 syntax
            if params:
                return db.execute(query, params)
            return db.execute(query)
        else:
            # SQLite syntax
            if params:
                return db.execute(query, params)
            return db.execute(query)
    
    def commit(self):
        """Commit transactie"""
        db = self.get_connection()
        if not self.is_cloudflare:
            db.commit()
    
    def close(self):
        """Sluit connectie"""
        if 'db' in g and not self.is_cloudflare:
            g.db.close()
            g.pop('db', None)

# Globale adapter instantie
db_adapter = DatabaseAdapter()

# Compatibiliteitsfuncties voor bestaande code
def get_db():
    """Haal database connectie (compatibel met bestaande code)"""
    return db_adapter.get_connection()

def init_db():
    """Initialiseer database schema"""
    db = get_db()
    
    if IS_CLOUDFLARE:
        # D1 schema wordt extern uitgevoerd via wrangler
        pass
    else:
        # SQLite schema initialisatie
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('docent','leerling')),
                vak TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
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
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS quizzen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titel TEXT NOT NULL,
                vak TEXT NOT NULL,
                klas TEXT NOT NULL,
                docent_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (docent_id) REFERENCES users(id)
            )
        """)
        db.execute("""
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
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS cijfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leerling_id INTEGER NOT NULL,
                vak TEXT NOT NULL,
                cijfer REAL NOT NULL CHECK(cijfer >= 1 AND cijfer <= 10),
                type TEXT NOT NULL,
                percentage INTEGER CHECK(percentage >= 0 AND percentage <= 100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (leerling_id) REFERENCES users(id)
            )
        """)
        db.execute("""
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
            )
        """)
        db.execute("""
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
            )
        """)
        db.execute("""
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
            )
        """)
        db.execute("""
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
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS rpg_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pin TEXT NOT NULL,
                bericht TEXT NOT NULL,
                type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pin) REFERENCES live_quizzen(pin)
            )
        """)
        db.commit()
