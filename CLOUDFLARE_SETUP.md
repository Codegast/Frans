# Cloudflare Gratis Deployment - SchoolPortaal

## Belangrijke Opmerking
De huidige app gebruikt SQLite database. Voor volledige Cloudflare Workers deployment moet de database aangepast worden naar D1. Dit gids beschrijft de eenvoudigste gratis opties.

## Optie 1: Cloudflare Pages (Aanbevolen voor Static/Serverless)

### Voordelen
- Gratis SSL
- CDN wereldwijd
- Git integration
- Serverless Functions

### Stap 1: GitHub Repository

1. Maak een GitHub repository
2. Push je code:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/jouw-username/schoolportaal.git
git push -u origin main
```

### Stap 2: Cloudflare Pages Setup

1. Ga naar Cloudflare Pages dashboard
2. "Create a project" → "Connect to Git"
3. Selecteer je GitHub repository
4. Build settings:
   - Framework preset: None
   - Build command: `pip install -r requirements.txt`
   - Build output directory: `/`

### Stap 3: Environment Variables

Voeg toe in Pages Settings:
- `SECRET_KEY`: jouw-geheime-sleier
- `FLASK_ENV`: production

### Stap 4: Custom Domein

1. Ga naar Custom Domains in Pages project
2. Voeg toe: `schoolportaal.jouw-domein.nl`

## Optie 2: Render.com (Aanbevolen voor Flask + SQLite)

### Voordelen
- Volledige Flask ondersteuning
- SQLite database werkt direct
- Gratis tier beschikbaar
- SSL inbegrepen

### Stap 1: Render Account

1. Ga naar [render.com](https://render.com)
2. Maak gratis account
3. Connect GitHub repository

### Stap 2: Web Service Aanmaken

1. "New" → "Web Service"
2. Selecteer repository
3. Build settings:
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
   - Environment: Python 3.9+

### Stap 3: Environment Variables

- `SECRET_KEY`: jouw-geheime-sleier
- `FLASK_ENV`: production

### Stap 4: Deploy

Klik op "Deploy Web Service"

## Optie 3: Railway.app (Alternatief)

### Voordelen
- SQLite ondersteuning
- Gratis tier
- Eenvoudige setup

### Stap 1: Railway Account

1. Ga naar [railway.app](https://railway.app)
2. Maak account
3. "New Project" → "Deploy from GitHub repo"

### Stap 2: Configureer

- Selecteer repository
- Add environment variables
- Deploy

## Optie 4: Cloudflare Workers met D1 (Complex)

Dit vereist het aanpassen van de database code in `app.py`:

### Vereiste aanpassingen

1. Uncomment database adapter in `app.py`:
```python
from db_adapter import get_db, init_db, db_adapter
```

2. Verwijder SQLite import

3. Gebruik `wrangler.toml` configuratie

4. Deploy met:
```bash
wrangler deploy
```

**Let op:** Dit vereist aanzienlijke code aanpassingen.

## Aanbevolen: Render.com

Voor de eenvoudigste gratis deployment met volledige functionaliteit:

1. Push code naar GitHub
2. Maak Render.com account
3. Connect repository
4. Configureer met bovenstaande instellingen
5. Deploy

Render.com ondersteunt SQLite direct en heeft een genereuze gratis tier.

## Custom Domein Setup

### Voor alle opties:

1. DNS record bij je domein provider:
```
Type: CNAME
Name: schoolportaal
Value: jouw-platform-url
TTL: 3600
```

2. Configureer in platform dashboard

## Monitoring

- Render.com: Dashboard met logs en statistieken
- Cloudflare Pages: Analytics dashboard
- Railway.app: Real-time logs

## Probleemoplossing

### SQLite werkt niet op platform
- Gebruik Render.com of Railway.app (ondersteunen SQLite)

### SSL fouten
- Wacht op DNS propagation (5-30 minuten)
- Check CNAME record

### Database fouten
- Check environment variables
- Bekijk platform logs

## Gratis Limits Vergelijking

| Platform | Requests/Dag | Database | SSL | Custom Domein |
|----------|--------------|----------|-----|----------------|
| Render.com | 750 hours | SQLite (1GB) | ✅ | ✅ |
| Railway.app | 500 hours | SQLite (1GB) | ✅ | ✅ |
| Cloudflare Pages | 500 builds | Geen | ✅ | ✅ |
| Cloudflare Workers | 100K | D1 (5GB) | ✅ | ✅ |

## Aanbeveling

**Gebruik Render.com** voor:
- Eenvoudigste setup
- SQLite ondersteuning
- Goede gratis limits
- Volledige Flask functionaliteit

**Gebruik Cloudflare Workers** alleen als je:
- D1 database wilt gebruiken
- Willing om database code aan te passen
- Maximaal performance nodig hebt
