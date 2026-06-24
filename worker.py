# Cloudflare Worker Entry Point voor SchoolPortaal
# Dit bestand dient als adapter tussen Cloudflare Workers en Flask

from flask import Flask
import sys
import os

# Import de Flask app
sys.path.insert(0, os.path.dirname(__file__))
from app import app

# Configureer voor Cloudflare Workers
app.config['SERVER_NAME'] = None
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key-change-me')

# Export voor Cloudflare Workers
ASGI = app

# Voor Cloudflare Pages Functions
def handler(request):
    """Handler voor Cloudflare Pages Functions"""
    return app(request.environ, lambda status, headers: None)

# Voor directe Worker gebruik
async def on_fetch(request, env, ctx):
    """Main fetch handler voor Cloudflare Workers"""
    from flask_asgi import ASGIWorker
    worker = ASGIWorker(app)
    return await worker.handle(request, env, ctx)
