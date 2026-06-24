# Subdomain Configuratie - SchoolPortaal

## Overzicht
Dit document helpt je om SchoolPortaal beschikbaar te maken via `schoolportaal.jouw-domein.nl`

## Stap 1: DNS Configuratie

### Option A: CNAME Record (Aanbevolen)
Voeg een CNAME record toe aan je DNS provider:

```
Type: CNAME
Name: schoolportaal
Value: jouw-domein.nl
TTL: 3600
```

### Option B: A Record
Als je een specifiek IP adres hebt:

```
Type: A
Name: schoolportaal
Value: 123.456.789.012 (jouw server IP)
TTL: 3600
```

## Stap 2: Flask App Configuratie

In `app.py`, uncomment en pas de SERVER_NAME regel aan:

```python
app.config['SERVER_NAME'] = 'schoolportaal.jouw-domein.nl'
```

**Belangrijk:** Verwijder deze regel voor lokaal ontwikkeling (localhost)

## Stap 3: Server Configuratie

### Met Nginx (Aanbevolen)

Maak `/etc/nginx/sites-available/schoolportaal`:

```nginx
server {
    listen 80;
    server_name schoolportaal.jouw-domein.nl;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activeer de configuratie:
```bash
sudo ln -s /etc/nginx/sites-available/schoolportaal /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Met Apache

Maak `/etc/apache2/sites-available/schoolportaal.conf`:

```apache
<VirtualHost *:80>
    ServerName schoolportaal.jouw-domein.nl
    
    ProxyPreserveHost On
    ProxyRequests Off
    
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
</VirtualHost>
```

Activeer:
```bash
sudo a2ensite schoolportaal
sudo systemctl reload apache2
```

## Stap 4: SSL Certificaat (Aanbevolen)

Gebruik Let's Encrypt voor gratis HTTPS:

```bash
sudo certbot --nginx -d schoolportaal.jouw-domein.nl
```

Of met Apache:
```bash
sudo certbot --apache -d schoolportaal.jouw-domein.nl
```

## Stap 5: Flask App Draaien

### Ontwikkeling (Lokaal)
```bash
python app.py
# Beschikbaar op http://localhost:5000
```

### Productie (Met Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app:app
```

### Met Systemd Service
Maak `/etc/systemd/system/schoolportaal.service`:

```ini
[Unit]
Description=SchoolPortaal Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/pad/naar/Frans
Environment="PATH=/pad/naar/venv/bin"
ExecStart=/pad/naar/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Activeer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable schoolportaal
sudo systemctl start schoolportaal
```

## Stap 6: Environment Variables

Maak een `.env` bestand in de project map:

```env
SECRET_KEY=jouw-geheime-sleier-hier
LOG_LEVEL=INFO
LOG_FILE=schoolportaal.log
```

## Testen

1. DNS propagation: `dig schoolportaal.jouw-domein.nl`
2. HTTP test: `curl http://schoolportaal.jouw-domein.nl`
3. HTTPS test: `curl https://schoolportaal.jouw-domein.nl`

## Probleemoplossing

### DNS niet gevonden
- Wacht 5-30 minuten op DNS propagation
- Check DNS record bij je provider

### 502 Bad Gateway
- Check of Flask app draait: `ps aux | grep gunicorn`
- Check logs: `sudo journalctl -u schoolportaal`

### SSL fouten
- Check certificaat: `sudo certbot certificates`
- Vernieuw certificaat: `sudo certbot renew`

## Veiligheid

- Zorg dat `SECRET_KEY` uniek en sterk is
- Gebruik HTTPS in productie
- Beperk toegang tot database bestand
- Update regelmatig afhankelijkheden

## Contact

Voor support, check de logs in `schoolportaal.log`
