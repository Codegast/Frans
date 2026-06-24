from flask import Flask, render_template_string, request, redirect, session, jsonify, g
import random, string, time, threading, logging
from markupsafe import escape
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# XSS Protection helper
def safe_string(s):
    """Escape string to prevent XSS attacks"""
    return escape(str(s)) if s else s

def generate_csrf_token():
    """Generate CSRF token for form protection"""
    if 'csrf_token' not in session:
        session['csrf_token'] = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    return session['csrf_token']

def validate_csrf_token(token):
    """Validate CSRF token"""
    return token and token == session.get('csrf_token')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('schoolportaal')

app = Flask(__name__)
app.secret_key = "schoolportaal2024"
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour session timeout

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per day", "100 per hour"],
    storage_uri="memory://",
    strategy="fixed-window"
)

# ====== Database (SQLite) ======
import sqlite3
import os
DB_PATH = os.path.join(os.path.dirname(__file__), 'schoolportaal.db')

def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        g.db = conn
    return g.db

@app.teardown_appcontext
def teardown_db(exc):
    db = g.pop('db', None)
    if db:
        db.close()

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template_string(ERROR_HTML, error="Pagina niet gevonden"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return render_template_string(ERROR_HTML, error="Er is een fout opgetreden"), 500

ERROR_HTML = """<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Fout</title></head><body>
<div class="container" style="text-align:center;padding:60px 20px">
<h1 style="color:#ff5252">❌ Fout</h1>
<div class="card"><p>{{error}}</p><a href="/" class="btn btn-p mt10">Terug naar home</a></div>
</div></body></html>"""

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('docent','leerling')),
        display_name TEXT NOT NULL,
        vak TEXT,
        klas TEXT,
        school_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS toetsen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titel TEXT NOT NULL,
        vak TEXT NOT NULL,
        klas TEXT NOT NULL,
        datum DATE NOT NULL,
        tijd TIME NOT NULL,
        duur INTEGER DEFAULT 60,
        docent_id INTEGER NOT NULL,
        school_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(docent_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS quizzen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titel TEXT NOT NULL,
        vak TEXT NOT NULL,
        klas TEXT NOT NULL,
        docent_id INTEGER NOT NULL,
        school_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(docent_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS vragen (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        tekst TEXT NOT NULL,
        optie_a TEXT NOT NULL,
        optie_b TEXT NOT NULL,
        optie_c TEXT NOT NULL,
        optie_d TEXT NOT NULL,
        antwoord INTEGER NOT NULL CHECK(antwoord BETWEEN 0 AND 3),
        volgorde INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(quiz_id) REFERENCES quizzen(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS live_quizzen (
        pin TEXT PRIMARY KEY,
        quiz_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'wacht' CHECK(status IN ('wacht','actief','klaar')),
        vraag_index INTEGER NOT NULL DEFAULT 0,
        gestart_op TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        beeindigd_op TIMESTAMP,
        school_id INTEGER DEFAULT 1,
        FOREIGN KEY(quiz_id) REFERENCES quizzen(id)
    );
    CREATE TABLE IF NOT EXISTS live_deelnemers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pin TEXT NOT NULL,
        naam TEXT NOT NULL,
        score INTEGER NOT NULL DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(pin) REFERENCES live_quizzen(pin) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS antwoorden (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pin TEXT NOT NULL,
        deelnemer_id INTEGER NOT NULL,
        vraag_id INTEGER NOT NULL,
        antwoord INTEGER NOT NULL,
        is_correct BOOLEAN NOT NULL,
        gegeven_op TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(pin) REFERENCES live_quizzen(pin) ON DELETE CASCADE,
        FOREIGN KEY(deelnemer_id) REFERENCES live_deelnemers(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS cijfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        leerling_id INTEGER NOT NULL,
        vak TEXT NOT NULL,
        cijfer REAL NOT NULL,
        type TEXT NOT NULL,
        percentage REAL NOT NULL,
        school_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(leerling_id) REFERENCES users(id)
    );
    """)
    db.commit()
    # Seed: standaard school
    db.execute("INSERT OR IGNORE INTO schools (id, name) VALUES (1, 'Demo School')")
    db.commit()

with app.app_context():
    init_db()

# ====== Block tracking requests ======
@app.route('/hybridaction/zybTrackerStatisticsAction', methods=['GET','POST','OPTIONS'])
def block_tracker():
    return '', 204

# ====== Seed Data (alleen voor demo) ======
def seed_demo_data():
    db = get_db()
    # Voeg docenten toe met hash-wachtwoorden
    demo_docenten = [
        ("maartsen","maa123","Mevr. M. van Aartsen","ak"),
        ("ialbracht","abt123","Mevr. I. Albracht","fa"),
        ("baltelaar","alt123","Mevr. B. Altelaar","na"),
        ("fbeer","bee123","Mevr. F. de Beer","bv"),
        ("bberends","beb123","Mevr. ir. B. Berends","na"),
    ]
    for u, p, naam, vak in demo_docenten:
        db.execute("INSERT OR IGNORE INTO users (username, password_hash, role, display_name, vak) VALUES (?,?,?,?,?)",
                   (u, generate_password_hash(p), 'docent', naam, vak))
    # Voeg leerlingen toe
    demo_leerlingen = [("piet","leerling123","Piet"),("anna","leerling123","Anna"),("tom","leerling123","Tom"),("lisa","leerling123","Lisa")]
    for u,p,naam in demo_leerlingen:
        db.execute("INSERT OR IGNORE INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)",
                   (u, generate_password_hash(p), 'leerling', naam))
    db.commit()

with app.app_context():
    seed_demo_data()

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;color:#fff}
.container{max-width:1200px;margin:0 auto;padding:20px}
.card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:25px;margin-bottom:20px}
.card h2{color:#b388ff;margin-bottom:12px}
.navbar{background:rgba(0,0,0,.4);backdrop-filter:blur(10px);padding:12px 30px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,.1)}
.navbar .logo{font-size:20px;font-weight:bold;color:#7c4dff}
.navbar a{color:#ccc;text-decoration:none;margin-left:15px;padding:6px 14px;border-radius:6px;font-size:14px}
.navbar a:hover{background:rgba(124,77,255,.3);color:#fff}
.btn{display:inline-block;padding:10px 22px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;border:none;cursor:pointer;text-align:center}
.btn-p{background:#7c4dff;color:#fff}
.btn-p:hover{background:#6a3fe8}
.btn-d{background:#ff5252;color:#fff}
.btn-g{background:rgba(76,175,80,.3);color:#69f0ae}
.welkom{font-size:18px;color:#ccc;margin-bottom:20px}
.welkom strong{color:#b388ff}
label.f{display:block;margin-bottom:10px;color:#b388ff;font-weight:600}
input,select,textarea{width:100%;padding:10px 14px;border:1px solid rgba(255,255,255,.2);border-radius:8px;background:rgba(255,255,255,.05);color:#fff;font-size:14px;outline:none;margin-top:4px}
input:focus,select:focus{border-color:#7c4dff}
table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid rgba(255,255,255,.08)}
th{color:#b388ff;font-size:13px}
tr:hover{background:rgba(255,255,255,.03)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px}
.stat-card{background:rgba(124,77,255,.12);border:1px solid rgba(124,77,255,.25);border-radius:12px;padding:20px;text-align:center}
.stat-card .getal{font-size:36px;font-weight:bold;color:#b388ff}
.stat-card .label{font-size:13px;color:#aaa}
.rol-select{text-align:center;padding:18px;border:2px solid rgba(124,77,255,.25);border-radius:12px;cursor:pointer;transition:.2s;user-select:none;flex:1;font-weight:600}
.rol-select:hover{border-color:#7c4dff;background:rgba(124,77,255,.1)}
.rol-select.selected{border-color:#7c4dff;background:rgba(124,77,255,.25);box-shadow:0 0 12px rgba(124,77,255,.3)}
.rol-icon{display:block;font-size:28px;margin-bottom:5px}.rol-icon svg{width:32px;height:32px;fill:none;stroke:currentColor;stroke-width:1.5}
.medal{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;font-size:13px;font-weight:bold;margin-right:8px}
.medal-1{background:linear-gradient(135deg,#ffd700,#ffaa00);color:#fff}
.medal-2{background:linear-gradient(135deg,#c0c0c0,#a0a0a0);color:#fff}
.medal-3{background:linear-gradient(135deg,#cd7f32,#b8860b);color:#fff}
.crown-icon{font-size:32px;color:#b388ff;display:block}
.antwoord{display:block;width:100%;padding:16px 20px;margin-bottom:10px;background:rgba(255,255,255,.04);border:2px solid rgba(255,255,255,.1);border-radius:12px;cursor:pointer;font-size:16px;transition:.15s;color:#fff}
.antwoord:hover{background:rgba(124,77,255,.15);border-color:rgba(124,77,255,.4)}
.antwoord.selected{background:rgba(124,77,255,.3);border-color:#7c4dff;box-shadow:0 0 12px rgba(124,77,255,.3)}
.antwoord .letter{display:inline-block;background:#7c4dff;color:#fff;width:32px;height:32px;line-height:32px;text-align:center;border-radius:50%;margin-right:12px;font-weight:bold}
.antwoord.selected .letter{background:#b388ff}
.pin-display{font-size:48px;font-weight:bold;color:#b388ff;letter-spacing:8px;text-align:center;padding:20px;background:rgba(124,77,255,.1);border:2px dashed rgba(124,77,255,.3);border-radius:12px;margin:15px 0}
.login-screen{display:flex;justify-content:center;align-items:center;min-height:100vh}.login-box{width:100%;max-width:400px;padding:20px}.login-header{text-align:center;margin-bottom:30px}.login-header h1{font-size:32px;color:#b388ff;margin-bottom:5px}.login-header p{color:#888}.error-msg{background:rgba(255,82,82,.15);border:1px solid #ff5252;border-radius:8px;padding:10px;margin-bottom:15px;color:#ff8a80;text-align:center}.rol-grid{display:flex;gap:12px;margin-bottom:15px}.btn-full{width:100%;padding:14px;font-size:16px}
.center{text-align:center}
.mt10{margin-top:10px}
.mb10{margin-bottom:10px}
"""

# Make CSRF token available in templates
@app.context_processor
def inject_csrf():
    return dict(csrf_token=generate_csrf_token())

# ====== Routes ======
@app.route('/')
def home():
    if 'rol' not in session:
        return redirect('/login')
    if session['rol'] == 'docent':
        return redirect('/docent')
    return redirect('/leerling')
    
@app.route('/robots.txt')
def robots_txt():
    return 'User-agent: *\nDisallow: /private\n', 200

@app.route('/login', methods=['GET','POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        un = request.form.get('gebruikersnaam', '').strip()
        ww = request.form.get('wachtwoord', '').strip()
        
        # Basic input validation
        if not un or not ww:
            logger.warning(f"Login attempt with empty credentials from {request.remote_addr}")
            return render_template_string(LOGIN_HTML, CSS=CSS, fout="Vul gebruikersnaam en wachtwoord in.")
        
        if len(un) > 50 or len(ww) > 128:
            logger.warning(f"Login attempt with suspicious input length from {request.remote_addr}")
            return render_template_string(LOGIN_HTML, CSS=CSS, fout="Ongeldige invoer.")
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (un,)).fetchone()
        if user and check_password_hash(user['password_hash'], ww):
            logger.info(f"Successful login: {un} (role: {user['role']})")
            session.clear()
            session['user_id'] = user['id']
            session['rol'] = user['role']
            session['naam'] = user['display_name']
            session['vak'] = user['vak'] or ''
            session['gebruikersnaam'] = user['username']
            session.permanent = True
            if user['role'] == 'docent':
                return redirect('/docent')
            return redirect('/leerling')
        
        logger.warning(f"Failed login attempt for username: {un} from {request.remote_addr}")
        return render_template_string(LOGIN_HTML, CSS=CSS, fout="Ongeldige inloggegevens.")
    return render_template_string(LOGIN_HTML, CSS=CSS, fout="")

LOGIN_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Inloggen - SchoolPortaal</title></head>
<body>
<div class="login-screen">
<div class="login-box">
<div class="login-header">
<h1>SchoolPortaal</h1>
<p>Log in om verder te gaan</p>
</div>
{% if fout %}<div class="error-msg">{{fout}}</div>{% endif %}
<div class="card">
<form method="POST" action="/login">
<label class="f">Rol</label>
<div class="rol-grid">
<div class="rol-select" onclick="selectRol(this,'docent')" id="rd"><span class="rol-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="6" r="4" fill="currentColor"/><path d="M4 21v-2a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v2" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span><span>Docent</span></div>
<div class="rol-select" onclick="selectRol(this,'leerling')" id="rl"><span class="rol-icon"><svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor"/><path d="M2 17l10 5 10-5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 12l10 5 10-5" fill="none" stroke="currentColor" stroke-width="1.5"/></svg></span><span>Leerling</span></div>
</div>
<input type="hidden" name="rol" id="rol" value="docent">
<label class="f">Gebruikersnaam<input type="text" name="gebruikersnaam" required></label>
<label class="f">Wachtwoord<input type="password" name="wachtwoord" required></label>
<button type="submit" class="btn btn-p btn-full">Inloggen</button>
</form></div></div></div>
<script>
document.getElementById('rd').classList.add('selected');
function selectRol(el,rol){
  document.querySelectorAll('.rol-select').forEach(e=>e.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('rol').value=rol;
}
</script>
</body></html>"""

# ====== Docent routes ======
@app.route('/docent')
def docent_dashboard():
    if 'rol' not in session or session['rol'] != 'docent':
        return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    aant_toetsen = db.execute("SELECT COUNT(*) as cnt FROM toetsen WHERE docent_id = ?", (user_id,)).fetchone()['cnt']
    aant_quizzen = db.execute("SELECT COUNT(*) as cnt FROM quizzen WHERE docent_id = ?", (user_id,)).fetchone()['cnt']
    aant_leerlingen = db.execute("SELECT COUNT(*) as cnt FROM users WHERE role = 'leerling'").fetchone()['cnt']
    aant_cijfers = db.execute("SELECT COUNT(*) as cnt FROM cijfers").fetchone()['cnt']
    return render_template_string(DOCENT_DASH_HTML, CSS=CSS, naam=session['naam'], vak=session['vak'],
        aant_toetsen=aant_toetsen, aant_quizzen=aant_quizzen, aant_leerlingen=aant_leerlingen, aant_cijfers=aant_cijfers)

DOCENT_DASH_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Dashboard</title></head>
<body>
<div class="navbar"><span class="logo">SchoolPortaal</span>
<div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a><a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
<a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
<div class="container">
<div class="welkom">Welkom terug, <strong>{{naam}}</strong>! | {{vak}}</div>
<div class="grid">
<div class="stat-card"><div class="getal">{{aant_leerlingen}}</div><div class="label">Leerlingen</div></div>
<div class="stat-card"><div class="getal">{{aant_toetsen+aant_quizzen}}</div><div class="label">Items</div></div>
<div class="stat-card"><div class="getal">{{aant_cijfers}}</div><div class="label">Cijfers</div></div>
</div></div></body></html>"""

@app.route('/docent/klassen')
def klassen():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    jaren = ['2','3','4','5','6']
    html = """<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>""" + CSS + """</style><title>Klassen</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a>
    <a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
    <a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Overzicht <strong>Klassen</strong></div>"""
    for j in jaren:
        html += f'<div class="card"><h2>Klas {j}</h2><div class="grid">'
        for k in ['1','2']:
            html += f'<div class="stat-card"><div class="getal" style="font-size:24px">la{j}{k}</div><div class="label">La</div></div>'
        for k in ['1','2','3']:
            if j=='6' and k=='3': continue
            html += f'<div class="stat-card"><div class="getal" style="font-size:24px">lh{j}{k}</div><div class="label">Lh</div></div>'
        html += '</div></div>'
    html += '</div></body></html>'
    return html

@app.route('/docent/cijfers')
def docent_cijfers():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Cijfers</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a>
    <a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
    <a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Cijfers - <strong>{session['vak']}</strong></div>
    <div class="card"><h2>Cijferoverzicht</h2><table><tr><th>Leerling</th><th>Klas</th><th>Cijfer</th><th>Type</th></tr>
    <tr><td>Piet de Groot</td><td>4VWO</td><td style="color:#69f0ae">8.5</td><td>Proefwerk</td></tr>
    <tr><td>Anna Smit</td><td>3HAVO</td><td style="color:#69f0ae">7.2</td><td>Huiswerk</td></tr>
    <tr><td>Tom Visser</td><td>5VWO</td><td style="color:#ffd740">6.0</td><td>Toets</td></tr></table></div></div></body></html>"""

@app.route('/docent/leerlingen')
def docent_leerlingen():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Leerlingen</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a>
    <a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
    <a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Overzicht <strong>Leerlingen</strong></div>
    <div class="card"><h2>Alle Leerlingen</h2><table><tr><th>Naam</th><th>Klas</th><th>Gemiddelde</th><th>Status</th></tr>
    <tr><td>Piet</td><td>4VWO</td><td style="color:#69f0ae">7.6</td><td><span class="btn btn-g" style="padding:3px 10px;font-size:12px">Actief</span></td></tr>
    <tr><td>Anna</td><td>3HAVO</td><td style="color:#69f0ae">7.1</td><td><span class="btn btn-g" style="padding:3px 10px;font-size:12px">Actief</span></td></tr>
    <tr><td>Tom</td><td>5VWO</td><td style="color:#ffd740">6.2</td><td><span class="btn" style="background:rgba(255,214,0,.2);color:#ffd740;padding:3px 10px;font-size:12px">Bezig</span></td></tr>
    <tr><td>Lisa</td><td>2HAVO</td><td style="color:#ff8a80">5.4</td><td><span class="btn" style="background:rgba(255,82,82,.2);color:#ff8a80;padding:3px 10px;font-size:12px">Nieuw</span></td></tr>
    </table></div></div></body></html>"""

@app.route('/docent/toetsen', methods=['GET','POST'])
def docent_toetsen():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    if request.method == 'POST':
        titel = request.form.get('titel', '').strip()
        vak = request.form.get('vak', '').strip()
        klas = request.form.get('klas', '').strip()
        datum = request.form.get('datum', '').strip()
        tijd = request.form.get('tijd', '').strip()
        duur = request.form.get('duur', 60)
        
        if not titel or not vak or not klas or not datum or not tijd:
            logger.warning(f"Empty toets creation attempt from user {user_id}")
            return redirect('/docent/toetsen')
        
        db.execute("INSERT INTO toetsen (titel,vak,klas,datum,tijd,duur,docent_id) VALUES (?,?,?,?,?,?,?)",
                   (titel, vak, klas, datum, tijd, int(duur), user_id))
        db.commit()
        return redirect('/docent/toetsen')
    rows = db.execute("SELECT * FROM toetsen WHERE docent_id = ? ORDER BY datum DESC", (user_id,)).fetchall()
    tbody = ""
    if not rows:
        tbody = '<tr><td colspan="4" style="text-align:center;color:#888">Geen toetsen</td></tr>'
    else:
        for t in rows:
            tbody += f'<tr><td>{t["titel"]}</td><td>{t["vak"]}</td><td>{t["klas"]}</td>'
            tbody += f'<td><form method="POST" action="/docent/toetsen/verwijder/{t["id"]}" style="display:inline"><button class="btn btn-d" style="padding:4px 10px">Del</button></form></td></tr>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Toetsen</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a>
    <a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
    <a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Toetsen - <strong>{session['vak']}</strong></div>
    <div class="card"><h2>Nieuwe Toets</h2><form method="POST">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <label class="f">Titel<input type="text" name="titel" required></label>
    <label class="f">Vak<select name="vak"><option>ak</option><option>fa</option><option>na</option><option>bv</option><option>wi</option><option>en</option><option>gs</option><option>ne</option><option>bi</option><option>ma</option></select></label>
    <label class="f">Klas<select name="klas"><option>la21</option><option>la22</option><option>lh21</option><option>lh22</option><option>lh23</option><option>la31</option><option>la32</option><option>lh31</option><option>lh32</option></select></label>
    <label class="f">Datum<input type="date" name="datum" required></label>
    <label class="f">Tijd<input type="time" name="tijd" required></label>
    <label class="f">Duur (min)<input type="number" name="duur" value="60"></label></div>
    <button type="submit" class="btn btn-p mt10">Aanmaken</button></form></div>
    <div class="card"><h2>Toetsen ({len(rows)})</h2><table><tr><th>Titel</th><th>Vak</th><th>Klas</th><th>Actie</th></tr>{tbody}</table></div>
    </div></body></html>"""

@app.route('/docent/toetsen/verwijder/<int:toets_id>', methods=['POST'])
def toets_verwijder(toets_id):
    if 'rol' not in session or session['rol'] != 'docent': 
        logger.warning(f"Unauthorized toets delete attempt from {request.remote_addr}")
        return redirect('/login')
    
    db = get_db()
    user_id = session.get('user_id')
    
    # Verify ownership
    toets = db.execute("SELECT id FROM toetsen WHERE id = ? AND docent_id = ?", (toets_id, user_id)).fetchone()
    if not toets:
        logger.warning(f"User {user_id} tried to delete toets {toets_id} without ownership")
        return redirect('/docent/toetsen')
    
    db.execute("DELETE FROM toetsen WHERE id = ?", (toets_id,))
    db.commit()
    
    logger.info(f"Toets {toets_id} deleted by user {user_id}")
    return redirect('/docent/toetsen')

@app.route('/docent/quizzen', methods=['GET','POST'])
def docent_quizzen():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    if request.method == 'POST':
        titel = request.form.get('titel', '').strip()
        vak = request.form.get('vak', '').strip()
        klas = request.form.get('klas', '').strip()
        
        if not titel or not vak or not klas:
            logger.warning(f"Empty quiz creation attempt from user {user_id}")
            return redirect('/docent/quizzen')
        
        db.execute("INSERT INTO quizzen (titel,vak,klas,docent_id) VALUES (?,?,?,?)",
                   (titel, vak, klas, user_id))
        db.commit()
        return redirect('/docent/quizzen')
    rijen = ""
    rows = db.execute("SELECT * FROM quizzen WHERE docent_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    if not rows:
        rijen = '<tr><td colspan="5" style="text-align:center;color:#888">Geen quizzen</td></tr>'
    else:
        for q in rows:
            q_id = q['id']
            aantal_vragen = db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = ?", (q_id,)).fetchone()['cnt']
            rijen += f'<tr><td>{q["titel"]}</td><td>{q["vak"]}</td><td>{q["klas"]}</td><td>{aantal_vragen}</td>'
            rijen += f'<td><a href="/docent/quiz/{q_id}" class="btn btn-p" style="padding:4px 10px">Bewerk</a> '
            rijen += f'<form method="POST" action="/docent/quiz/verwijder/{q_id}" style="display:inline"><button class="btn btn-d" style="padding:4px 10px">Del</button></form></td></tr>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Quizzen</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a>
    <a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
    <a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Quizzen - <strong>{session['vak']}</strong></div>
    <div class="card"><h2>Nieuwe Quiz</h2><form method="POST">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <label class="f">Titel<input type="text" name="titel" required></label>
    <label class="f">Vak<select name="vak"><option>ak</option><option>fa</option><option>na</option><option>bv</option><option>wi</option><option>en</option><option>gs</option><option>ne</option><option>bi</option><option>ma</option></select></label>
    <label class="f">Klas<select name="klas"><option>la21</option><option>la22</option><option>lh21</option><option>lh22</option><option>lh23</option><option>la31</option><option>la32</option></select></label></div>
    <button type="submit" class="btn btn-p mt10">Aanmaken</button></form></div>
    <div class="card"><h2>Quizzen ({len(rows)})</h2><table><tr><th>Titel</th><th>Vak</th><th>Klas</th><th>Vragen</th><th>Actie</th></tr>{rijen}</table></div>
    </div></body></html>"""

@app.route('/docent/quiz/verwijder/<int:quiz_id>', methods=['POST'])
def quiz_verwijder(quiz_id):
    if 'rol' not in session or session['rol'] != 'docent': 
        logger.warning(f"Unauthorized quiz delete attempt from {request.remote_addr}")
        return redirect('/login')
    
    db = get_db()
    user_id = session.get('user_id')
    
    # Verify quiz ownership
    quiz = db.execute("SELECT id FROM quizzen WHERE id = ? AND docent_id = ?", (quiz_id, user_id)).fetchone()
    if not quiz:
        logger.warning(f"User {user_id} tried to delete quiz {quiz_id} without ownership")
        return redirect('/docent/quizzen')
    
    # Delete related live quizzes
    db.execute("DELETE FROM live_quizzen WHERE quiz_id = ?", (quiz_id,))
    # Delete related questions
    db.execute("DELETE FROM vragen WHERE quiz_id = ?", (quiz_id,))
    # Delete the quiz
    db.execute("DELETE FROM quizzen WHERE id = ?", (quiz_id,))
    db.commit()
    
    logger.info(f"Quiz {quiz_id} deleted by user {user_id}")
    return redirect('/docent/quizzen')

@app.route('/docent/quiz/<int:quiz_id>', methods=['GET','POST'])
def quiz_bewerk(quiz_id):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    quiz = db.execute("SELECT * FROM quizzen WHERE id = ?", (quiz_id,)).fetchone()
    if not quiz:
        return redirect('/docent/quizzen')
    if request.method == 'POST':
        vraag = request.form.get('vraag', '').strip()
        opt0 = request.form.get('opt0', '').strip()
        opt1 = request.form.get('opt1', '').strip()
        opt2 = request.form.get('opt2', '').strip()
        opt3 = request.form.get('opt3', '').strip()
        antwoord = request.form.get('antwoord', '0')
        
        if not vraag or not opt0 or not opt1 or not opt2 or not opt3:
            logger.warning(f"Empty question creation attempt from user {session.get('user_id')}")
            return redirect(f'/docent/quiz/{quiz_id}')
        
        volgorde = db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = ?", (quiz_id,)).fetchone()['cnt']
        db.execute("""INSERT INTO vragen (quiz_id, tekst, optie_a, optie_b, optie_c, optie_d, antwoord, volgorde)
                      VALUES (?,?,?,?,?,?,?,?)""",
                   (quiz_id, vraag, opt0, opt1, opt2, opt3, int(antwoord), volgorde))
        db.commit()
        return redirect(f'/docent/quiz/{quiz_id}')
    vragen_db = db.execute("SELECT * FROM vragen WHERE quiz_id = ? ORDER BY volgorde", (quiz_id,)).fetchall()
    vragen_html = ""
    for vi,v in enumerate(vragen_db):
        vragen_html += f'<div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:15px;margin-bottom:10px">'
        vragen_html += f'<p><strong>Vraag {vi+1}:</strong> {v["tekst"]}</p><p style="margin-top:5px">'
        opties = [v['optie_a'], v['optie_b'], v['optie_c'], v['optie_d']]
        for o in range(4):
            c = "#69f0ae;font-weight:bold" if o == v['antwoord'] else "#ccc"
            vragen_html += f'<span style="color:{c};margin-right:12px">{chr(65+o)}. {opties[o]}</span>'
        vragen_html += '</p></div>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>{quiz['titel']}</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a>
    <a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
    <a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Quiz: <strong>{quiz['titel']}</strong> | {quiz['vak']} | {quiz['klas']}</div>
    <div class="card"><h2>Vragen ({len(vragen_db)})</h2>{vragen_html}</div>
    <div class="card"><h2>Nieuwe Vraag</h2><form method="POST">
    <label class="f">Vraag<textarea name="vraag" rows="2" required style="resize:vertical"></textarea></label>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <label class="f">A<input type="text" name="opt0" required></label>
    <label class="f">B<input type="text" name="opt1" required></label>
    <label class="f">C<input type="text" name="opt2" required></label>
    <label class="f">D<input type="text" name="opt3" required></label></div>
    <label class="f">Correct<select name="antwoord"><option value="0">A</option><option value="1">B</option><option value="2">C</option><option value="3">D</option></select></label>
    <button type="submit" class="btn btn-p">Toevoegen</button></form></div>
    <a href="/docent/quizzen" class="btn btn-d">Terug</a></div></body></html>"""

# ====== LIVE QUIZ ======
@app.route('/docent/live')
def docent_live():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    rijen = ""
    live_lijst = db.execute("""
        SELECT lq.pin, q.titel, q.id as quiz_id, lq.status, lq.vraag_index,
               (SELECT COUNT(*) FROM live_deelnemers WHERE pin = lq.pin) as spelers
        FROM live_quizzen lq
        JOIN quizzen q ON lq.quiz_id = q.id
        WHERE q.docent_id = ?
        ORDER BY lq.gestart_op DESC
    """, (user_id,)).fetchall()
    for lq in live_lijst:
        quiz_done = lq['vraag_index'] >= (db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = ?", (lq['quiz_id'],)).fetchone()['cnt'])
        rijen += f'<tr><td style="font-size:24px;font-weight:bold;color:#b388ff">{lq["pin"]}</td>'
        rijen += f'<td>{lq["titel"]}</td><td>{lq["spelers"]}</td>'
        if quiz_done:
            rijen += f'<td><span class="btn btn-g" style="padding:3px 10px;font-size:12px">Klaar</span></td>'
            rijen += f'<td><a href="/docent/live/scoreboard/{lq["pin"]}" class="btn btn-p" style="padding:4px 10px">Scorebord</a> '
            rijen += f'<form method="POST" action="/docent/live/stop/{lq["pin"]}" style="display:inline"><button class="btn btn-d" style="padding:4px 10px">Sluit</button></form></td></tr>'
        elif lq['status'] == 'wacht':
            rijen += f'<td><span style="color:#ffd740">Wacht</span></td>'
            rijen += f'<td><form method="POST" action="/docent/live/start/{lq["pin"]}" style="display:inline"><button class="btn btn-p" style="padding:4px 10px">Start</button></form> '
            rijen += f'<form method="POST" action="/docent/live/stop/{lq["pin"]}" style="display:inline"><button class="btn btn-d" style="padding:4px 10px">Stop</button></form></td></tr>'
        else:
            vraag_nr = lq['vraag_index'] + 1
            totaal_vr = db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = ?", (lq['quiz_id'],)).fetchone()['cnt']
            rijen += f'<td><span style="color:#69f0ae">Vraag {vraag_nr}/{totaal_vr}</span></td>'
            rijen += f'<td><form method="POST" action="/docent/live/volgende/{lq["pin"]}" style="display:inline"><button class="btn btn-p" style="padding:4px 10px">Volgende</button></form> '
            rijen += f'<a href="/docent/live/scoreboard/{lq["pin"]}" class="btn btn-p" style="padding:4px 10px">Scorebord</a> '
            rijen += f'<form method="POST" action="/docent/live/stop/{lq["pin"]}" style="display:inline"><button class="btn btn-d" style="padding:4px 10px">Stop</button></form></td></tr>'
    if not rijen:
        rijen = '<tr><td colspan="5" style="text-align:center;color:#888">Geen actieve quizzen</td></tr>'
    quiz_opties = ""
    for q in db.execute("SELECT id, titel FROM quizzen WHERE docent_id = ? ORDER BY created_at DESC", (user_id,)).fetchall():
        aantal_vr = db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = ?", (q['id'],)).fetchone()['cnt']
        quiz_opties += f'<option value="{q["id"]}">{q["titel"]} ({aantal_vr} vragen)</option>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Live Quiz Beheer</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent">Dashboard</a><a href="/docent/klassen">Klassen</a><a href="/docent/toetsen">Toetsen</a><a href="/docent/quizzen">Quizzen</a>
    <a href="/docent/cijfers">Cijfers</a><a href="/docent/leerlingen">Leerlingen</a>
    <a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom"><strong>Live Quiz</strong> Beheer</div>
    <div class="card"><h2>Actieve Quizzen</h2><table><tr><th>PIN</th><th>Quiz</th><th>Spelers</th><th>Status</th><th>Acties</th></tr>{rijen}</table></div>
    <div class="card"><h2>Nieuwe Live Quiz</h2><form method="POST" action="/docent/live/maak">
    <label class="f">Kies een Quiz<select name="quiz">{quiz_opties}</select></label>
    <button type="submit" class="btn btn-p">Maak Live Quiz</button></form></div></div></body></html>"""

@app.route('/docent/live/maak', methods=['POST'])
def live_maak():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    quiz_id = request.form.get('quiz', '')
    if quiz_id == '':
        return redirect('/docent/live')
    quiz = db.execute("SELECT id FROM quizzen WHERE id = ? AND docent_id = ?", (quiz_id, user_id)).fetchone()
    if not quiz:
        return redirect('/docent/live')
    pin = str(random.randint(1000,9999))
    while db.execute("SELECT pin FROM live_quizzen WHERE pin = ?", (pin,)).fetchone():
        pin = str(random.randint(1000,9999))
    db.execute("INSERT INTO live_quizzen (pin, quiz_id, status) VALUES (?,?, 'wacht')", (pin, quiz_id))
    db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/start/<pin>', methods=['POST'])
def live_start(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    lq = db.execute("SELECT lq.* FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id = q.id WHERE lq.pin = ? AND q.docent_id = ?", (pin, user_id)).fetchone()
    if lq:
        db.execute("UPDATE live_quizzen SET status = 'actief', vraag_index = 0 WHERE pin = ?", (pin,))
        db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/volgende/<pin>', methods=['POST'])
def live_volgende(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    lq = db.execute("SELECT lq.*, q.id as quiz_id FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id = q.id WHERE lq.pin = ? AND q.docent_id = ?", (pin, user_id)).fetchone()
    if lq:
        totaal = db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = ?", (lq['quiz_id'],)).fetchone()['cnt']
        nieuwe_index = lq['vraag_index'] + 1
        if nieuwe_index >= totaal:
            db.execute("UPDATE live_quizzen SET status = 'klaar', beeindigd_op = CURRENT_TIMESTAMP WHERE pin = ?", (pin,))
        else:
            db.execute("UPDATE live_quizzen SET vraag_index = ? WHERE pin = ?", (nieuwe_index, pin))
        db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/stop/<pin>', methods=['POST'])
def live_stop(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    db.execute("DELETE FROM live_quizzen WHERE pin = ? AND quiz_id IN (SELECT id FROM quizzen WHERE docent_id = ?)", (pin, user_id))
    db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/scoreboard/<pin>')
def live_scoreboard(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    lq = db.execute("SELECT lq.*, q.titel FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id = q.id WHERE lq.pin = ?", (pin,)).fetchone()
    if not lq:
        return redirect('/docent/live')
    deelnemers = db.execute("SELECT naam, score FROM live_deelnemers WHERE pin = ? ORDER BY score DESC", (pin,)).fetchall()
    rijen = ""
    for idx,(naam,score) in enumerate(deelnemers):
        medal = ""
        if idx == 0: medal = "G"
        elif idx == 1: medal = "Z"
        elif idx == 2: medal = "B"
        rijen += f'<tr><td style="font-size:20px"><span class="medal medal-{idx+1}">{medal}</span> {naam}</td><td style="color:#b388ff;font-size:24px;font-weight:bold">{score}</td></tr>'
    if not rijen:
        rijen = '<tr><td colspan="2" style="text-align:center;color:#888">Geen spelers</td></tr>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Scorebord</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/docent/live">Live Quiz</a><a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Scorebord: <strong>{lq['titel']}</strong></div>
    <div class="card"><h2>🏆 Eindstand</h2><table><tr><th>Naam</th><th>Score</th></tr>{rijen}</table></div>
    <a href="/docent/live" class="btn btn-d">Terug</a></div></body></html>"""

# ====== Leerling routes ======
@app.route('/leerling')
def leerling_dashboard():
    if 'rol' not in session or session['rol'] != 'leerling': return redirect('/login')
    db = get_db()
    user_id = session.get('user_id')
    gemiddelde = db.execute("SELECT AVG(cijfer) as avg FROM cijfers WHERE leerling_id = ?", (user_id,)).fetchone()['avg'] or 0
    aantal_cijfers = db.execute("SELECT COUNT(*) as cnt FROM cijfers WHERE leerling_id = ?", (user_id,)).fetchone()['cnt']
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Dashboard</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/leerling">Dashboard</a><a href="/leerling/cijfers">Cijfers</a><a href="/leerling/quiz/spel">🎮 Live Quiz</a><a href="/leerling/schoolgids">Schoolgids</a>
    <a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Welkom, <strong>{session['naam']}</strong>!</div>
    <div class="grid">
    <div class="stat-card"><div class="getal">{gemiddelde:.1f}</div><div class="label">Gemiddeld</div></div>
    <div class="stat-card"><div class="getal">{aantal_cijfers}</div><div class="label">Cijfers</div></div>
    <div class="stat-card"><div class="getal">0</div><div class="label">Openstaand</div></div>
    </div></div></body></html>"""

@app.route('/leerling/cijfers')
def leerling_cijfers():
    if 'rol' not in session or session['rol'] != 'leerling': return redirect('/login')
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Mijn Cijfers</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/leerling">Dashboard</a><a href="/leerling/cijfers">Cijfers</a><a href="/leerling/quiz/spel">🎮 Live Quiz</a><a href="/leerling/schoolgids">Schoolgids</a>
    <a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Cijfers van <strong>{session['naam']}</strong></div>
    <div class="card"><h2>Wiskunde</h2><table><tr><th>Type</th><th>Cijfer</th><th>%</th></tr>
    <tr><td>Proefwerk</td><td style="color:#69f0ae">8.5</td><td>40%</td></tr><tr><td>Huiswerk</td><td style="color:#69f0ae">7.8</td><td>20%</td></tr></table></div>
    <div class="card"><h2>Nederlands</h2><table><tr><th>Type</th><th>Cijfer</th><th>%</th></tr>
    <tr><td>Huiswerk</td><td style="color:#69f0ae">7.2</td><td>30%</td></tr><tr><td>Tentamen</td><td style="color:#ffd740">6.0</td><td>35%</td></tr></table></div></div></body></html>"""

@app.route('/leerling/schoolgids')
def schoolgids():
    if 'rol' not in session or session['rol'] != 'leerling': return redirect('/login')
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Schoolgids</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/leerling">Dashboard</a><a href="/leerling/cijfers">Cijfers</a><a href="/leerling/quiz/spel">🎮 Live Quiz</a><a href="/leerling/schoolgids">Schoolgids</a>
    <a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Schoolgids voor <strong>{session['naam']}</strong></div>
    <div class="grid"><div class="card"><h2>Schooluren</h2><table><tr><th>Les</th><th>Tijd</th></tr>
    <tr><td>1e</td><td>08:30-09:20</td></tr><tr><td>2e</td><td>09:25-10:15</td></tr><tr><td>3e</td><td>10:45-11:35</td></tr>
    <tr><td>4e</td><td>11:40-12:30</td></tr><tr><td>5e</td><td>13:15-14:05</td></tr><tr><td>6e</td><td>14:10-15:00</td></tr></table></div>
    <div class="card"><h2>Contact</h2><p>Schoolstraat 1, Amsterdam</p><p>020-1234567</p></div></div></div></body></html>"""

# ====== LIVE QUIZ (Student) ======
@app.route('/leerling/quiz/spel', methods=['GET','POST'])
def quiz_spel():
    if 'rol' not in session or session['rol'] != 'leerling':
        session['spel_naam'] = None
        if request.method == 'GET':
            return render_template_string(PIN_HTML, CSS=CSS, fout="")
        pin = request.form['pin']
        naam = request.form['naam']
        session['spel_naam'] = naam
        db = get_db()
        live = db.execute("SELECT * FROM live_quizzen WHERE pin = ?", (pin,)).fetchone()
        if live and live['status'] in ('wacht','actief'):
            if naam not in [r['naam'] for r in db.execute("SELECT naam FROM live_deelnemers WHERE pin = ?", (pin,)).fetchall()]:
                db.execute("INSERT INTO live_deelnemers (pin,naam) VALUES (?,?)", (pin,naam))
                db.commit()
            return redirect(f'/leerling/quiz/spelen/{pin}')
        return render_template_string(PIN_HTML, CSS=CSS, fout="Ongeldige code of quiz niet beschikbaar.")
    if request.method == 'GET':
        return render_template_string(PIN_HTML, CSS=CSS, fout="")
    pin = request.form['pin']
    naam = session.get('naam','Speler')
    db = get_db()
    live = db.execute("SELECT * FROM live_quizzen WHERE pin = ?", (pin,)).fetchone()
    if live and live['status'] in ('wacht','actief'):
        if naam not in [r['naam'] for r in db.execute("SELECT naam FROM live_deelnemers WHERE pin = ?", (pin,)).fetchall()]:
            db.execute("INSERT INTO live_deelnemers (pin,naam) VALUES (?,?)", (pin,naam))
            db.commit()
        return redirect(f'/leerling/quiz/spelen/{pin}')
    return render_template_string(PIN_HTML, CSS=CSS, fout="Ongeldige code of quiz niet beschikbaar.")

PIN_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Live Quiz</title></head>
<body>
<div style="display:flex;justify-content:center;align-items:center;min-height:100vh">
<div style="width:100%;max-width:400px;padding:20px">
<div class="center" style="margin-bottom:30px">
<h1 style="font-size:36px;color:#b388ff;margin-bottom:5px">🎮 Live Quiz</h1>
<p style="color:#888">Voer de spelcode in om mee te doen</p>
</div>
{% if fout %}<div style="background:rgba(255,82,82,.15);border:1px solid #ff5252;border-radius:8px;padding:10px;margin-bottom:15px;color:#ff8a80;text-align:center">{{fout}}</div>{% endif %}
<div class="card">
<form method="POST">
<label class="f">Spelcode</label>
<input type="text" name="pin" placeholder="Bijv. 1234" pattern="[0-9]{4}" required style="font-size:24px;text-align:center;letter-spacing:8px">
<label class="f" style="margin-top:15px">Jouw naam</label>
<input type="text" name="naam" placeholder="Vul je naam in" required>
<button type="submit" class="btn btn-p" style="width:100%;padding:14px;font-size:16px;margin-top:15px">Meedoen</button>
</form></div></div></div></body></html>"""

@app.route('/leerling/quiz/spelen/<pin>')
def quiz_spelen(pin):
    db = get_db()
    live = db.execute("SELECT lq.*, q.titel, q.vak, q.klas FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id = q.id WHERE lq.pin = ?", (pin,)).fetchone()
    if not live:
        return redirect('/leerling/quiz/spel')
    if live['status'] == 'wacht':
        deelnemers = db.execute("SELECT naam FROM live_deelnemers WHERE pin = ?", (pin,)).fetchall()
        deelnemers_html = "".join(f'<p style="color:#888;margin:3px 0">{r["naam"]}</p>' for r in deelnemers)
        return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
        <style>{CSS}</style><title>Wachten...</title></head><body>
        <div class="container" style="text-align:center;padding:60px 20px">
        <h1 style="font-size:28px;color:#b388ff;margin-bottom:10px">⏳ Wachten op de docent</h1>
        <p style="color:#888;margin-bottom:30px">Je bent ingeschreven voor: <strong>{live['titel']}</strong></p>
        <div class="card" style="max-width:300px;margin:0 auto"><h2>Deelnemers</h2>{deelnemers_html}</div>
        <script>setInterval(function(){{fetch('/leerling/check/{pin}').then(r=>r.json()).then(d=>{{if(d.status=='actief')location.reload()}})}},2000);</script>
        </div></body></html>"""
    if live['status'] == 'actief':
        vragen_db = db.execute("SELECT * FROM vragen WHERE quiz_id = ? ORDER BY volgorde", (live['quiz_id'],)).fetchall()
        if live['vraag_index'] < len(vragen_db):
            v = vragen_db[live['vraag_index']]
            huidig = live['vraag_index'] + 1
            totaal = len(vragen_db)
            opties = [v['optie_a'], v['optie_b'], v['optie_c'], v['optie_d']]
            opties_html = "".join(f'<div class="antwoord" onclick="kies(this,{o})"><span class="letter">{chr(65+o)}</span> {opties[o]}</div>' for o in range(4))
            return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
            <style>{CSS}</style><title>Vraag {huidig}</title></head><body>
            <div class="container" style="max-width:700px;margin:0 auto;padding:30px 20px">
            <div style="text-align:center;margin-bottom:20px">
            <p style="color:#888;font-size:14px">Vraag {huidig} / {totaal}</p>
            <h1 style="font-size:24px;color:#fff;margin-top:10px">{v['tekst']}</h1></div>
            <form id="quizForm" method="POST" action="/leerling/antwoord/{pin}">
            <input type="hidden" name="antwoord" id="antwoord" value="">
            {opties_html}
            </form>
            <div style="text-align:center;margin-top:10px"><button class="btn btn-p" onclick="verstuur()" style="padding:12px 40px;font-size:16px">Bevestig</button></div>
            <script>
            let gekozen = null;
            function kies(el,o){{
            document.querySelectorAll('.antwoord').forEach(e=>e.classList.remove('selected'));
            el.classList.add('selected');
            gekozen = o;
            document.getElementById('antwoord').value = o;
            }}
            function verstuur(){{
            if(gekozen!==null) document.getElementById('quizForm').submit();
            else alert('Selecteer eerst een antwoord!');
            }}
            </script></div></body></html>"""
    return redirect(f'/leerling/scoreboard/{pin}')

@app.route('/leerling/check/<pin>')
def check_status(pin):
    db = get_db()
    row = db.execute("SELECT status FROM live_quizzen WHERE pin = ?", (pin,)).fetchone()
    if row:
        return jsonify({'status': row['status']})
    return jsonify({'status':'weg'})

@app.route('/leerling/antwoord/<pin>', methods=['POST'])
def leerling_antwoord(pin):
    db = get_db()
    live = db.execute("SELECT * FROM live_quizzen WHERE pin = ?", (pin,)).fetchone()
    if not live:
        return redirect('/leerling/quiz/spel')
    if live['status'] != 'actief':
        return redirect(f'/leerling/scoreboard/{pin}')
    vragen_db = db.execute("SELECT * FROM vragen WHERE quiz_id = ? ORDER BY volgorde", (live['quiz_id'],)).fetchall()
    if live['vraag_index'] >= len(vragen_db):
        return redirect(f'/leerling/scoreboard/{pin}')
    v = vragen_db[live['vraag_index']]
    naam = session.get('spel_naam', session.get('naam','Ik'))
    antw = request.form.get('antwoord','-1')
    if antw == '' or antw == '-1':
        return redirect(f'/leerling/quiz/spelen/{pin}')
    bestaand = db.execute("SELECT id FROM antwoorden WHERE pin = ? AND deelnemer_id = (SELECT id FROM live_deelnemers WHERE pin = ? AND naam = ? LIMIT 1)",
                          (pin, pin, naam)).fetchone()
    if not bestaand:
        deelnemer = db.execute("SELECT id FROM live_deelnemers WHERE pin = ? AND naam = ?", (pin, naam)).fetchone()
        deelnemer_id = deelnemer['id'] if deelnemer else None
        is_correct = int(antw) == v['antwoord']
        db.execute("INSERT INTO antwoorden (pin, deelnemer_id, vraag_id, antwoord, is_correct) VALUES (?,?,?,?,?)",
                   (pin, deelnemer_id, v['id'], int(antw), is_correct))
        if is_correct:
            db.execute("UPDATE live_deelnemers SET score = score + 10 WHERE pin = ? AND naam = ?", (pin, naam))
        db.commit()
    return redirect(f'/leerling/scoreboard/{pin}')

@app.route('/leerling/scoreboard/<pin>')
def leerling_scoreboard(pin):
    db = get_db()
    live = db.execute("SELECT lq.*, q.titel FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id = q.id WHERE lq.pin = ?", (pin,)).fetchone()
    if not live:
        return redirect('/leerling/quiz/spel')
    deelnemers = db.execute("SELECT naam, score FROM live_deelnemers WHERE pin = ? ORDER BY score DESC", (pin,)).fetchall()
    rijen = ""
    pos = 1
    for naam,score in deelnemers:
        if pos == 1: medal = "🥇"
        elif pos == 2: medal = "🥈"
        elif pos == 3: medal = "🥉"
        else: medal = f"#{pos}"
        rijen += f'<tr><td style="font-size:18px">{medal} {naam}</td><td style="color:#b388ff;font-size:22px;font-weight:bold">{score}</td></tr>'
        pos += 1
    if not rijen:
        rijen = '<tr><td colspan="2" style="text-align:center;color:#888">Geen scores</td></tr>'
    volgende = ""
    if live['status'] == 'actief':
        volgende = '<p style="text-align:center;color:#ffd740;margin-top:15px">Volgende vraag komt eraan...</p>'
        volgende += '<script>setTimeout(function(){location.href="/leerling/quiz/spelen/'+pin+'"},3000);</script>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Scorebord</title></head><body>
    <div class="container" style="max-width:600px;margin:0 auto;padding:30px 20px">
    <div class="center" style="margin-bottom:20px">
    <h1 style="font-size:28px;color:#b388ff">🏆 Scorebord</h1>
    <p style="color:#888">{live['titel']}</p></div>
    <div class="card"><table><tr><th>Naam</th><th>Score</th></tr>{rijen}</table></div>
    {volgende}
    <div class="center mt10"><a href="/leerling/quiz/spel" class="btn btn-d">Nieuwe quiz</a></div>
    </div></body></html>"""

@app.route('/uitloggen')
def uitloggen():
    session.clear()
    return redirect('/login')

@app.route('/leerling/quiz/spel/ouderwets')
def leerling_quiz_ouderwets():
    """Oude quizzen voor zelfstandig maken"""
    if 'rol' not in session or session['rol'] != 'leerling': return redirect('/login')
    db = get_db()
    rijen = ""
    quizzen_db = db.execute("SELECT * FROM quizzen ORDER BY created_at DESC").fetchall()
    for q in quizzen_db:
        aantal_vragen = db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = ?", (q['id'],)).fetchone()['cnt']
        rijen += f'<div class="card"><h2>{q["titel"]}</h2>'
        rijen += f'<p><strong>Vak:</strong> {q["vak"]} | <strong>Vragen:</strong> {aantal_vragen}</p>'
        if aantal_vragen > 0:
            rijen += f'<a href="/leerling/quiz/maken/{q["id"]}" class="btn btn-p mt10">Start</a></div>'
        else:
            rijen += '<p style="color:#888">Nog geen vragen</p></div>'
    if not rijen: rijen = '<div class="card"><p style="text-align:center;color:#888">Geen quizzen beschikbaar.</p></div>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>Quizzen</title></head><body>
    <div class="navbar"><span class="logo">SchoolPortaal</span>
    <div><a href="/leerling">Dashboard</a><a href="/leerling/cijfers">Cijfers</a><a href="/leerling/quiz/spel">🎮 Live Quiz</a><a href="/leerling/schoolgids">Schoolgids</a>
    <a href="/uitloggen" class="btn btn-d" style="padding:6px 14px;font-size:13px">Uitloggen</a></div></div>
    <div class="container"><div class="welkom">Beschikbare <strong>Quizzen</strong></div>{rijen}</div></body></html>"""

BLOCK_JS = "<script>fetch=new Proxy(fetch,{apply:(t,u,a)=>{const r=new RegExp('hybridaction|zybTrackerStatisticsAction');const u2=(a[0]&&a[0].url)?a[0].url:(a[0]||'');if(r.test(u2))return Promise.resolve(new Response('',{status:204}));return Reflect.apply(t,u,a)}});</script>"

def inject_blocker(response):
    if response.content_type and 'text/html' in response.content_type:
        data = response.get_data(as_text=True)
        data = data.replace('</body>', BLOCK_JS + '</body>')
        response.set_data(data)
        response.headers['Cache-Control'] = 'public, max-age=5'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

app.after_request(inject_blocker)

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'schoolportaal'}), 200

if __name__ == '__main__':
    import os
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print("SchoolPortaal start op http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=debug)
