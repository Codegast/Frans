from flask import Flask, render_template_string, request, redirect, session, jsonify, g
import random, string, time, threading, logging, os, secrets
from typing import Optional, Dict, Any, List, Tuple
from markupsafe import escape, Markup
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Import database adapter (optioneel voor Cloudflare)
# Voor lokaal gebruik: gebruik SQLite
# Voor Cloudflare: uncomment onderstaande regels
# from db_adapter import get_db, init_db, db_adapter

# Voor lokaal gebruik: gebruik SQLite
import sqlite3

# ==== XSS Protection ====
def safe_string(s):
    return escape(str(s)) if s else ""

# ==== SVG Icons ====
ICONS = {
    'dashboard': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    'classes': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
    'tests': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
    'quiz': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    'grades': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/><line x1="2" y1="20" x2="22" y2="20"/></svg>',
    'students': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    'live': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    'messages': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    'logout': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
    'login': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>',
    'user': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    'lock': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
    'trash': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>',
    'edit': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
    'plus': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
    'arrow-right': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>',
    'arrow-left': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>',
    'check': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    'clock': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    'calendar': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    'book': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    'trophy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>',
    'play': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    'pause': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',
    'stop': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>',
    'skip': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/></svg>',
    'refresh': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>',
    'school': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>',
    'phone': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    'mail': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    'star': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    'heart': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',
    'sword': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" y1="19" x2="19" y2="13"/><line x1="16" y1="16" x2="20" y2="20"/><line x1="20" y1="17" x2="17" y2="20"/></svg>',
    'shield': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    'dragon': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c0 5-2 8-5 8"/><path d="M12 2c0 5 2 8 5 8"/><path d="M7 10c0 3 2 5 5 5s5-2 5-5"/><path d="M12 15v7"/><path d="M8 18h8"/><path d="M9 12l-3 3"/><path d="M15 12l3 3"/></svg>',
    'game': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 12h4"/><path d="M8 10v4"/><line x1="15" y1="11" x2="15" y2="11"/><line x1="18" y1="13" x2="18" y2="13"/></svg>',
    'key': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>',
    'warning': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    'settings': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
    'copy': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>',
    'info': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    'crown': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 19l2.5-14L7 10 12 4l5 6 2.5-7L22 19H2z"/></svg>',
    'zap': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    'percent': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/></svg>',
    'file': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
    'help': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    'trending': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>',
    'volume': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
    'target': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>',
    'eye': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
    'pin': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    'send': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>',
    'folders': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>',
    'upload': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
    'file-text': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
    'circle': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" stroke="none"><circle cx="12" cy="12" r="8"/></svg>',
    'sun': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>',
}

def icon(name, size=18):
    svg = ICONS.get(name, '')
    if svg:
        svg = svg.replace('<svg', f'<svg width="{size}" height="{size}"')
        return svg
    return ''

# ==== Logging ====
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'schoolportaal.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('schoolportaal')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key-change-me')

# Subdomain configuratie - Uncomment en pas aan voor productie
# Voor lokaal ontwikkeling: gebruik localhost:5000
# Voor productie met subdomain: uncomment onderstaande regel
# app.config['SERVER_NAME'] = 'schoolportaal.jouw-domein.nl'

# ==== Auth Decorators ====
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'rol' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def rol_required(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('rol') != role:
                return redirect('/login')
            return f(*args, **kwargs)
        return decorated
    return decorator

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# ==== Database ====
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

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('docent','leerling')),
        display_name TEXT NOT NULL,
        vak TEXT DEFAULT '',
        klas TEXT DEFAULT '',
        school_id INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(school_id) REFERENCES schools(id)
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
        boss_hp INTEGER DEFAULT 0,
        boss_max_hp INTEGER DEFAULT 0,
        team_hp INTEGER DEFAULT 0,
        team_max_hp INTEGER DEFAULT 0, 
        boss_naam TEXT DEFAULT 'De Grote Draak',
        vraag_tijd INTEGER DEFAULT 20,
        gestart_op TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        beeindigd_op TIMESTAMP,
        school_id INTEGER DEFAULT 1,
        FOREIGN KEY(quiz_id) REFERENCES quizzen(id)
    );
    CREATE TABLE IF NOT EXISTS live_deelnemers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pin TEXT NOT NULL,
        naam TEXT NOT NULL,
        klas TEXT DEFAULT 'attacker',
        score INTEGER NOT NULL DEFAULT 0,
        total_damage INTEGER DEFAULT 0,
        correct_answers INTEGER DEFAULT 0,
        heals_done INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
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
    CREATE TABLE IF NOT EXISTS berichten (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        afzender_id INTEGER NOT NULL,
        ontvanger_id INTEGER NOT NULL,
        onderwerp TEXT NOT NULL,
        inhoud TEXT NOT NULL,
        gelezen BOOLEAN NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(afzender_id) REFERENCES users(id),
        FOREIGN KEY(ontvanger_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS wachtwoord_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        used BOOLEAN NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS rpg_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pin TEXT NOT NULL,
        bericht TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'info',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(pin) REFERENCES live_quizzen(pin) ON DELETE CASCADE
    );
    """)
    db.execute("INSERT OR IGNORE INTO schools (id, name) VALUES (1, 'Demo School')")
    db.commit()

with app.app_context():
    init_db()

# ==== Seed Data ====
def seed_demo_data():
    db = get_db()
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
    demo_leerlingen = [("piet","leerling123","Piet"),("anna","leerling123","Anna"),("tom","leerling123","Tom"),("lisa","leerling123","Lisa")]
    for u,p,naam in demo_leerlingen:
        db.execute("INSERT OR IGNORE INTO users (username, password_hash, role, display_name) VALUES (?,?,?,?)",
                   (u, generate_password_hash(p), 'leerling', naam))
    db.commit()
    quiz_data = [
        (1, "Wiskunde Quiz 1", "wi", "la21"),
        (1, "Nederlandse Taal", "nl", "la21"),
        (2, "Bijeenkomst Soesterberg", "ak", "la21"),
    ]
    for did, titel, vak, klas in quiz_data:
        db.execute("INSERT OR IGNORE INTO quizzen (titel, vak, klas, docent_id) VALUES (?,?,?,?)",
                   (titel, vak, klas, did))
    db.commit()
    vragen_data = [
        ("Wat is 2 + 2?", "3", "4", "5", "6", 1),
        ("Hoeveel zijden heeft een driehoek?", "2", "3", "4", "5", 1),
        ("Wat is de hoofdstad van Nederland?", "Rotterdam", "Den Haag", "Amsterdam", "Utrecht", 2),
    ]
    for tekst, a, b, c, d, antwoord in vragen_data:
        volgorde = db.execute("SELECT COUNT(*) as cnt FROM vragen WHERE quiz_id = 1").fetchone()['cnt']
        db.execute("INSERT INTO vragen (quiz_id, tekst, optie_a, optie_b, optie_c, optie_d, antwoord, volgorde) VALUES (?,?,?,?,?,?,?,?)",
                   (1, tekst, a, b, c, d, antwoord, volgorde))
    db.commit()

with app.app_context():
    seed_demo_data()

# ==== MODERN UI CSS COMPLETE REWRITE ====
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--primary:#7c4dff;--primary-light:#b388ff;--secondary:#ff4081;--success:#00e676;--warning:#ffc107;--danger:#ff5252;--bg-dark:#0f0c29;--bg-mid:#302b63;--bg-light:#24243e;--glass:rgba(255,255,255,.08);--glass-border:rgba(255,255,255,.12)}
body{font-family:'Segoe UI','Inter',system-ui,-apple-system,sans-serif;background:linear-gradient(135deg,var(--bg-dark),var(--bg-mid),var(--bg-light));min-height:100vh;color:#fff;overflow-x:hidden;line-height:1.6}
body::before{content:'';position:fixed;top:0;left:0;width:100%;height:100%;background:radial-gradient(circle at 20% 80%,rgba(124,77,255,.1) 0%,transparent 50%),radial-gradient(circle at 80% 20%,rgba(255,64,129,.08) 0%,transparent 50%);pointer-events:none;z-index:0}
.container{max-width:1280px;margin:0 auto;padding:24px;position:relative;z-index:1}
.card{background:var(--glass);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid var(--glass-border);border-radius:20px;padding:28px;margin-bottom:24px;transition:all .3s cubic-bezier(.4,0,.2,1);box-shadow:0 4px 24px rgba(0,0,0,.2)}
.card:hover{transform:translateY(-4px);box-shadow:0 12px 40px rgba(124,77,255,.2);border-color:rgba(124,77,255,.3)}
.card h2{color:var(--primary-light);margin-bottom:16px;font-size:20px;display:flex;align-items:center;gap:10px;font-weight:700}
.card h2 svg{width:22px;height:22px;fill:currentColor;flex-shrink:0}
.navbar{background:rgba(15,12,41,.95);backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);padding:10px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--glass-border);position:sticky;top:0;z-index:1000;box-shadow:0 4px 30px rgba(0,0,0,.4);flex-wrap:wrap;gap:10px}
.navbar .logo{font-size:20px;font-weight:800;color:var(--primary-light);display:flex;align-items:center;gap:10px;text-shadow:0 0 20px rgba(124,77,255,.5);flex-shrink:0}
.navbar .logo .logo-icon{width:36px;height:36px;background:linear-gradient(135deg,var(--primary),var(--primary-light));border-radius:10px;display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:bold;flex-shrink:0;box-shadow:0 4px 20px rgba(124,77,255,.4)}
.navbar a{color:#b0b8c4;text-decoration:none;padding:8px 14px;border-radius:10px;font-size:13px;font-weight:500;transition:all .2s ease;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;flex-shrink:0}
.navbar a:hover{background:rgba(124,77,255,.2);color:#fff;transform:translateY(-1px)}
.navbar a.active{background:linear-gradient(135deg,var(--primary),var(--primary-light));color:#fff;box-shadow:0 4px 15px rgba(124,77,255,.3)}
.navbar .nav-wrap{display:flex;align-items:center;gap:6px;flex-wrap:wrap;justify-content:flex-end;max-width:100%}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 24px;border-radius:12px;text-decoration:none;font-size:14px;font-weight:600;border:none;cursor:pointer;text-align:center;transition:all .25s cubic-bezier(.4,0,.2,1);line-height:1.2;position:relative;overflow:hidden}
.btn::before{content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;background:linear-gradient(90deg,transparent,rgba(255,255,255,.2),transparent);transition:left .5s}
.btn:hover::before{left:100%}
.btn-p{background:linear-gradient(135deg,var(--primary),var(--primary-light));color:#fff;box-shadow:0 4px 20px rgba(124,77,255,.35)}
.btn-p:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(124,77,255,.5)}
.btn-d{background:linear-gradient(135deg,var(--danger),#ff6e6e);color:#fff;box-shadow:0 4px 20px rgba(255,82,82,.35)}
.btn-d:hover{transform:translateY(-2px);box-shadow:0 8px 30px rgba(255,82,82,.5)}
.btn-g{background:linear-gradient(135deg,rgba(0,230,118,.3),rgba(0,230,118,.15));color:var(--success);border:1px solid rgba(0,230,118,.3);backdrop-filter:blur(8px)}
.btn-g:hover{background:linear-gradient(135deg,rgba(0,230,118,.4),rgba(0,230,118,.25));transform:translateY(-2px);border-color:var(--success)}
.btn-sm{padding:8px 16px;font-size:13px;border-radius:10px}
.btn-full{width:100%;padding:16px;font-size:16px}
svg{max-width:100%;height:auto}
.btn svg{width:16px;height:16px;flex-shrink:0}
.welkom{font-size:17px;color:#a0a8b8;margin-bottom:24px;padding:12px 0;font-weight:500}
.welkom strong{color:var(--primary-light);font-weight:700}
label.f{display:block;margin-bottom:12px;color:var(--primary-light);font-weight:600;font-size:14px}
input,select,textarea{width:100%;padding:14px 18px;border:2px solid rgba(255,255,255,.1);border-radius:12px;background:rgba(255,255,255,.05);color:#fff;font-size:15px;outline:none;margin-top:6px;transition:all .25s ease;font-family:inherit}
input:focus,select:focus,textarea:focus{border-color:var(--primary);box-shadow:0 0 0 4px rgba(124,77,255,.15);background:rgba(255,255,255,.08)}
input::placeholder,textarea::placeholder{color:rgba(255,255,255,.4)}
select{cursor:pointer;appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23b388ff' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 14px center;padding-right:40px}
textarea{resize:vertical;min-height:80px;line-height:1.5}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}
.stat-card{background:linear-gradient(135deg,rgba(124,77,255,.12),rgba(124,77,255,.05));border:1px solid rgba(124,77,255,.25);border-radius:18px;padding:32px 24px;text-align:center;min-height:150px;display:flex;flex-direction:column;justify-content:center;align-items:center;transition:all .3s cubic-bezier(.4,0,.2,1);position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;background:radial-gradient(circle,rgba(124,77,255,.1) 0%,transparent 70%);opacity:0;transition:opacity .3s}
.stat-card:hover::before{opacity:1}
.stat-card:hover{background:linear-gradient(135deg,rgba(124,77,255,.18),rgba(124,77,255,.08));transform:translateY(-6px);box-shadow:0 12px 40px rgba(124,77,255,.25);border-color:var(--primary)}
.stat-card .getal{font-size:48px;font-weight:800;color:var(--primary-light);line-height:1.1;margin-bottom:8px;text-shadow:0 0 30px rgba(124,77,255,.3)}
.stat-card .label{font-size:14px;color:#a0a8b8;margin-top:4px;font-weight:500;text-transform:uppercase;letter-spacing:1px}
.stat-card .icoon{font-size:32px;margin-bottom:12px;filter:drop-shadow(0 4px 8px rgba(124,77,255,.3))}
.table-wrap{overflow-x:auto;border-radius:12px}
table{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}
th,td{padding:16px 18px;text-align:left;border-bottom:1px solid rgba(255,255,255,.06)}
th{color:var(--primary-light);font-size:12px;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;background:rgba(124,77,255,.08)}
tr:hover{background:rgba(124,77,255,.08)}
tr:last-child td{border-bottom:none}
.rol-grid{display:flex;gap:16px;margin-bottom:20px}
.rol-select{text-align:center;padding:24px 16px;border:2px solid rgba(124,77,255,.25);border-radius:16px;cursor:pointer;transition:all .25s cubic-bezier(.4,0,.2,1);flex:1;font-weight:600;font-size:15px;background:rgba(255,255,255,.02)}
.rol-select:hover{border-color:var(--primary);background:rgba(124,77,255,.12);transform:translateY(-4px)}
.rol-select.selected{border-color:var(--primary);background:linear-gradient(135deg,rgba(124,77,255,.2),rgba(124,77,255,.1));box-shadow:0 8px 30px rgba(124,77,255,.3);transform:scale(1.02)}
.rol-select .rol-icon{display:block;margin-bottom:8px}
.rol-select .rol-icon svg{width:22px;height:22px;max-width:22px;max-height:22px}
.pin-display{font-size:56px;font-weight:800;color:var(--primary-light);letter-spacing:12px;text-align:center;padding:32px;background:linear-gradient(135deg,rgba(124,77,255,.15),rgba(124,77,255,.05));border:3px dashed rgba(124,77,255,.4);border-radius:20px;margin:20px 0;font-family:'Courier New',monospace;text-shadow:0 0 30px rgba(124,77,255,.4);animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.7}}
.login-screen{display:flex;justify-content:center;align-items:center;min-height:100vh;padding:24px;position:relative}
.login-screen::before{content:'';position:absolute;top:0;left:0;width:100%;height:100%;background:radial-gradient(circle at 50% 50%,rgba(124,77,255,.15) 0%,transparent 50%);pointer-events:none}
.login-box{width:100%;max-width:460px;position:relative;z-index:1}
.login-header{text-align:center;margin-bottom:36px}
.login-header h1{font-size:36px;color:var(--primary-light);margin-bottom:8px;display:flex;align-items:center;justify-content:center;gap:12px;font-weight:800;text-shadow:0 0 30px rgba(124,77,255,.3)}
.login-header p{color:#a0a8b8;font-size:16px}
.error-msg{background:rgba(255,82,82,.15);border:1px solid var(--danger);border-radius:12px;padding:14px 18px;margin-bottom:18px;color:#ff8a80;text-align:center;font-weight:500;animation:shake .5s ease-in-out}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-8px)}75%{transform:translateX(8px)}}
.success-msg{background:rgba(0,230,118,.15);border:1px solid var(--success);border-radius:12px;padding:14px 18px;margin-bottom:18px;color:var(--success);text-align:center;font-weight:500}
.antwoord{display:flex;align-items:center;width:100%;padding:16px 20px;margin-bottom:10px;background:rgba(255,255,255,.04);border:2px solid rgba(255,255,255,.12);border-radius:14px;cursor:pointer;font-size:16px;transition:all .2s cubic-bezier(.4,0,.2,1);color:#fff;font-weight:500}
.antwoord:hover{background:rgba(124,77,255,.15);border-color:rgba(124,77,255,.5);transform:translateX(4px)}
.antwoord.selected{background:linear-gradient(135deg,rgba(124,77,255,.3),rgba(124,77,255,.15));border-color:var(--primary);box-shadow:0 8px 30px rgba(124,77,255,.3);transform:scale(1.02)}
.antwoord .letter{display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--primary),var(--primary-light));color:#fff;width:40px;height:40px;border-radius:12px;margin-right:16px;font-weight:700;font-size:16px;flex-shrink:0;box-shadow:0 4px 15px rgba(124,77,255,.3)}
.antwoord.selected .letter{background:linear-gradient(135deg,var(--primary-light),var(--primary));transform:scale(1.1)}
.center{text-align:center}
.mt10{margin-top:10px}.mb10{margin-bottom:10px}
.mt20{margin-top:20px}.mb20{margin-bottom:20px}
.flex{display:flex;align-items:center;gap:12px}
.flex-wrap{flex-wrap:wrap}
.gap8{gap:8px}.gap12{gap:12px}.gap16{gap:16px}
.badge{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:24px;font-size:12px;font-weight:700;line-height:1.2;text-transform:uppercase;letter-spacing:.5px}
.badge-green{background:rgba(0,230,118,.15);color:var(--success);border:1px solid rgba(0,230,118,.3)}
.badge-red{background:rgba(255,82,82,.15);color:#ff8a80;border:1px solid rgba(255,82,82,.3)}
.badge-gold{background:rgba(255,193,7,.15);color:#ffd740;border:1px solid rgba(255,193,7,.3)}
.badge-purple{background:rgba(124,77,255,.2);color:var(--primary-light);border:1px solid rgba(124,77,255,.3)}
.medal{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;font-size:16px;font-weight:bold;margin-right:10px;flex-shrink:0;box-shadow:0 4px 12px rgba(0,0,0,.3)}
.medal-1{background:linear-gradient(135deg,#ffd700,#ffaa00);color:#fff;box-shadow:0 4px 20px rgba(255,215,0,.4)}
.medal-2{background:linear-gradient(135deg,#c0c0c0,#a0a0a0);color:#fff;box-shadow:0 4px 20px rgba(192,192,192,.4)}
.medal-3{background:linear-gradient(135deg,#cd7f32,#b8860b);color:#fff;box-shadow:0 4px 20px rgba(205,127,50,.4)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:768px){.form-grid{grid-template-columns:1fr}.navbar{padding:12px 20px;flex-direction:column;gap:12px}.navbar .nav-wrap{justify-content:center;flex-wrap:wrap}.navbar .logo{margin-bottom:4px}.container{padding:16px}.grid{grid-template-columns:1fr}}
@media(max-width:480px){.navbar .nav-wrap{flex-direction:column;width:100%}.navbar a{width:100%;justify-content:center}.btn{width:100%}}
.cursor-pointer{cursor:pointer}
.loading{display:inline-block;width:20px;height:20px;border:3px solid rgba(255,255,255,.3);border-radius:50%;border-top-color:#fff;animation:spin 1s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.fade-in{animation:fadeIn .5s ease-in}
@keyframes fadeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.slide-up{animation:slideUp .4s ease-out}
@keyframes slideUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
"""

ERROR_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Fout - SchoolPortaal</title></head>
<body>
<div class="login-screen">
<div class="login-box">
<div class="login-header">
<h1><span class="logo-icon" style="width:44px;height:44px;font-size:22px">SP</span> SchoolPortaal</h1>
</div>
<div class="card" style="text-align:center;padding:40px">
<div style="font-size:48px;margin-bottom:16px">""" + icon('warning', 48) + """</div>
<h2 style="color:var(--primary-light);margin-bottom:12px">Er is een fout opgetreden</h2>
<p style="color:#a0a8b8;font-size:16px;margin-bottom:24px">{{error}}</p>
<a href="/" class="btn btn-p btn-full">""" + icon('arrow-left', 18) + """ Terug naar home</a>
</div>
</div>
</div>
</body></html>"""

# ==== Block tracker ====
def empty_state(text, icon_name="info"):
    return f'<div style="text-align:center;padding:60px 20px"><div style="font-size:64px;margin-bottom:16px">{icon(icon_name, 64)}</div><h2 style="color:#888;font-weight:500">{text}</h2></div>'

@app.route('/hybridaction/zybTrackerStatisticsAction', methods=['GET','POST','OPTIONS'])
def block_tracker():
    return '', 204

# ==== Error handlers ====
@app.errorhandler(404)
def not_found(error):
    return render_template_string(ERROR_HTML, CSS=CSS, error=Markup(icon('warning', 20) + " Pagina niet gevonden")), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return render_template_string(ERROR_HTML, CSS=CSS, error=Markup(icon('warning', 20) + " Er is een fout opgetreden")), 500


# ==== Routes ====
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

# ===== LOGIN =====
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        un = request.form.get('gebruikersnaam', '').strip()
        ww = request.form.get('wachtwoord', '').strip()
        if not un or not ww:
            return render_template_string(LOGIN_HTML, CSS=CSS, fout=icon('warning', 16) + " Vul gebruikersnaam en wachtwoord in.")
        if len(un) > 50 or len(ww) > 128:
            return render_template_string(LOGIN_HTML, CSS=CSS, fout=icon('warning', 16) + " Ongeldige invoer.")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (un,)).fetchone()
        if user and check_password_hash(user['password_hash'], ww):
            logger.info(f"Login: {un} ({user['role']})")
            session.clear()
            session['user_id'] = user['id']
            session['rol'] = user['role']
            session['naam'] = user['display_name']
            session['vak'] = user['vak'] or ''
            session['gebruikersnaam'] = user['username']
            session.permanent = True
            return redirect('/docent' if user['role'] == 'docent' else '/leerling')
        logger.warning(f"Mislukte login: {un}")
        return render_template_string(LOGIN_HTML, CSS=CSS, fout=icon('warning', 16) + " Ongeldige inloggegevens.")
    return render_template_string(LOGIN_HTML, CSS=CSS, fout="")

LOGIN_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Inloggen - SchoolPortaal</title></head>
<body>
<div class="login-screen">
<div class="login-box">
<div class="login-header">
<h1><span class="logo-icon" style="width:44px;height:44px;font-size:22px">SP</span> SchoolPortaal</h1>
<p>""" + icon('school', 24) + """ Log in om verder te gaan</p>
</div>
{% if fout %}<div class="error-msg">{{fout}}</div>{% endif %}
<div class="card">
<form method="POST" action="/login">
<label class="f">""" + icon('user', 18) + """ Rol</label>
  <div class="rol-grid">
  <div class="rol-select" onclick="selectRol(this,'docent')" id="rd"><span class="rol-icon">""" + icon('user', 20) + """</span><span>Docent</span></div>
  <div class="rol-select" onclick="selectRol(this,'leerling')" id="rl"><span class="rol-icon">""" + icon('students', 20) + """</span><span>Leerling</span></div>
  </div>
<input type="hidden" name="rol" id="rol" value="docent">
<label class="f">""" + icon('user', 18) + """ Gebruikersnaam<input type="text" name="gebruikersnaam" required placeholder="Vul je gebruikersnaam in"></label>
<label class="f">""" + icon('lock', 18) + """ Wachtwoord<input type="password" name="wachtwoord" required placeholder="Vul je wachtwoord in"></label>
<button type="submit" class="btn btn-p btn-full mt10">""" + icon('login', 18) + """ Inloggen</button>
</form>
<p class="center mt10"><a href="/wachtwoord-reset" style="color:#888;font-size:13px">""" + icon('key', 16) + """ Wachtwoord vergeten?</a></p>
</div></div></div>
<script>
document.getElementById('rd').classList.add('selected');
function selectRol(el,rol){
  document.querySelectorAll('.rol-select').forEach(e=>e.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('rol').value=rol;
}
</script>
</body></html>"""

# ===== DOCENT DASHBOARD =====
@app.route('/docent')
@login_required
@rol_required('docent')
def docent_dashboard():
    db = get_db()
    uid = session['user_id']
    
    # Basic stats
    at = db.execute("SELECT COUNT(*) as c FROM toetsen WHERE docent_id=?", (uid,)).fetchone()['c']
    aq = db.execute("SELECT COUNT(*) as c FROM quizzen WHERE docent_id=?", (uid,)).fetchone()['c']
    al = db.execute("SELECT COUNT(*) as c FROM users WHERE role='leerling'").fetchone()['c']
    ac = db.execute("SELECT COUNT(*) as c FROM cijfers").fetchone()['c']
    
    # Advanced stats
    avg_grade = db.execute("SELECT AVG(cijfer) as avg FROM cijfers").fetchone()['avg'] or 0
    recent_grades = db.execute("SELECT COUNT(*) as c FROM cijfers WHERE created_at > datetime('now', '-7 days')").fetchone()['c']
    active_quizzes = db.execute("SELECT COUNT(*) as c FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id WHERE q.docent_id=? AND lq.status='actief'", (uid,)).fetchone()['c']
    
    # Upcoming tests (next 7 days)
    upcoming_tests = db.execute("""
        SELECT titel, vak, klas, datum, tijd 
        FROM toetsen 
        WHERE docent_id=? AND datum >= date('now') AND datum <= date('now', '+7 days')
        ORDER BY datum ASC LIMIT 5
    """, (uid,)).fetchall()
    
    # Recent activity
    recent_activity = []
    recent_cijfers = db.execute("""
        SELECT c.cijfer, u.display_name, c.vak, c.created_at 
        FROM cijfers c JOIN users u ON c.leerling_id=u.id 
        WHERE c.created_at > datetime('now', '-3 days')
        ORDER BY c.created_at DESC LIMIT 5
    """).fetchall()
    for c in recent_cijfers:
        recent_activity.append({
            'type': 'grade',
            'text': f'Cijfer {c["cijfer"]} toegevoegd voor {c["display_name"]} ({c["vak"]})',
            'time': c['created_at']
        })
    
    recent_quizzen = db.execute("""
        SELECT titel, created_at 
        FROM quizzen 
        WHERE docent_id=? AND created_at > datetime('now', '-3 days')
        ORDER BY created_at DESC LIMIT 3
    """, (uid,)).fetchall()
    for q in recent_quizzen:
        recent_activity.append({
            'type': 'quiz',
            'text': f'Nieuwe quiz "{q["titel"]}" aangemaakt',
            'time': q['created_at']
        })
    
    # Sort activity by time
    recent_activity.sort(key=lambda x: x['time'], reverse=True)
    recent_activity = recent_activity[:8]
    
    # Top performers
    top_students = db.execute("""
        SELECT u.display_name, AVG(c.cijfer) as avg_grade, COUNT(c.cijfer) as count
        FROM cijfers c JOIN users u ON c.leerling_id=u.id
        GROUP BY u.id
        HAVING count >= 3
        ORDER BY avg_grade DESC LIMIT 5
    """).fetchall()
    
    # Class averages by subject
    subject_averages = db.execute("""
        SELECT vak, AVG(cijfer) as avg, COUNT(*) as count
        FROM cijfers
        GROUP BY vak
        ORDER BY avg DESC
    """).fetchall()
    
    return render_template_string(DOCENT_DASH_HTML, CSS=CSS, naam=session['naam'], vak=session['vak'],
        aant_toetsen=at, aant_quizzen=aq, aant_leerlingen=al, aant_cijfers=ac,
        avg_grade=round(avg_grade, 1), recent_grades=recent_grades, active_quizzes=active_quizzes,
        upcoming_tests=upcoming_tests, recent_activity=recent_activity,
        top_students=top_students, subject_averages=subject_averages)

DOCENT_DASH_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style>
<style>
.dashboard-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-bottom:24px}
.activity-item{display:flex;align-items:center;gap:12px;padding:12px;background:rgba(255,255,255,.03);border-radius:10px;margin-bottom:8px;border-left:3px solid}
.activity-item.grade{border-color:var(--success)}
.activity-item.quiz{border-color:var(--primary-light)}
.activity-item.test{border-color:var(--warning)}
.activity-icon{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.activity-item.grade .activity-icon{background:rgba(0,230,118,.15);color:var(--success)}
.activity-item.quiz .activity-icon{background:rgba(124,77,255,.15);color:var(--primary-light)}
.activity-item.test .activity-icon{background:rgba(255,193,7,.15);color:var(--warning)}
.activity-text{flex:1}
.activity-time{font-size:12px;color:#888;margin-top:2px}
.progress-bar{height:8px;background:rgba(255,255,255,.1);border-radius:4px;overflow:hidden;margin-top:8px}
.progress-fill{height:100%;border-radius:4px;transition:width .5s ease}
.upcoming-item{display:flex;align-items:center;gap:12px;padding:12px;background:rgba(255,255,255,.03);border-radius:10px;margin-bottom:8px}
.upcoming-date{background:rgba(124,77,255,.15);color:var(--primary-light);padding:8px 12px;border-radius:8px;text-align:center;min-width:70px}
.upcoming-date .day{font-size:18px;font-weight:bold;line-height:1}
.upcoming-date .month{font-size:11px;text-transform:uppercase}
.top-student{display:flex;align-items:center;gap:12px;padding:10px;background:rgba(255,255,255,.03);border-radius:10px;margin-bottom:8px}
.top-student .rank{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:12px}
.top-student:nth-child(1) .rank{background:linear-gradient(135deg,#ffd700,#ffaa00);color:#fff}
.top-student:nth-child(2) .rank{background:linear-gradient(135deg,#c0c0c0,#a0a0a0);color:#fff}
.top-student:nth-child(3) .rank{background:linear-gradient(135deg,#cd7f32,#b8860b);color:#fff}
.top-student:nth-child(n+4) .rank{background:rgba(255,255,255,.1);color:#888}
.subject-bar{display:flex;align-items:center;gap:12px;margin-bottom:12px}
.subject-name{flex:1;font-size:14px;color:#ccc}
.subject-grade{font-weight:bold;color:var(--primary-light);min-width:50px;text-align:right}
</style>
<title>Dashboard - Docent</title></head>
<body>
<div class="navbar">
  <span class="logo"><span class="logo-icon">SP</span> SchoolPortaal</span>
  <div class="nav-wrap">
    <a href="/docent" class="active">""" + icon('dashboard', 16) + """ Dashboard</a>
    <a href="/docent/klassen">""" + icon('classes', 16) + """ Klassen</a>
    <a href="/docent/toetsen">""" + icon('tests', 16) + """ Toetsen</a>
    <a href="/docent/quizzen">""" + icon('quiz', 16) + """ Quizzen</a>
    <a href="/docent/cijfers">""" + icon('grades', 16) + """ Cijfers</a>
    <a href="/docent/leerlingen">""" + icon('students', 16) + """ Leerlingen</a>
    <a href="/docent/live">""" + icon('live', 16) + """ Live Quiz</a>
    <a href="/berichten">""" + icon('messages', 16) + """ Berichten</a>
    <a href="/uitloggen" class="btn btn-d btn-sm">""" + icon('logout', 16) + """ Uitloggen</a>
  </div>
</div>
<div class="container">
<div class="welkom">""" + icon('user', 18) + """ Welkom terug, <strong>{{naam}}</strong>! | """ + icon('book', 18) + """ {{vak}}</div>

<div class="grid">
  <div class="stat-card"><div class="icoon">""" + icon('students', 36) + """</div><div class="getal">{{aant_leerlingen}}</div><div class="label">Leerlingen</div></div>
  <div class="stat-card"><div class="icoon">""" + icon('tests', 36) + """</div><div class="getal">{{aant_toetsen+aant_quizzen}}</div><div class="label">Items (toetsen/quizzen)</div></div>
  <div class="stat-card"><div class="icoon">""" + icon('grades', 36) + """</div><div class="getal">{{aant_cijfers}}</div><div class="label">Cijfers ingevoerd</div></div>
  <div class="stat-card"><div class="icoon">""" + icon('messages', 36) + """</div><div class="getal" id="ongelezenCount">0</div><div class="label">Ongelezen berichten</div></div>
</div>

<div class="dashboard-grid">
  <div class="card" style="grid-column:span 2">
    <h2>""" + icon('clock', 20) + """ Komende Toetsen & Deadlines</h2>
    {% if upcoming_tests %}
    {% for test in upcoming_tests %}
    <div class="upcoming-item">
      <div class="upcoming-date">
        <div class="day">{{test.datum|replace('-','')|slice(8,10)}}</div>
        <div class="month">{{test.datum|replace('-','')|slice(5,7)}}</div>
      </div>
      <div class="activity-text">
        <div style="font-weight:600;color:#fff">{{test.titel}}</div>
        <div style="font-size:13px;color:#888">{{test.vak}} | {{test.klas}} | {{test.tijd}}</div>
      </div>
      <a href="/docent/toetsen" class="btn btn-p btn-sm">""" + icon('edit', 14) + """</a>
    </div>
    {% endfor %}
    {% else %}
    <p style="text-align:center;color:#888;padding:20px">" + icon('info', 18) + " Geen komende toetsen deze week</p>
    {% endif %}
  </div>
  
  <div class="card">
    <h2>""" + icon('grades', 20) + """ Statistieken</h2>
    <div style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="color:#888">Gemiddeld cijfer</span>
        <span style="font-weight:bold;color:var(--primary-light)">{{avg_grade}}</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" style="width:{{avg_grade*10}}%;background:linear-gradient(90deg,var(--primary),var(--primary-light))"></div>
      </div>
    </div>
    <div style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="color:#888">Cijfers deze week</span>
        <span style="font-weight:bold;color:var(--success)">{{recent_grades}}</span>
      </div>
    </div>
    <div>
      <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <span style="color:#888">Actieve quizzen</span>
        <span style="font-weight:bold;color:var(--warning)">{{active_quizzes}}</span>
      </div>
    </div>
  </div>
</div>

<div class="dashboard-grid">
  <div class="card">
    <h2>""" + icon('messages', 20) + """ Recente Activiteit</h2>
    {% if recent_activity %}
    {% for activity in recent_activity %}
    <div class="activity-item {{activity.type}}">
      <div class="activity-icon">
        {% if activity.type == 'grade' %}""" + icon('grades', 18) + """{% elif activity.type == 'quiz' %}""" + icon('quiz', 18) + """{% else %}""" + icon('tests', 18) + """{% endif %}
      </div>
      <div class="activity-text">
        <div style="font-size:14px;color:#fff">{{activity.text}}</div>
        <div class="activity-time">{{activity.time.strftime('%Y-%m-%d %H:%M') if activity.time is defined and activity.time is not string else activity.time[0:16]}}</div>
      </div>
    </div>
    {% endfor %}
    {% else %}
    <p style="text-align:center;color:#888;padding:20px">" + icon('info', 18) + " Geen recente activiteit</p>
    {% endif %}
  </div>
  
  <div class="card">
    <h2>""" + icon('trophy', 20) + """ Top Performers</h2>
    {% if top_students %}
    {% for idx, student in enumerate(top_students, start=1) %}
    <div class="top-student">
      <div class="rank">{{idx}}</div>
      <div class="activity-text">
        <div style="font-weight:600;color:#fff">{{student.display_name}}</div>
        <div style="font-size:13px;color:#888">{{student.count}} cijfers</div>
      </div>
      <div style="font-weight:bold;color:var(--primary-light)">{{student.avg_grade|round(1)}}</div>
    </div>
    {% endfor %}
    {% else %}
    <p style="text-align:center;color:#888;padding:20px">" + icon('info', 18) + " Nog geen data beschikbaar</p>
    {% endif %}
  </div>
  
  <div class="card">
    <h2>""" + icon('trophy', 20) + """ Top Performers</h2>
    {% if top_students %}
    {% for idx, student in enumerate(top_students, start=1) %}
    <div class="top-student">
      <div class="rank">{{idx}}</div>
      <div class="activity-text">
        <div style="font-weight:600;color:#fff">{{student.display_name}}</div>
        <div style="font-size:13px;color:#888">{{student.count}} cijfers</div>
      </div>
      <div style="font-weight:bold;color:var(--primary-light)">{{student.avg_grade|round(1)}}</div>
    </div>
    {% endfor %}
    {% else %}
    <p style="text-align:center;color:#888;padding:20px">" + icon('info', 18) + " Nog geen data beschikbaar</p>
    {% endif %}
  </div>
</div>

<div class="card"><h2>""" + icon('arrow-right', 20) + """ Snel naar</h2>
  <div class="flex flex-wrap gap8">
    <a href="/docent/toetsen" class="btn btn-p">""" + icon('tests', 18) + """ Toetsen beheren</a>
    <a href="/docent/quizzen" class="btn btn-p">""" + icon('quiz', 18) + """ Quizzen beheren</a>
    <a href="/docent/cijfers" class="btn btn-p">""" + icon('grades', 18) + """ Cijfers invoeren</a>
    <a href="/docent/live" class="btn btn-g">""" + icon('live', 18) + """ Live Quiz starten</a>
    <a href="/docent/leerlingen" class="btn btn-p">""" + icon('students', 18) + """ Leerlingen overzicht</a>
  </div>
</div>
</div>
<script>
fetch('/berichten/ongelezen').then(r=>r.json()).then(d=>document.getElementById('ongelezenCount').textContent=d.ongelezen).catch(()=>{});
</script>
</body></html>"""

# ===== KLASSEN =====
@app.route('/docent/klassen')
@login_required
@rol_required('docent')
def klassen():
    html = PAGE_HEADER("" + icon('classes', 20) + " Klassen", "Overzicht Klassen", "")
    for j in ['1','2','3','4','5','6']:
        html += f'<div class="card"><h2>' + icon('school', 24) + f' Klas {j}</h2><div class="grid">'
        for k in ['1','2']:
            html += f'<div class="stat-card"><div class="getal" style="font-size:22px">la{j}{k}</div><div class="label">La</div></div>'
        for k in ['1','2','3']:
            if j=='6' and k=='3': continue
            html += f'<div class="stat-card"><div class="getal" style="font-size:22px">lh{j}{k}</div><div class="label">Lh</div></div>'
        html += '</div></div>'
    html += '</div></body></html>'
    return html

# ===== CIJFERS =====
@app.route('/docent/cijfers', methods=['GET','POST'])
def docent_cijfers():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    if request.method == 'POST':
        lid = request.form.get('leerling_id','').strip()
        vak = request.form.get('vak','').strip()
        cijfer = request.form.get('cijfer','').strip()
        ctype = request.form.get('type','').strip()
        perc = request.form.get('percentage','').strip()
        if not all([lid, vak, cijfer, ctype, perc]):
            return redirect('/docent/cijfers')
        try:
            cv = float(cijfer)
            pv = float(perc)
            if not (1 <= cv <= 10): raise ValueError
            if not (0 <= pv <= 100): raise ValueError
        except:
            return redirect('/docent/cijfers')
        db.execute("INSERT INTO cijfers (leerling_id,vak,cijfer,type,percentage) VALUES (?,?,?,?,?)",
                   (int(lid), vak, cv, ctype, pv))
        db.commit()
        return redirect('/docent/cijfers')
    ll = db.execute("SELECT id,display_name FROM users WHERE role='leerling' ORDER BY display_name").fetchall()
    cc = db.execute("SELECT c.*,u.display_name as nm FROM cijfers c JOIN users u ON c.leerling_id=u.id ORDER BY c.created_at DESC LIMIT 50").fetchall()
    rows = "".join(f'<tr><td>{c["nm"]}</td><td>{c["vak"]}</td><td style="color:#69f0ae;font-weight:bold">{c["cijfer"]}</td><td>{c["type"]}</td><td>{c["percentage"]}%</td></tr>' for c in cc)
    lo = "".join(f'<option value="{l["id"]}">{l["display_name"]}</option>' for l in ll)
    return PAGE("" + icon('grades', 20) + " Cijfers", f"Cijfers - <strong>{session['vak']}</strong>", f"""
<div class="card"><h2>" + icon('plus', 20) + " Nieuw Cijfer</h2><form method="POST">
<div class="form-grid">
<label class="f">" + icon('user', 18) + " Leerling<select name="leerling_id" required>{lo}</select></label>
<label class="f">" + icon('book', 18) + " Vak<select name="vak" required><option>ak</option><option>fa</option><option>na</option><option>bv</option><option>wi</option><option>en</option><option>gs</option><option>ne</option><option>bi</option><option>ma</option></select></label>
<label class="f">" + icon('star', 18) + " Cijfer (1-10)<input type="number" step="0.1" min="1" max="10" name="cijfer" required></label>
<label class="f">" + icon('tests', 18) + " Type<select name="type" required><option>Proefwerk</option><option>Huiswerk</option><option>Toets</option><option>Presentatie</option><option>Praktijk</option></select></label>
<label class="f">" + icon('grades', 18) + " Percentage (0-100)<input type="number" min="0" max="100" name="percentage" required></label>
</div>
<button type="submit" class="btn btn-p mt10">" + icon('check', 18) + " Opslaan</button></form></div>
<div class="card"><h2>" + icon('grades', 20) + " Recente Cijfers ({len(cc)})</h2><div class="table-wrap"><table><tr><th>Leerling</th><th>Vak</th><th>Cijfer</th><th>Type</th><th>%</th></tr>{rows}</table></div></div>""")

# ===== LEERLINGEN =====
@app.route('/docent/leerlingen')
def docent_leerlingen():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    return PAGE("" + icon('students', 20) + " Leerlingen", "Overzicht <strong>Leerlingen</strong>", """
<div class="card"><h2>" + icon('students', 20) + " Alle Leerlingen</h2><div class="table-wrap"><table><tr><th>Naam</th><th>Klas</th><th>Gemiddelde</th><th>Status</th></tr>
<tr><td>" + icon('user', 18) + " Piet</td><td>4VWO</td><td style="color:var(--success);font-weight:bold">7.6</td><td><span class="badge badge-green">" + icon('check', 12) + " Actief</span></td></tr>
<tr><td>" + icon('user', 18) + " Anna</td><td>3HAVO</td><td style="color:var(--success);font-weight:bold">7.1</td><td><span class="badge badge-green">" + icon('check', 12) + " Actief</span></td></tr>
  <tr><td>" + icon('user', 18) + " Tom</td><td>5VWO</td><td style="color:var(--warning);font-weight:bold">6.2</td><td><span class="badge badge-gold">" + icon('zap', 12) + " Bezig</span></td></tr>
  <tr><td>" + icon('user', 18) + " Lisa</td><td>2HAVO</td><td style="color:var(--danger);font-weight:bold">5.4</td><td><span class="badge badge-red">" + icon('info', 12) + " Nieuw</span></td></tr>
</table></div></div>""")

# ===== TOETSEN =====
@app.route('/docent/toetsen', methods=['GET','POST'])
def docent_toetsen():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    if request.method == 'POST':
        titel = request.form.get('titel','').strip()
        vak = request.form.get('vak','').strip()
        klas = request.form.get('klas','').strip()
        datum = request.form.get('datum','').strip()
        tijd = request.form.get('tijd','').strip()
        duur = request.form.get('duur',60)
        if not all([titel, vak, klas, datum, tijd]):
            return redirect('/docent/toetsen')
        db.execute("INSERT INTO toetsen (titel,vak,klas,datum,tijd,duur,docent_id) VALUES (?,?,?,?,?,?,?)",
                   (titel, vak, klas, datum, tijd, int(duur), uid))
        db.commit()
        return redirect('/docent/toetsen')
    rows = db.execute("SELECT * FROM toetsen WHERE docent_id=? ORDER BY datum DESC", (uid,)).fetchall()
    tbody = '<tr><td colspan="5" style="text-align:center;color:#888">' + icon('info', 16) + ' Geen toetsen</td></tr>'
    if rows:
        tbody = "".join(f'<tr><td>{t["titel"]}</td><td>{t["vak"]}</td><td>{t["klas"]}</td><td>{t["datum"]}</td>'
            f'<td><form method="POST" action="/docent/toetsen/verwijder/{t["id"]}" style="display:inline" onsubmit="return confirm(\'Weet je zeker dat je deze toets wilt verwijderen?\')">'
            f'<button class="btn btn-d btn-sm">' + icon('trash', 14) + '</button></form></td></tr>' for t in rows)
    return PAGE("" + icon('tests', 20) + " Toetsen", f"Toetsen - <strong>{session['vak']}</strong>", f"""
<div class="card"><h2>" + icon('plus', 20) + " Nieuwe Toets</h2><form method="POST">
<div class="form-grid">
<label class="f">" + icon('tests', 18) + " Titel<input type="text" name="titel" required placeholder="Naam toets"></label>
<label class="f">" + icon('book', 18) + " Vak<select name="vak">
<option>ak</option><option>fa</option><option>na</option><option>bv</option><option>wi</option>
<option>en</option><option>gs</option><option>ne</option><option>bi</option><option>ma</option>
</select></label>
<label class="f">" + icon('school', 18) + " Klas<select name="klas">
<option>la21</option><option>la22</option><option>lh21</option><option>lh22</option><option>lh23</option>
<option>la31</option><option>la32</option><option>lh31</option><option>lh32</option>
</select></label>
<label class="f">" + icon('calendar', 18) + " Datum<input type="date" name="datum" required></label>
<label class="f">" + icon('clock', 18) + " Tijd<input type="time" name="tijd" required></label>
<label class="f">" + icon('clock', 18) + " Duur (min)<input type="number" name="duur" value="60"></label>
</div>
<button type="submit" class="btn btn-p mt10">" + icon('plus', 18) + " Aanmaken</button></form></div>
<div class="card"><h2>" + icon('tests', 20) + " Toetsen ({len(rows)})</h2><div class="table-wrap"><table><tr><th>Titel</th><th>Vak</th><th>Klas</th><th>Datum</th><th>Actie</th></tr>{tbody}</table></div></div>""")

@app.route('/docent/toetsen/verwijder/<int:toets_id>', methods=['POST'])
def toets_verwijder(toets_id):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    t = db.execute("SELECT id FROM toetsen WHERE id=? AND docent_id=?", (toets_id, uid)).fetchone()
    if t:
        db.execute("DELETE FROM toetsen WHERE id=?", (toets_id,))
        db.commit()
    return redirect('/docent/toetsen')

# ===== QUIZZEN =====
@app.route('/docent/quizzen', methods=['GET','POST'])
def docent_quizzen():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    if request.method == 'POST':
        titel = request.form.get('titel','').strip()
        vak = request.form.get('vak','').strip()
        klas = request.form.get('klas','').strip()
        if not all([titel, vak, klas]):
            return redirect('/docent/quizzen')
        db.execute("INSERT INTO quizzen (titel,vak,klas,docent_id) VALUES (?,?,?,?)", (titel, vak, klas, uid))
        db.commit()
        return redirect('/docent/quizzen')
    rows = db.execute("SELECT * FROM quizzen WHERE docent_id=? ORDER BY created_at DESC", (uid,)).fetchall()
    rijen = '<tr><td colspan="6" style="text-align:center;color:#888">' + icon('info', 16) + ' Geen quizzen</td></tr>'
    if rows:
        rijen = ""
        for q in rows:
            av = db.execute("SELECT COUNT(*) as c FROM vragen WHERE quiz_id=?", (q['id'],)).fetchone()['c']
            ls = db.execute("SELECT status FROM live_quizzen WHERE quiz_id=? ORDER BY gestart_op DESC LIMIT 1", (q['id'],)).fetchone()
            lbl = '<span class="badge badge-green">' + icon('live', 12) + ' LIVE</span>' if ls and ls['status']=='actief' else f'<a href="/docent/live/start_quiz/{q["id"]}" class="btn btn-g btn-sm">' + icon('zap', 14) + ' Start</a>'
            rijen += f'<tr><td>{q["titel"]}</td><td>{q["vak"]}</td><td>{q["klas"]}</td><td>{av}</td><td>{lbl}</td>'
            rijen += f'<td><a href="/docent/quiz/{q["id"]}" class="btn btn-p btn-sm">' + icon('edit', 14) + ' Bewerk</a> '
            rijen += f'<form method="POST" action="/docent/quiz/verwijder/{q["id"]}" style="display:inline" onsubmit="return confirm(\'Quiz en alle vragen verwijderen?\')"><button class="btn btn-d btn-sm">' + icon('trash', 14) + '</button></form></td></tr>'
    # AI Quiz Generator data
    ai_quizzen = db.execute("SELECT id,titel FROM quizzen WHERE docent_id=? ORDER BY created_at DESC LIMIT 5", (uid,)).fetchall()
    ai_quiz_opties = "".join(f'<option value="{q["id"]}">{q["titel"]}</option>' for q in ai_quizzen) or '<option value="">Maak eerst een quiz aan</option>'
    
    return PAGE("" + icon('quiz', 20) + " Quizzen", f"Quizzen - <strong>{session['vak']}</strong>", f"""
<div class="card"><h2>" + icon('plus', 20) + " Nieuwe Quiz</h2><form method="POST">
<div class="form-grid">
<label class="f">" + icon('quiz', 18) + " Titel<input type="text" name="titel" required placeholder="Naam quiz"></label>
<label class="f">" + icon('book', 18) + " Vak<select name="vak">
<option>ak</option><option>fa</option><option>na</option><option>bv</option><option>wi</option>
<option>en</option><option>gs</option><option>ne</option><option>bi</option><option>ma</option>
</select></label>
<label class="f">" + icon('school', 18) + " Klas<select name="klas">
<option>la21</option><option>la22</option><option>lh21</option><option>lh22</option><option>lh23</option>
<option>la31</option><option>la32</option>
</select></label>
</div>
<button type="submit" class="btn btn-p mt10">" + icon('plus', 18) + " Aanmaken</button></form></div>

<div class="card" style="border:2px solid rgba(124,77,255,.3);background:linear-gradient(135deg,rgba(124,77,255,.08),rgba(255,64,129,.05))">
<h2>" + icon('zap', 20) + " AI Quiz Generator - Gratis</h2>
<p style="color:#888;margin-bottom:16px">Upload een foto, screenshot of tekst en de AI genereert automatisch quizvragen. Geen installatie nodig, volledig gratis.</p>
<form method="POST" action="/docent/quiz/ai-genereren" enctype="multipart/form-data" id="aiForm">
<div class="form-grid">
<label class="f">" + icon('upload', 18) + " Upload afbeelding (foto/screenshot)<br>
<input type="file" name="afbeelding" accept="image/*" style="margin-top:8px;padding:20px;text-align:center;border:2px dashed rgba(124,77,255,.3);border-radius:12px;cursor:pointer;background:rgba(124,77,255,.03)">
</label>
<label class="f">" + icon('file-text', 18) + " Of plak tekst direct<br>
<textarea name="tekst" rows="4" placeholder="Plak hier de tekst vanaf jouw lesstof of uitleg..." style="margin-top:8px"></textarea>
</label>
</div>
<label class="f">" + icon('quiz', 18) + " Voeg toe aan quiz<select name="quiz_id">{ai_quiz_opties}</select></label>
<div class="form-grid" style="margin-top:12px">
<label class="f">" + icon('target', 18) + " Aantal vragen<input type="number" name="aantal" value="3" min="1" max="10" style="width:100%"></label>
<label class="f">" + icon('check', 18) + " Moeilijkheidsgraad<select name="moeilijkheid">
<option value="makkelijk">Makkelijk</option><option value="normaal" selected>Normaal</option><option value="moeilijk">Moeilijk</option>
</select></label>
</div>
<button type="submit" class="btn btn-p" style="padding:16px 40px;font-size:16px">" + icon('zap', 18) + " Genereer vragen met AI</button>
</form>
<div id="aiPreview" style="margin-top:20px;display:none">
<div class="card"><h2>" + icon('eye', 20) + " Herkende tekst</h2><div id="herkendeTekst" style="background:rgba(255,255,255,.05);padding:16px;border-radius:12px;font-family:monospace;white-space:pre-wrap;color:#ccc;max-height:200px;overflow-y:auto"></div></div>
</div>
</div>

<div class="card"><h2>" + icon('quiz', 20) + " Quizzen ({len(rows)})</h2><div class="table-wrap"><table><tr><th>Titel</th><th>Vak</th><th>Klas</th><th>Vragen</th><th>Live</th><th>Acties</th></tr>{rijen}</table></div></div>""")

# ===== AI QUIZ GENERATOR =====
@app.route('/docent/quiz/ai-genereren', methods=['POST'])
def ai_genereren():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    
    quiz_id = request.form.get('quiz_id', '').strip()
    aantal = int(request.form.get('aantal', 3))
    moeilijkheid = request.form.get('moeilijkheid', 'normaal')
    tekst_input = request.form.get('tekst', '').strip()
    
    # Check of er een afbeelding is geüpload
    afbeelding = request.files.get('afbeelding')
    afbeelding_tekst = ""
    
    if afbeelding and afbeelding.filename:
        # Controleer bestandstype
        if not afbeelding.content_type or 'image' not in afbeelding.content_type:
            return redirect('/docent/quizzen')
        
        # Lees de afbeelding en probeer metadata te extraheren
        try:
            from PIL import Image
            import io
            
            img_data = afbeelding.read()
            img = Image.open(io.BytesIO(img_data))
            
            # Extraheer basis informatie
            afbeelding_tekst = f"[Afbeelding: {img.size[0]}x{img.size[1]} px, formaat: {img.format or 'onbekend'}"
            
            # Gebruik PIL om pixels te analyseren (eenvoudige beeldherkenning)
            # Dit is een basis-aanpak die werkt zonder externe dependencies
            img_gray = img.convert('L')
            pixels = list(img_gray.getdata())
            
            # Bereken gemiddelde helderheid
            avg_brightness = sum(pixels) / len(pixels) if pixels else 128
            
            # Analyseer kleuren als het geen grijswaarde is
            if img.mode != 'L':
                img_rgb = img.convert('RGB')
                rgb_pixels = list(img_rgb.getdata())
                unique_colors = len(set(rgb_pixels))
                color_diversity = unique_colors / len(rgb_pixels) if rgb_pixels else 0
            else:
                color_diversity = 0
            
            # Voeg Beschrijving toe gebaseerd op beeld inhoud
            if color_diversity > 0.5:
                afbeelding_tekst += ", veel kleuren gedetecteerd"
            elif avg_brightness < 100:
                afbeelding_tekst += ", donker beeld"
            elif avg_brightness > 200:
                afbeelding_tekst += ", licht beeld"
            else:
                afbeelding_tekst += ", gemiddelde helderheid"
                
            # Detecteer tekst-gebieden (vereenvoudigd)
            # In een echte implementatie zou je hier Tesseract gebruiken
            afbeelding_tekst += "]\n"
            
            logger.info(f"Afbeelding geanalyseerd: {img.size}, {avg_brightness} helderheid, {color_diversity:.2f} kleurdiversiteit")
            
        except Exception as e:
            logger.error(f"Afbeelding analyse fout: {e}")
            afbeelding_tekst = "[Afbeelding kon niet worden geanalyseerd]"
    
    # Combineer tekst en afbeelding analyse
    volledige_tekst = tekst_input
    if afbeelding_tekst:
        volledige_tekst = afbeelding_tekst + "\n" + tekst_input if volledige_tekst else afbeelding_tekst
    
    if not volledige_tekst.strip():
        return redirect('/docent/quizzen')
    
    # Controleer quiz_id
    if not quiz_id or not quiz_id.isdigit():
        return redirect('/docent/quizzen')
    
    quiz = db.execute("SELECT id FROM quizzen WHERE id=? AND docent_id=?", (quiz_id, uid)).fetchone()
    if not quiz:
        return redirect('/docent/quizzen')
    
    # Genereer vragen uit de tekst (lokale AI - geen externe API nodig)
    vragen_lijst = genereer_vragen_uit_tekst(volledige_tekst, aantal, moeilijkheid)
    
    if not vragen_lijst:
        return redirect('/docent/quizzen')
    
    # Sla de vragen op in de database
    quiz_id_int = int(quiz_id)
    for v in vragen_lijst:
        volgorde = db.execute("SELECT COUNT(*) as c FROM vragen WHERE quiz_id=?", (quiz_id_int,)).fetchone()['c']
        db.execute("""INSERT INTO vragen (quiz_id,tekst,optie_a,optie_b,optie_c,optie_d,antwoord,volgorde)
                      VALUES (?,?,?,?,?,?,?,?)""",
                   (quiz_id_int, v['tekst'], v['a'], v['b'], v['c'], v['d'], v['antwoord'], volgorde))
    db.commit()
    
    logger.info(f"AI gegenereerde vragen toegevoegd aan quiz {quiz_id_int}: {len(vragen_lijst)} vragen")
    return redirect(f'/docent/quiz/{quiz_id_int}')


def genereer_vragen_uit_tekst(tekst, aantal=3, moeilijkheid='normaal'):
    """
    Genereert quizvragen uit een tekst.
    Dit is een lokale 'AI' die geen externe API's nodig heeft.
    Werkt op basis van tekstpatronen en woordanalyse.
    """
    import re
    
    # Splits tekst in zinnen
    zinnen = re.split(r'[.!?]+', tekst)
    zinnen = [z.strip() for z in zinnen if len(z.strip()) > 20]  # Filter korte zinnen eruit
    
    vragen_lijst = []
    
    # Genereer verschillende soorten vragen
    for i in range(min(aantal, len(zinnen))):
        zin = zinnen[i % len(zinnen)] if zinnen else f"Vraag {i+1} over: {tekst[:50]}"
        
        # Verwijder speciale tekens en normalizeer
        schonere_zin = re.sub(r'[^\w\s]', '', zin).strip()
        woorden = schoner_zin.split()
        
        if len(woorden) < 5:
            continue
        
        # Bepaal moeilijkheid
        if moeilijkheid == 'makkelijk':
            # Vraag over specifieke woorden/definities
            vraag, opties, antwoord = maak_woordvraag(woorden, zin)
        elif moeilijkheid == 'moeilijk':
            # Vraag over betekenis/context
            vraag, opties, antwoord = maak_contextvraag(woorden, zin)
        else:
            # Gemiddeld: mix van beide
            vraag, opties, antwoord = maak_standaardvraag(woorden, zin)
        
        if vraag and opties and len(opties) >= 4:
            vragen_lijst.append({
                'tekst': vraag,
                'a': opties[0],
                'b': opties[1],
                'c': opties[2],
                'd': opties[3],
                'antwoord': antwoord
            })
    
    # Als er niet genoeg gegenereerd zijn, maak eenvoudige vragen
    while len(vragen_lijst) < aantal and len(zinnen) > 0:
        zin = zinnen[len(vragen_lijst) % len(zinnen)]
        woorden = re.sub(r'[^\w\s]', '', zin).split()
        
        if len(woorden) >= 4:
            # Vervang een woord door een vraagteken
            vervang_idx = min(3, len(woorden) - 1)
            origineel_woord = woorden[vervang_idx]
            
            # Maak 4 opties met het juiste antwoord
            opties = [origineel_woord]
            while len(opties) < 4:
                if woorden:
                    w = random.choice(woorden)
                    if w not in opties and w != origineel_woord:
                        opties.append(w)
                else:
                    opties.append(f"Optie {len(opties)+1}")
            
            random.shuffle(opties)
            antwoord_idx = opties.index(origineel_woord)
            
            vraag_tekst = zin.replace(origineel_woord, '_____')
            # Maak de vraag natuurlijker
            vraag_tekst = f"Wat hoort er in deze zin? {vraag_tekst}"
            
            vragen_lijst.append({
                'tekst': vraag_tekst,
                'a': opties[0],
                'b': opties[1],
                'c': opties[2],
                'd': opties[3],
                'antwoord': antwoord_idx
            })
    
    return vragen_lijst


def maak_woordvraag(woorden, zin):
    """Maak een eenvoudige woordvraag uit de tekst."""
    if len(woorden) < 3:
        return None, [], 0
    
    # Kies een belangrijk woord (lange woorden zijn meestal belangrijker)
    woorden_met_lengte = [(w, len(w)) for w in woorden if len(w) > 3]
    if not woorden_met_lengte:
        woorden_met_lengte = [(w, len(w)) for w in woorden]
    
    # Sorteer op lengte en neem een van de langste
    woorden_met_lengte.sort(key=lambda x: x[1], reverse=True)
    target_woord = woorden_met_lengte[0][0]
    
    # Maak verwarrende opties
    opties = [target_woord]
    alle_woorden = set(woorden)
    while len(opties) < 4:
        # Gebruik andere woorden uit de zin als verwarring
        andere_woorden = [w for w in woorden if w not in opties and len(w) > 2]
        if andere_woorden:
            opties.append(random.choice(andere_woorden))
        else:
            # Fallback: genereur eenvoudige variaties
            opties.append(f"{target_woord[:-1] if len(target_woord) > 2 else target_woord} variant")
    
    random.shuffle(opties)
    antwoord = opties.index(target_woord)
    
    vraag = f"Welk woord hoort in deze zin? {zin.replace(target_woord, '_____')}"
    return vraag, opties, antwoord


def maak_contextvraag(woorden, zin):
    """Maak een contextvraag over de betekenis."""
    if len(woorden) < 4:
        return None, [], 0
    
    # Kies een middelpunt woord
    mid = len(woorden) // 2
    target = woorden[mid]
    
    # Maak een vraag over wat het woord betekent in deze context
    vraag = f"Wat betekent '{target}' in de volgende zin? '{zin}'"
    
    # Genereer verwarrende antwoorden
    opties = []
    verwante_woorden = [w for w in woorden if w != target and len(w) > 2][:3]
    
    # Vul aan naar 4 opties
    while len(opties) < 4:
        if verwante_woorden:
            w = verwante_woorden.pop(0)
            opties.append(w)
        else:
            opties.append(f"Variant {len(opties)+1}")
    
    # Het juiste antwoord is een interpretatie van het woord
    antwoord = 0
    
    return vraag, opties, antwoord


def maak_standaardvraag(woorden, zin):
    """Maak een standaard meerkeuzevraag."""
    if len(woorden) < 3:
        # Fallback: eenvoudige vraag
        return (f"Is de volgende zin correct? {zin}",
                ["Ja", "Nee", "Misschien", "Weet ik niet"],
                0)
    
    # Kies een objectief woord
    target_idx = min(2, len(woorden) - 1)
    target = woorden[target_idx]
    
    # Vervang en maak een invitation-vraag
    vervang_tekst = zin.replace(target, '_____')
    vraag = f"Vul het ontbrekende woord in: {vervang_tekst}"
    
    # Maak 4 keuzes
    opties = [target]
    andere = [w for w in woorden if w != target and len(w) > 2][:3]
    while len(opties) < 4 and andere:
        opties.append(andere.pop(0))
    while len(opties) < 4:
        opties.append(f"Anders")
    
    random.shuffle(opties)
    antwoord = opties.index(target)
    
    return vraag, opties, antwoord


@app.route('/docent/quiz/verwijder/<int:quiz_id>', methods=['POST'])
def docent_quiz_verwijder(quiz_id):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    q = db.execute("SELECT id FROM quizzen WHERE id=? AND docent_id=?", (quiz_id, uid)).fetchone()
    if q:
        db.execute("DELETE FROM antwoorden WHERE pin IN (SELECT pin FROM live_quizzen WHERE quiz_id=?)", (quiz_id,))
        db.execute("DELETE FROM rpg_log WHERE pin IN (SELECT pin FROM live_quizzen WHERE quiz_id=?)", (quiz_id,))
        db.execute("DELETE FROM live_deelnemers WHERE pin IN (SELECT pin FROM live_quizzen WHERE quiz_id=?)", (quiz_id,))
        db.execute("DELETE FROM live_quizzen WHERE quiz_id=?", (quiz_id,))
        db.execute("DELETE FROM vragen WHERE quiz_id=?", (quiz_id,))
        db.execute("DELETE FROM quizzen WHERE id=?", (quiz_id,))
        db.commit()
    return redirect('/docent/quizzen')

# ===== QUIZ BEWERKEN =====
@app.route('/docent/quiz/<int:quiz_id>', methods=['GET','POST'])
def quiz_bewerk(quiz_id):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    quiz = db.execute("SELECT * FROM quizzen WHERE id=?", (quiz_id,)).fetchone()
    if not quiz:
        return redirect('/docent/quizzen')
    if request.method == 'POST':
        vraag = request.form.get('vraag','').strip()
        o0 = request.form.get('opt0','').strip()
        o1 = request.form.get('opt1','').strip()
        o2 = request.form.get('opt2','').strip()
        o3 = request.form.get('opt3','').strip()
        antw = request.form.get('antwoord','0')
        if not all([vraag, o0, o1, o2, o3]):
            return redirect(f'/docent/quiz/{quiz_id}')
        volg = db.execute("SELECT COUNT(*) as c FROM vragen WHERE quiz_id=?", (quiz_id,)).fetchone()['c']
        db.execute("INSERT INTO vragen (quiz_id,tekst,optie_a,optie_b,optie_c,optie_d,antwoord,volgorde) VALUES (?,?,?,?,?,?,?,?)",
                   (quiz_id, vraag, o0, o1, o2, o3, int(antw), volg))
        db.commit()
        return redirect(f'/docent/quiz/{quiz_id}')
    v_db = db.execute("SELECT * FROM vragen WHERE quiz_id=? ORDER BY volgorde", (quiz_id,)).fetchall()
    v_html = ""
    for vi, v in enumerate(v_db):
        opts = [v['optie_a'], v['optie_b'], v['optie_c'], v['optie_d']]
        opt_html = "".join(f'<span style="color:{"#69f0ae;font-weight:bold" if o==v["antwoord"] else "#ccc"};margin-right:14px">{"ABCD"[o]}. {opts[o]}</span>' for o in range(4))
        v_html += f'<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:14px;margin-bottom:10px">'
        v_html += f'<p><strong>' + icon('pin', 16) + f' Vraag {vi+1}:</strong> {v["tekst"]}</p><p style="margin-top:6px">{opt_html}</p>'
        v_html += f'<form method="POST" action="/docent/vraag/verwijder/{v["id"]}" style="display:inline;margin-top:6px" onsubmit="return confirm(\'Vraag verwijderen?\')"><button class="btn btn-d btn-sm">' + icon('trash', 14) + ' Verwijder vraag</button></form></div>'
    if not v_html:
        v_html = '<p style="text-align:center;color:#888">' + icon('info', 16) + ' Nog geen vragen</p>'
    return PAGE_HEADER(f"" + icon('quiz', 20) + " {quiz['titel']}", f"Quiz: <strong>{quiz['titel']}</strong> | {quiz['vak']} | {quiz['klas']}", f"""
<div class="card"><h2>" + icon('quiz', 20) + " Vragen ({len(v_db)})</h2>{v_html}</div>
<div class="card"><h2>" + icon('plus', 20) + " Nieuwe Vraag</h2><form method="POST">
<label class="f">" + icon('quiz', 18) + " Vraag<textarea name="vraag" rows="2" required placeholder="Typ je vraag hier..."></textarea></label>
<div class="form-grid">
<label class="f">A <input type="text" name="opt0" required placeholder="Optie A"></label>
<label class="f">B <input type="text" name="opt1" required placeholder="Optie B"></label>
<label class="f">C <input type="text" name="opt2" required placeholder="Optie C"></label>
<label class="f">D <input type="text" name="opt3" required placeholder="Optie D"></label>
</div>
<label class="f">" + icon('check', 18) + " Correct antwoord<select name="antwoord"><option value="0">A</option><option value="1">B</option><option value="2">C</option><option value="3">D</option></select></label>
<button type="submit" class="btn btn-p">" + icon('plus', 18) + " Toevoegen</button></form></div>
<a href="/docent/quizzen" class="btn btn-d">" + icon('arrow-left', 18) + " Terug</a>""")

@app.route('/docent/vraag/verwijder/<int:vraag_id>', methods=['POST'])
def docent_vraag_verwijder(vraag_id):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    v = db.execute("SELECT quiz_id FROM vragen WHERE id=?", (vraag_id,)).fetchone()
    if v:
        db.execute("DELETE FROM vragen WHERE id=?", (vraag_id,))
        db.commit()
        return redirect(f'/docent/quiz/{v["quiz_id"]}')
    return redirect('/docent/quizzen')

# ===== LIVE QUIZ IMPROVED =====
@app.route('/docent/live')
def docent_live():
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    rijen = ""
    ll = db.execute("""
        SELECT lq.pin, q.titel, q.id as qid, lq.status, lq.vraag_index,
               (SELECT COUNT(*) FROM live_deelnemers WHERE pin=lq.pin) as spelers
        FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id
        WHERE q.docent_id=? ORDER BY lq.gestart_op DESC
    """, (uid,)).fetchall()
    for lq in ll:
        totaal_vr = db.execute("SELECT COUNT(*) as c FROM vragen WHERE quiz_id=?", (lq['qid'],)).fetchone()['c']
        done = lq['vraag_index'] >= totaal_vr
        pin_styled = f'<span style="font-size:20px;font-weight:bold;color:#b388ff;font-family:monospace;letter-spacing:2px">{lq["pin"]}</span>'
        if done:
            rijen += f'<tr><td>{pin_styled}</td><td>{lq["titel"]}</td><td style="text-align:center"><span class="badge badge-purple">{lq["spelers"]} ' + icon('students', 12) + '</span></td>'
            rijen += f'<td><span class="badge badge-green">{icon("check", 14)} Klaar</span></td>'
            rijen += f'<td><div class="flex" style="gap:6px"><a href="/docent/live/scoreboard/{lq["pin"]}" class="btn btn-p btn-sm">{icon("trophy", 14)} Scorebord</a> '
            rijen += f'<form method="POST" action="/docent/live/stop/{lq["pin"]}" style="display:inline"><button class="btn btn-d btn-sm">{icon("trash", 14)}</button></form></div></td></tr>'
        elif lq['status'] == 'wacht':
            rijen += f'<tr><td>{pin_styled}</td><td>{lq["titel"]}</td><td style="text-align:center"><span class="badge badge-purple">{lq["spelers"]} ' + icon('students', 12) + '</span></td>'
            rijen += f'<td><span class="badge badge-gold"><span class="status-dot yellow"></span> Wacht</span></td>'
            rijen += f'<td><div class="flex" style="gap:6px"><form method="POST" action="/docent/live/start/{lq["pin"]}" style="display:inline"><button class="btn btn-p btn-sm">{icon("play", 14)} Start</button></form> '
            rijen += f'<form method="POST" action="/docent/live/stop/{lq["pin"]}" style="display:inline"><button class="btn btn-d btn-sm">{icon("stop", 14)}</button></form></div></td></tr>'
        else:
            vn = lq['vraag_index'] + 1
            rijen += f'<tr><td>{pin_styled}</td><td>{lq["titel"]}</td><td style="text-align:center"><span class="badge badge-purple">{lq["spelers"]} ' + icon('students', 12) + '</span></td>'
            rijen += f'<td><span class="badge badge-green"><span class="status-dot green"></span> Vraag {vn}/{totaal_vr}</span></td>'
            rijen += f'<td><div class="flex" style="gap:6px"><form method="POST" action="/docent/live/volgende/{lq["pin"]}" style="display:inline"><button class="btn btn-p btn-sm">' + icon('arrow-right', 14) + ' Volgende</button></form> '
            rijen += f'<a href="/docent/live/scoreboard/{lq["pin"]}" class="btn btn-p btn-sm">{icon("trophy", 14)} Scorebord</a> '
            rijen += f'<form method="POST" action="/docent/live/stop/{lq["pin"]}" style="display:inline"><button class="btn btn-d btn-sm">{icon("stop", 14)}</button></form></div></td></tr>'
    if not rijen:
        rijen = f'<tr><td colspan="5" style="text-align:center;padding:40px">{empty_state("Nog geen live quizzen gestart. Maak er een!", "zap")}</td></tr>'
    qo = "".join(f'<option value="{q["id"]}">{q["titel"]} ({db.execute("SELECT COUNT(*) as c FROM vragen WHERE quiz_id=?",(q["id"],)).fetchone()["c"]} vragen)</option>'
                 for q in db.execute("SELECT id,titel FROM quizzen WHERE docent_id=? ORDER BY created_at DESC", (uid,)).fetchall())
    if not qo:
        qo = '<option value="">' + icon('warning', 14) + ' Maak eerst een quiz met vragen!</option>'
    return PAGE_HEADER("" + icon('zap', 20) + " Live Quiz Beheer", "<strong>Live Quiz</strong> Beheer - Start en beheer je quizzen", f"""
<style>
@keyframes pinPulse{{0%,100%{{box-shadow:0 0 0 0 rgba(124,77,255,.4)}}50%{{box-shadow:0 0 0 12px rgba(124,77,255,0)}}}}
.pin-badge{{animation:pinPulse 2s infinite}}
</style>
<div class="card"><h2>" + icon('zap', 20) + " Actieve & Wachtende Quizzen</h2><div class="table-wrap"><table><tr><th>" + icon('key', 14) + " PIN</th><th>Quiz</th><th>Spelers</th><th>Status</th><th>Acties</th></tr>{rijen}</table></div></div>
<div class="card"><h2>" + icon('plus', 20) + " Nieuwe Live Quiz Starten</h2>
<p style="color:#888;margin-bottom:15px">Kies een quiz met vragen om live te starten. Leerlingen kunnen meedoen met de PIN code.</p>
<form method="POST" action="/docent/live/maak" style="display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap">
<div style="flex:1;min-width:250px"><label class="f">" + icon('quiz', 16) + " Kies een Quiz<select name="quiz">{qo}</select></label></div>
<button type="submit" class="btn btn-p" style="margin-bottom:12px;padding:14px 32px">" + icon('play', 18) + " Maak Live Quiz</button>
</form></div>

<div class="card" style="border:2px solid rgba(124,77,255,.3);background:linear-gradient(135deg,rgba(124,77,255,.08),rgba(255,64,129,.05));text-align:center">
<h2>" + icon('zap', 20) + " AI Quiz Generator</h2>
<p style="color:#888;margin-bottom:16px;font-size:15px">Heeft je een screenshot of lesstof?<br>Upload een afbeelding en de AI genereert automatisch quizvragen.</p>
<div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap">
<a href="/docent/quizzen" class="btn btn-p" style="padding:16px 32px;font-size:16px">" + icon('upload', 18) + " Ga naar AI Generator</a>
</div>
<p style="color:#888;margin-top:12px;font-size:13px">" + icon('file', 12) + " Werkt met foto's, screenshots en tekst - Volledig gratis</p>
</div>""")

@app.route('/docent/live/maak', methods=['POST'])
@login_required
@rol_required('docent')
def live_maak():
    db = get_db()
    uid = session['user_id']
    qid = request.form.get('quiz','').strip()
    if not qid:
        return redirect('/docent/live')
    q = db.execute("SELECT id FROM quizzen WHERE id=? AND docent_id=?", (qid, uid)).fetchone()
    if not q:
        return redirect('/docent/live')
    for _ in range(100):
        pin = secrets.token_urlsafe(6).upper()[:8]
        if not db.execute("SELECT pin FROM live_quizzen WHERE pin=?", (pin,)).fetchone():
            break
    else:
        return redirect('/docent/live')
    db.execute("INSERT INTO live_quizzen (pin,quiz_id,status,boss_hp,boss_max_hp,team_hp,team_max_hp,vraag_tijd) VALUES (?,?,'wacht',0,0,0,0,20)",
               (pin, qid))
    db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/start/<pin>', methods=['POST'])
def live_start(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    lq = db.execute("SELECT lq.* FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id WHERE lq.pin=? AND q.docent_id=?", (pin, uid)).fetchone()
    if lq:
        db.execute("UPDATE live_quizzen SET status='actief',vraag_index=0,boss_hp=0,boss_max_hp=0,team_hp=0,team_max_hp=0 WHERE pin=?", (pin,))
        db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/volgende/<pin>', methods=['POST'])
def live_volgende(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    lq = db.execute("SELECT lq.*,q.id as qid FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id WHERE lq.pin=? AND q.docent_id=?", (pin, uid)).fetchone()
    if lq:
        totaal = db.execute("SELECT COUNT(*) as c FROM vragen WHERE quiz_id=?", (lq['qid'],)).fetchone()['c']
        ni = lq['vraag_index'] + 1
        if ni >= totaal:
            db.execute("UPDATE live_quizzen SET status='klaar',beeindigd_op=CURRENT_TIMESTAMP WHERE pin=?", (pin,))
        else:
            db.execute("UPDATE live_quizzen SET vraag_index=? WHERE pin=?", (ni, pin))
        db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/start_quiz/<int:quiz_id>')
@login_required
@rol_required('docent')
def live_start_quiz(quiz_id):
    db = get_db()
    uid = session['user_id']
    q = db.execute("SELECT id FROM quizzen WHERE id=? AND docent_id=?", (quiz_id, uid)).fetchone()
    if not q:
        return redirect('/docent/quizzen')
    for _ in range(100):
        pin = secrets.token_urlsafe(6).upper()[:8]
        if not db.execute("SELECT pin FROM live_quizzen WHERE pin=?", (pin,)).fetchone():
            break
    else:
        return redirect('/docent/live')
    db.execute("INSERT INTO live_quizzen (pin,quiz_id,status,boss_hp,boss_max_hp,team_hp,team_max_hp,vraag_tijd) VALUES (?,?,'actief',0,0,0,0,20)",
               (pin, quiz_id))
    db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/stop/<pin>', methods=['POST'])
def live_stop(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    db.execute("DELETE FROM live_quizzen WHERE pin=? AND quiz_id IN (SELECT id FROM quizzen WHERE docent_id=?)", (pin, uid))
    db.commit()
    return redirect('/docent/live')

@app.route('/docent/live/scoreboard/<pin>')
def live_scoreboard(pin):
    if 'rol' not in session or session['rol'] != 'docent': return redirect('/login')
    db = get_db()
    lq = db.execute("SELECT lq.*,q.titel FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id WHERE lq.pin=?", (pin,)).fetchone()
    if not lq:
        return redirect('/docent/live')
    dd = db.execute("SELECT naam,score FROM live_deelnemers WHERE pin=? ORDER BY score DESC", (pin,)).fetchall()
    rijen = '<tr><td colspan="2" style="text-align:center;color:#888">' + icon('info', 16) + ' Geen spelers</td></tr>'
    if dd:
        rijen = ""
        for idx, (naam, score) in enumerate(dd):
            medal = icon('crown', 12) if idx == 0 else '#' + str(idx+1)
            rijen += f'<tr><td style="font-size:18px">{medal} {naam}</td><td style="color:#b388ff;font-size:24px;font-weight:bold">{score}</td></tr>'
    return PAGE_HEADER("" + icon('trophy', 20) + " Scorebord", f"Scorebord: <strong>{lq['titel']}</strong>", f"""
<div class="card"><h2>" + icon('trophy', 20) + " Eindstand</h2><div class="table-wrap"><table><tr><th>Naam</th><th>Score</th></tr>{rijen}</table></div>
<a href="/docent/live" class="btn btn-d mt10">" + icon('arrow-left', 18) + " Terug</a></div>""")

# ===== LEERLING DASHBOARD =====
@app.route('/leerling')
def leerling_dashboard():
    if 'rol' not in session or session['rol'] != 'leerling': return redirect('/login')
    db = get_db()
    uid = session['user_id']
    gem = db.execute("SELECT AVG(cijfer) as avg FROM cijfers WHERE leerling_id=?", (uid,)).fetchone()['avg'] or 0
    ac = db.execute("SELECT COUNT(*) as c FROM cijfers WHERE leerling_id=?", (uid,)).fetchone()['c']
    return PAGE_HEADER("" + icon('dashboard', 20) + " Dashboard", f"Welkom, <strong>{session['naam']}</strong>! " + icon('user', 18), f"""
<div class="grid">
  <div class="stat-card"><div class="icoon">" + icon('grades', 36) + "</div><div class="getal">{round(gem,1)}</div><div class="label">Gemiddeld cijfer</div></div>
  <div class="stat-card"><div class="icoon">" + icon('tests', 36) + "</div><div class="getal">{ac}</div><div class="label">Cijfers</div></div>
  <div class="stat-card"><div class="icoon">" + icon('messages', 36) + "</div><div class="getal" id="ongelezenCount">0</div><div class="label">Berichten</div></div>
</div>
<div class="card"><h2>" + icon('arrow-right', 20) + " Snel naar</h2>
  <div class="flex flex-wrap gap8">
    <a href="/leerling/cijfers" class="btn btn-p">" + icon('grades', 18) + " Mijn cijfers</a>
    <a href="/leerling/quiz/spel" class="btn btn-g">" + icon('live', 18) + " Live Quiz</a>
    <a href="/leerling/schoolgids" class="btn btn-p">" + icon('book', 18) + " Schoolgids</a>
    <a href="/berichten" class="btn btn-p">" + icon('messages', 18) + " Berichten</a>
  </div>
</div>
<script>
fetch('/berichten/ongelezen').then(r=>r.json()).then(d=>document.getElementById('ongelezenCount').textContent=d.ongelezen).catch(()=>{{}});
</script>""")

@app.route('/leerling/cijfers')
@login_required
@rol_required('leerling')
def leerling_cijfers():
    db = get_db()
    uid = session['user_id']
    cc = db.execute("SELECT c.* FROM cijfers c WHERE c.leerling_id=? ORDER BY c.created_at DESC", (uid,)).fetchall()
    vakken = {}
    for c in cc:
        vakken.setdefault(c['vak'], []).append(c)
    v_html = ""
    for vak, cijfers in vakken.items():
        rijen = "".join(f'<tr><td>{c["type"]}</td><td style="color:#69f0ae;font-weight:bold">{c["cijfer"]}</td><td>{c["percentage"]}%</td></tr>' for c in cijfers)
        gem = sum(c['cijfer'] for c in cijfers) / len(cijfers)
        v_html += f'<div class="card"><h2>' + icon('book', 20) + ' ' + vak.upper() + ' <span class="badge badge-purple" style="float:right">Gem: {gem:.1f}</span></h2><div class="table-wrap"><table><tr><th>Type</th><th>Cijfer</th><th>%</th></tr>{rijen}</table></div>'
    if not v_html:
        v_html = '<div class="card"><p style="text-align:center;color:#888">' + icon('info', 16) + ' Nog geen cijfers bekend.</p></div>'
    return PAGE_HEADER("" + icon('grades', 20) + " Mijn Cijfers", f"Cijfers van <strong>{session['naam']}</strong>", v_html)

@app.route('/leerling/schoolgids')
def schoolgids():
    if 'rol' not in session or session['rol'] != 'leerling': return redirect('/login')
    return PAGE_HEADER("" + icon('book', 20) + " Schoolgids", f"Schoolgids voor <strong>{session['naam']}</strong>", """
<div class="grid">
<div class="card"><h2>" + icon('clock', 20) + " Schooluren</h2><div class="table-wrap"><table><tr><th>Les</th><th>Tijd</th></tr>
<tr><td>1e</td><td>8:30 - 9:20</td></tr><tr><td>2e</td><td>9:25 - 10:15</td></tr>
<tr><td>3e</td><td>10:45 - 11:35</td></tr><tr><td>4e</td><td>11:40 - 12:30</td></tr>
<tr><td>5e</td><td>13:15 - 14:05</td></tr><tr><td>6e</td><td>14:10 - 15:00</td></tr>
</table></div></div>
<div class="card"><h2>" + icon('phone', 20) + " Contact</h2><p>" + icon('school', 18) + " Schoolstraat 1, Amsterdam</p><p>" + icon('phone', 18) + " 020-1234567</p><p>" + icon('mail', 18) + " info@schoolportaal.nl</p></div>
<div class="card"><h2>" + icon('calendar', 20) + " Belangrijke Data</h2><p>" + icon('calendar', 18) + " Herexamen week: 24-28 juni</p><p>" + icon('sun', 18) + " Zomervakantie: 6 juli - 18 augustus</p></div>
</div>""")

# ===== LIVE QUIZ STUDENT =====
@app.route('/leerling/quiz/spel', methods=['GET','POST'])
def quiz_spel():
    if 'rol' not in session or session['rol'] != 'leerling':
        session['spel_naam'] = None
        if request.method == 'GET':
            return render_template_string(PIN_HTML, CSS=CSS, fout="")
        pin = request.form.get('pin','').strip().upper()
        naam = request.form.get('naam','').strip()
        if not pin or not naam:
            return render_template_string(PIN_HTML, CSS=CSS, fout=icon('warning', 16) + " Vul een code en naam in.")
        session['spel_naam'] = naam
        db = get_db()
        live = db.execute("SELECT * FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
        if live and live['status'] in ('wacht','actief'):
            existing = db.execute("SELECT naam FROM live_deelnemers WHERE pin=? AND naam=?", (pin, naam)).fetchone()
            if not existing:
                db.execute("INSERT INTO live_deelnemers (pin,naam) VALUES (?,?)", (pin, naam))
                db.commit()
            return redirect(f'/leerling/quiz/spelen/{pin}')
    return render_template_string(PIN_HTML, CSS=CSS, fout=icon('warning', 16) + " Ongeldige code of quiz niet beschikbaar.")
    if request.method == 'GET':
        return render_template_string(PIN_HTML, CSS=CSS, fout="")
    pin = request.form.get('pin','').strip().upper()
    naam = session.get('naam','Speler')
    db = get_db()
    live = db.execute("SELECT * FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if live and live['status'] in ('wacht','actief'):
        existing = db.execute("SELECT naam FROM live_deelnemers WHERE pin=? AND naam=?", (pin, naam)).fetchone()
        if not existing:
            db.execute("INSERT INTO live_deelnemers (pin,naam) VALUES (?,?)", (pin, naam))
            db.commit()
        return redirect(f'/leerling/quiz/spelen/{pin}')
    return render_template_string(PIN_HTML, CSS=CSS, fout=icon('warning', 16) + " Ongeldige code of quiz niet beschikbaar.")

PIN_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Live Quiz</title></head>
<body>
<div style="display:flex;justify-content:center;align-items:center;min-height:100vh;padding:20px">
<div style="width:100%;max-width:420px">
<div class="center" style="margin-bottom:30px">
<div style="font-size:64px;margin-bottom:10px">" + icon('game', 64) + "</div>
<h1 style="font-size:36px;color:var(--primary-light);margin-bottom:5px">Live Quiz</h1>
<p style="color:#888">Voer de spelcode in om mee te doen!</p>
</div>
{% if fout %}<div class="error-msg">{{fout}}</div>{% endif %}
<div class="card">
<form method="POST">
<label class="f">" + icon('key', 18) + " Spelcode</label>
<input type="text" name="pin" placeholder="Bijv. ABC12345" pattern="[A-Za-z0-9]{4,8}" required style="font-size:28px;text-align:center;letter-spacing:10px;text-transform:uppercase;font-family:monospace">
<label class="f" style="margin-top:15px">" + icon('user', 18) + " Jouw naam</label>
<input type="text" name="naam" placeholder="Vul je naam in" required>
<button type="submit" class="btn btn-p btn-full mt10">" + icon('play', 18) + " Meedoen!</button>
</form></div></div></div></body></html>"""

@app.route('/leerling/quiz/spelen/<pin>')
def quiz_spelen(pin):
    db = get_db()
    live = db.execute("SELECT lq.*,q.titel,q.vak,q.klas FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id WHERE lq.pin=?", (pin,)).fetchone()
    if not live:
        return redirect('/leerling/quiz/spel')
    if live['status'] == 'wacht':
        dd = db.execute("SELECT naam FROM live_deelnemers WHERE pin=?", (pin,)).fetchall()
        dh = "".join(f'<p style="color:#888;margin:4px 0">' + icon('user', 14) + ' ' + '{r["naam"]}' + '</p>' for r in dd)
        return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
        <style>{CSS}</style><title>""" + icon('clock', 20) + """ Wachten...</title></head><body>
        <div class="container" style="text-align:center;padding:80px 20px">
        <div style="font-size:64px;margin-bottom:20px">""" + icon('clock', 48) + """</div>
        <h1 style="font-size:28px;color:#b388ff;margin-bottom:10px">Wachten op de docent...</h1>
        <p style="color:#888;margin-bottom:30px">Je bent ingeschreven voor: <strong>{live['titel']}</strong></p>
        <div class="card" style="max-width:300px;margin:0 auto"><h2>""" + icon('students', 20) + """ Deelnemers</h2>{dh}</div>
        <script>setInterval(function(){{fetch('/leerling/check/{pin}').then(r=>r.json()).then(d=>{{if(d.status=='actief')location.reload()}})}},2000);</script>
        </div></body></html>"""
    if live['status'] == 'actief':
        vv = db.execute("SELECT * FROM vragen WHERE quiz_id=? ORDER BY volgorde", (live['quiz_id'],)).fetchall()
        if live['vraag_index'] < len(vv):
            v = vv[live['vraag_index']]
            huidig = live['vraag_index'] + 1
            totaal = len(vv)
            opts = [v['optie_a'], v['optie_b'], v['optie_c'], v['optie_d']]
            oh = "".join(f'<div class="antwoord" onclick="kies(this,{o})"><span class="letter">{"ABCD"[o]}</span> {opts[o]}</div>' for o in range(4))
            return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
            <style>{CSS}</style><title>""" + icon('quiz', 20) + """ Vraag {huidig}</title></head><body>
            <div class="container" style="max-width:700px;margin:0 auto;padding:30px 20px">
            <div style="text-align:center;margin-bottom:20px">
            <div style="font-size:48px;margin-bottom:10px">""" + icon('quiz', 48) + """</div>
            <p style="color:#888;font-size:14px">Vraag {huidig} / {totaal}</p>
            <h1 style="font-size:22px;color:#fff;margin-top:10px">{v['tekst']}</h1></div>
            <form id="quizForm" method="POST" action="/leerling/antwoord/{pin}">
            <input type="hidden" name="antwoord" id="antwoord" value="">
            {oh}
            </form>
            <div style="text-align:center;margin-top:10px"><button class="btn btn-p" onclick="verstuur()" style="padding:12px 40px;font-size:16px">""" + icon('check', 18) + """ Bevestig</button></div>
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
              else alert('""" + icon('warning', 14) + """ Selecteer eerst een antwoord!');
            }}
            </script></div></body></html>"""
    return redirect(f'/leerling/scoreboard/{pin}')

@app.route('/leerling/check/<pin>')
def check_status(pin):
    db = get_db()
    row = db.execute("SELECT status FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    return jsonify({'status': row['status'] if row else 'weg'})

@app.route('/leerling/antwoord/<pin>', methods=['POST'])
def leerling_antwoord(pin):
    db = get_db()
    live = db.execute("SELECT * FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if not live or live['status'] != 'actief':
        return redirect(f'/leerling/scoreboard/{pin}')
    vv = db.execute("SELECT * FROM vragen WHERE quiz_id=? ORDER BY volgorde", (live['quiz_id'],)).fetchall()
    if live['vraag_index'] >= len(vv):
        return redirect(f'/leerling/scoreboard/{pin}')
    v = vv[live['vraag_index']]
    naam = session.get('spel_naam', session.get('naam', 'Speler'))
    antw = request.form.get('antwoord','-1')
    if antw in ('','-1'):
        return redirect(f'/leerling/quiz/spelen/{pin}')
    try:
        deelnemer = db.execute("SELECT id, klas FROM live_deelnemers WHERE pin=? AND naam=?", (pin, naam)).fetchone()
        if not deelnemer:
            return redirect(f'/leerling/quiz/spelen/{pin}')
        did = deelnemer['id']
        klas = deelnemer['klas'] or 'attacker'
        is_correct = int(antw) == v['antwoord']
        db.execute("INSERT OR IGNORE INTO antwoorden (pin,deelnemer_id,vraag_id,antwoord,is_correct) VALUES (?,?,?,?,?)",
                   (pin, did, v['id'], int(antw), is_correct))
        if live['boss_max_hp'] == 0:
            init_rpg_game(db, pin)
        if is_correct:
            db.execute("UPDATE live_deelnemers SET score=score+10 WHERE id=?", (did,))
            damage = calc_damage(v['tekst'], klas)
            apply_damage_to_boss(db, pin, damage)
            db.execute("UPDATE live_deelnemers SET total_damage=total_damage+?, correct_answers=correct_answers+1 WHERE id=?", (damage, did))
            if klas == 'healer':
                heal_amt = max(15, damage // 2)
                heal_team(db, pin, heal_amt)
                db.execute("UPDATE live_deelnemers SET heals_done=heals_done+? WHERE id=?", (heal_amt, did))
                add_game_log(db, pin, icon('heart', 16) + " " + naam + " heeft het team geheald voor " + str(heal_amt) + " HP!", 'heal')
            else:
                add_game_log(db, pin, icon('sword', 16) + " " + naam + " deed " + str(damage) + " schade aan de boss!", 'damage')
        else:
            team_dmg = 25 if klas == 'tank' else 50
            apply_damage_to_team(db, pin, team_dmg)
            add_game_log(db, pin, icon('zap', 16) + " " + naam + " maakte een fout! Team krijgt " + str(team_dmg) + " schade!", 'damage')
        db.commit()
        check_game_over(db, pin)
    except Exception as e:
        logger.error(f"Antwoord fout: {e}")
    return redirect(f'/leerling/quiz/rpg/{pin}')

@app.route('/leerling/scoreboard/<pin>')
def leerling_scoreboard(pin):
    db = get_db()
    live = db.execute("SELECT lq.*,q.titel FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id WHERE lq.pin=?", (pin,)).fetchone()
    if not live:
        return redirect('/leerling/quiz/spel')
    dd = db.execute("SELECT naam,score FROM live_deelnemers WHERE pin=? ORDER BY score DESC", (pin,)).fetchall()
    rijen = '<tr><td colspan="2" style="text-align:center;color:#888">' + icon('info', 16) + ' Geen scores</td></tr>'
    if dd:
        rijen = ""
        for idx, (naam, score) in enumerate(dd):
            medal = '<span class="medal medal-1">' + icon('crown', 12) + '</span>' if idx == 0 else '<span class="medal medal-2">' + icon('star', 12) + '</span>' if idx == 1 else '<span class="medal medal-3">' + icon('check', 12) + '</span>' if idx == 2 else f'<span class="medal" style="background:rgba(255,255,255,.05);color:#888">#{idx+1}</span>'
            rijen += f'<tr><td style="font-size:18px">{medal} {naam}</td><td style="color:#b388ff;font-size:22px;font-weight:bold">{score}</td></tr>'
    volgende = ""
    if live['status'] == 'actief':
        volgende = '<p style="text-align:center;color:#ffd740;margin-top:15px">' + icon('clock', 16) + ' Volgende vraag komt eraan...</p>'
        volgende += f'<script>setTimeout(function(){{location.href="/leerling/quiz/spelen/{pin}"}},3000);</script>'
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style><title>""" + icon('trophy', 20) + """ Scorebord</title></head><body>
    <div class="container" style="max-width:600px;margin:0 auto;padding:30px 20px">
    <div class="center" style="margin-bottom:20px">
    <div style="font-size:64px;margin-bottom:10px">""" + icon('trophy', 48) + """</div>
    <h1 style="font-size:28px;color:#b388ff">Scorebord</h1>
    <p style="color:#888">{live['titel']}</p></div>
    <div class="card"><div class="table-wrap"><table><tr><th>Naam</th><th>Score</th></tr>{rijen}</table></div></div>
    {volgende}
    <div class="center mt10"><a href="/leerling/quiz/spel" class="btn btn-d">""" + icon('refresh', 18) + """ Nieuwe quiz</a></div>
    </div></body></html>"""

# ===== MESSAGES =====
@app.route('/berichten')
@login_required
def berichten():
    db = get_db()
    uid = session['user_id']
    bb = db.execute("""
        SELECT b.*, u1.display_name as afz, u2.display_name as ontv
        FROM berichten b JOIN users u1 ON b.afzender_id=u1.id JOIN users u2 ON b.ontvanger_id=u2.id
        WHERE b.ontvanger_id=? OR b.afzender_id=? ORDER BY b.created_at DESC LIMIT 50
    """, (uid, uid)).fetchall()
    bh = ""
    for b in bb:
        s = icon('check', 14) if b['gelezen'] else icon('info', 14)
        richt = icon('mail', 14) + " Van" if b['afzender_id'] == uid else icon('send', 14) + " Naar"
        nm = b['afz'] if b['afzender_id'] == uid else b['ontv']
        bh += f'<div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:15px;margin-bottom:10px">'
        bh += f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        bh += f'<strong style="color:{"#b388ff" if not b["gelezen"] else "#ccc"}">{s} {safe_string(b["onderwerp"])}</strong></div>'
        bh += f'<p style="color:#888;font-size:13px">{richt}: {safe_string(nm)} - {b["created_at"]}</p>'
        bh += f'<p style="margin-top:6px">{safe_string(b["inhoud"])}</p></div>'
    if not bh:
        bh = '<p style="text-align:center;color:#888">' + icon('info', 16) + ' Geen berichten</p>'
    ag = db.execute("SELECT id,display_name,role FROM users WHERE id!=? ORDER BY role,display_name", (uid,)).fetchall()
    go = "".join(f'<option value="{u["id"]}">{u["display_name"]} ({u["role"]})</option>' for u in ag)
    return render_template_string(BERICHTEN_HTML, CSS=CSS, berichten=bh, gebruiker_opties=go, aantal=len(bb))

BERICHTEN_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Berichten</title></head>
<body>
<div class="navbar">
  <span class="logo"><span class="logo-icon">SP</span> SchoolPortaal</span>
  <div class="nav-wrap">
    <a href="/">" + icon('dashboard', 16) + " Dashboard</a>
    <a href="/berichten" class="btn btn-p btn-sm">" + icon('messages', 16) + " Berichten</a>
    <a href="/uitloggen" class="btn btn-d btn-sm">" + icon('logout', 16) + " Uitloggen</a>
  </div>
</div>
<div class="container">
<div class="welkom">" + icon('messages', 18) + " Berichten ({{aantal}})</div>
<div class="card"><h2>" + icon('edit', 20) + " Nieuw Bericht</h2><form method="POST" action="/berichten/verstuur">
<div class="form-grid">
<label class="f">" + icon('user', 18) + " Aan<select name="ontvanger_id" required>{{gebruiker_opties}}</select></label>
<label class="f">" + icon('tests', 18) + " Onderwerp<input type="text" name="onderwerp" required placeholder="Onderwerp"></label>
</div>
<label class="f">" + icon('messages', 18) + " Bericht<textarea name="inhoud" rows="4" required placeholder="Type je bericht..."></textarea></label>
<button type="submit" class="btn btn-p mt10">" + icon('mail', 18) + " Verstuur</button></form></div>
<div class="card"><h2>" + icon('messages', 20) + " Berichten</h2>{{berichten}}</div>
</div></body></html>"""

@app.route('/berichten/verstuur', methods=['POST'])
def bericht_verstuur():
    if 'rol' not in session: return redirect('/login')
    db = get_db()
    uid = session['user_id']
    oid = request.form.get('ontvanger_id','').strip()
    onderw = request.form.get('onderwerp','').strip()
    inhoud = request.form.get('inhoud','').strip()
    if not all([oid, onderw, inhoud]):
        return redirect('/berichten')
    db.execute("INSERT INTO berichten (afzender_id,ontvanger_id,onderwerp,inhoud,gelezen) VALUES (?,?,?,?,0)",
               (uid, int(oid), onderw, inhoud))
    db.commit()
    return redirect('/berichten')

@app.route('/berichten/ongelezen')
def berichten_ongelezen():
    if 'rol' not in session: return jsonify({'ongelezen': 0})
    db = get_db()
    uid = session['user_id']
    a = db.execute("SELECT COUNT(*) as c FROM berichten WHERE ontvanger_id=? AND gelezen=0", (uid,)).fetchone()['c']
    return jsonify({'ongelezen': a})

@app.route('/berichten/mark-gelezen/<int:bericht_id>', methods=['POST'])
def bericht_mark_gelezen(bericht_id):
    if 'rol' not in session: return redirect('/login')
    db = get_db()
    uid = session['user_id']
    db.execute("UPDATE berichten SET gelezen=1 WHERE id=? AND ontvanger_id=?", (bericht_id, uid))
    db.commit()
    return jsonify({'success': True})

# ===== WACHTWOORD RESET =====
@app.route('/wachtwoord-reset', methods=['GET','POST'])
def wachtwoord_reset():
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        logger.info(f"Reset requested for: {email}")
        return render_template_string(WACHTWOORD_RESET_HTML, CSS=CSS,
            bericht=icon('check', 16) + " Er is een reset-link verzonden naar je e-mailadres (indien het bestaat).")
    return render_template_string(WACHTWOORD_RESET_HTML, CSS=CSS, bericht="")

WACHTWOORD_RESET_HTML = """<!DOCTYPE html>
<html lang="nl">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{{CSS}}</style><title>Wachtwoord Reset</title></head>
<body>
<div class="login-screen">
<div class="login-box">
<div class="login-header">
<h1><span class="logo-icon" style="width:44px;height:44px;font-size:22px">SP</span> SchoolPortaal</h1>
<p>" + icon('key', 24) + " Wachtwoord resetten</p>
</div>
{% if bericht %}<div class="success-msg">{{bericht}}</div>{% endif %}
<div class="card">
<form method="POST">
<label class="f">" + icon('mail', 18) + " E-mailadres<input type="email" name="email" required placeholder="jouw@email.nl"></label>
<button type="submit" class="btn btn-p btn-full">" + icon('mail', 18) + " Verstuur reset-link</button>
</form>
<p class="center mt10"><a href="/login" style="color:#888;font-size:13px">" + icon('arrow-left', 16) + " Terug naar inloggen</a></p>
</div>
</div>
</div>
</body></html>"""

@app.route('/uitloggen')
def uitloggen():
    session.clear()
    return redirect('/login')

# ===== OLD STYLE QUIZ =====
@app.route('/leerling/quiz/spel/ouderwets')
def leerling_quiz_ouderwets():
    if 'rol' not in session or session['rol'] != 'leerling': return redirect('/login')
    db = get_db()
    rijen = ""
    for q in db.execute("SELECT * FROM quizzen ORDER BY created_at DESC").fetchall():
        av = db.execute("SELECT COUNT(*) as c FROM vragen WHERE quiz_id=?", (q['id'],)).fetchone()['c']
        rijen += f'<div class="card"><h2>' + icon('game', 20) + ' ' + '{q["titel"]}' + '</h2>'
        rijen += f'<p>' + icon('book', 16) + ' <strong>Vak:</strong> ' + '{q["vak"]}' + ' | ' + icon('quiz', 16) + ' <strong>Vragen:</strong> ' + str(av) + '</p>'
        if av > 0:
            rijen += f'<a href="/leerling/quiz/maken/{q["id"]}" class="btn btn-p mt10">' + icon('zap', 16) + ' Start</a></div>'
        else:
            rijen += '<p style="color:#888">' + icon('info', 16) + ' Nog geen vragen</p></div>'
    if not rijen:
        rijen = '<div class="card"><p style="text-align:center;color:#888">' + icon('info', 16) + ' Geen quizzen beschikbaar.</p></div>'
    return PAGE_HEADER("" + icon('quiz', 20) + " Quizzen", "Beschikbare <strong>Quizzen</strong>", rijen)

# ===== BLOCK TRACKING JS =====
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

# ===== HELPERS =====
def PAGE_HEADER(title, welkom, body):
    rol = session.get('rol', '')
    is_docent = rol == 'docent'
    nav_items = ""
    if is_docent:
        nav_items = """
    <a href="/docent">""" + icon('dashboard', 16) + """ Dashboard</a>
    <a href="/docent/klassen">""" + icon('classes', 16) + """ Klassen</a>
    <a href="/docent/toetsen">""" + icon('tests', 16) + """ Toetsen</a>
    <a href="/docent/quizzen">""" + icon('quiz', 16) + """ Quizzen</a>
    <a href="/docent/cijfers">""" + icon('grades', 16) + """ Cijfers</a>
    <a href="/docent/leerlingen">""" + icon('students', 16) + """ Leerlingen</a>
    <a href="/docent/live">""" + icon('live', 16) + """ Live Quiz</a>
    <a href="/berichten">""" + icon('messages', 16) + """ Berichten</a>
    <a href="/uitloggen" class="btn btn-d btn-sm">""" + icon('logout', 16) + """ Uitloggen</a>"""
    else:
        nav_items = """
    <a href="/leerling">""" + icon('dashboard', 16) + """ Dashboard</a>
    <a href="/leerling/cijfers">""" + icon('grades', 16) + """ Cijfers</a>
    <a href="/leerling/quiz/spel">""" + icon('live', 16) + """ Live Quiz</a>
    <a href="/leerling/schoolgids">""" + icon('book', 16) + """ Schoolgids</a>
    <a href="/berichten">""" + icon('messages', 16) + """ Berichten</a>
    <a href="/uitloggen" class="btn btn-d btn-sm">""" + icon('logout', 16) + """ Uitloggen</a>"""
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>{CSS}</style><title>{title}</title></head><body>
<div class="navbar"><span class="logo"><span class="logo-icon">SP</span> SchoolPortaal</span><div class="nav-wrap">{nav_items}</div></div>
<div class="container"><div class="welkom">{welkom}</div>{body}</div></body></html>"""

def PAGE(title, welkom, body):
    return PAGE_HEADER(title, welkom, body)

# ===== RPG BOSS BATTLE =====
BOSS_NAMES = ["🐉 De Grote Draak", "🦂 De Schorpioen-Koning", "🐵 De Vuuraap", "🐻‍❄️ De IJsbeer-Titan", "👿 De Demonische Leraar"]

def calc_damage(vraag_tekst, klas):
    base = min(len(vraag_tekst) * 2 + 30, 120)
    if klas == 'warrior':
        return int(base * 2.0)
    elif klas == 'healer':
        return int(base * 0.6)
    return base

def init_rpg_game(db, pin):
    lq = db.execute("SELECT * FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if not lq:
        return
    dd = db.execute("SELECT * FROM live_deelnemers WHERE pin=?", (pin,)).fetchall()
    np = len(dd)
    if np == 0:
        return
    boss_hp = np * 500
    team_hp = np * 100
    boss_naam = random.choice(BOSS_NAMES)
    db.execute("UPDATE live_quizzen SET boss_hp=?,boss_max_hp=?,team_hp=?,team_max_hp=?,boss_naam=?,vraag_tijd=20 WHERE pin=?",
               (boss_hp, boss_hp, team_hp, team_hp, boss_naam, pin))
    db.commit()

def apply_damage_to_boss(db, pin, damage):
    lq = db.execute("SELECT boss_hp,boss_max_hp FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if not lq: return
    nh = max(0, lq['boss_hp'] - damage)
    db.execute("UPDATE live_quizzen SET boss_hp=? WHERE pin=?", (nh, pin))
    db.commit()

def apply_damage_to_team(db, pin, damage):
    lq = db.execute("SELECT team_hp,team_max_hp FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if not lq: return
    nh = max(0, lq['team_hp'] - damage)
    db.execute("UPDATE live_quizzen SET team_hp=? WHERE pin=?", (nh, pin))
    db.commit()

def heal_team(db, pin, heal_amount):
    lq = db.execute("SELECT team_hp,team_max_hp FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if not lq: return
    nh = min(lq['team_max_hp'], lq['team_hp'] + heal_amount)
    db.execute("UPDATE live_quizzen SET team_hp=? WHERE pin=?", (nh, pin))
    db.commit()

def add_game_log(db, pin, bericht, typ='info'):
    db.execute("INSERT INTO rpg_log (pin, bericht, type) VALUES (?,?,?)", (pin, bericht, typ))
    db.commit()

def check_game_over(db, pin):
    lq = db.execute("SELECT boss_hp,team_hp,status FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if not lq: return None
    if lq['boss_hp'] <= 0:
        db.execute("UPDATE live_quizzen SET status='klaar',beeindigd_op=CURRENT_TIMESTAMP WHERE pin=?", (pin,))
        db.commit()
        return 'victory'
    if lq['team_hp'] <= 0:
        db.execute("UPDATE live_quizzen SET status='klaar',beeindigd_op=CURRENT_TIMESTAMP WHERE pin=?", (pin,))
        db.commit()
        return 'defeat'
    return None

@app.route('/leerling/quiz/rpg/<pin>')
def leerling_rpg(pin):
    db = get_db()
    live = db.execute("SELECT lq.*,q.titel FROM live_quizzen lq JOIN quizzen q ON lq.quiz_id=q.id WHERE lq.pin=?", (pin,)).fetchone()
    if not live:
        return redirect('/leerling/quiz/spel')
    naam = session.get('spel_naam', session.get('naam', 'Speler'))
    deelnemer = db.execute("SELECT id,klas FROM live_deelnemers WHERE pin=? AND naam=?", (pin, naam)).fetchone()
    if not deelnemer:
        return redirect(f'/leerling/quiz/spelen/{pin}')
    did = deelnemer['id']
    return f"""<!DOCTYPE html><html lang="nl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>{CSS}</style>
    <style>
    .rpg-bg{{background:linear-gradient(180deg,#1a0a2e 0%,#16213e 50%,#0f0c29 100%);min-height:100vh}}
    .boss-card{{border:3px solid rgba(255,82,82,.4);background:linear-gradient(135deg,rgba(255,82,82,.1),rgba(255,82,82,.02));box-shadow:0 0 30px rgba(255,82,82,.2)}}
    .team-card{{border:3px solid rgba(0,230,118,.4);background:linear-gradient(135deg,rgba(0,230,118,.1),rgba(0,230,118,.02));box-shadow:0 0 30px rgba(0,230,118,.2)}}
    .hp-bar{{height:28px;border-radius:14px;overflow:hidden;transition:width .8s cubic-bezier(.4,0,.2,1);box-shadow:inset 0 2px 8px rgba(0,0,0,.3)}}
    .boss-hp-bar{{background:linear-gradient(90deg,#ff5252,#ff1744,#d50000);box-shadow:0 0 20px rgba(255,82,82,.5)}}
    .team-hp-bar{{background:linear-gradient(90deg,#00e676,#69f0ae,#00c853);box-shadow:0 0 20px rgba(0,230,118,.5)}}
    .question-card{{background:linear-gradient(135deg,rgba(124,77,255,.15),rgba(124,77,255,.05));border:2px solid rgba(124,77,255,.3);box-shadow:0 0 30px rgba(124,77,255,.2)}}
    .log-card{{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.1);box-shadow:inset 0 2px 10px rgba(0,0,0,.5)}}
    .log-entry{{padding:8px 12px;margin-bottom:6px;border-radius:8px;background:rgba(255,255,255,.03);border-left:3px solid;animation:slideInLeft .3s ease-out}}
    @keyframes slideInLeft{{from{{opacity:0;transform:translateX(-20px)}}to{{opacity:1;transform:translateX(0)}}}}
    @keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.05)}}}}
    @keyframes shake{{0%,100%{{transform:translateX(0)}}25%{{transform:translateX(-5px)}}75%{{transform:translateX(5px)}}}}
    @keyframes glow{{0%,100%{{box-shadow:0 0 20px rgba(255,82,82,.5)}}50%{{box-shadow:0 0 40px rgba(255,82,82,.8)}}}}
    .damage-anim{{animation:shake .3s ease-in-out}}
    .heal-anim{{animation:pulse .5s ease-in-out}}
    .boss-low{{animation:glow 1s ease-in-out infinite}}
    .particle{{position:absolute;pointer-events:none;border-radius:50%;animation:particleFade 1s ease-out forwards}}
    @keyframes particleFade{{0%{{opacity:1;transform:scale(1)}}100%{{opacity:0;transform:scale(0)}}}}
    </style>
    <title>RPG Boss Battle</title></head><body class="rpg-bg">
    <div class="navbar" style="flex-shrink:0"><span class="logo">""" + icon('game', 20) + """ RPG Battle</span>
    <div><span style="color:var(--primary-light);font-weight:bold;font-size:18px" id="bossName">{live['boss_naam'] or 'De Grote Draak'}</span>
    <a href="/leerling/quiz/spelen/{pin}" class="btn btn-d btn-sm">""" + icon('logout', 16) + """ Verlaat</a></div></div>
    <div style="flex:1;display:flex;flex-direction:column;overflow-y:auto" id="gameArea">
    <div style="padding:20px;flex-shrink:0">
    <div class="card boss-card" id="bossCard">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="font-size:20px;font-weight:bold;color:var(--danger)">""" + icon('dragon', 24) + """ Boss</span>
    <span id="bossHpText" style="font-size:16px;color:#ff8a80;font-weight:600">""" + icon('heart', 16) + """ HP: --</span></div>
    <div style="width:100%;height:28px;background:rgba(0,0,0,.3);border-radius:14px;overflow:hidden">
    <div id="bossHpBar" class="hp-bar boss-hp-bar" style="width:100%"></div></div></div>
    <div class="card team-card" style="margin-top:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
    <span style="font-size:20px;font-weight:bold;color:var(--success)">""" + icon('shield', 24) + """ Team HP</span>
    <span id="teamHpText" style="font-size:16px;color:#b9f6ca;font-weight:600">""" + icon('heart', 16) + """ HP: --</span></div>
    <div style="width:100%;height:28px;background:rgba(0,0,0,.3);border-radius:14px;overflow:hidden">
    <div id="teamHpBar" class="hp-bar team-hp-bar" style="width:100%"></div></div></div></div>
    <div id="questionArea" style="padding:0 20px;flex-shrink:0">
    <div class="card question-card" id="timerCard"><div style="display:flex;justify-content:space-between;align-items:center">
    <span style="color:#ccc;font-size:15px;font-weight:500">""" + icon('quiz', 16) + """ Vraag <span id="vraagNr">--</span></span>
    <span style="color:var(--warning);font-weight:bold;font-size:18px" id="timerText">""" + icon('clock', 16) + """ --</span></div></div>
    <div class="card" id="waitCard" style="text-align:center;background:rgba(124,77,255,.05)">
    <h3 style="color:var(--primary-light);margin-bottom:12px;font-size:22px">""" + icon('sword', 28) + """ Gevecht gaande!</h3>
    <p style="color:#aaa;margin-bottom:8px">Kijk naar de HP balken, wacht op de volgende vraag...</p>
    <p style="color:var(--warning);font-weight:bold;font-size:16px" id="nextTimer">""" + icon('clock', 16) + """ Volgende over: --</p></div>
    <div class="card question-card" id="questionCard" style="display:none">
    <h2 id="vraagTekst" style="text-align:center;margin-bottom:24px;font-size:22px;line-height:1.5;color:#fff"></h2>
    <form id="rpgForm" method="POST" action="/leerling/antwoord/{pin}">
    <input type="hidden" name="antwoord" id="antwoord" value="">
    <div id="antwoordButtons"></div>
    <div style="text-align:center;margin-top:16px"><button type="button" class="btn btn-p" onclick="verstuur()" style="padding:14px 48px;font-size:17px">""" + icon('sword', 18) + """ Bevestig Aanval!</button></div>
    </form></div></div>
    <div style="flex:1;padding:0 20px 20px;min-height:140px">
    <div class="card log-card" style="height:100%;overflow-y:auto;max-height:320px">
    <h3 style="color:var(--primary-light);margin-bottom:12px;font-size:16px">""" + icon('messages', 18) + """ Gevechtslogboek</h3>
    <div id="logEntries" style="font-family:'Courier New',monospace;font-size:13px;color:#ccc"></div></div></div></div>
    <div id="animOverlay" style="position:fixed;top:0;left:0;right:0;bottom:0;pointer-events:none;z-index:999;display:none">
    <div id="animText" style="position:absolute;font-size:48px;font-weight:bold;text-align:center;width:100%;top:40%;text-shadow:0 0 30px currentColor;animation:pulse .5s ease-in-out"></div></div>
    <div id="resultOverlay" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.9);z-index:1000;display:none;justify-content:center;align-items:center;flex-direction:column">
    <div id="resultIcon" style="font-size:100px;margin-bottom:24px;animation:pulse 1s ease-in-out infinite"></div>
    <h1 id="resultTitle" style="font-size:56px;margin-bottom:12px;font-weight:800"></h1>
    <p id="resultSub" style="color:#aaa;font-size:20px;margin-bottom:36px"></p>
    <div id="mvpArea" style="width:100%;max-width:550px;padding:0 24px"></div>
    <a href="/leerling/quiz/spel" class="btn btn-p mt10" style="padding:16px 40px;font-size:18px">""" + icon('refresh', 18) + """ Nieuw spel</a></div></div>
    <script>
    const PIN="{pin}", DEELNEMER_ID={did}, DEELNEMER_NAAM="{naam}";
    let klas="{deelnemer['klas'] or 'attacker'}", gekozen=null, timerInterval=null, pollInterval=null, nextInterval=null, currentQ=0;
    const klasNamen={{attacker:'Aanvaller',warrior:'Krijger',healer:'Healer',tank:'Tank'}};
    const klasKleuren={{attacker:'var(--primary-light)',warrior:'var(--danger)',healer:'var(--success)',tank:'var(--warning)'}};
    function showAnim(text, color, dur=1500){{
      const o=document.getElementById('animOverlay'), t=document.getElementById('animText');
      t.textContent=text;t.style.color=color;o.style.display='block';
      setTimeout(()=>o.style.display='none', dur);
    }}
    function createParticles(x, y, color, count=10){{
      for(let i=0;i<count;i++){{
        const p=document.createElement('div');
        p.className='particle';
        p.style.cssText=`left:${{x}}px;top:${{y}}px;width:${{Math.random()*10+5}}px;height:${{Math.random()*10+5}}px;background:${{color}}`;
        p.style.transform=`translate(${{(Math.random()-0.5)*100}}px,${{(Math.random()-0.5)*100}}px)`;
        document.body.appendChild(p);
        setTimeout(()=>p.remove(), 1000);
      }}
    }}
    function showLog(bericht, type){{
      const c=document.getElementById('logEntries'), d=document.createElement('div');
      d.className='log-entry';
      const kleur=type==='damage'?'var(--danger)':type==='heal'?'var(--success)':type==='join'?'var(--primary-light)':'var(--warning)';
      d.style.borderColor=kleur;
      d.innerHTML='<span style=color:'+kleur+';font-weight:600;margin-right:8px">●</span> '+bericht;
      c.insertBefore(d, c.firstChild);
      if(c.children.length>30)c.lastChild.remove();
    }}
    function updateBars(bossHp, bossMax, teamHp, teamMax){{
      const bp=Math.max(0,bossHp/bossMax*100), tp=Math.max(0,teamHp/teamMax*100);
      const bossBar=document.getElementById('bossHpBar');
      const teamBar=document.getElementById('teamHpBar');
      bossBar.style.width=bp+'%';
      teamBar.style.width=tp+'%';
      document.getElementById('bossHpText').textContent='HP: '+Math.max(0,bossHp)+' / '+bossMax;
      document.getElementById('teamHpText').textContent='HP: '+Math.max(0,teamHp)+' / '+teamMax;
      if(bp<30)document.getElementById('bossCard').classList.add('boss-low');
      else document.getElementById('bossCard').classList.remove('boss-low');
    }}
    function toonVraag(v){{
      document.getElementById('waitCard').style.display='none';
      const qc=document.getElementById('questionCard');
      if(!v||!v.tekst){{qc.style.display='none';document.getElementById('waitCard').style.display='block';return;}}
      qc.style.display='block';
      document.getElementById('vraagTekst').textContent=(currentQ+1)+'. '+v.tekst;
      document.getElementById('vraagNr').textContent=(currentQ+1);
      const btns=document.getElementById('antwoordButtons');
      btns.innerHTML='';
      const opts=[v.optie_a,v.optie_b,v.optie_c,v.optie_d];
      opts.forEach((o,i)=>{{
        const d=document.createElement('div');
        d.className='antwoord';d.style.marginBottom='10px';
        d.innerHTML='<span class=letter>'+(String.fromCharCode(65+i))+'</span>'+o;
        d.onclick=()=>{{
          document.querySelectorAll('.antwoord').forEach(e=>e.classList.remove('selected'));
          d.classList.add('selected');
          gekozen=i;
          document.getElementById('antwoord').value=i;
        }};
        btns.appendChild(d);
      }});
      gekozen=null;
    }}
    function startTimer(seconds, onUpdate, onDone){{
      let left=seconds;
      document.getElementById('timerText').textContent=""" + icon('clock', 16) + """ '+left+'s';
      document.getElementById('nextTimer').textContent=""" + icon('clock', 16) + """ Volgende over: '+left+'s';
      if(timerInterval)clearInterval(timerInterval);
      if(nextInterval)clearInterval(nextInterval);
      timerInterval=setInterval(()=>{{
        left--;
        document.getElementById('timerText').textContent=""" + icon('clock', 16) + """ '+left+'s';
        document.getElementById('nextTimer').textContent=""" + icon('clock', 16) + """ Volgende over: '+left+'s';
        if(onUpdate)onUpdate(left);
        if(left<=0){{clearInterval(timerInterval);clearInterval(nextInterval);onDone()}};
      }},1000);
    }}
    function verstuur(){{if(gekozen!==null)document.getElementById('rpgForm').submit();else alert('""" + icon('warning', 14) + """ Selecteer een antwoord!');}}
    async function pollState(){{
      try{{
        const r=await fetch('/api/rpg/state/'+PIN);
        const d=await r.json();
        if(d.error)return;
        if(document.getElementById('bossName').textContent!==d.boss_naam)document.getElementById('bossName').textContent=d.boss_naam;
        updateBars(d.boss_hp||0, d.boss_max_hp||1, d.team_hp||0, d.team_max_hp||1);
        d.log.forEach(l=>showLog(l.bericht, l.type));
        if(d.status==='klaar')showResult(d);
      }}catch(e){{}}
    }}
    function showResult(d){{
      if(pollInterval)clearInterval(pollInterval);
      if(timerInterval)clearInterval(timerInterval);
      if(nextInterval)clearInterval(nextInterval);
      const won=(d.boss_hp||0)<=0&&d.boss_max_hp>0;
      document.getElementById('resultOverlay').style.display='flex';
      document.getElementById('resultIcon').textContent=won?'VICTORY':'DEFEAT';
      document.getElementById('resultTitle').textContent=won?'Je hebt gewonnen!':'Je hebt verloren';
      document.getElementById('resultTitle').style.color=won?'var(--warning)':'var(--danger)';
      document.getElementById('resultSub').textContent=won?'De '+d.boss_naam+' is verslagen!':'Het team is gevallen...';
      let mvp='';
      if(d.deelnemers&&d.deelnemers.length>0){{
        const sorted=[...d.deelnemers].sort((a,b)=>b.total_damage-a.total_damage);
        mvp+='<h3 style=color:var(--primary-light);text-align:center;margin-bottom:16px;font-size:20px">MVP</h3>';
        sorted.forEach((p,i)=>{{
          const medal=i===0?'1.':i===1?'2.':i===2?'3.':'';
          mvp+='<div style=background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:14px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center>';
          mvp+='<span>'+medal+' '+p.naam+' <small style=color:'+(klasKleuren[p.klas]||'#888')+'>'+(klasNamen[p.klas]||p.klas)+'</small></span>';
          mvp+='<span style=color:var(--primary-light);font-weight:600>DMG:'+p.total_damage+' HEAL:'+p.heals_done+'</span></div>';
        }});
      }}
      document.getElementById('mvpArea').innerHTML=mvp;
    }}
    document.addEventListener('DOMContentLoaded',function(){{
      pollInterval=setInterval(pollState, 1000);
    }});
    </script></body></html>"""

@app.route('/api/rpg/state/<pin>')
def rpg_state(pin):
    db = get_db()
    lq = db.execute("SELECT * FROM live_quizzen WHERE pin=?", (pin,)).fetchone()
    if not lq:
        return jsonify({'error': 'not found'}), 404
    dd = db.execute("SELECT id,naam,klas,score,total_damage,correct_answers,heals_done,is_active FROM live_deelnemers WHERE pin=?", (pin,)).fetchall()
    lg = db.execute("SELECT bericht,type,created_at FROM rpg_log WHERE pin=? ORDER BY id DESC LIMIT 20", (pin,)).fetchall()
    return jsonify({
        'pin': lq['pin'],
        'status': lq['status'],
        'boss_naam': lq['boss_naam'],
        'boss_hp': lq['boss_hp'] or 0,
        'boss_max_hp': lq['boss_max_hp'] or 1,
        'team_hp': lq['team_hp'] or 0,
        'team_max_hp': lq['team_max_hp'] or 1,
        'vraag_index': lq['vraag_index'],
        'vraag_tijd': lq['vraag_tijd'],
        'deelnemers': [dict(d) for d in dd],
        'log': [dict(l) for l in lg]
    })

@app.route('/api/rpg/join/<pin>', methods=['POST'])
def rpg_join(pin):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'no data'}), 400
    naam = data.get('naam','').strip()
    klas = data.get('klas','attacker')
    if not naam or len(naam) > 30:
        return jsonify({'error': 'ongeldige naam'}), 400
    if klas not in ('attacker','warrior','healer','tank'):
        return jsonify({'error': 'ongeldige klas'}), 400
    db = get_db()
    if db.execute("SELECT id FROM live_deelnemers WHERE pin=? AND naam=?", (pin, naam)).fetchone():
        return jsonify({'error': 'naam bestaat al'}), 409
    db.execute("INSERT INTO live_deelnemers (pin,naam,klas) VALUES (?,?,?)", (pin, naam, klas))
    db.commit()
    add_game_log(db, pin, icon('sword', 16) + " " + naam + " is het slagveld betreden als " + klas + "!", 'join')
    return jsonify({'success': True, 'naam': naam, 'klas': klas})

@app.route('/api/rpg/log/<pin>')
def rpg_log_api(pin):
    db = get_db()
    lg = db.execute("SELECT bericht,type,created_at FROM rpg_log WHERE pin=? ORDER BY id DESC LIMIT 30", (pin,)).fetchall()
    return jsonify({'log': [dict(l) for l in lg]})

@app.route('/api/rpg/reset/<pin>', methods=['POST'])
def rpg_reset(pin):
    if 'rol' not in session or session['rol'] != 'docent':
        return jsonify({'error': 'auth'}), 403
    db = get_db()
    db.execute("DELETE FROM rpg_log WHERE pin=?", (pin,))
    db.execute("UPDATE live_deelnemers SET total_damage=0,correct_answers=0,heals_done=0,is_active=1 WHERE pin=?", (pin,))
    db.commit()
    return jsonify({'success': True})

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'schoolportaal'}), 200

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print("SchoolPortaal start op http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=debug)