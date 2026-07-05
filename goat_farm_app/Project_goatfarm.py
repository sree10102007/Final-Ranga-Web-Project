import os
import secrets
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import psycopg2.extras
import sys
import os
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
import re
import uuid
import pyotp
import qrcode
import base64
import io
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Resolve root path to handle Windows folder redirection (e.g. OneDrive)
base_dir = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(base_dir, 'templates')):
    # Try replacing \Documents\ with \OneDrive\Documents\
    alt_dir = base_dir.replace('\\Documents\\', '\\OneDrive\\Documents\\').replace('/Documents/', '/OneDrive/Documents/')
    if os.path.exists(os.path.join(alt_dir, 'templates')):
        base_dir = alt_dir

# Load environment variables from .env file if dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(base_dir, '.env'))
except ImportError:
    pass

def validate_env():
    required_vars = ['SECRET_KEY', 'DB_ENCRYPTION_KEY']
    if not os.environ.get('DATABASE_URL'):
        required_vars.extend(['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'])
    
    missing_or_placeholder = []
    for var in required_vars:
        val = os.environ.get(var)
        if not val or 'your_' in val.lower():
            missing_or_placeholder.append(var)
            
    if missing_or_placeholder:
        print(f"CRITICAL CONFIGURATION ERROR: Missing or placeholder environment variables: {', '.join(missing_or_placeholder)}")
        print("Please copy .env.example to .env and configure the actual connection and secret key settings.")
        sys.exit(1)

    flask_env = os.environ.get('FLASK_ENV', '').lower()
    limiter_uri = os.environ.get('LIMITER_STORAGE_URI', '')
    if flask_env == 'production' and (not limiter_uri or 'memory://' in limiter_uri):
        print("\n==========================================================================")
        print("WARNING: FLASK_ENV is set to production, but LIMITER_STORAGE_URI")
        print("is unset or using in-memory storage ('memory://'). Rate limit state")
        print("will not survive worker restarts or be shared across Gunicorn workers.")
        print("Please configure a persistent backend (e.g., Redis) in production.")
        print("==========================================================================\n")

validate_env()

from cryptography.fernet import Fernet
import logging
from logging.handlers import RotatingFileHandler

from goat_farm_app.app_factory import create_app
from goat_farm_app.extensions import (
    csrf,
    limiter,
    get_db,
    log_security_event,
    db_encryptor,
    validate_password_strength,
    DatabaseEncryptor,
    DecryptedRow,
    encrypt_query_params,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
    get_db_connection,
    sqlite3
)
from flask_wtf.csrf import CSRFProtect, CSRFError

# Initialize application using the Application Factory pattern
app = create_app()


# ── CSP NONCE: generate a fresh cryptographic nonce for every request ────────
# This allows us to whitelist our own inline scripts/styles without using
# 'unsafe-inline', which is flagged by OWASP ZAP and other scanners.
@app.before_request
def set_csp_nonce():
    g.csp_nonce = secrets.token_hex(16)

# Expose g.csp_nonce in every Jinja2 template automatically
@app.context_processor
def inject_csp_nonce():
    return dict(csp_nonce=getattr(g, 'csp_nonce', ''))



from flask_limiter.errors import RateLimitExceeded

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit_exceeded(e):
    # Log security event
    log_security_event("rate_limit_exceeded", f"Rate limit exceeded: {e.description}")
    
    retry_after = getattr(e, 'retry_after', 60)
    if retry_after is None:
        retry_after = 60
        
    if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json' or request.is_json:
        response = jsonify({
            "success": False,
            "error": "Too many requests",
            "retry_after": f"{retry_after} seconds"
        })
        response.headers['Retry-After'] = str(retry_after)
        return response, 429
        
    try:
        return render_template('rate_limit.html', retry_after=retry_after), 429
    except Exception:
        # High-end fallback HTML response if template fails
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rate Limit Exceeded - Ranga Farms</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
            <style>
                body {{
                    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
                    color: #f8fafc;
                    font-family: 'Outfit', sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    overflow: hidden;
                }}
                .card {{
                    background: rgba(30, 41, 59, 0.45);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 24px;
                    padding: 3rem;
                    text-align: center;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                    max-width: 480px;
                    width: 90%;
                    animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
                }}
                @keyframes fadeInUp {{
                    from {{ opacity: 0; transform: translateY(20px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
                .icon {{
                    width: 80px;
                    height: 80px;
                    background: linear-gradient(135deg, #ef4444 0%, #f43f5e 100%);
                    border-radius: 50%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin: 0 auto 2rem;
                    box-shadow: 0 10px 25px -5px rgba(239, 68, 68, 0.4);
                }}
                .icon svg {{
                    width: 40px;
                    height: 40px;
                    fill: none;
                    stroke: white;
                    stroke-width: 2.5;
                    stroke-linecap: round;
                    stroke-linejoin: round;
                }}
                h1 {{
                    font-size: 2.25rem;
                    font-weight: 800;
                    margin: 0 0 1rem;
                    background: linear-gradient(to right, #fca5a5, #f43f5e);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }}
                p {{
                    font-size: 1.1rem;
                    line-height: 1.6;
                    color: #94a3b8;
                    margin: 0 0 2rem;
                }}
                .timer {{
                    font-size: 1.25rem;
                    font-weight: 600;
                    background: rgba(244, 63, 94, 0.1);
                    border: 1px solid rgba(244, 63, 94, 0.2);
                    padding: 0.75rem 1.5rem;
                    border-radius: 12px;
                    display: inline-block;
                    color: #fda4af;
                    margin-bottom: 2rem;
                }}
                .btn {{
                    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
                    color: white;
                    border: none;
                    padding: 1rem 2rem;
                    font-size: 1rem;
                    font-weight: 600;
                    border-radius: 12px;
                    cursor: pointer;
                    text-decoration: none;
                    display: inline-block;
                    transition: all 0.2s ease;
                    box-shadow: 0 10px 20px -5px rgba(99, 102, 241, 0.4);
                }}
                .btn:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 15px 25px -5px rgba(99, 102, 241, 0.5);
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <div class="icon">
                    <svg viewBox="0 0 24 24">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                </div>
                <h1>Too Many Requests</h1>
                <p>You have made too many requests in a short period. To protect our system against automated scraping and abuse, your access has been temporarily limited.</p>
                <div class="timer">Please try again in <span id="countdown">{retry_after}</span> seconds.</div>
                <div>
                    <button class="btn" onclick="location.reload()">Refresh Page</button>
                </div>
            </div>
            <script>
                let seconds = {retry_after};
                const countdownEl = document.getElementById('countdown');
                const interval = setInterval(() => {{
                    seconds--;
                    if (seconds <= 0) {{
                        clearInterval(interval);
                        location.reload();
                    }} else {{
                        countdownEl.textContent = seconds;
                    }}
                }}, 1000);
            </script>
        </body>
        </html>
        """, 429

# Global security response headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    # Content-Security-Policy: strict nonce-based policy — no unsafe-inline.
    # A unique nonce is generated per request (set_csp_nonce above) and injected
    # into every <script> and <style> tag via the Jinja2 {{ csp_nonce }} variable.
    nonce = getattr(g, 'csp_nonce', '')
    nonce_src = f"'nonce-{nonce}'" if nonce else ''
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        f"script-src 'self' {nonce_src} cdn.jsdelivr.net; "
        f"style-src 'self' {nonce_src} cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; "
        "font-src 'self' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    # Return correlation ID in headers
    correlation_id = getattr(g, 'correlation_id', None)
    if correlation_id:
        response.headers['X-Correlation-ID'] = correlation_id
    return response




# Ensure FLASK_DEBUG can override only in non-production environments
if os.environ.get('FLASK_DEBUG') in ['1', 'true', 'True']:
    if flask_env != 'production':
        app.config['DEBUG'] = True
    else:
        app.config['DEBUG'] = False

# Fallback session secret key validation if missing
if not app.config.get('SECRET_KEY'):
    raise RuntimeError("SECRET_KEY environment variable is required but not set.")

# --- Logging Setup ---
# Create logs directory if it doesn't exist
os.makedirs(os.path.join(base_dir, 'logs'), exist_ok=True)
log_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
file_handler = RotatingFileHandler(os.path.join(base_dir, 'logs/app.log'), maxBytes=10240000, backupCount=10)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Set custom filters to strip database password or secret values if accidentally printed (secure logging)
class SensitiveDataFilter(logging.Filter):
    def filter(self, record):
        if not isinstance(record.msg, str):
            return True
        sensitive_keywords = ['password', 'secret_key', 'token', 'key']
        for keyword in sensitive_keywords:
            if keyword in record.msg.lower():
                record.msg = "[REDACTED SENSITIVE LOG]"
        return True

file_handler.addFilter(SensitiveDataFilter())
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Goat Farm app starting up')

# --- Session Inactivity / Idle Timeout Hook ---
@app.before_request
def check_session_timeout():
    # Allow asset serving, CSS/JS, and login/register without timeout checks
    if request.endpoint in ['static', 'login', 'register', 'logout']:
        return
        
    if 'user_id' in session:
        session.permanent = True
        now = datetime.utcnow()
        last_activity_str = session.get('last_activity')
        
        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                # Force logout if user is idle for more than 15 minutes
                if now - last_activity > timedelta(minutes=15):
                    session.clear()
                    flash('Your session has expired due to inactivity. Please log in again.', 'warning')
                    return redirect(url_for('auth.login'))
            except ValueError:
                pass
        session['last_activity'] = now.isoformat()

# --- File Upload Security Helpers ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
ALLOWED_MIMETYPES = {'image/png', 'image/jpeg', 'application/pdf'}
MAGIC_SIGNATURES = {
    'png': b'\x89PNG\r\n\x1a\n',
    'jpg': b'\xff\xd8\xff',
    'jpeg': b'\xff\xd8\xff',
    'pdf': b'%PDF'
}

def is_secure_file(file_stream, filename):
    if not filename or '.' not in filename:
        return False
        
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
        
    # Check mime type
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type or mime_type not in ALLOWED_MIMETYPES:
        return False
        
    # Read first few bytes for magic bytes check
    file_stream.seek(0)
    header = file_stream.read(16)
    file_stream.seek(0) # Reset stream position
    
    # Check header matches extension
    sig = MAGIC_SIGNATURES.get(ext)
    if sig and not header.startswith(sig):
        return False
        
    return True

def generate_secure_filename(filename):
    ext = filename.rsplit('.', 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"

# --- Error Handlers ---
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    app.logger.warning(f"CSRF Validation Failed: {e.description}")
    if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
        return jsonify({'success': False, 'error': f'CSRF token validation failed: {e.description}'}), 400
    return render_template('csrf_error.html', reason=e.description), 400

@app.errorhandler(403)
def forbidden_error(error):
    if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
        return jsonify({'success': False, 'error': 'Not Found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
@app.errorhandler(Exception)
def internal_error(error):
    # Log the traceback exception securely
    app.logger.error(f'Server Error: {error}', exc_info=True)
    if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
        return jsonify({'success': False, 'error': 'Internal Server Error'}), 500
    
    # In development mode, display original error/traceback
    if app.config.get('DEBUG'):
        raise error
    return render_template('500.html'), 500





def parse_date_safely(date_val):
    if not date_val:
        return None
    from datetime import date, datetime
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val
    if isinstance(date_val, str):
        date_str = date_val.strip()
        if not date_str:
            return None
        for fmt in ('%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y', '%m-%d-%Y'):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
    return None

def calculate_age_str(dob_str):
    if not dob_str:
        return 'N/A'
    try:
        dob = parse_date_safely(dob_str)
        if not dob:
            return 'N/A'
        from datetime import datetime
        today = datetime.now().date()
        if dob > today:
            return 'Newborn'
        
        years = today.year - dob.year
        months = today.month - dob.month
        days = today.day - dob.day
        
        if days < 0:
            months -= 1
            import calendar
            prev_month = today.month - 1 if today.month > 1 else 12
            prev_year = today.year if today.month > 1 else today.year - 1
            days_in_prev = calendar.monthrange(prev_year, prev_month)[1]
            days += days_in_prev
            
        if months < 0:
            years -= 1
            months += 12
            
        total_days_diff = (today - dob).days
        
        if total_days_diff < 30:
            # Under 30 days: show exact age in days till only 30
            return f"{total_days_diff} day{'s' if total_days_diff != 1 else ''}"
        elif years < 1:
            # Over 30 days, but under 12 months (less than 1 year): show months only (no days!)
            if months > 0:
                return f"{months} mo{'s' if months > 1 else ''}"
            return "1 mo"
        else:
            # 1 year or older: show years and current month (no days!)
            parts = []
            parts.append(f"{years} yr{'s' if years > 1 else ''}")
            if months > 0:
                parts.append(f"{months} mo{'s' if months > 1 else ''}")
            return ", ".join(parts)
    except Exception:
        return 'N/A'

def parse_dob_to_age_dict(dob_str):
    if not dob_str:
        return {'years': 0, 'months': 0, 'days': 0}
    try:
        dob = parse_date_safely(dob_str)
        if not dob:
            return {'years': 0, 'months': 0, 'days': 0}
        from datetime import datetime
        today = datetime.now().date()
        if dob > today:
            return {'years': 0, 'months': 0, 'days': 0}
        
        years = today.year - dob.year
        months = today.month - dob.month
        days = today.day - dob.day
        
        if days < 0:
            months -= 1
            days += 30
        if months < 0:
            years -= 1
            months += 12
            
        return {'years': max(0, years), 'months': max(0, months), 'days': max(0, days)}
    except Exception:
        return {'years': 0, 'months': 0, 'days': 0}

def calculate_kid_age_months(birth_date_str):
    if not birth_date_str:
        return 0.0
    try:
        birth_date = parse_date_safely(birth_date_str)
        if not birth_date:
            return 0.0
        from datetime import datetime
        today = datetime.now().date()
        if birth_date > today:
            return 0.0
        # Calculate difference in months with decimal fraction
        years_diff = today.year - birth_date.year
        months_diff = today.month - birth_date.month
        days_diff = today.day - birth_date.day
        
        total_months = years_diff * 12 + months_diff + (days_diff / 30.44)
        return round(max(0.0, total_months), 1)
    except Exception:
        return 0.0

def init_db():
    with get_db() as conn:
        old_autocommit = conn.conn.autocommit
        conn.conn.autocommit = True
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        # Add security-related columns to users dynamically
        def add_user_col(column, definition):
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} {definition}")
            except Exception:
                pass
        add_user_col("mfa_secret", "TEXT")
        add_user_col("mfa_enabled", "INTEGER DEFAULT 0")
        add_user_col("backup_codes", "TEXT")
        add_user_col("login_attempts", "INTEGER DEFAULT 0")
        add_user_col("locked_until", "TIMESTAMP DEFAULT NULL")
        add_user_col("password_history", "TEXT")
        add_user_col("is_admin", "INTEGER DEFAULT 0")

        conn.execute('''
            CREATE TABLE IF NOT EXISTS goats_data (
                id SERIAL PRIMARY KEY,
                tag_number TEXT NOT NULL,
                date DATE NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                notes TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS master_records (
                id SERIAL PRIMARY KEY,
                si_no TEXT, tag_no TEXT UNIQUE NOT NULL, breed TEXT, breed_percent TEXT,
                status TEXT, sold TEXT, expired TEXT, gender TEXT, purchase_date DATE,
                color TEXT, weight_kg REAL, purchase_amount REAL, insurance_date DATE,
                vaccination TEXT, vaccination_period TEXT, vaccination_next_due DATE, medicine TEXT, medicine_period TEXT,
                feed TEXT, feed_amount TEXT, mating_date DATE, mating_goat_no TEXT,
                goat_week_period TEXT, delivery_date DATE, new_goat_gender TEXT,
                new_goat_color TEXT, birth_weight REAL, selling_date DATE, selling_weight REAL,
                selling_price REAL, mortality_date DATE, mortality_weight REAL,
                mortality_reason TEXT, insurance_claim_amount REAL, insurance_inform_date DATE,
                insurance_claim_date DATE, dob DATE
            )
        ''')
        try:
            conn.execute('ALTER TABLE master_records ADD COLUMN IF NOT EXISTS vaccination_next_due DATE')
        except Exception:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sales_records (
                id SERIAL PRIMARY KEY,
                sr_no TEXT,
                tag_id TEXT NOT NULL,
                breed TEXT,
                breed_percent TEXT,
                gender TEXT,
                weight REAL,
                sold_price REAL,
                date_of_sale DATE,
                buyer_name TEXT,
                buyer_city TEXT,
                buyer_contact TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS other_sales_records (
                id SERIAL PRIMARY KEY,
                sr_no TEXT,
                item_name TEXT NOT NULL,
                quantity REAL,
                unit TEXT,
                price_per_unit REAL,
                total_amount REAL,
                date_of_sale DATE,
                buyer_name TEXT,
                buyer_city TEXT,
                buyer_contact TEXT,
                notes TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS medicine_records (
                id SERIAL PRIMARY KEY,
                sr_no TEXT,
                tag_no TEXT NOT NULL,
                breed TEXT,
                breed_percent TEXT,
                med1_date DATE, med1_name TEXT,
                vac1_date DATE, vac1_name TEXT,
                med2_date DATE, med2_name TEXT,
                med3_date DATE, med3_name TEXT,
                vac2_date DATE, vac2_name TEXT,
                medicine_amount REAL,
                vaccine_amount REAL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS mortality_records (
                id SERIAL PRIMARY KEY,
                sr_no TEXT,
                tag_id TEXT NOT NULL,
                breed TEXT,
                breed_percent TEXT,
                gender TEXT,
                birth_date DATE,
                expired_date DATE,
                total_age_month TEXT,
                weight_kgs REAL,
                insurance_inform_date DATE,
                insurance_claim_date DATE,
                current_value REAL,
                claim_amount REAL,
                cause_of_death TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feed_inventory (
                id SERIAL PRIMARY KEY,
                feed_name TEXT NOT NULL,
                opening_stock REAL DEFAULT 0,
                purchased_qty REAL DEFAULT 0,
                used_qty REAL DEFAULT 0,
                wastage_qty REAL DEFAULT 0,
                closing_stock REAL DEFAULT 0,
                unit TEXT,
                cost_per_unit REAL DEFAULT 0,
                total_cost REAL DEFAULT 0,
                purchase_date DATE,
                supplier TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS medicine_inventory (
                id SERIAL PRIMARY KEY,
                medicine_name TEXT NOT NULL,
                opening_stock REAL DEFAULT 0,
                purchased_qty REAL DEFAULT 0,
                used_qty REAL DEFAULT 0,
                wastage_qty REAL DEFAULT 0,
                closing_stock REAL DEFAULT 0,
                unit TEXT,
                cost_per_unit REAL DEFAULT 0,
                total_cost REAL DEFAULT 0,
                purchase_date DATE,
                supplier TEXT,
                alert_level REAL DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS vaccine_inventory (
                id SERIAL PRIMARY KEY,
                vaccine_name TEXT NOT NULL,
                opening_stock REAL DEFAULT 0,
                purchased_qty REAL DEFAULT 0,
                used_qty REAL DEFAULT 0,
                wastage_qty REAL DEFAULT 0,
                closing_stock REAL DEFAULT 0,
                unit TEXT,
                cost_per_unit REAL DEFAULT 0,
                total_cost REAL DEFAULT 0,
                purchase_date DATE,
                supplier TEXT,
                alert_level REAL DEFAULT 0
            )
        ''')
        try:
            conn.execute('ALTER TABLE feed_inventory ADD COLUMN IF NOT EXISTS wastage_qty REAL DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS kid_records (
                id SERIAL PRIMARY KEY,
                s_no TEXT,
                kid_id TEXT NOT NULL,
                breed TEXT,
                breed_percent TEXT,
                gender TEXT,
                color TEXT,
                litter_size INTEGER,
                birth_date DATE,
                age_month TEXT,
                birth_weight REAL,
                mother_id TEXT,
                father_id TEXT
            )
        ''')
        def add_column(table, column, definition):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
            except sqlite3.OperationalError:
                pass
                
        add_column("kid_records", "mother_id", "TEXT")
        add_column("kid_records", "father_id", "TEXT")
        add_column("kid_records", "insurance_policy_no", "TEXT")
        add_column("kid_records", "insurance_company", "TEXT")
        add_column("kid_records", "insurance_expiry", "DATE")
        add_column("kid_records", "insurance_amount", "REAL")

        try:
            conn.execute("ALTER TABLE master_records ADD COLUMN IF NOT EXISTS kit_status TEXT DEFAULT 'No'")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE master_records ADD COLUMN IF NOT EXISTS dob DATE")
        except sqlite3.OperationalError:
            pass

        add_column("feed_inventory", "purchase_id", "INTEGER")
        add_column("medicine_inventory", "purchase_id", "INTEGER")
        add_column("vaccine_inventory", "purchase_id", "INTEGER")
        
        # P&L Ledgers / Category Migrations
        add_column("purchases", "pnl_category", "TEXT DEFAULT 'Purchase'")
        add_column("feed_purchases", "pnl_category", "TEXT DEFAULT 'Purchase'")
        add_column("medicine_purchases", "pnl_category", "TEXT DEFAULT 'Purchase'")
        add_column("vaccine_purchases", "pnl_category", "TEXT DEFAULT 'Purchase'")
        add_column("equipment", "pnl_category", "TEXT DEFAULT 'Purchase'")
        add_column("sales_records", "pnl_category", "TEXT DEFAULT 'Sales'")
        add_column("other_sales_records", "pnl_category", "TEXT DEFAULT 'Sales'")
        add_column("expenses", "pnl_category", "TEXT DEFAULT 'Direct Expenses'")

        # Form details alignment for all vouchers
        add_column("purchases", "bill_date", "DATE")
        add_column("purchases", "bill_no", "TEXT")
        
        add_column("feed_purchases", "bill_date", "DATE")
        add_column("feed_purchases", "bill_no", "TEXT")
        add_column("feed_purchases", "notes", "TEXT")
        
        add_column("medicine_purchases", "bill_date", "DATE")
        add_column("medicine_purchases", "bill_no", "TEXT")
        add_column("medicine_purchases", "notes", "TEXT")
        
        add_column("vaccine_purchases", "bill_date", "DATE")
        add_column("vaccine_purchases", "bill_no", "TEXT")
        add_column("vaccine_purchases", "notes", "TEXT")
        
        # Voucher Particulars alignment
        add_column("purchases", "particular_id", "INTEGER")
        add_column("purchases", "particular_name", "TEXT")
        
        add_column("feed_purchases", "particular_id", "INTEGER")
        add_column("feed_purchases", "particular_name", "TEXT")
        
        add_column("medicine_purchases", "particular_id", "INTEGER")
        add_column("medicine_purchases", "particular_name", "TEXT")
        
        add_column("vaccine_purchases", "particular_id", "INTEGER")
        add_column("vaccine_purchases", "particular_name", "TEXT")
        
        # Expenses columns alignment with Other Vouchers
        add_column("expenses", "particular_id", "INTEGER")
        add_column("expenses", "bill_date", "DATE")
        add_column("expenses", "bill_no", "TEXT")
        add_column("expenses", "quantity", "REAL")
        add_column("expenses", "unit_id", "INTEGER")
        add_column("expenses", "unit_name", "TEXT")

        # Ensure equipment table has all required fields
        conn.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id SERIAL PRIMARY KEY,
                name TEXT,
                type TEXT,
                purchase_date DATE,
                purchase_cost REAL,
                supplier TEXT,
                status TEXT,
                notes TEXT,
                assigned_employee TEXT,
                service_due_date DATE
            )
        ''')
        add_column("equipment", "assigned_employee", "TEXT")
        add_column("equipment", "service_due_date", "DATE")

        conn.execute('''
            CREATE TABLE IF NOT EXISTS medicine_history (
                id SERIAL PRIMARY KEY,
                tag_no TEXT NOT NULL,
                doctor_name TEXT,
                consultation_date DATE NOT NULL,
                medicine_name TEXT NOT NULL,
                dose TEXT,
                quantity TEXT,
                cost REAL NOT NULL,
                notes TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS breeds (
                id SERIAL PRIMARY KEY,
                breed_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id SERIAL PRIMARY KEY,
                supplier_name TEXT UNIQUE NOT NULL,
                contact_person TEXT,
                phone TEXT,
                address TEXT,
                supplier_type TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feed_purchases (
                id SERIAL PRIMARY KEY,
                feed_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT,
                cost REAL NOT NULL,
                purchase_date DATE NOT NULL,
                supplier TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS medicine_purchases (
                id SERIAL PRIMARY KEY,
                medicine_name TEXT NOT NULL,
                dose_unit TEXT,
                quantity REAL NOT NULL,
                cost REAL NOT NULL,
                purchase_date DATE NOT NULL,
                supplier TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS vaccine_purchases (
                id SERIAL PRIMARY KEY,
                vaccine_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                cost REAL NOT NULL,
                purchase_date DATE NOT NULL,
                supplier TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                seller_name TEXT NOT NULL,
                invoice_details TEXT,
                purchase_date DATE NOT NULL,
                tag_id TEXT NOT NULL,
                price REAL NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS farm_info (
                id SERIAL PRIMARY KEY,
                farm_name TEXT,
                farm_address TEXT,
                farm_city TEXT,
                farm_phone TEXT,
                bank_name TEXT,
                account_number TEXT,
                ifsc_code TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS vaccine_records (
                id SERIAL PRIMARY KEY,
                sr_no TEXT,
                tag_no TEXT NOT NULL,
                vaccine_date DATE NOT NULL,
                vaccine_name TEXT NOT NULL,
                amount_spent REAL,
                additional_vaccines TEXT,
                additional_medicines TEXT,
                required_vaccines TEXT,
                required_medicines TEXT,
                notes TEXT
            )
        ''')
        try:
            conn.execute("ALTER TABLE vaccine_records ADD COLUMN IF NOT EXISTS next_due_date DATE")
        except sqlite3.OperationalError:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS doctor_details (
                id SERIAL PRIMARY KEY,
                doctor_name TEXT NOT NULL,
                specialization TEXT,
                contact_number TEXT,
                email TEXT,
                clinic_name TEXT,
                clinic_address TEXT,
                clinic_city TEXT,
                availability TEXT,
                registration_number TEXT,
                notes TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS eligible_to_sell (
                id SERIAL PRIMARY KEY,
                tag_id TEXT UNIQUE NOT NULL,
                tag_no TEXT NOT NULL,
                breed TEXT,
                gender TEXT,
                weight_kg REAL,
                date_added DATE,
                FOREIGN KEY (tag_id) REFERENCES master_records(tag_no)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_login_tracking (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                last_login_date DATE DEFAULT NULL,
                has_seen_weight_notification INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        # Add alert_level column to feed_inventory if it doesn't exist
        try:
            conn.execute('ALTER TABLE feed_inventory ADD COLUMN IF NOT EXISTS alert_level REAL DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        # Create batch_reminders table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS batch_reminders (
                id SERIAL PRIMARY KEY,
                batch_name TEXT NOT NULL,
                reminder_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                reminder_date DATE NOT NULL,
                is_completed INTEGER DEFAULT 0
            )
        ''')

        # ── EXPENSES MASTER TABLES ──────────────────────────────────────────────
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ledger_groups (
                id SERIAL PRIMARY KEY,
                group_name TEXT UNIQUE NOT NULL,
                description TEXT,
                group_type TEXT DEFAULT 'Expense'
            )
        ''')
        
        add_column("ledger_groups", "group_type", "TEXT DEFAULT 'Expense'")

        # Seed default ledger groups if empty or missing
        default_groups = [
            ('Direct Expenses', 'Direct expenses on farm operations', 'Expense'),
            ('Indirect Expenses', 'Indirect expenses/overheads', 'Expense'),
            ('Capital Account', 'Capital assets and investments', 'Expense'),
            ('Administrative Expenses', 'Admin and office expenses', 'Expense'),
            ('Selling Expenses', 'Marketing and selling costs', 'Expense'),
            ('Direct Income', 'Direct revenue from sales of goats, milk, manure, etc.', 'Income'),
            ('Indirect Income', 'Indirect revenue/interest/subsidies', 'Income'),
            ('Sales', 'Sales revenue from farm products', 'Income')
        ]
        for gname, gdesc, gtype in default_groups:
            try:
                row = conn.execute('SELECT 1 FROM ledger_groups WHERE group_name = ?', (gname,)).fetchone()
                if not row:
                    conn.execute('INSERT INTO ledger_groups (group_name, description, group_type) VALUES (?, ?, ?)', (gname, gdesc, gtype))
                else:
                    conn.execute('UPDATE ledger_groups SET group_type = ? WHERE group_name = ? AND group_type IS NULL', (gtype, gname))
            except Exception:
                pass

        conn.execute('''
            CREATE TABLE IF NOT EXISTS expense_ledgers (
                id SERIAL PRIMARY KEY,
                ledger_name TEXT UNIQUE NOT NULL,
                ledger_group TEXT DEFAULT 'Direct Expenses',
                description TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS expense_particulars (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                ledger_id INTEGER,
                description TEXT,
                FOREIGN KEY (ledger_id) REFERENCES expense_ledgers(id)
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS expense_units (
                id SERIAL PRIMARY KEY,
                unit_name TEXT UNIQUE NOT NULL,
                unit_symbol TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS other_vouchers (
                id SERIAL PRIMARY KEY,
                voucher_date DATE NOT NULL,
                supplier_name TEXT,
                particular_id INTEGER,
                particular_name TEXT,
                bill_date DATE,
                bill_no TEXT,
                quantity REAL,
                unit_id INTEGER,
                unit_name TEXT,
                amount REAL NOT NULL DEFAULT 0,
                notes TEXT,
                pnl_category TEXT DEFAULT 'Direct Expenses',
                FOREIGN KEY (particular_id) REFERENCES expense_particulars(id),
                FOREIGN KEY (unit_id) REFERENCES expense_units(id)
            )
        ''')

        # Seed default expense units if empty
        unit_count = conn.execute('SELECT COUNT(*) FROM expense_units').fetchone()[0]
        if unit_count == 0:
            default_units = [
                ('Nos', 'Nos'), ('KG', 'KG'), ('Grams', 'g'), ('Litres', 'L'),
                ('ML', 'ml'), ('Bags', 'Bags'), ('Tons', 'T'), ('Packets', 'Pkts'),
                ('Pairs', 'Pr'), ('Meters', 'm'), ('Sets', 'Sets'), ('Boxes', 'Box'),
                ('Bundles', 'Bnd'), ('Rolls', 'Rll'), ('Pieces', 'Pcs')
            ]
            for uname, usym in default_units:
                try:
                    conn.execute('INSERT INTO expense_units (unit_name, unit_symbol) VALUES (?, ?)', (uname, usym))
                except Exception:
                    pass

        # Seed default expense ledgers if empty
        ledger_count = conn.execute('SELECT COUNT(*) FROM expense_ledgers').fetchone()[0]
        if ledger_count == 0:
            default_ledgers = [
                ('Consumables Non Taxable', 'Direct Expenses', 'Day-to-day consumable items'),
                ('Electricity Charges', 'Indirect Expenses', 'Power and electricity bills'),
                ('Repair & Maintenance', 'Indirect Expenses', 'Farm equipment and structure repairs'),
                ('Transport & Logistics', 'Direct Expenses', 'Freight, vehicle fuel, logistics'),
                ('Veterinary Expenses', 'Direct Expenses', 'Vet visits and consultations'),
                ('Capital Assets', 'Capital Account', 'Machinery, equipment, infrastructure'),
                ('Miscellaneous Expenses', 'Indirect Expenses', 'General petty cash expenses'),
            ]
            for lname, lgrp, ldesc in default_ledgers:
                try:
                    conn.execute('INSERT INTO expense_ledgers (ledger_name, ledger_group, description) VALUES (?, ?, ?)', (lname, lgrp, ldesc))
                except Exception:
                    pass
        # Check if admin user exists
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not user:
            conn.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, 1)',
                         ('admin', generate_password_hash(admin_password)))
        else:
            conn.execute('UPDATE users SET is_admin = 1 WHERE username = ?', ('admin',))
            if not check_password_hash(user['password'], admin_password):
                conn.execute('UPDATE users SET password = ? WHERE username = ?',
                             (generate_password_hash(admin_password), 'admin'))


                         
        # Backfill si_no for master_records that have NULL or empty si_no
        null_records = conn.execute("SELECT id FROM master_records WHERE si_no IS NULL OR si_no = '' ORDER BY id ASC").fetchall()
        if null_records:
            res_si = conn.execute("SELECT MAX(CAST(si_no AS INTEGER)) FROM master_records WHERE si_no IS NOT NULL AND si_no != ''").fetchone()[0]
            current_si = res_si or 0
            for row in null_records:
                current_si += 1
                conn.execute("UPDATE master_records SET si_no = ? WHERE id = ?", (str(current_si), row[0]))
        conn.commit()
        conn.conn.autocommit = old_autocommit

db_connection_error = None

# Initialize DB on startup
try:
    with app.app_context():
        init_db()
except psycopg2.OperationalError as e:
    db_connection_error = str(e)
    print("\n" + "="*80)
    print("  DATABASE CONNECTION ERROR")
    print("="*80)
    print(f"Could not connect to PostgreSQL database: {e}")
    print("\nPlease verify your connection parameters in the '.env' file located in the 'goat_farm_app' directory.")
    print("Specifically, make sure 'DB_PASSWORD' matches your PostgreSQL user's password.")
    print("="*80 + "\n")

@app.before_request
def check_db_connection():
    from flask import g, request
    g.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
    
    global db_connection_error
    if db_connection_error:
        # Re-check the connection in case they updated the .env file
        try:
            # Re-read .env variables manually in case they changed
            from dotenv import load_dotenv
            load_dotenv(os.path.join(base_dir, '.env'), override=True)
            with get_db_connection() as conn:
                pass
            # If successful, reload database schema and clear the error flag
            with app.app_context():
                init_db()
                init_employee_tables()
            db_connection_error = None
            return # Proceed to the normal route
        except Exception as new_err:
            # Still failed, render error page
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Database Connection Error</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f3f4f6;
                        color: #1f2937;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }}
                    .card {{
                        background: white;
                        padding: 40px;
                        border-radius: 16px;
                        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                        max-width: 600px;
                        width: 90%;
                    }}
                    h1 {{
                        color: #e11d48;
                        font-size: 26px;
                        margin-top: 0;
                        border-bottom: 2px solid #ffe4e6;
                        padding-bottom: 15px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    }}
                    p {{
                        line-height: 1.6;
                        color: #4b5563;
                        font-size: 15px;
                    }}
                    .code-block {{
                        background-color: #1f2937;
                        color: #f9fafb;
                        padding: 18px;
                        border-radius: 8px;
                        font-family: 'Fira Code', 'Courier New', Courier, monospace;
                        font-size: 13px;
                        white-space: pre-wrap;
                        margin: 20px 0;
                        border-left: 4px solid #ef4444;
                        overflow-x: auto;
                    }}
                    .instruction {{
                        background-color: #f0f9ff;
                        border-left: 4px solid #0284c7;
                        padding: 20px;
                        margin: 20px 0;
                        border-radius: 0 12px 12px 0;
                    }}
                    .instruction h3 {{
                        margin-top: 0;
                        color: #0369a1;
                    }}
                    .instruction ol {{
                        margin-bottom: 0;
                        padding-left: 20px;
                    }}
                    .instruction li {{
                        margin: 10px 0;
                    }}
                    .highlight {{
                        font-weight: bold;
                        color: #0284c7;
                        background: #e0f2fe;
                        padding: 2px 6px;
                        border-radius: 4px;
                    }}
                    .button-container {{
                        margin-top: 25px;
                        text-align: right;
                    }}
                    .btn {{
                        background-color: #2563eb;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-weight: 600;
                        transition: background-color 0.2s;
                        text-decoration: none;
                        display: inline-block;
                    }}
                    .btn:hover {{
                        background-color: #1d4ed8;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>🔌 Database Connection Failed</h1>
                    <p>The web application server is running, but it cannot connect to your PostgreSQL database.</p>
                    
                    <h3>Technical Error Details:</h3>
                    <div class="code-block">{new_err}</div>
                    
                    <div class="instruction">
                        <h3>How to fix this:</h3>
                        <ol>
                            <li>Open the file <span class="highlight">goat_farm_app/.env</span> in your text editor.</li>
                            <li>Change <span class="highlight">DB_PASSWORD=postgres</span> to your actual PostgreSQL password.</li>
                            <li>Save the file and click <strong>"Retry Connection"</strong> below.</li>
                        </ol>
                    </div>
                    
                    <div class="button-container">
                        <button onclick="window.location.reload()" class="btn">Retry Connection</button>
                    </div>
                </div>
            </body>
            </html>
            """

@app.before_request
def require_login():
    allowed_routes = ['auth.login', 'static', 'goats', 'goat_detail', 'auth.mfa_verify_login']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('auth.login'))

@app.route('/')
@app.route('/dashboard')
def dashboard():
    db = get_db()
    
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search_q = request.args.get('search', '')
    
    # 1. Dashboard Metrics
    total_goats = db.execute("SELECT COUNT(*) FROM master_records WHERE status = 'Active'").fetchone()[0] or 0
    total_kids = db.execute("SELECT COUNT(*) FROM kid_records").fetchone()[0] or 0
    total_employees = db.execute("SELECT COUNT(*) FROM employees WHERE status = 'Active'").fetchone()[0] or 0
    
    # Income = sales + other sales
    goat_sales = db.execute("SELECT SUM(sold_price) FROM sales_records").fetchone()[0] or 0.0
    other_sales = db.execute("SELECT SUM(total_amount) FROM other_sales_records").fetchone()[0] or 0.0
    income = goat_sales + other_sales
    
    # Detailed expense calculation for dashboard
    # 1. Purchases (Goats, Feed, Med, Vac)
    exp_goat = db.execute("SELECT SUM(price) FROM purchases").fetchone()[0] or 0.0
    exp_feed = db.execute("SELECT SUM(total_cost) FROM feed_inventory").fetchone()[0] or 0.0
    exp_med = db.execute("SELECT SUM(cost) FROM medicine_purchases").fetchone()[0] or 0.0
    exp_vac = db.execute("SELECT SUM(cost) FROM vaccine_purchases").fetchone()[0] or 0.0
    
    # 2. Operations (Maintenance + Salaries + General Expenses)
    exp_salary = db.execute("SELECT SUM(net_salary) FROM salary_payments").fetchone()[0] or 0.0
    exp_maint = db.execute("SELECT SUM(service_cost) FROM equipment_services").fetchone()[0] or 0.0
    exp_gen = db.execute("SELECT SUM(amount) FROM expenses WHERE status='Approved' AND LOWER(COALESCE(category, '')) NOT LIKE '%labor%' AND LOWER(COALESCE(category, '')) NOT LIKE '%labour%'").fetchone()[0] or 0.0
    
    expense = exp_goat + exp_feed + exp_med + exp_vac + exp_salary + exp_maint + exp_gen
    profit = income - expense
    
    # 3. Weight Notification Logic (Disabled)
    heavy_goats = []
    show_weight_notification = False
    
    # 4. Goat Search Logic - Enhanced to support last 4, 3, or 2 digits and pattern matching
    searched_goat = None
    if search_q:
        search_q_stripped = search_q.strip()
        # 1. Exact Tag No Match
        searched_goat_raw = db.execute("SELECT * FROM master_records WHERE tag_no = ?", (search_q_stripped,)).fetchone()
        
        # 2. Suffix Match for 2, 3, or 4 digits
        if not searched_goat_raw and search_q_stripped.isdigit() and len(search_q_stripped) in [2, 3, 4]:
            searched_goat_raw = db.execute("SELECT * FROM master_records WHERE tag_no LIKE ? ORDER BY id DESC LIMIT 1", (f"%{search_q_stripped}",)).fetchone()
            
        # 3. Substring search if still not found
        if not searched_goat_raw:
            searched_goat_raw = db.execute("SELECT * FROM master_records WHERE tag_no LIKE ? OR breed LIKE ? ORDER BY id DESC LIMIT 1", 
                                      (f"%{search_q_stripped}%", f"%{search_q_stripped}%")).fetchone()
        
        if searched_goat_raw:
            searched_goat = dict(searched_goat_raw)
            searched_goat['age_str'] = calculate_age_str(searched_goat.get('dob'))
        
        # General list search for all matches
        goats_raw = db.execute("SELECT * FROM master_records WHERE tag_no LIKE ? OR breed LIKE ? ORDER BY id ASC", 
                          (f"%{search_q_stripped}%", f"%{search_q_stripped}%")).fetchall()
    else:
        goats_raw = db.execute("SELECT * FROM master_records ORDER BY id ASC LIMIT 10").fetchall()
        
    goats = []
    for g in goats_raw:
        g_dict = dict(g)
        g_dict['age_str'] = calculate_age_str(g_dict.get('dob'))
        goats.append(g_dict)
        
    return render_template('dashboard.html', 
        income=income, expense=expense, profit=profit, 
        total_goats=total_goats, total_kids=total_kids, total_employees=total_employees,
        goats=goats, search_q=search_q, searched_goat=searched_goat,
        heavy_goats=heavy_goats, show_weight_notification=show_weight_notification)

@app.route('/records')
def records():
    db = get_db()
    tag_search = request.args.get('tag_number', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = "SELECT * FROM goats_data WHERE 1=1"
    params = []
    
    if tag_search:
        query += " AND tag_number LIKE ?"
        params.append(f"%{tag_search}%")
    
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
        
    query += " ORDER BY date DESC"
    
    records = db.execute(query, params).fetchall()
    return render_template('records.html', records=records)

@app.route('/add_record', methods=['GET', 'POST'])
def add_record():
    if request.method == 'POST':
        tag_number = request.form['tag_number'].strip()
        date = request.form['date']
        category = request.form['category']
        type_val = request.form['type'].strip()
        amount = request.form['amount']
        notes = request.form.get('notes', '').strip()
        
        if not tag_number or not date or not category or not type_val or not amount:
            flash('All fields except notes are required.', 'danger')
            return render_template('add_record.html')
            
        try:
            amount = float(amount)
        except ValueError:
            flash('Amount must be a number.', 'danger')
            return render_template('add_record.html')
            
        db = get_db()
        db.execute('INSERT INTO goats_data (tag_number, date, category, type, amount, notes) VALUES (?, ?, ?, ?, ?, ?)',
                   (tag_number, date, category, type_val, amount, notes))
                   
        # Connected Sync Logic: If any goat purchase is recorded directly in Financial Records
        is_goat_purchase = False
        type_lower = type_val.lower()
        if category.lower() == 'expense' and ('purchase' in type_lower or 'buy' in type_lower or 'procure' in type_lower):
            # Exclude non-goat purchases
            if 'feed' not in type_lower and 'med' not in type_lower and 'vac' not in type_lower and 'equipment' not in type_lower and 'asset' not in type_lower:
                is_goat_purchase = True
                
        if is_goat_purchase:
            # 1. Sync to master_records (if it doesn't already exist)
            exists_master = db.execute('SELECT 1 FROM master_records WHERE tag_no = ?', (tag_number,)).fetchone()
            if not exists_master:
                res_si = db.execute('SELECT MAX(CAST(si_no AS INTEGER)) FROM master_records').fetchone()[0]
                next_si = (res_si or 0) + 1
                db.execute('''
                    INSERT INTO master_records (si_no, tag_no, purchase_date, purchase_amount, status, breed, gender, weight_kg, color)
                    VALUES (?, ?, ?, ?, ?, 'Active', 'Unknown', 'Unknown', 0.0, 'Unknown')
                ''', (str(next_si), tag_number, date, amount))
                
            # 2. Sync to purchases (if it doesn't already exist)
            exists_purch = db.execute('SELECT 1 FROM purchases WHERE tag_id = ?', (tag_number,)).fetchone()
            if not exists_purch:
                db.execute('''
                    INSERT INTO purchases (seller_name, invoice_details, purchase_date, tag_id, price)
                    VALUES (?, ?, ?, ?, ?)
                ''', ('Direct Entry Supplier', notes or 'Direct purchase entry', date, tag_number, amount))
                   
        db.commit()
        flash('Record added successfully.', 'success')
        return redirect(url_for('records'))
        
    return render_template('add_record.html')

@app.route('/edit_record/<int:id>', methods=['GET', 'POST'])
def edit_record(id):
    db = get_db()
    record = db.execute('SELECT * FROM goats_data WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('records'))
        
    if request.method == 'POST':
        tag_number = request.form['tag_number'].strip()
        date = request.form['date']
        category = request.form['category']
        type_val = request.form['type'].strip()
        amount = request.form['amount']
        notes = request.form.get('notes', '').strip()
        
        if not tag_number or not date or not category or not type_val or not amount:
            flash('All fields except notes are required.', 'danger')
            return render_template('edit_record.html', record=record)
            
        try:
            amount = float(amount)
        except ValueError:
            flash('Amount must be a number.', 'danger')
            return render_template('edit_record.html', record=record)
            
        db.execute('''UPDATE goats_data 
                      SET tag_number = ?, date = ?, category = ?, type = ?, amount = ?, notes = ? 
                      WHERE id = ?''',
                   (tag_number, date, category, type_val, amount, notes, id))
                   
        # Connected Sync Logic: If it is or was a goat purchase record
        is_goat_purchase = False
        type_lower = type_val.lower()
        if category.lower() == 'expense' and ('purchase' in type_lower or 'buy' in type_lower or 'procure' in type_lower):
            if 'feed' not in type_lower and 'med' not in type_lower and 'vac' not in type_lower and 'equipment' not in type_lower and 'asset' not in type_lower:
                is_goat_purchase = True
                
        old_type_lower = (record['type'] or '').lower()
        old_category_lower = (record['category'] or '').lower()
        was_goat_purchase = False
        if old_category_lower == 'expense' and ('purchase' in old_type_lower or 'buy' in old_type_lower or 'procure' in old_type_lower):
            if 'feed' not in old_type_lower and 'med' not in old_type_lower and 'vac' not in old_type_lower and 'equipment' not in old_type_lower and 'asset' not in old_type_lower:
                was_goat_purchase = True
                
        if is_goat_purchase or was_goat_purchase:
            old_tag = record['tag_number']
            
            if is_goat_purchase:
                # 1. Sync to master_records: update if old_tag exists in master, else insert new one
                exists_master = db.execute('SELECT 1 FROM master_records WHERE tag_no = ?', (old_tag,)).fetchone()
                if exists_master:
                    db.execute('''
                        UPDATE master_records 
                        SET tag_no = ?, purchase_date = ?, purchase_amount = ?
                        WHERE tag_no = ?
                    ''', (tag_number, date, amount, old_tag))
                else:
                    res_si = db.execute('SELECT MAX(CAST(si_no AS INTEGER)) FROM master_records').fetchone()[0]
                    next_si = (res_si or 0) + 1
                    db.execute('''
                        INSERT INTO master_records (si_no, tag_no, purchase_date, purchase_amount, status, breed, gender, weight_kg, color)
                        VALUES (?, ?, ?, ?, ?, 'Active', 'Unknown', 'Unknown', 0.0, 'Unknown')
                    ''', (str(next_si), tag_number, date, amount))
                
                # 2. Sync to purchases: update if old_tag exists in purchases, else insert new one
                exists_purch = db.execute('SELECT 1 FROM purchases WHERE tag_id = ?', (old_tag,)).fetchone()
                if exists_purch:
                    db.execute('''
                        UPDATE purchases 
                        SET seller_name = ?, invoice_details = ?, purchase_date = ?, tag_id = ?, price = ?
                        WHERE tag_id = ?
                    ''', ('Direct Entry Supplier', notes or 'Direct purchase entry', date, tag_number, amount, old_tag))
                else:
                    db.execute('''
                        INSERT INTO purchases (seller_name, invoice_details, purchase_date, tag_id, price)
                        VALUES (?, ?, ?, ?, ?)
                    ''', ('Direct Entry Supplier', notes or 'Direct purchase entry', date, tag_number, amount))
            else:
                # If it WAS a goat purchase but no longer is, remove from master register and purchases
                db.execute('DELETE FROM master_records WHERE tag_no = ?', (old_tag,))
                db.execute('DELETE FROM purchases WHERE tag_id = ?', (old_tag,))
                db.execute('DELETE FROM eligible_to_sell WHERE tag_id = ?', (old_tag,))
                   
        db.commit()
        flash('Record updated successfully.', 'success')
        return redirect(url_for('records'))
        
    return render_template('edit_record.html', record=record)

@app.route('/delete_record/<int:id>', methods=['POST'])
def delete_record(id):
    db = get_db()
    
    # Get record details before deleting
    record = db.execute('SELECT * FROM goats_data WHERE id = ?', (id,)).fetchone()
    if record:
        tag_number = record['tag_number']
        type_lower = (record['type'] or '').lower()
        category_lower = (record['category'] or '').lower()
        
        is_goat_purchase = False
        if category_lower == 'expense' and ('purchase' in type_lower or 'buy' in type_lower or 'procure' in type_lower):
            if 'feed' not in type_lower and 'med' not in type_lower and 'vac' not in type_lower and 'equipment' not in type_lower and 'asset' not in type_lower:
                is_goat_purchase = True
                
        db.execute('DELETE FROM goats_data WHERE id = ?', (id,))
        
        if is_goat_purchase:
            db.execute('DELETE FROM master_records WHERE tag_no = ?', (tag_number,))
            db.execute('DELETE FROM purchases WHERE tag_id = ?', (tag_number,))
            db.execute('DELETE FROM eligible_to_sell WHERE tag_id = ?', (tag_number,))
            
    db.commit()
    flash('Record deleted successfully.', 'success')
    return redirect(url_for('records'))

@app.route('/goats')
def goats():
    db = get_db()
    
    # Get search parameter
    search_q = request.args.get('search', '')
    
    # Get all goats from master records and their financial summary
    goats_summary_raw = db.execute('''
        WITH AllRecords AS (
            SELECT tag_number as tag_no, date, category, amount FROM goats_data
            UNION ALL
            SELECT tag_id as tag_no, date_of_sale as date, 'income' as category, sold_price as amount FROM sales_records WHERE date_of_sale IS NOT NULL
            UNION ALL
            SELECT tag_no, COALESCE(med1_date, vac1_date) as date, 'expense' as category, IFNULL(medicine_amount, 0) + IFNULL(vaccine_amount, 0) as amount FROM medicine_records WHERE (med1_date IS NOT NULL OR vac1_date IS NOT NULL)
            UNION ALL
            SELECT tag_id as tag_no, expired_date as date, 'expense' as category, IFNULL(current_value, 0) as amount FROM mortality_records WHERE expired_date IS NOT NULL
            UNION ALL
            SELECT tag_id as tag_no, insurance_claim_date as date, 'income' as category, IFNULL(claim_amount, 0) as amount FROM mortality_records WHERE insurance_claim_date IS NOT NULL
            UNION ALL
            SELECT tag_no, purchase_date as date, 'expense' as category, IFNULL(purchase_amount, 0) as amount FROM master_records WHERE purchase_date IS NOT NULL
        )
        SELECT m.tag_no as tag_number, 
               m.status,
               m.dob,
               COUNT(a.amount) as total_records,
               IFNULL(SUM(CASE WHEN a.category = 'income' THEN a.amount ELSE 0 END), 0) as total_income,
               IFNULL(SUM(CASE WHEN a.category = 'expense' THEN a.amount ELSE 0 END), 0) as total_expense
        FROM master_records m
        LEFT JOIN AllRecords a ON m.tag_no = a.tag_no
        GROUP BY m.tag_no, m.status, m.dob
        ORDER BY LENGTH(m.tag_no) ASC, m.tag_no ASC
    ''').fetchall()
    
    goats_summary = []
    for g in goats_summary_raw:
        g_dict = dict(g)
        g_dict['age_str'] = calculate_age_str(g_dict.get('dob'))
        goats_summary.append(g_dict)
    
    # Filter by search query if provided - Enhanced to support last 4 digits
    if search_q:
        search_q_stripped = search_q.strip()
        filtered_goats = []
        
        if len(search_q_stripped) == 4 and search_q_stripped.isdigit():
            # Search by last 4 digits
            for goat in goats_summary:
                if goat['tag_number'].endswith(search_q_stripped):
                    filtered_goats.append(goat)
        
        # Also search by full tag match or partial match
        for goat in goats_summary:
            if (search_q_stripped in goat['tag_number'] or 
                goat['tag_number'].endswith(search_q_stripped)):
                if goat not in filtered_goats:
                    filtered_goats.append(goat)
        
        goats_summary = filtered_goats
    
    return render_template('goats.html', goats=goats_summary, search_q=search_q)

@app.route('/goat/<tag_number>')
def goat_detail(tag_number):
    db = get_db()
    goat_raw = db.execute('SELECT * FROM master_records WHERE tag_no = ?', (tag_number,)).fetchone()
    if not goat_raw:
        flash('This goat record does not exist or has been deleted.', 'danger')
        return redirect(url_for('goats'))
    
    goat = dict(goat_raw)
    goat['age_str'] = calculate_age_str(goat.get('dob'))
    
    history_query = '''
    SELECT date, category, type, amount, notes FROM goats_data WHERE tag_number = ?
    UNION ALL
    SELECT date_of_sale as date, 'income' as category, 'Sales' as type, sold_price as amount, '' as notes FROM sales_records WHERE tag_id = ? AND date_of_sale IS NOT NULL
    UNION ALL
    SELECT COALESCE(med1_date, vac1_date) as date, 'expense' as category, 'Medicine/Vaccine' as type, IFNULL(medicine_amount, 0) + IFNULL(vaccine_amount, 0) as amount, '' as notes FROM medicine_records WHERE tag_no = ? AND (med1_date IS NOT NULL OR vac1_date IS NOT NULL)
    UNION ALL
    SELECT expired_date as date, 'expense' as category, 'Mortality Loss' as type, IFNULL(current_value, 0) as amount, cause_of_death as notes FROM mortality_records WHERE tag_id = ? AND expired_date IS NOT NULL
    UNION ALL
    SELECT insurance_claim_date as date, 'income' as category, 'Insurance Claim' as type, IFNULL(claim_amount, 0) as amount, '' as notes FROM mortality_records WHERE tag_id = ? AND insurance_claim_date IS NOT NULL
    UNION ALL
    SELECT purchase_date as date, 'expense' as category, 'Purchase' as type, IFNULL(purchase_amount, 0) as amount, '' as notes FROM master_records WHERE tag_no = ? AND purchase_date IS NOT NULL
    ORDER BY date DESC
    '''
    history = db.execute(history_query, (tag_number, tag_number, tag_number, tag_number, tag_number, tag_number)).fetchall()
    
    income = 0.0
    for r in history:
        if r['category'] == 'income':
            try:
                income += float(r['amount'] or 0.0)
            except (ValueError, TypeError):
                pass

    expense = 0.0
    for r in history:
        if r['category'] == 'expense':
            try:
                expense += float(r['amount'] or 0.0)
            except (ValueError, TypeError):
                pass
    profit = income - expense
    
    return render_template('goat_detail.html', tag_number=tag_number, goat=goat, income=income, expense=expense, profit=profit, history=history)

@app.route('/goat_batches')
def goat_batches():
    db = get_db()
    
    # 1. Fetch active goats from master records
    goats_raw = db.execute('''
        SELECT id, tag_no as identifier, breed, breed_percent, gender, color, weight_kg as weight, dob, purchase_date, status, 'Goat' as record_type
        FROM master_records 
        WHERE status = 'Active'
    ''').fetchall()
    
    # 2. Fetch kids from kid records
    kids_raw = db.execute('''
        SELECT id, kid_id as identifier, breed, breed_percent, gender, color, birth_weight as weight, birth_date as dob, birth_date as purchase_date, 'Active' as status, 'Kid' as record_type
        FROM kid_records
    ''').fetchall()
    
    # Combined list
    all_animals = []
    today = datetime.now().date()
    
    for row in goats_raw:
        animal = dict(row)
        dob_str = animal.get('dob')
        days_old = 9999
        dob_date = parse_date_safely(dob_str)
        if dob_date:
            days_old = (today - dob_date).days
        animal['days_old'] = days_old
        animal['age_str'] = calculate_age_str(dob_str)
        all_animals.append(animal)
        
    for row in kids_raw:
        animal = dict(row)
        dob_str = animal.get('dob')
        days_old = 9999
        dob_date = parse_date_safely(dob_str)
        if dob_date:
            days_old = (today - dob_date).days
        animal['days_old'] = days_old
        animal['age_str'] = calculate_age_str(dob_str)
        all_animals.append(animal)
        
    # Grouping
    batch_0_6m = []
    batch_6m_1y = []
    batch_1y_2y = []
    batch_above_2y = []
    
    for animal in all_animals:
        days = animal['days_old']
        if days <= 182:
            batch_0_6m.append(animal)
        elif days <= 365:
            batch_6m_1y.append(animal)
        elif days <= 730:
            batch_1y_2y.append(animal)
        else:
            batch_above_2y.append(animal)
            
    # Sort by age (youngest first)
    batch_0_6m.sort(key=lambda x: x['days_old'])
    batch_6m_1y.sort(key=lambda x: x['days_old'])
    batch_1y_2y.sort(key=lambda x: x['days_old'])
    batch_above_2y.sort(key=lambda x: x['days_old'])
    
    # Fetch active batch reminders
    reminders_raw = db.execute('SELECT * FROM batch_reminders WHERE is_completed = 0 ORDER BY reminder_date ASC').fetchall()
    reminders = [dict(r) for r in reminders_raw]
    
    return render_template('goat_batches.html',
                           batch_0_6m=batch_0_6m,
                           batch_6m_1y=batch_6m_1y,
                           batch_1y_2y=batch_1y_2y,
                           batch_above_2y=batch_above_2y,
                           reminders=reminders)

@app.route('/master_add', methods=['GET', 'POST'])
def master_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db = get_db()
        
        # Calculate DOB from entered Age
        try:
            from datetime import timedelta
            age_years = int(f.get('age_years') or 0)
            age_months = int(f.get('age_months') or 0)
            age_days = int(f.get('age_days') or 0)
            total_days = age_years * 365 + age_months * 30 + age_days
            dob_date = datetime.now().date() - timedelta(days=total_days)
            dob_str = dob_date.strftime('%Y-%m-%d')
        except Exception:
            dob_str = None

        db.execute('''
            INSERT INTO master_records (
                si_no, tag_no, breed, breed_percent, status, sold, expired, gender, purchase_date, color,
                weight_kg, purchase_amount, insurance_date, vaccination, vaccination_period, vaccination_next_due, medicine,
                medicine_period, feed, feed_amount, mating_date, mating_goat_no, goat_week_period,
                delivery_date, new_goat_gender, new_goat_color, birth_weight, selling_date,
                selling_weight, selling_price, mortality_date, mortality_weight, mortality_reason,
                insurance_claim_amount, insurance_inform_date, insurance_claim_date, kit_status, dob
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('si_no'), f.get('tag_no'), f.get('breed'), f.get('breed_percent'), f.get('status'),
            f.get('sold'), f.get('expired'), f.get('gender'), f.get('purchase_date'), f.get('color'),
            f.get('weight_kg'), f.get('purchase_amount'), f.get('insurance_date'), f.get('vaccination'),
            f.get('vaccination_period'), f.get('vaccination_next_due') or None, f.get('medicine'), f.get('medicine_period'), f.get('feed'),
            f.get('feed_amount'), f.get('mating_date'), f.get('mating_goat_no'), f.get('goat_week_period'),
            f.get('delivery_date'), f.get('new_goat_gender'), f.get('new_goat_color'), f.get('birth_weight'),
            f.get('selling_date') or None, f.get('selling_weight'), f.get('selling_price'), f.get('mortality_date') or None,
            f.get('mortality_weight'), f.get('mortality_reason'), f.get('insurance_claim_amount'),
            f.get('insurance_inform_date') or None, f.get('insurance_claim_date') or None, 1 if f.get('kit_status') else 0, dob_str
        ))
        # Connected Auto-Entry Generation Logic
        tag_no = f.get('tag_no')
        p_date = f.get('purchase_date') or datetime.now().strftime('%Y-%m-%d')
        purchase_amt = f.get('purchase_amount')
        
        # 1. Auto-Populate Goat Purchase disabled as requested (should not add purchase voucher/expense automatically)
        pass

        # 2. Auto-Populate Vaccination
        vaccine_name = f.get('vaccination')
        vaccine_period = f.get('vaccination_period') or p_date
        if vaccine_name and vaccine_name.strip() and vaccine_name.lower() != 'none':
            res_vac = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM vaccine_records').fetchone()[0]
            next_vac_sr = (res_vac or 0) + 1
            db.execute('''
                INSERT INTO vaccine_records (sr_no, tag_no, vaccine_date, vaccine_name, amount_spent, notes, next_due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (next_vac_sr, tag_no, vaccine_period, vaccine_name, 0.0, 'Auto-entered from Goat Creation', f.get('vaccination_next_due') or None))
            
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES (?, ?, 'expense', 'Vaccine', ?, ?)
            ''', (tag_no, vaccine_period, 0.0, f"Vaccination: {vaccine_name}"))

        # 3. Auto-Populate Medicine
        med_name = f.get('medicine')
        med_period = f.get('medicine_period') or p_date
        if med_name and med_name.strip() and med_name.lower() != 'none':
            db.execute('''
                INSERT INTO medicine_history (tag_no, doctor_name, consultation_date, medicine_name, dose, quantity, cost, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tag_no, 'Farm Doctor', med_period, med_name, '1 dose', 1.0, 0.0, 'Auto-entered from Goat Creation'))
            
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES (?, ?, 'expense', 'Medicine', ?, ?)
            ''', (tag_no, med_period, 0.0, f"Medicine: {med_name}"))

        # 4. Auto-Populate Feed Consumption & Inventory Adjustment
        feed_name = f.get('feed')
        feed_qty = f.get('feed_amount')
        if feed_name and feed_name.strip() and feed_qty:
            try:
                feed_qty_val = float(feed_qty)
                if feed_qty_val > 0:
                    last_feed = db.execute('SELECT closing_stock, cost_per_unit FROM feed_inventory WHERE feed_name = ? ORDER BY purchase_date DESC, id DESC LIMIT 1', (feed_name,)).fetchone()
                    opening = last_feed['closing_stock'] if last_feed else 0.0
                    cost_per_unit = last_feed['cost_per_unit'] if last_feed else 0.0
                    closing = max(0.0, opening - feed_qty_val)
                    cost = feed_qty_val * cost_per_unit
                    
                    db.execute('''
                        INSERT INTO feed_inventory (feed_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (feed_name, opening, 0.0, feed_qty_val, 0.0, closing, 'KG', cost_per_unit, cost, p_date, 'Auto-allocated from Goat Creation'))
                    
                    db.execute('''
                        INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                        VALUES (?, ?, 'expense', 'Feed', ?, ?)
                    ''', (tag_no, p_date, cost, f"Feed Consumption: {feed_name} ({feed_qty_val} KG)"))
            except ValueError:
                pass
        
        # 5. Connected Mortality Log Synchronization
        status = f.get('status')
        mortality_date = f.get('mortality_date')
        if status == 'Expired' or mortality_date:
            mort_exists = db.execute('SELECT 1 FROM mortality_records WHERE tag_id = ?', (tag_no,)).fetchone()
            if not mort_exists:
                res_mort = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM mortality_records').fetchone()[0]
                next_mort_sr = (res_mort or 0) + 1
                db.execute('''
                    INSERT INTO mortality_records (
                        sr_no, tag_id, breed, breed_percent, gender, expired_date, 
                        weight_kgs, insurance_inform_date, insurance_claim_date,
                        current_value, claim_amount, cause_of_death
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(next_mort_sr), tag_no, f.get('breed'), f.get('breed_percent'), f.get('gender'),
                    mortality_date or datetime.now().strftime('%Y-%m-%d'),
                    f.get('mortality_weight'), f.get('insurance_inform_date') or None, f.get('insurance_claim_date') or None,
                    f.get('purchase_amount') or 0.0, f.get('insurance_claim_amount') or 0.0, f.get('mortality_reason') or 'Unspecified'
                ))
        
        db.commit()
        flash('Master record added successfully and connected entries generated in other menus!', 'success')
        return redirect(url_for('master'))
    # Get next serial number
    res = db.execute('SELECT MAX(CAST(si_no AS INTEGER)) FROM master_records').fetchone()[0]
    next_sr = (res or 0) + 1
    return render_template('master_add.html', next_sr=next_sr)

@app.route('/master')
def master():
    db = get_db()
    tag_search = request.args.get('tag_no', '')
    if tag_search:
        records_raw = db.execute('SELECT * FROM master_records WHERE tag_no LIKE ? OR si_no LIKE ? ORDER BY id ASC', 
             (f"%{tag_search}%", f"%{tag_search}%")).fetchall()
    else:
        records_raw = db.execute('SELECT * FROM master_records ORDER BY id ASC').fetchall()
        
    records = []
    for r in records_raw:
        r_dict = dict(r)
        r_dict['age_str'] = calculate_age_str(r_dict.get('dob'))
        records.append(r_dict)
    return render_template('master.html', records=records)

@app.route('/sales')
def sales():
    db = get_db()
    count_goat = db.execute("SELECT COUNT(*) FROM sales_records").fetchone()[0] or 0
    sum_goat = db.execute("SELECT SUM(sold_price) FROM sales_records").fetchone()[0] or 0.0
    
    count_other = db.execute("SELECT COUNT(*) FROM other_sales_records").fetchone()[0] or 0
    sum_other = db.execute("SELECT SUM(total_amount) FROM other_sales_records").fetchone()[0] or 0.0
    
    return render_template('sales_dashboard.html', 
                           count_goat=count_goat, sum_goat=sum_goat,
                           count_other=count_other, sum_other=sum_other)

@app.route('/sales/<s_type>')
def sales_register(s_type):
    db = get_db()
    records = []
    
    if s_type == 'goat':
        raw_records = db.execute('SELECT * FROM sales_records ORDER BY date_of_sale DESC, id DESC').fetchall()
        groups = {}
        for r in raw_records:
            sr = r['sr_no']
            if sr not in groups:
                groups[sr] = []
            groups[sr].append(r)
            
        for sr, items in groups.items():
            first = items[0]
            total_amount = sum(float(item['sold_price'] or 0) for item in items)
            if len(items) == 1:
                title = f"Goat Sale - Tag: {first['tag_id']}"
                subtitle = f"Breed: {first['breed']} ({first['breed_percent']}%) | Weight: {first['weight']} kg | Buyer: {first['buyer_name']}"
                notes = f"Sold {first['gender']} Goat with Tag ID {first['tag_id']}."
            else:
                tags = ", ".join(item['tag_id'] for item in items)
                title = f"Goat Sale - Tags: {tags}"
                subtitle = f"{len(items)} Goats Sold | Buyer: {first['buyer_name']}"
                notes = f"Sold {len(items)} Goats: " + ", ".join(f"{item['tag_id']} ({item['gender']})" for item in items)
                
            records.append({
                'id': first['id'],
                'sr_no': sr,
                'title': title,
                'subtitle': subtitle,
                'date': first['date_of_sale'],
                'amount': total_amount,
                'buyer_name': first['buyer_name'],
                'buyer_city': first['buyer_city'],
                'buyer_contact': first['buyer_contact'],
                'notes': notes
            })
            
    elif s_type == 'other':
        raw_records = db.execute('SELECT * FROM other_sales_records ORDER BY date_of_sale DESC, id DESC').fetchall()
        groups = {}
        for r in raw_records:
            sr = r['sr_no']
            if sr not in groups:
                groups[sr] = []
            groups[sr].append(r)
            
        for sr, items in groups.items():
            first = items[0]
            total_amount = sum(float(item['total_amount'] or 0) for item in items)
            if len(items) == 1:
                title = f"Other Sale: {first['item_name']}"
                subtitle = f"Quantity: {first['quantity']} {first['unit']} @ ₹{first['price_per_unit']}/unit | Buyer: {first['buyer_name']}"
                notes = first['notes']
            else:
                item_descs = ", ".join(f"{item['item_name']} (x{item['quantity']})" for item in items)
                title = f"Other Sale: {len(items)} items"
                subtitle = f"Items: {item_descs} | Buyer: {first['buyer_name']}"
                notes = "; ".join(filter(None, [item['notes'] for item in items])) or "Multiple items sold."
                
            records.append({
                'id': first['id'],
                'sr_no': sr,
                'title': title,
                'subtitle': subtitle,
                'date': first['date_of_sale'],
                'amount': total_amount,
                'buyer_name': first['buyer_name'],
                'buyer_city': first['buyer_city'],
                'buyer_contact': first['buyer_contact'],
                'notes': notes
            })
            
    # Group month-wise
    grouped = {}
    for r in records:
        try:
            dt = datetime.strptime(r['date'], '%Y-%m-%d')
            month_str = dt.strftime('%B %Y')
        except Exception:
            month_str = "Unknown Date"
        if month_str not in grouped:
            grouped[month_str] = []
        grouped[month_str].append(r)
        
    return render_template('sales_register.html', s_type=s_type, grouped_records=grouped)

@app.route('/sales/<s_type>/add', methods=['GET', 'POST'])
def sales_add(s_type):
    db = get_db()
    ledger_groups = db.execute("SELECT * FROM ledger_groups WHERE group_type = 'Income' ORDER BY group_name").fetchall()
    today_str = datetime.now().strftime('%Y-%m-%d')
    res = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM sales_records').fetchone()[0]
    res_other = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM other_sales_records').fetchone()[0]
    next_sr = str(max(res or 0, res_other or 0) + 1)
    
    if request.method == 'POST':
        f = request.form
        p_date = f.get('date_of_sale') or today_str
        pnl_cat = f.get('pnl_category', 'Sales')
        buyer_name = f.get('buyer_name')
        buyer_city = f.get('buyer_city')
        buyer_contact = f.get('buyer_contact')
        
        if s_type == 'goat':
            tag_ids = f.getlist('tag_id')
            breeds = f.getlist('breed')
            breed_percents = f.getlist('breed_percent')
            genders = f.getlist('gender')
            weights = f.getlist('weight')
            sold_prices = f.getlist('sold_price')
            
            # Validate tags exist in master_records and weight >= 25 kg
            for i, tag_id in enumerate(tag_ids):
                if not tag_id.strip():
                    continue
                goat = db.execute('SELECT weight_kg FROM master_records WHERE tag_no = ?', (tag_id.strip(),)).fetchone()
                if not goat:
                    flash(f'No goat exists with tag id "{tag_id}"', 'danger')
                    goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' ORDER BY tag_no ASC").fetchall()
                    return render_template('sales_form.html', s_type=s_type, action='Create', today=today_str, next_sr=next_sr, record=f, goats=goats, ledger_groups=ledger_groups)
                
                # Retrieve the weight entered in the form or default to the database weight
                form_weight_str = weights[i].strip() if i < len(weights) else ""
                if form_weight_str:
                    try:
                        sold_weight = float(form_weight_str)
                    except ValueError:
                        sold_weight = 0.0
                else:
                    sold_weight = goat['weight_kg'] if goat['weight_kg'] is not None else 0.0


            
            inserted_count = 0
            for i in range(len(tag_ids)):
                t_id = tag_ids[i].strip()
                if not t_id:
                    continue
                
                breed = breeds[i] if i < len(breeds) else ""
                breed_pct = breed_percents[i] if i < len(breed_percents) else ""
                gender = genders[i] if i < len(genders) else ""
                weight = float(weights[i] or 0) if i < len(weights) and weights[i] else 0.0
                price = float(sold_prices[i] or 0) if i < len(sold_prices) and sold_prices[i] else 0.0
                
                db.execute('''
                    INSERT INTO sales_records (
                        sr_no, tag_id, breed, breed_percent, gender, weight, sold_price, 
                        date_of_sale, buyer_name, buyer_city, buyer_contact, pnl_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    next_sr, t_id, breed, breed_pct, gender, weight, price,
                    p_date, buyer_name, buyer_city, buyer_contact, pnl_cat
                ))
                
                # Update status and selling weight in master_records
                db.execute("UPDATE master_records SET status = 'Sold', selling_date = ?, selling_price = ?, selling_weight = ? WHERE tag_no = ?",
                           (p_date, price, weight, t_id))
                
                # Remove from eligible_to_sell list
                db.execute("DELETE FROM eligible_to_sell WHERE tag_id = ?", (t_id,))
                inserted_count += 1
                
            if inserted_count == 0:
                flash('No items were added.', 'warning')
                return redirect(url_for('sales_register', s_type=s_type))
                
        elif s_type == 'other':
            item_names = f.getlist('item_name')
            quantities = f.getlist('quantity')
            units = f.getlist('unit')
            price_per_units = f.getlist('price_per_unit')
            notes = f.get('notes', '')
            
            inserted_count = 0
            for i in range(len(item_names)):
                name = item_names[i].strip()
                if not name:
                    continue
                
                qty = float(quantities[i] or 0) if i < len(quantities) and quantities[i] else 0.0
                unit = units[i] if i < len(units) else ""
                price_per = float(price_per_units[i] or 0) if i < len(price_per_units) and price_per_units[i] else 0.0
                total = qty * price_per
                
                db.execute('''
                    INSERT INTO other_sales_records (
                        sr_no, item_name, quantity, unit, price_per_unit, total_amount,
                        date_of_sale, buyer_name, buyer_city, buyer_contact, notes, pnl_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    next_sr, name, qty, unit, price_per, total,
                    p_date, buyer_name, buyer_city, buyer_contact, notes, pnl_cat
                ))
                inserted_count += 1
                
            if inserted_count == 0:
                flash('No items were added.', 'warning')
                return redirect(url_for('sales_register', s_type=s_type))
                
        db.commit()
        flash('Sales record added successfully!', 'success')
        return redirect(url_for('sales_register', s_type=s_type))
        
    goats = []
    if s_type == 'goat':
        goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' ORDER BY tag_no ASC").fetchall()
    return render_template('sales_form.html', s_type=s_type, action='Create', today=today_str, next_sr=next_sr, goats=goats, ledger_groups=ledger_groups)

@app.route('/sales/<s_type>/edit/<int:id>', methods=['GET', 'POST'])
def sales_edit(s_type, id):
    db = get_db()
    ledger_groups = db.execute("SELECT * FROM ledger_groups WHERE group_type = 'Income' ORDER BY group_name").fetchall()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if s_type == 'goat':
        record_raw = db.execute('SELECT * FROM sales_records WHERE id = ?', (id,)).fetchone()
        if not record_raw:
            flash('Record not found.', 'danger')
            return redirect(url_for('sales_register', s_type=s_type))
        sr_no = record_raw['sr_no']
        records_list = db.execute('SELECT * FROM sales_records WHERE sr_no = ? ORDER BY id ASC', (sr_no,)).fetchall()
        record = dict(record_raw)
        record['pnl_category'] = record_raw['pnl_category'] or 'Sales'
    else:
        record_raw = db.execute('SELECT * FROM other_sales_records WHERE id = ?', (id,)).fetchone()
        if not record_raw:
            flash('Record not found.', 'danger')
            return redirect(url_for('sales_register', s_type=s_type))
        sr_no = record_raw['sr_no']
        records_list = db.execute('SELECT * FROM other_sales_records WHERE sr_no = ? ORDER BY id ASC', (sr_no,)).fetchall()
        record = dict(record_raw)
        record['pnl_category'] = record_raw['pnl_category'] or 'Sales'
        
    if request.method == 'POST':
        f = request.form
        p_date = f.get('date_of_sale') or today_str
        pnl_cat = f.get('pnl_category', 'Sales')
        buyer_name = f.get('buyer_name')
        buyer_city = f.get('buyer_city')
        buyer_contact = f.get('buyer_contact')
        
        if s_type == 'goat':
            tag_ids = f.getlist('tag_id')
            breeds = f.getlist('breed')
            breed_percents = f.getlist('breed_percent')
            genders = f.getlist('gender')
            weights = f.getlist('weight')
            sold_prices = f.getlist('sold_price')
            
            # Validate tags exist in master_records and weight >= 25 kg
            for i, tag_id in enumerate(tag_ids):
                if not tag_id.strip():
                    continue
                goat = db.execute('SELECT weight_kg FROM master_records WHERE tag_no = ?', (tag_id.strip(),)).fetchone()
                if not goat:
                    flash(f'No goat exists with tag id "{tag_id}"', 'danger')
                    goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' OR tag_no IN (SELECT tag_id FROM sales_records WHERE sr_no = ?) ORDER BY tag_no ASC", (sr_no,)).fetchall()
                    return render_template('sales_form.html', s_type=s_type, action='Edit', today=today_str, record=record, records_list=records_list, goats=goats, ledger_groups=ledger_groups)
                
                # Retrieve the weight entered in the form or default to the database weight
                form_weight_str = weights[i].strip() if i < len(weights) else ""
                if form_weight_str:
                    try:
                        sold_weight = float(form_weight_str)
                    except ValueError:
                        sold_weight = 0.0
                else:
                    sold_weight = goat['weight_kg'] if goat['weight_kg'] is not None else 0.0


            
            # Revert old goats to Active status first
            old_goats = db.execute('SELECT tag_id FROM sales_records WHERE sr_no = ?', (sr_no,)).fetchall()
            for og in old_goats:
                db.execute("UPDATE master_records SET status = 'Active', selling_date = NULL, selling_price = NULL, selling_weight = NULL WHERE tag_no = ?", (og['tag_id'],))
                db.execute("INSERT OR IGNORE INTO eligible_to_sell (tag_id, tag_no, breed, gender, weight_kg) SELECT tag_no, tag_no, breed, gender, weight_kg FROM master_records WHERE tag_no = ?", (og['tag_id'],))
            
            # Delete old sales rows
            db.execute('DELETE FROM sales_records WHERE sr_no = ?', (sr_no,))
            
            # Insert new sales rows
            inserted_count = 0
            for i in range(len(tag_ids)):
                t_id = tag_ids[i].strip()
                if not t_id:
                    continue
                
                breed = breeds[i] if i < len(breeds) else ""
                breed_pct = breed_percents[i] if i < len(breed_percents) else ""
                gender = genders[i] if i < len(genders) else ""
                weight = float(weights[i] or 0) if i < len(weights) and weights[i] else 0.0
                price = float(sold_prices[i] or 0) if i < len(sold_prices) and sold_prices[i] else 0.0
                
                db.execute('''
                    INSERT INTO sales_records (
                        sr_no, tag_id, breed, breed_percent, gender, weight, sold_price, 
                        date_of_sale, buyer_name, buyer_city, buyer_contact, pnl_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sr_no, t_id, breed, breed_pct, gender, weight, price,
                    p_date, buyer_name, buyer_city, buyer_contact, pnl_cat
                ))
                
                # Update status and selling weight in master records
                db.execute("UPDATE master_records SET status = 'Sold', selling_date = ?, selling_price = ?, selling_weight = ? WHERE tag_no = ?",
                           (p_date, price, weight, t_id))
                
                # Remove from eligible_to_sell
                db.execute("DELETE FROM eligible_to_sell WHERE tag_id = ?", (t_id,))
                inserted_count += 1
                
            if inserted_count == 0:
                flash('All items were removed. Record deleted.', 'warning')
                db.commit()
                return redirect(url_for('sales_register', s_type=s_type))
                
        elif s_type == 'other':
            item_names = f.getlist('item_name')
            quantities = f.getlist('quantity')
            units = f.getlist('unit')
            price_per_units = f.getlist('price_per_unit')
            notes = f.get('notes', '')
            
            # Delete old rows
            db.execute('DELETE FROM other_sales_records WHERE sr_no = ?', (sr_no,))
            
            # Insert new rows
            inserted_count = 0
            for i in range(len(item_names)):
                name = item_names[i].strip()
                if not name:
                    continue
                
                qty = float(quantities[i] or 0) if i < len(quantities) and quantities[i] else 0.0
                unit = units[i] if i < len(units) else ""
                price_per = float(price_per_units[i] or 0) if i < len(price_per_units) and price_per_units[i] else 0.0
                total = qty * price_per
                
                db.execute('''
                    INSERT INTO other_sales_records (
                        sr_no, item_name, quantity, unit, price_per_unit, total_amount,
                        date_of_sale, buyer_name, buyer_city, buyer_contact, notes, pnl_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sr_no, name, qty, unit, price_per, total,
                    p_date, buyer_name, buyer_city, buyer_contact, notes, pnl_cat
                ))
                inserted_count += 1
                
            if inserted_count == 0:
                flash('All items were removed. Record deleted.', 'warning')
                db.commit()
                return redirect(url_for('sales_register', s_type=s_type))
                
        db.commit()
        flash('Sales record updated successfully!', 'success')
        return redirect(url_for('sales_register', s_type=s_type))
        
    goats = []
    if s_type == 'goat':
        goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' OR tag_no IN (SELECT tag_id FROM sales_records WHERE sr_no = ?) ORDER BY tag_no ASC", (sr_no,)).fetchall()
    return render_template('sales_form.html', s_type=s_type, action='Edit', record=record, records_list=records_list, today=today_str, goats=goats, ledger_groups=ledger_groups)

@app.route('/sales/<s_type>/delete/<int:id>', methods=['POST'])
def sales_delete(s_type, id):
    db = get_db()
    if s_type == 'goat':
        record = db.execute('SELECT sr_no FROM sales_records WHERE id = ?', (id,)).fetchone()
        if record:
            sr_no = record['sr_no']
            # Revert statuses of all goats under this sr_no
            goats = db.execute('SELECT tag_id FROM sales_records WHERE sr_no = ?', (sr_no,)).fetchall()
            for g in goats:
                tag_id = g['tag_id']
                db.execute("UPDATE master_records SET status = 'Active', selling_date = NULL, selling_price = NULL WHERE tag_no = ?", (tag_id,))
                db.execute("INSERT OR IGNORE INTO eligible_to_sell (tag_id, tag_no, breed, gender, weight_kg) SELECT tag_no, tag_no, breed, gender, weight_kg FROM master_records WHERE tag_no = ?", (tag_id,))
            db.execute('DELETE FROM sales_records WHERE sr_no = ?', (sr_no,))
    elif s_type == 'other':
        record = db.execute('SELECT sr_no FROM other_sales_records WHERE id = ?', (id,)).fetchone()
        if record:
            sr_no = record['sr_no']
            db.execute('DELETE FROM other_sales_records WHERE sr_no = ?', (sr_no,))
            
    db.commit()
    flash('Sales record deleted successfully!', 'success')
    return redirect(url_for('sales_register', s_type=s_type))

@app.route('/sales/<s_type>/invoice/<int:id>')
def sales_invoice(s_type, id):
    db = get_db()
    settings_raw = db.execute('SELECT * FROM farm_settings WHERE id = 1').fetchone()
    if settings_raw:
        farm_info = {
            'farm_name': settings_raw['farm_name'] or 'Ranga Farms',
            'farm_address': settings_raw['address'] or 'Aandigounder Street, Pachapalayam, Perur',
            'farm_city': 'Coimbatore 641010',
            'farm_phone': settings_raw['phone'] or '',
            'bank_name': settings_raw['bank_name'] or 'State Bank of India',
            'account_number': settings_raw['account_no'] or '39820129381',
            'account_no': settings_raw['account_no'] or '39820129381',
            'ifsc_code': settings_raw['ifsc_code'] or 'SBIN0001234',
            'gst_no': settings_raw['gst_no'] or ''
        }
    else:
        legacy_raw = db.execute('SELECT * FROM farm_info WHERE id = 1').fetchone()
        if legacy_raw:
            farm_info = {
                'farm_name': legacy_raw['farm_name'],
                'farm_address': legacy_raw['farm_address'],
                'farm_city': legacy_raw['farm_city'],
                'farm_phone': legacy_raw['farm_phone'],
                'bank_name': legacy_raw['bank_name'],
                'account_number': legacy_raw['account_number'],
                'account_no': legacy_raw['account_number'],
                'ifsc_code': legacy_raw['ifsc_code'],
                'gst_no': ''
            }
        else:
            farm_info = {
                'farm_name': 'Ranga Farms',
                'farm_address': 'Aandigounder Street, Pachapalayam, Perur',
                'farm_city': 'Coimbatore 641010',
                'farm_phone': '',
                'bank_name': 'State Bank of India',
                'account_number': '39820129381',
                'account_no': '39820129381',
                'ifsc_code': 'SBIN0001234',
                'gst_no': ''
            }
        
    if s_type == 'goat':
        sale_raw = db.execute('SELECT * FROM sales_records WHERE id = ?', (id,)).fetchone()
        if not sale_raw:
            flash('Sales record not found.', 'danger')
            return redirect(url_for('sales_register', s_type=s_type))
        sr_no = sale_raw['sr_no']
        sales_list = db.execute('SELECT * FROM sales_records WHERE sr_no = ? ORDER BY id ASC', (sr_no,)).fetchall()
        
        total_amount = sum(float(item['sold_price'] or 0) for item in sales_list)
        sale = {
            'id': sale_raw['id'],
            'sr_no': sr_no,
            'date_of_sale': sale_raw['date_of_sale'],
            'buyer_name': sale_raw['buyer_name'],
            'buyer_city': sale_raw['buyer_city'],
            'buyer_contact': sale_raw['buyer_contact'],
            'total_amount': total_amount
        }
    else:
        sale_raw = db.execute('SELECT * FROM other_sales_records WHERE id = ?', (id,)).fetchone()
        if not sale_raw:
            flash('Sales record not found.', 'danger')
            return redirect(url_for('sales_register', s_type=s_type))
        sr_no = sale_raw['sr_no']
        sales_list = db.execute('SELECT * FROM other_sales_records WHERE sr_no = ? ORDER BY id ASC', (sr_no,)).fetchall()
        
        total_amount = sum(float(item['total_amount'] or 0) for item in sales_list)
        sale = {
            'id': sale_raw['id'],
            'sr_no': sr_no,
            'date_of_sale': sale_raw['date_of_sale'],
            'buyer_name': sale_raw['buyer_name'],
            'buyer_city': sale_raw['buyer_city'],
            'buyer_contact': sale_raw['buyer_contact'],
            'total_amount': total_amount,
            'notes': sale_raw['notes']
        }
        
    return render_template('sales_invoice.html', sale=sale, sales_list=sales_list, farm_info=farm_info, s_type=s_type, current_date=datetime.now())

@app.route('/sales/<s_type>/invoice_txt/<int:id>')
def sales_invoice_txt(s_type, id):
    from io import BytesIO
    db = get_db()
    settings_raw = db.execute('SELECT * FROM farm_settings WHERE id = 1').fetchone()
    if settings_raw:
        farm_info = {
            'farm_name': settings_raw['farm_name'] or 'Ranga Farms',
            'farm_address': settings_raw['address'] or 'Aandigounder Street, Pachapalayam, Perur',
            'farm_phone': settings_raw['phone'] or '',
            'bank_name': settings_raw['bank_name'] or 'State Bank of India',
            'account_no': settings_raw['account_no'] or '39820129381',
            'ifsc_code': settings_raw['ifsc_code'] or 'SBIN0001234'
        }
    else:
        legacy_raw = db.execute('SELECT * FROM farm_info WHERE id = 1').fetchone()
        if legacy_raw:
            farm_info = {
                'farm_name': legacy_raw['farm_name'],
                'farm_address': legacy_raw['farm_address'],
                'farm_phone': legacy_raw['farm_phone'],
                'bank_name': legacy_raw['bank_name'],
                'account_no': legacy_raw['account_number'],
                'ifsc_code': legacy_raw['ifsc_code']
            }
        else:
            farm_info = {
                'farm_name': 'Ranga Farms',
                'farm_address': 'Aandigounder Street, Pachapalayam, Perur',
                'farm_phone': '',
                'bank_name': 'State Bank of India',
                'account_no': '39820129381',
                'ifsc_code': 'SBIN0001234'
            }
    
    if s_type == 'goat':
        sale_raw = db.execute('SELECT * FROM sales_records WHERE id = ?', (id,)).fetchone()
        if not sale_raw:
            flash('Sales record not found.', 'danger')
            return redirect(url_for('sales_register', s_type=s_type))
        sr_no = sale_raw['sr_no']
        sales_list = db.execute('SELECT * FROM sales_records WHERE sr_no = ? ORDER BY id ASC', (sr_no,)).fetchall()
    else:
        sale_raw = db.execute('SELECT * FROM other_sales_records WHERE id = ?', (id,)).fetchone()
        if not sale_raw:
            flash('Sales record not found.', 'danger')
            return redirect(url_for('sales_register', s_type=s_type))
        sr_no = sale_raw['sr_no']
        sales_list = db.execute('SELECT * FROM other_sales_records WHERE sr_no = ? ORDER BY id ASC', (sr_no,)).fetchall()
        
    # Generate text bill
    bill_text = ""
    bill_text += "=" * 70 + "\n"
    bill_text += f"{(farm_info['farm_name'] if farm_info and farm_info['farm_name'] else 'Ranga Farms'):^70}\n"
    bill_text += "=" * 70 + "\n"
    bill_text += f"{('SALES INVOICE (' + s_type.upper() + ')'):^70}\n"
    bill_text += "=" * 70 + "\n\n"
    
    bill_text += f"Invoice #: INV-{s_type.upper()[:3]}-{sale_raw['id']}\n"
    bill_text += f"Bill/Serial #: {sr_no}\n"
    bill_text += f"Date of Issue: {sale_raw['date_of_sale']}\n\n"
    
    bill_text += "BILL TO:\n"
    bill_text += f"Buyer Name: {sale_raw['buyer_name'] or 'Walk-in Customer'}\n"
    bill_text += f"City: {sale_raw['buyer_city'] or 'N/A'}\n"
    bill_text += f"Contact: {sale_raw['buyer_contact'] or 'N/A'}\n\n"
    
    bill_text += "-" * 70 + "\n"
    if s_type == 'goat':
        bill_text += f"{'Tag ID':<15} | {'Breed':<20} | {'Gender':<10} | {'Weight':<10} | {'Price (INR)':<10}\n"
        bill_text += "-" * 70 + "\n"
        total_amount = 0.0
        for item in sales_list:
            gender_short = "Male" if item['gender'] in ['Male', 'M', 'm'] else "Female"
            breed_str = f"{item['breed']} ({item['breed_percent']}%)"
            bill_text += f"{item['tag_id']:<15} | {breed_str[:20]:<20} | {gender_short:<10} | {str(item['weight']) + ' kg':<10} | {item['sold_price']:<10.2f}\n"
            total_amount += float(item['sold_price'] or 0)
    else:
        bill_text += f"{'Item Description':<35} | {'Quantity':<15} | {'Rate (INR)':<10} | {'Total (INR)':<10}\n"
        bill_text += "-" * 70 + "\n"
        total_amount = 0.0
        for item in sales_list:
            qty_unit = f"{item['quantity']} {item['unit']}"
            bill_text += f"{item['item_name'][:35]:<35} | {qty_unit:<15} | {item['price_per_unit']:<10.2f} | {item['total_amount']:<10.2f}\n"
            total_amount += float(item['total_amount'] or 0)
            
    bill_text += "-" * 70 + "\n"
    bill_text += f"{'TOTAL AMOUNT':<57} | INR {total_amount:.2f}\n"
    bill_text += "=" * 70 + "\n\n"
    
    if s_type == 'other' and sale_raw['notes']:
        bill_text += f"Remarks / Notes:\n{sale_raw['notes']}\n\n"
        
    bill_text += "Thank you for your business!\n"
    
    # Download file response
    mem_file = BytesIO()
    mem_file.write(bill_text.encode('utf-8'))
    mem_file.seek(0)
    
    return send_file(
        mem_file,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"Invoice_{s_type}_{sale_raw['id']}.txt"
    )

@app.route('/sales_add')
def old_sales_add():
    return redirect(url_for('sales_add', s_type='goat'))


@app.route('/medicine_add', methods=['GET', 'POST'])
def medicine_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db.execute('''
            INSERT INTO medicine_history (
                tag_no, doctor_name, consultation_date, medicine_name, dose, quantity, cost, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('tag_no'), f.get('doctor_name'), f.get('consultation_date'), f.get('medicine_name'),
            f.get('dose'), f.get('quantity'), f.get('cost') or 0.0, f.get('notes')
        ))
        db.commit()
        flash('Medicine record added successfully!', 'success')
        return redirect(url_for('medicine'))
    
    goats = db.execute('SELECT tag_no FROM master_records ORDER BY tag_no ASC').fetchall()
    doctors = db.execute('SELECT doctor_name FROM doctor_details ORDER BY doctor_name ASC').fetchall()
    return render_template('medicine_add.html', goats=goats, doctors=doctors)

@app.route('/medicine')
def medicine():
    db = get_db()
    tag_search = request.args.get('tag_no', '')
    month_filter = request.args.get('month', '') # Format: YYYY-MM
    
    q = 'SELECT * FROM medicine_history WHERE 1=1'
    p = []
    
    if tag_search:
        q += ' AND tag_no LIKE ?'
        p.append(f"%{tag_search}%")
        
    if month_filter:
        q += " AND TO_CHAR(consultation_date, 'YYYY-MM') = ?"
        p.append(month_filter)
        
    q += ' ORDER BY consultation_date ASC, id ASC'
    records = db.execute(q, p).fetchall()
    
    # Calculate totals
    total_cost = sum(r['cost'] for r in records)
    
    return render_template('medicine.html', records=records, total_cost=total_cost, month_filter=month_filter, tag_search=tag_search)

@app.route('/mortality_add', methods=['GET', 'POST'])
def mortality_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('''
            INSERT INTO mortality_records (
                sr_no, tag_id, breed, breed_percent, gender, birth_date, expired_date, 
                total_age_month, weight_kgs, insurance_inform_date, insurance_claim_date,
                current_value, claim_amount, cause_of_death
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('sr_no'), f.get('tag_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'),
            f.get('birth_date'), f.get('expired_date'), f.get('total_age_month'), f.get('weight_kgs'), 
            f.get('insurance_inform_date'), f.get('insurance_claim_date'), f.get('current_value'), 
            f.get('claim_amount'), f.get('cause_of_death')
        ))
        
        # LOGIC FIX: Update status in master_records
        db.execute("UPDATE master_records SET status = 'Expired', mortality_date = ?, mortality_reason = ? WHERE tag_no = ?",
                   (f.get('expired_date'), f.get('cause_of_death'), f.get('tag_id')))
        
        db.commit()
        flash('Mortality record added successfully!', 'success')
        return redirect(url_for('mortality'))
    db = get_db()
    res = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM mortality_records').fetchone()[0]
    next_sr = (res or 0) + 1
    return render_template('mortality_add.html', next_sr=next_sr)

@app.route('/mortality')
def mortality():
    db = get_db()
    tag_search = request.args.get('tag_id', '')
    if tag_search:
        records = db.execute('SELECT * FROM mortality_records WHERE tag_id LIKE ? ORDER BY CAST(sr_no AS INTEGER) ASC', 
             (f"%{tag_search}%",)).fetchall()
    else:
        records = db.execute('SELECT * FROM mortality_records ORDER BY CAST(sr_no AS INTEGER) ASC').fetchall()
    return render_template('mortality.html', records=records)

@app.route('/get_feed_stock/<feed_name>')
def get_feed_stock(feed_name):
    db = get_db()
    last_record = db.execute('''
        SELECT closing_stock, cost_per_unit, total_cost, opening_stock FROM feed_inventory 
        WHERE feed_name = ? 
        ORDER BY purchase_date DESC, id DESC LIMIT 1
    ''', (feed_name,)).fetchone()
    
    stock = last_record['closing_stock'] if last_record else 0.0
    rate = 0.0
    if last_record:
        if last_record['cost_per_unit'] and last_record['cost_per_unit'] > 0:
            rate = last_record['cost_per_unit']
        elif last_record['total_cost'] and last_record['opening_stock'] and last_record['opening_stock'] > 0:
            rate = last_record['total_cost'] / last_record['opening_stock']
            
    return {'closing_stock': stock, 'rate_per_kg': rate}

def get_goats_in_batch(batch_number):
    db = get_db()
    # Fetch active goats
    goats_raw = db.execute('''
        SELECT id, tag_no as identifier, breed, breed_percent, gender, color, weight_kg as weight, dob, purchase_date, status, 'Goat' as record_type
        FROM master_records 
        WHERE status = 'Active'
    ''').fetchall()
    
    # Fetch kids
    kids_raw = db.execute('''
        SELECT id, kid_id as identifier, breed, breed_percent, gender, color, birth_weight as weight, birth_date as dob, birth_date as purchase_date, 'Active' as status, 'Kid' as record_type
        FROM kid_records
    ''').fetchall()
    
    all_animals = []
    today = datetime.now().date()
    
    for row in goats_raw:
        animal = dict(row)
        dob_str = animal.get('dob')
        days_old = 9999
        dob_date = parse_date_safely(dob_str)
        if dob_date:
            days_old = (today - dob_date).days
        animal['days_old'] = days_old
        all_animals.append(animal)
        
    for row in kids_raw:
        animal = dict(row)
        dob_str = animal.get('dob')
        days_old = 9999
        dob_date = parse_date_safely(dob_str)
        if dob_date:
            days_old = (today - dob_date).days
        animal['days_old'] = days_old
        all_animals.append(animal)
        
    batch_animals = []
    for animal in all_animals:
        days = animal['days_old']
        if batch_number == 1 and days <= 182:
            batch_animals.append(animal)
        elif batch_number == 2 and 182 < days <= 365:
            batch_animals.append(animal)
        elif batch_number == 3 and 365 < days <= 730:
            batch_animals.append(animal)
        elif batch_number == 4 and days > 730:
            batch_animals.append(animal)
            
    return batch_animals

@app.route('/feed')
def feed():
    db = get_db()
    
    # Fetch feed inventory
    feed_records = db.execute("SELECT * FROM feed_inventory ORDER BY id ASC").fetchall()
    feed_names = db.execute("SELECT DISTINCT feed_name FROM feed_inventory").fetchall()
    feed_stocks = {}
    for row in feed_names:
        name = row['feed_name']
        last = db.execute("SELECT closing_stock, unit FROM feed_inventory WHERE feed_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        if last:
            feed_stocks[name] = {
                'closing_stock': last['closing_stock'],
                'unit': last['unit'] or 'KG'
            }
            
    # Fetch medicine inventory
    medicine_records = db.execute("SELECT * FROM medicine_inventory ORDER BY id ASC").fetchall()
    med_names = db.execute("SELECT DISTINCT medicine_name FROM medicine_inventory").fetchall()
    med_stocks = {}
    for row in med_names:
        name = row['medicine_name']
        last = db.execute("SELECT closing_stock, unit FROM medicine_inventory WHERE medicine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        if last:
            med_stocks[name] = {
                'closing_stock': last['closing_stock'],
                'unit': last['unit'] or 'Doses'
            }
            
    # Fetch vaccine inventory
    vaccine_records = db.execute("SELECT * FROM vaccine_inventory ORDER BY id ASC").fetchall()
    vac_names = db.execute("SELECT DISTINCT vaccine_name FROM vaccine_inventory").fetchall()
    vac_stocks = {}
    for row in vac_names:
        name = row['vaccine_name']
        last = db.execute("SELECT closing_stock, unit FROM vaccine_inventory WHERE vaccine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        if last:
            vac_stocks[name] = {
                'closing_stock': last['closing_stock'],
                'unit': last['unit'] or 'Doses'
            }
            
    # Calculate counts in the 4 batches
    goats_raw = db.execute("SELECT dob FROM master_records WHERE status = 'Active'").fetchall()
    kids_raw = db.execute("SELECT birth_date as dob FROM kid_records").fetchall()
    
    today = datetime.now().date()
    batch_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for row in goats_raw:
        dob_str = row['dob']
        dob_date = parse_date_safely(dob_str)
        if dob_date:
            days = (today - dob_date).days
            if days <= 182:
                batch_counts[1] += 1
            elif days <= 365:
                batch_counts[2] += 1
            elif days <= 730:
                batch_counts[3] += 1
            else:
                batch_counts[4] += 1
                
    for row in kids_raw:
        dob_str = row['dob']
        dob_date = parse_date_safely(dob_str)
        if dob_date:
            days = (today - dob_date).days
            if days <= 182:
                batch_counts[1] += 1
            elif days <= 365:
                batch_counts[2] += 1
            elif days <= 730:
                batch_counts[3] += 1
            else:
                batch_counts[4] += 1
                
    return render_template('feed.html',
                           feed_records=feed_records,
                           feed_stocks=feed_stocks,
                           medicine_records=medicine_records,
                           med_stocks=med_stocks,
                           vaccine_records=vaccine_records,
                           vac_stocks=vac_stocks,
                           batch_counts=batch_counts)

@app.route('/stock_inventory')
def stock_inventory():
    db = get_db()
    
    # Fetch feed inventory
    feed_records = db.execute("SELECT * FROM feed_inventory ORDER BY id ASC").fetchall()
    feed_names = db.execute("SELECT DISTINCT feed_name FROM feed_inventory").fetchall()
    feed_stocks = {}
    for row in feed_names:
        name = row['feed_name']
        last = db.execute("SELECT closing_stock, unit, alert_level FROM feed_inventory WHERE feed_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        if last:
            feed_stocks[name] = {
                'closing_stock': last['closing_stock'],
                'unit': last['unit'] or 'KG',
                'alert_level': last['alert_level'] or 0.0
            }
            
    # Fetch medicine inventory
    medicine_records = db.execute("SELECT * FROM medicine_inventory ORDER BY id ASC").fetchall()
    med_names = db.execute("SELECT DISTINCT medicine_name FROM medicine_inventory").fetchall()
    med_stocks = {}
    for row in med_names:
        name = row['medicine_name']
        last = db.execute("SELECT closing_stock, unit, alert_level FROM medicine_inventory WHERE medicine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        if last:
            med_stocks[name] = {
                'closing_stock': last['closing_stock'],
                'unit': last['unit'] or 'Doses',
                'alert_level': last['alert_level'] or 0.0
            }
            
    # Fetch vaccine inventory
    vaccine_records = db.execute("SELECT * FROM vaccine_inventory ORDER BY id ASC").fetchall()
    vac_names = db.execute("SELECT DISTINCT vaccine_name FROM vaccine_inventory").fetchall()
    vac_stocks = {}
    for row in vac_names:
        name = row['vaccine_name']
        last = db.execute("SELECT closing_stock, unit, alert_level FROM vaccine_inventory WHERE vaccine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
        if last:
            vac_stocks[name] = {
                'closing_stock': last['closing_stock'],
                'unit': last['unit'] or 'Doses',
                'alert_level': last['alert_level'] or 0.0
            }

    return render_template('stock_inventory.html',
                           feed_records=feed_records,
                           feed_stocks=feed_stocks,
                           medicine_records=medicine_records,
                           med_stocks=med_stocks,
                           vaccine_records=vaccine_records,
                           vac_stocks=vac_stocks)

@app.route('/buy_stock', methods=['POST'])
def buy_stock():
    db = get_db()
    f = request.form
    item_type = f.get('item_type') # 'feed', 'medicine', 'vaccine'
    item_name = f.get('item_name', '').strip()
    qty = float(f.get('quantity') or 0)
    cost = float(f.get('cost') or 0)
    supplier = f.get('supplier', '').strip() or 'Market'
    date_str = f.get('purchase_date') or datetime.now().strftime('%Y-%m-%d')
    unit = f.get('unit') or ('KG' if item_type == 'feed' else 'Doses')
    
    # Process optional alert level setting from buy stock modal
    alert_limit = f.get('alert_limit')
    if alert_limit:
        try:
            alert_limit = float(alert_limit)
        except ValueError:
            alert_limit = 0.0
    else:
        # Fall back to existing alert level for this item if available
        if item_type == 'feed':
            existing = db.execute("SELECT alert_level FROM feed_inventory WHERE feed_name = ? AND alert_level IS NOT NULL ORDER BY id DESC LIMIT 1", (item_name,)).fetchone()
            alert_limit = existing['alert_level'] if existing else 0.0
        elif item_type == 'medicine':
            existing = db.execute("SELECT alert_level FROM medicine_inventory WHERE medicine_name = ? AND alert_level IS NOT NULL ORDER BY id DESC LIMIT 1", (item_name,)).fetchone()
            alert_limit = existing['alert_level'] if existing else 0.0
        elif item_type == 'vaccine':
            existing = db.execute("SELECT alert_level FROM vaccine_inventory WHERE vaccine_name = ? AND alert_level IS NOT NULL ORDER BY id DESC LIMIT 1", (item_name,)).fetchone()
            alert_limit = existing['alert_level'] if existing else 0.0
        else:
            alert_limit = 0.0

    if not item_name or qty <= 0 or cost <= 0:
        flash('Invalid purchase details! Please fill all fields with correct numbers.', 'danger')
        return redirect(url_for('feed'))
        
    if item_type == 'feed':
        cursor = db.execute('''
            INSERT INTO feed_purchases (feed_name, quantity, unit, cost, purchase_date, supplier)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (item_name, qty, unit, cost, date_str, supplier))
        purchase_id = cursor.lastrowid
        
        last = db.execute("SELECT closing_stock FROM feed_inventory WHERE feed_name = ? ORDER BY id DESC LIMIT 1", (item_name,)).fetchone()
        opening = last['closing_stock'] if last else 0.0
        closing = opening + qty
        cost_per_unit = cost / qty if qty > 0 else 0.0
        
        db.execute('''
            INSERT INTO feed_inventory (feed_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id, alert_level)
            VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_name, opening, qty, closing, unit, cost_per_unit, cost, date_str, supplier, purchase_id, alert_limit))
        
    elif item_type == 'medicine':
        cursor = db.execute('''
            INSERT INTO medicine_purchases (medicine_name, dose_unit, quantity, cost, purchase_date, supplier)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (item_name, 'ml', qty, cost, date_str, supplier))
        purchase_id = cursor.lastrowid
        
        last = db.execute("SELECT closing_stock FROM medicine_inventory WHERE medicine_name = ? ORDER BY id DESC LIMIT 1", (item_name,)).fetchone()
        opening = last['closing_stock'] if last else 0.0
        closing = opening + qty
        cost_per_unit = cost / qty if qty > 0 else 0.0
        
        db.execute('''
            INSERT INTO medicine_inventory (medicine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id, alert_level)
            VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_name, opening, qty, closing, unit, cost_per_unit, cost, date_str, supplier, purchase_id, alert_limit))
        
    elif item_type == 'vaccine':
        cursor = db.execute('''
            INSERT INTO vaccine_purchases (vaccine_name, quantity, cost, purchase_date, supplier)
            VALUES (?, ?, ?, ?, ?)
        ''', (item_name, qty, cost, date_str, supplier))
        purchase_id = cursor.lastrowid
        
        last = db.execute("SELECT closing_stock FROM vaccine_inventory WHERE vaccine_name = ? ORDER BY id DESC LIMIT 1", (item_name,)).fetchone()
        opening = last['closing_stock'] if last else 0.0
        closing = opening + qty
        cost_per_unit = cost / qty if qty > 0 else 0.0
        
        db.execute('''
            INSERT INTO vaccine_inventory (vaccine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id, alert_level)
            VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_name, opening, qty, closing, unit, cost_per_unit, cost, date_str, supplier, purchase_id, alert_limit))
        
    # Logical expenses recording
    desc = f"Purchased {qty} {unit} of {item_name} from {supplier}"
    db.execute('''
        INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
        VALUES ('All', ?, 'expense', ?, ?, ?)
    ''', (date_str, item_type.capitalize(), cost, desc))
    
    db.execute('''
        INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
        VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid')
    ''', (item_type.capitalize() + ' Purchase', cost, date_str, desc, supplier))
    
    db.commit()
    flash(f'{item_type.capitalize()} purchase of {qty} {unit} recorded and marked in Expenses successfully!', 'success')
    return redirect(url_for('feed'))

@app.route('/consume_feed', methods=['POST'])
def consume_feed():
    db = get_db()
    f = request.form
    feed_name = f.get('feed_name')
    batch_num = int(f.get('batch_num') or 1)
    qty = float(f.get('quantity') or 0)
    wastage = float(f.get('wastage') or 0)
    date_str = f.get('date') or datetime.now().strftime('%Y-%m-%d')
    
    if not feed_name or qty <= 0:
        flash('Invalid feed allocation details!', 'danger')
        return redirect(url_for('feed'))
        
    last = db.execute("SELECT closing_stock, cost_per_unit, unit FROM feed_inventory WHERE feed_name = ? ORDER BY id DESC LIMIT 1", (feed_name,)).fetchone()
    opening = last['closing_stock'] if last else 0.0
    cost_per_unit = last['cost_per_unit'] if last else 0.0
    unit = last['unit'] or 'KG'
    
    if opening <= 0:
        flash(f'No stock available for {feed_name}! Please buy feed first.', 'danger')
        return redirect(url_for('feed'))
        
    closing = max(0.0, opening - qty)
    
    db.execute('''
        INSERT INTO feed_inventory (feed_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier)
        VALUES (?, ?, 0.0, ?, ?, ?, ?, ?, 0.0, ?, ?)
    ''', (feed_name, opening, qty, wastage, closing, unit, cost_per_unit, date_str, f"Allocated to Batch {batch_num}"))
    
    db.commit()
    flash(f'Gave {qty} {unit} feed to Batch {batch_num} successfully!', 'success')
    return redirect(url_for('feed'))

@app.route('/consume_medicine', methods=['POST'])
def consume_medicine():
    db = get_db()
    f = request.form
    med_name = f.get('medicine_name')
    batch_num = int(f.get('batch_num') or 1)
    qty = float(f.get('quantity') or 0)
    date_str = f.get('date') or datetime.now().strftime('%Y-%m-%d')
    notes = f.get('notes') or f"Allocated to Batch {batch_num}"
    
    if not med_name or qty <= 0:
        flash('Invalid medicine allocation details!', 'danger')
        return redirect(url_for('feed'))
        
    last = db.execute("SELECT closing_stock, cost_per_unit, unit FROM medicine_inventory WHERE medicine_name = ? ORDER BY id DESC LIMIT 1", (med_name,)).fetchone()
    opening = last['closing_stock'] if last else 0.0
    cost_per_unit = last['cost_per_unit'] if last else 0.0
    unit = last['unit'] or 'Doses'
    
    if opening <= 0:
        flash(f'No stock available for {med_name}! Please buy medicine first.', 'danger')
        return redirect(url_for('feed'))
        
    closing = max(0.0, opening - qty)
    
    db.execute('''
        INSERT INTO medicine_inventory (medicine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier)
        VALUES (?, ?, 0.0, ?, 0.0, ?, ?, ?, 0.0, ?, ?)
    ''', (med_name, opening, qty, closing, unit, cost_per_unit, date_str, f"Allocated to Batch {batch_num}"))
    
    goats = get_goats_in_batch(batch_num)
    for g in goats:
        tag = g['identifier']
        db.execute('''
            INSERT INTO medicine_history (tag_no, doctor_name, consultation_date, medicine_name, dose, quantity, cost, notes)
            VALUES (?, 'Farm Doctor', ?, ?, ?, ?, 0.0, ?)
        ''', (tag, date_str, med_name, f"{qty / len(goats):.2f} {unit}" if goats else f"1 {unit}", f"{qty / len(goats):.2f}" if goats else "1", notes))
        
        db.execute('''
            INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
            VALUES (?, ?, 'expense', 'Medicine', 0.0, ?)
        ''', (tag, date_str, f"Batch {batch_num} Medication: {med_name}"))
        
    db.commit()
    flash(f'Successfully allocated {qty} {unit} medicine to Batch {batch_num} and logged for {len(goats)} goats!', 'success')
    return redirect(url_for('feed'))

@app.route('/consume_vaccine', methods=['POST'])
def consume_vaccine():
    db = get_db()
    f = request.form
    vac_name = f.get('vaccine_name')
    batch_num = int(f.get('batch_num') or 1)
    qty = float(f.get('quantity') or 0)
    date_str = f.get('date') or datetime.now().strftime('%Y-%m-%d')
    next_due = f.get('next_due_date') or None
    notes = f.get('notes') or f"Allocated to Batch {batch_num}"
    
    if not vac_name or qty <= 0:
        flash('Invalid vaccine allocation details!', 'danger')
        return redirect(url_for('feed'))
        
    last = db.execute("SELECT closing_stock, cost_per_unit, unit FROM vaccine_inventory WHERE vaccine_name = ? ORDER BY id DESC LIMIT 1", (vac_name,)).fetchone()
    opening = last['closing_stock'] if last else 0.0
    cost_per_unit = last['cost_per_unit'] if last else 0.0
    unit = last['unit'] or 'Doses'
    
    if opening <= 0:
        flash(f'No stock available for {vac_name}! Please buy vaccine first.', 'danger')
        return redirect(url_for('feed'))
        
    closing = max(0.0, opening - qty)
    
    db.execute('''
        INSERT INTO vaccine_inventory (vaccine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier)
        VALUES (?, ?, 0.0, ?, 0.0, ?, ?, ?, 0.0, ?, ?)
    ''', (vac_name, opening, qty, closing, unit, cost_per_unit, date_str, f"Allocated to Batch {batch_num}"))
    
    goats = get_goats_in_batch(batch_num)
    for g in goats:
        tag = g['identifier']
        db.execute('''
            INSERT INTO vaccine_records (sr_no, tag_no, vaccine_date, vaccine_name, amount_spent, notes, next_due_date)
            VALUES (?, ?, ?, ?, 0.0, ?, ?)
        ''', (f"B{batch_num}", tag, date_str, vac_name, notes, next_due))
        
        db.execute('''
            INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
            VALUES (?, ?, 'expense', 'Vaccine', 0.0, ?)
        ''', (tag, date_str, f"Batch {batch_num} Vaccination: {vac_name}"))
        
    db.commit()
    flash(f'Successfully allocated {qty} {unit} vaccine to Batch {batch_num} and logged for {len(goats)} goats!', 'success')
    return redirect(url_for('feed'))

@app.route('/feed_add', methods=['GET', 'POST'])
def feed_add():
    return redirect(url_for('feed'))

@app.route('/kid_add', methods=['GET', 'POST'])
def kid_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db = get_db()
        
        # Validate parent IDs in master_records
        mother_id = f.get('mother_id', '').strip()
        father_id = f.get('father_id', '').strip()

        if mother_id and father_id and mother_id == father_id:
            flash("Validation failed: Mother and Father cannot have the same Tag ID!", 'danger')
            return redirect(url_for('kid_add'))

        # Check mother ID
        if mother_id:
            mother = db.execute('SELECT tag_no, gender FROM master_records WHERE tag_no = ?', (mother_id,)).fetchone()
            if not mother:
                flash(f"Validation failed: Mother Tag ID '{mother_id}' does not exist in Master Records!", 'danger')
                return redirect(url_for('kid_add'))
            elif mother['gender'] == 'Male':
                flash(f"Validation failed: Mother Tag ID '{mother_id}' is a Male goat! A male goat cannot be registered as a Mother.", 'danger')
                return redirect(url_for('kid_add'))

        # Check father ID
        if father_id:
            father = db.execute('SELECT tag_no, gender FROM master_records WHERE tag_no = ?', (father_id,)).fetchone()
            if not father:
                flash(f"Validation failed: Father Tag ID '{father_id}' does not exist in Master Records!", 'danger')
                return redirect(url_for('kid_add'))
            elif father['gender'] == 'Female':
                flash(f"Validation failed: Father Tag ID '{father_id}' is a Female goat! A female goat cannot be registered as a Father.", 'danger')
                return redirect(url_for('kid_add'))
                
        db.execute('''
            INSERT INTO kid_records (
                s_no, kid_id, breed, breed_percent, gender, color, 
                litter_size, birth_date, age_month, birth_weight, mother_id, father_id,
                insurance_policy_no, insurance_company, insurance_expiry
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('s_no'), f.get('kid_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'),
            f.get('color'), f.get('litter_size'), f.get('birth_date'), f.get('age_month'), f.get('birth_weight'),
            f.get('mother_id'), f.get('father_id'), f.get('insurance_policy_no'), f.get('insurance_company'),
            f.get('insurance_expiry')
        ))
        db.commit()
        flash('Kid record added successfully!', 'success')
        return redirect(url_for('kid'))
    db = get_db()
    res = db.execute('SELECT MAX(CAST(s_no AS INTEGER)) FROM kid_records').fetchone()[0]
    next_sr = (res or 0) + 1
    return render_template('kid_add.html', next_sr=next_sr)

@app.route('/kid')
def kid():
    db = get_db()
    kid_search = request.args.get('kid_id', '')
    if kid_search:
        records_raw = db.execute('SELECT * FROM kid_records WHERE kid_id LIKE ? ORDER BY birth_date DESC', 
             (f"%{kid_search}%",)).fetchall()
    else:
        records_raw = db.execute('SELECT * FROM kid_records ORDER BY birth_date DESC').fetchall()
        
    records = []
    for r in records_raw:
        r_dict = dict(r)
        r_dict['age_month'] = calculate_kid_age_months(r_dict.get('birth_date'))
        records.append(r_dict)
        
    return render_template('kid.html', records=records)

@app.route('/vaccine_add', methods=['GET', 'POST'])
def vaccine_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db.execute('''
            INSERT INTO vaccine_records (
                sr_no, tag_no, vaccine_date, vaccine_name, amount_spent, 
                additional_vaccines, additional_medicines, required_vaccines, 
                required_medicines, notes, next_due_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('sr_no'), f.get('tag_no'), f.get('vaccine_date'), f.get('vaccine_name'), 
            f.get('amount_spent') or 0.0, f.get('additional_vaccines'), f.get('additional_medicines'),
            f.get('required_vaccines'), f.get('required_medicines'), f.get('notes'), f.get('next_due_date')
        ))
        db.commit()
        flash('Vaccine record added successfully!', 'success')
        return redirect(url_for('vaccine'))
    
    goats = db.execute('SELECT tag_no FROM master_records ORDER BY tag_no ASC').fetchall()
    return render_template('vaccine_add.html', goats=goats)

@app.route('/vaccine')
def vaccine():
    db = get_db()
    tag_search = request.args.get('tag_no', '')
    month_filter = request.args.get('month', '')
    
    q = 'SELECT * FROM vaccine_records WHERE 1=1'
    p = []
    
    if tag_search:
        q += ' AND (tag_no LIKE ? OR sr_no LIKE ?)'
        p.extend([f"%{tag_search}%", f"%{tag_search}%"])
        
    if month_filter:
        q += " AND TO_CHAR(vaccine_date, 'YYYY-MM') = ?"
        p.append(month_filter)
        
    q += ' ORDER BY CAST(sr_no AS INTEGER) ASC, id ASC'
    records = db.execute(q, p).fetchall()
    
    total_cost = sum(r['amount_spent'] or 0 for r in records)
    
    return render_template('vaccine.html', records=records, total_cost=total_cost, tag_search=tag_search, month_filter=month_filter)

@app.route('/doctor_add', methods=['GET', 'POST'])
def doctor_add():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('''
            INSERT INTO doctor_details (
                doctor_name, specialization, contact_number, email, clinic_name,
                clinic_address, clinic_city, availability, registration_number, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('doctor_name'), f.get('specialization'), f.get('contact_number'), 
            f.get('email'), f.get('clinic_name'), f.get('clinic_address'), f.get('clinic_city'),
            f.get('availability'), f.get('registration_number'), f.get('notes')
        ))
        db.commit()
        flash('Doctor details added successfully!', 'success')
        return redirect(url_for('doctor'))
    return render_template('doctor_add.html')

@app.route('/doctor')
def doctor():
    db = get_db()
    search = request.args.get('search', '')
    if search:
        records = db.execute('''SELECT * FROM doctor_details 
                               WHERE doctor_name LIKE ? OR clinic_name LIKE ? 
                               OR contact_number LIKE ? ORDER BY doctor_name ASC''', 
             (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        records = db.execute('SELECT * FROM doctor_details ORDER BY doctor_name ASC').fetchall()
    return render_template('doctor.html', records=records)

@app.route('/doctor_edit/<int:id>', methods=['GET', 'POST'])
def doctor_edit(id):
    db = get_db()
    doctor = db.execute('SELECT * FROM doctor_details WHERE id = ?', (id,)).fetchone()
    
    if not doctor:
        flash('Doctor record not found.', 'danger')
        return redirect(url_for('doctor'))
    
    if request.method == 'POST':
        f = request.form
        db.execute('''
            UPDATE doctor_details SET 
            doctor_name = ?, specialization = ?, contact_number = ?, email = ?,
            clinic_name = ?, clinic_address = ?, clinic_city = ?, availability = ?,
            registration_number = ?, notes = ? WHERE id = ?
        ''', (
            f.get('doctor_name'), f.get('specialization'), f.get('contact_number'), 
            f.get('email'), f.get('clinic_name'), f.get('clinic_address'), f.get('clinic_city'),
            f.get('availability'), f.get('registration_number'), f.get('notes'), id
        ))
        db.commit()
        flash('Doctor details updated successfully!', 'success')
        return redirect(url_for('doctor'))
    
    return render_template('doctor_edit.html', doctor=doctor)

@app.route('/doctor_delete/<int:id>', methods=['POST'])
def doctor_delete(id):
    db = get_db()
    db.execute('DELETE FROM doctor_details WHERE id = ?', (id,))
    db.commit()
    flash('Doctor record deleted successfully!', 'success')
    return redirect(url_for('doctor'))

# MASTER RECORDS EDIT & DELETE
@app.route('/master_edit/<int:id>', methods=['GET', 'POST'])
def master_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM master_records WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('master'))
    
    if request.method == 'POST':
        f = request.form
        
        # Calculate DOB from entered Age
        try:
            from datetime import timedelta
            age_years = int(f.get('age_years') or 0)
            age_months = int(f.get('age_months') or 0)
            age_days = int(f.get('age_days') or 0)
            total_days = age_years * 365 + age_months * 30 + age_days
            dob_date = datetime.now().date() - timedelta(days=total_days)
            dob_str = dob_date.strftime('%Y-%m-%d')
        except Exception:
            dob_str = None

        db.execute('''
            UPDATE master_records SET 
            si_no = ?, tag_no = ?, breed = ?, breed_percent = ?, status = ?, sold = ?, expired = ?, gender = ?,
            purchase_date = ?, color = ?, weight_kg = ?, purchase_amount = ?, insurance_date = ?,
            vaccination = ?, vaccination_period = ?, vaccination_next_due = ?, medicine = ?, medicine_period = ?, feed = ?,
            feed_amount = ?, mating_date = ?, mating_goat_no = ?, goat_week_period = ?,
            delivery_date = ?, new_goat_gender = ?, new_goat_color = ?, birth_weight = ?,
            selling_date = ?, selling_weight = ?, selling_price = ?, mortality_date = ?,
            mortality_weight = ?, mortality_reason = ?, insurance_claim_amount = ?,
            insurance_inform_date = ?, insurance_claim_date = ?, kit_status = ?, dob = ? WHERE id = ?
        ''', (
            f.get('si_no'), f.get('tag_no'), f.get('breed'), f.get('breed_percent'), f.get('status'),
            f.get('sold'), f.get('expired'), f.get('gender'), f.get('purchase_date'), f.get('color'),
            f.get('weight_kg'), f.get('purchase_amount'), f.get('insurance_date'), f.get('vaccination'),
            f.get('vaccination_period'), f.get('vaccination_next_due') or None, f.get('medicine'), f.get('medicine_period'), f.get('feed'),
            f.get('feed_amount'), f.get('mating_date'), f.get('mating_goat_no'), f.get('goat_week_period'),
            f.get('delivery_date'), f.get('new_goat_gender'), f.get('new_goat_color'), f.get('birth_weight'),
            f.get('selling_date') or None, f.get('selling_weight'), f.get('selling_price'), f.get('mortality_date') or None,
            f.get('mortality_weight'), f.get('mortality_reason'), f.get('insurance_claim_amount'),
            f.get('insurance_inform_date') or None, f.get('insurance_claim_date') or None, 1 if f.get('kit_status') else 0, dob_str, id
        ))
        
        # Connected Mortality Log Synchronization
        tag_no = f.get('tag_no')
        status = f.get('status')
        mortality_date = f.get('mortality_date')
        if status == 'Expired' or mortality_date:
            mort_exists = db.execute('SELECT 1 FROM mortality_records WHERE tag_id = ?', (tag_no,)).fetchone()
            if not mort_exists:
                res_mort = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM mortality_records').fetchone()[0]
                next_mort_sr = (res_mort or 0) + 1
                db.execute('''
                    INSERT INTO mortality_records (
                        sr_no, tag_id, breed, breed_percent, gender, expired_date, 
                        weight_kgs, insurance_inform_date, insurance_claim_date,
                        current_value, claim_amount, cause_of_death
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(next_mort_sr), tag_no, f.get('breed'), f.get('breed_percent'), f.get('gender'),
                    mortality_date or datetime.now().strftime('%Y-%m-%d'),
                    f.get('mortality_weight'), f.get('insurance_inform_date') or None, f.get('insurance_claim_date') or None,
                    f.get('purchase_amount') or 0.0, f.get('insurance_claim_amount') or 0.0, f.get('mortality_reason') or 'Unspecified'
                ))
            else:
                db.execute('''
                    UPDATE mortality_records SET
                    breed = ?, breed_percent = ?, gender = ?, expired_date = ?, 
                    weight_kgs = ?, insurance_inform_date = ?, insurance_claim_date = ?,
                    claim_amount = ?, cause_of_death = ?
                    WHERE tag_id = ?
                ''', (
                    f.get('breed'), f.get('breed_percent'), f.get('gender'),
                    mortality_date or datetime.now().strftime('%Y-%m-%d'),
                    f.get('mortality_weight'), f.get('insurance_inform_date') or None, f.get('insurance_claim_date') or None,
                    f.get('insurance_claim_amount') or 0.0, f.get('mortality_reason') or 'Unspecified',
                    tag_no
                ))
        else:
            db.execute('DELETE FROM mortality_records WHERE tag_id = ?', (tag_no,))
        
        db.commit()
        flash('Master record updated successfully!', 'success')
        return redirect(url_for('master'))
    
    record_dict = dict(record)
    age_dict = parse_dob_to_age_dict(record_dict.get('dob'))
    record_dict['age_years'] = age_dict['years']
    record_dict['age_months'] = age_dict['months']
    record_dict['age_days'] = age_dict['days']
    return render_template('master_edit.html', record=record_dict)

@app.route('/master_delete/<int:id>', methods=['POST'])
def master_delete(id):
    db = get_db()
    record = db.execute('SELECT tag_no FROM master_records WHERE id = ?', (id,)).fetchone()
    if record:
        tag_no = record['tag_no']
        db.execute('DELETE FROM master_records WHERE id = ?', (id,))
        db.execute('DELETE FROM goats_data WHERE tag_number = ?', (tag_no,))
        db.execute('DELETE FROM sales_records WHERE tag_id = ?', (tag_no,))
        db.execute('DELETE FROM medicine_history WHERE tag_no = ?', (tag_no,))
        db.execute('DELETE FROM vaccine_records WHERE tag_no = ?', (tag_no,))
        db.execute('DELETE FROM mortality_records WHERE tag_id = ?', (tag_no,))
        db.execute('DELETE FROM eligible_to_sell WHERE tag_id = ?', (tag_no,))
        db.commit()
        flash('Master record and all related history/financial logs deleted successfully!', 'success')
    else:
        flash('Record not found.', 'danger')
    return redirect(url_for('master'))

# BACKWARD COMPATIBILITY SALES REDIRECTS
@app.route('/sales_edit/<int:id>', methods=['GET', 'POST'])
def old_sales_edit(id):
    return redirect(url_for('sales_edit', s_type='goat', id=id))

@app.route('/sales_delete/<int:id>', methods=['POST'])
def old_sales_delete(id):
    return sales_delete('goat', id)

# MEDICINE RECORDS EDIT & DELETE
@app.route('/medicine_edit/<int:id>', methods=['GET', 'POST'])
def medicine_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM medicine_history WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('medicine'))
    
    if request.method == 'POST':
        f = request.form
        db.execute('''
            UPDATE medicine_history SET 
            tag_no = ?, doctor_name = ?, consultation_date = ?, medicine_name = ?,
            dose = ?, quantity = ?, cost = ?, notes = ? WHERE id = ?
        ''', (
            f.get('tag_no'), f.get('doctor_name'), f.get('consultation_date'), f.get('medicine_name'),
            f.get('dose'), f.get('quantity'), f.get('cost') or 0.0, f.get('notes'), id
        ))
        db.commit()
        flash('Medicine record updated successfully!', 'success')
        return redirect(url_for('medicine'))
    
    goats = db.execute('SELECT tag_no FROM master_records ORDER BY tag_no ASC').fetchall()
    doctors = db.execute('SELECT doctor_name FROM doctor_details ORDER BY doctor_name ASC').fetchall()
    return render_template('medicine_edit.html', record=record, goats=goats, doctors=doctors)

@app.route('/medicine_delete/<int:id>', methods=['POST'])
def medicine_delete(id):
    db = get_db()
    db.execute('DELETE FROM medicine_history WHERE id = ?', (id,))
    db.commit()
    flash('Medicine record deleted successfully!', 'success')
    return redirect(url_for('medicine'))

# MORTALITY RECORDS EDIT & DELETE
@app.route('/mortality_edit/<int:id>', methods=['GET', 'POST'])
def mortality_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM mortality_records WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('mortality'))
    
    if request.method == 'POST':
        f = request.form
        db.execute('''
            UPDATE mortality_records SET 
            sr_no = ?, tag_id = ?, breed = ?, breed_percent = ?, gender = ?, birth_date = ?,
            expired_date = ?, total_age_month = ?, weight_kgs = ?, insurance_inform_date = ?,
            insurance_claim_date = ?, current_value = ?, claim_amount = ?, cause_of_death = ? WHERE id = ?
        ''', (
            f.get('sr_no'), f.get('tag_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'),
            f.get('birth_date'), f.get('expired_date'), f.get('total_age_month'), f.get('weight_kgs'),
            f.get('insurance_inform_date'), f.get('insurance_claim_date'), f.get('current_value'),
            f.get('claim_amount'), f.get('cause_of_death'), id
        ))
        db.commit()
        flash('Mortality record updated successfully!', 'success')
        return redirect(url_for('mortality'))
    
    return render_template('mortality_edit.html', record=record)

@app.route('/mortality_delete/<int:id>', methods=['POST'])
def mortality_delete(id):
    db = get_db()
    record = db.execute('SELECT tag_id FROM mortality_records WHERE id = ?', (id,)).fetchone()
    if record:
        tag_id = record['tag_id']
        db.execute('DELETE FROM mortality_records WHERE id = ?', (id,))
        # Revert status in master_records
        db.execute("UPDATE master_records SET status = 'Active', mortality_date = NULL, mortality_reason = NULL WHERE tag_no = ?", (tag_id,))
        # Delete related transaction from goats_data
        db.execute("DELETE FROM goats_data WHERE tag_number = ? AND type = 'Mortality Loss'", (tag_id,))
        
        # Restore into eligible_to_sell if it meets weight/age criteria or just re-insert
        db.execute("INSERT OR IGNORE INTO eligible_to_sell (tag_id, tag_no, breed, gender, weight_kg) SELECT tag_no, tag_no, breed, gender, weight_kg FROM master_records WHERE tag_no = ?", (tag_id,))
        
        db.commit()
        flash('Mortality record deleted, loss transaction reversed, and goat status reverted to Active!', 'success')
    else:
        flash('Record not found.', 'danger')
    return redirect(url_for('mortality'))

# FEED RECORDS EDIT & DELETE
@app.route('/feed_edit/<int:id>', methods=['GET', 'POST'])
def feed_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM feed_inventory WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('feed'))
    
    if request.method == 'POST':
        f = request.form
        opening = float(f.get('opening_qty') or f.get('opening_stock') or 0)
        consumption = float(f.get('consumption_qty') or f.get('used_qty') or 0)
        wastage = float(f.get('wastage_qty') or 0)
        closing = opening - consumption
        
        purchase_amt = float(f.get('purchase_amount') or 0)
        cost_per_unit = purchase_amt / opening if opening > 0 else 0.0
        
        # If this is linked to a purchase, update voucher, expense and goats_data
        p_id = record['purchase_id']
        if p_id:
            old_purch = db.execute("SELECT * FROM feed_purchases WHERE id = ?", (p_id,)).fetchone()
            if old_purch:
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Feed' AND amount = ?", (old_purch['purchase_date'], old_purch['cost']))
                db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Feed Purchase' AND amount = ? AND vendor_name = ?", (old_purch['purchase_date'], old_purch['cost'], old_purch['supplier']))
                
            db.execute('''
                UPDATE feed_purchases SET feed_name = ?, quantity = ?, unit = ?, cost = ?, purchase_date = ?, supplier = ?
                WHERE id = ?
            ''', (f.get('feed_name'), opening, f.get('unit'), purchase_amt, f.get('date'), f.get('supplier'), p_id))
            
            desc = f"Purchased {opening} {f.get('unit')} of {f.get('feed_name')} from {f.get('supplier')}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', 'Feed', ?, ?)
            ''', (f.get('date'), purchase_amt, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                VALUES ('Feed Purchase', ?, ?, ?, ?, 'Cash', 'Paid')
            ''', (purchase_amt, f.get('date'), desc, f.get('supplier')))

        db.execute('''
            UPDATE feed_inventory SET 
            feed_name = ?, opening_stock = ?, purchased_qty = ?, used_qty = ?, wastage_qty = ?, closing_stock = ?,
            unit = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ? WHERE id = ?
        ''', (
            f.get('feed_name'), opening, (opening if p_id else 0.0), consumption, wastage, closing, f.get('unit'), 
            cost_per_unit, purchase_amt, f.get('date'), f.get('supplier'), id
        ))
        db.commit()
        flash('Feed record and connected expense logs updated successfully!', 'success')
        return redirect(url_for('feed'))
    
    return render_template('feed_edit.html', record=record)

@app.route('/feed_delete/<int:id>', methods=['POST'])
def feed_delete(id):
    db = get_db()
    record = db.execute("SELECT * FROM feed_inventory WHERE id = ?", (id,)).fetchone()
    if record and record['purchase_id']:
        p_id = record['purchase_id']
        old_purch = db.execute("SELECT * FROM feed_purchases WHERE id = ?", (p_id,)).fetchone()
        if old_purch:
            db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Feed' AND amount = ?", (old_purch['purchase_date'], old_purch['cost']))
            db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Feed Purchase' AND amount = ? AND vendor_name = ?", (old_purch['purchase_date'], old_purch['cost'], old_purch['supplier']))
        db.execute('DELETE FROM feed_purchases WHERE id = ?', (p_id,))
        
    db.execute('DELETE FROM feed_inventory WHERE id = ?', (id,))
    db.commit()
    flash('Feed record and all connected expense/voucher logs deleted successfully!', 'success')
    return redirect(url_for('feed'))

@app.route('/medicine_inventory_edit/<int:id>', methods=['GET', 'POST'])
def medicine_inventory_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM medicine_inventory WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('feed'))
    
    if request.method == 'POST':
        f = request.form
        opening = float(f.get('opening_qty') or f.get('opening_stock') or 0)
        consumption = float(f.get('used_qty') or f.get('consumption_qty') or 0)
        wastage = float(f.get('wastage_qty') or 0)
        closing = opening - consumption - wastage
        
        purchase_amt = float(f.get('purchase_amount') or 0)
        cost_per_unit = purchase_amt / opening if opening > 0 else 0.0
        
        # If linked to a purchase, update voucher, expense and goats_data
        p_id = record['purchase_id']
        if p_id:
            old_purch = db.execute("SELECT * FROM medicine_purchases WHERE id = ?", (p_id,)).fetchone()
            if old_purch:
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Medicine' AND amount = ?", (old_purch['purchase_date'], old_purch['cost']))
                db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Medicine Purchase' AND amount = ? AND vendor_name = ?", (old_purch['purchase_date'], old_purch['cost'], old_purch['supplier']))
                
            db.execute('''
                UPDATE medicine_purchases SET medicine_name = ?, dose_unit = ?, quantity = ?, cost = ?, purchase_date = ?, supplier = ?
                WHERE id = ?
            ''', (f.get('medicine_name'), f.get('unit'), opening, purchase_amt, f.get('date'), f.get('supplier'), p_id))
            
            desc = f"Purchased {opening} Doses of {f.get('medicine_name')} from {f.get('supplier')}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', 'Medicine', ?, ?)
            ''', (f.get('date'), purchase_amt, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                VALUES ('Medicine Purchase', ?, ?, ?, ?, 'Cash', 'Paid')
            ''', (purchase_amt, f.get('date'), desc, f.get('supplier')))

        db.execute('''
            UPDATE medicine_inventory SET 
            medicine_name = ?, opening_stock = ?, purchased_qty = ?, used_qty = ?, wastage_qty = ?, closing_stock = ?,
            unit = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ? WHERE id = ?
        ''', (
            f.get('medicine_name'), opening, (opening if p_id else 0.0), consumption, wastage, closing, f.get('unit'), 
            cost_per_unit, purchase_amt, f.get('date'), f.get('supplier'), id
        ))
        db.commit()
        flash('Medicine record and connected expense logs updated successfully!', 'success')
        return redirect(url_for('feed'))
    
    return render_template('medicine_inventory_edit.html', record=record)

@app.route('/medicine_inventory_delete/<int:id>', methods=['POST'])
def medicine_inventory_delete(id):
    db = get_db()
    record = db.execute("SELECT * FROM medicine_inventory WHERE id = ?", (id,)).fetchone()
    if record and record['purchase_id']:
        p_id = record['purchase_id']
        old_purch = db.execute("SELECT * FROM medicine_purchases WHERE id = ?", (p_id,)).fetchone()
        if old_purch:
            db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Medicine' AND amount = ?", (old_purch['purchase_date'], old_purch['cost']))
            db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Medicine Purchase' AND amount = ? AND vendor_name = ?", (old_purch['purchase_date'], old_purch['cost'], old_purch['supplier']))
        db.execute('DELETE FROM medicine_purchases WHERE id = ?', (p_id,))
        
    db.execute('DELETE FROM medicine_inventory WHERE id = ?', (id,))
    db.commit()
    flash('Medicine inventory record and all connected expense/voucher logs deleted successfully!', 'success')
    return redirect(url_for('feed'))

@app.route('/vaccine_inventory_edit/<int:id>', methods=['GET', 'POST'])
def vaccine_inventory_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM vaccine_inventory WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('feed'))
    
    if request.method == 'POST':
        f = request.form
        opening = float(f.get('opening_qty') or f.get('opening_stock') or 0)
        consumption = float(f.get('used_qty') or f.get('consumption_qty') or 0)
        wastage = float(f.get('wastage_qty') or 0)
        closing = opening - consumption - wastage
        
        purchase_amt = float(f.get('purchase_amount') or 0)
        cost_per_unit = purchase_amt / opening if opening > 0 else 0.0
        
        # If linked to a purchase, update voucher, expense and goats_data
        p_id = record['purchase_id']
        if p_id:
            old_purch = db.execute("SELECT * FROM vaccine_purchases WHERE id = ?", (p_id,)).fetchone()
            if old_purch:
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Vaccine' AND amount = ?", (old_purch['purchase_date'], old_purch['cost']))
                db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Vaccine Purchase' AND amount = ? AND vendor_name = ?", (old_purch['purchase_date'], old_purch['cost'], old_purch['supplier']))
                
            db.execute('''
                UPDATE vaccine_purchases SET vaccine_name = ?, quantity = ?, cost = ?, purchase_date = ?, supplier = ?
                WHERE id = ?
            ''', (f.get('vaccine_name'), opening, purchase_amt, f.get('date'), f.get('supplier'), p_id))
            
            desc = f"Purchased {opening} Doses of {f.get('vaccine_name')} from {f.get('supplier')}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', 'Vaccine', ?, ?)
            ''', (f.get('date'), purchase_amt, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                VALUES ('Vaccine Purchase', ?, ?, ?, ?, 'Cash', 'Paid')
            ''', (purchase_amt, f.get('date'), desc, f.get('supplier')))

        db.execute('''
            UPDATE vaccine_inventory SET 
            vaccine_name = ?, opening_stock = ?, purchased_qty = ?, used_qty = ?, wastage_qty = ?, closing_stock = ?,
            unit = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ? WHERE id = ?
        ''', (
            f.get('vaccine_name'), opening, (opening if p_id else 0.0), consumption, wastage, closing, f.get('unit'), 
            cost_per_unit, purchase_amt, f.get('date'), f.get('supplier'), id
        ))
        db.commit()
        flash('Vaccine record and connected expense logs updated successfully!', 'success')
        return redirect(url_for('feed'))
    
    return render_template('vaccine_inventory_edit.html', record=record)

@app.route('/vaccine_inventory_delete/<int:id>', methods=['POST'])
def vaccine_inventory_delete(id):
    db = get_db()
    record = db.execute("SELECT * FROM vaccine_inventory WHERE id = ?", (id,)).fetchone()
    if record and record['purchase_id']:
        p_id = record['purchase_id']
        old_purch = db.execute("SELECT * FROM vaccine_purchases WHERE id = ?", (p_id,)).fetchone()
        if old_purch:
            db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Vaccine' AND amount = ?", (old_purch['purchase_date'], old_purch['cost']))
            db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Vaccine Purchase' AND amount = ? AND vendor_name = ?", (old_purch['purchase_date'], old_purch['cost'], old_purch['supplier']))
        db.execute('DELETE FROM vaccine_purchases WHERE id = ?', (p_id,))
        
    db.execute('DELETE FROM vaccine_inventory WHERE id = ?', (id,))
    db.commit()
    flash('Vaccine inventory record and all connected expense/voucher logs deleted successfully!', 'success')
    return redirect(url_for('feed'))

# KID RECORDS EDIT & DELETE
@app.route('/kid_edit/<int:id>', methods=['GET', 'POST'])
def kid_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM kid_records WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('kid'))
    
    if request.method == 'POST':
        f = request.form
        
        # Validate parent IDs in master_records
        mother_id = f.get('mother_id', '').strip()
        father_id = f.get('father_id', '').strip()

        if mother_id and father_id and mother_id == father_id:
            flash("Validation failed: Mother and Father cannot have the same Tag ID!", 'danger')
            return redirect(url_for('kid_edit', id=id))

        # Check mother ID
        if mother_id:
            mother = db.execute('SELECT tag_no, gender FROM master_records WHERE tag_no = ?', (mother_id,)).fetchone()
            if not mother:
                flash(f"Validation failed: Mother Tag ID '{mother_id}' does not exist in Master Records!", 'danger')
                return redirect(url_for('kid_edit', id=id))
            elif mother['gender'] == 'Male':
                flash(f"Validation failed: Mother Tag ID '{mother_id}' is a Male goat! A male goat cannot be registered as a Mother.", 'danger')
                return redirect(url_for('kid_edit', id=id))

        # Check father ID
        if father_id:
            father = db.execute('SELECT tag_no, gender FROM master_records WHERE tag_no = ?', (father_id,)).fetchone()
            if not father:
                flash(f"Validation failed: Father Tag ID '{father_id}' does not exist in Master Records!", 'danger')
                return redirect(url_for('kid_edit', id=id))
            elif father['gender'] == 'Female':
                flash(f"Validation failed: Father Tag ID '{father_id}' is a Female goat! A female goat cannot be registered as a Father.", 'danger')
                return redirect(url_for('kid_edit', id=id))

        db.execute('''
            UPDATE kid_records SET 
            s_no = ?, kid_id = ?, breed = ?, breed_percent = ?, gender = ?, color = ?,
            litter_size = ?, birth_date = ?, age_month = ?, birth_weight = ?, mother_id = ?, father_id = ?,
            insurance_policy_no = ?, insurance_company = ?, insurance_expiry = ? WHERE id = ?
        ''', (
            f.get('s_no'), f.get('kid_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'), f.get('color'),
            f.get('litter_size'), f.get('birth_date'), f.get('age_month'), f.get('birth_weight'),
            f.get('mother_id'), f.get('father_id'), f.get('insurance_policy_no'), f.get('insurance_company'),
            f.get('insurance_expiry'), id
        ))
        db.commit()
        flash('Kid record updated successfully!', 'success')
        return redirect(url_for('kid'))
    
    record_dict = dict(record)
    record_dict['age_month'] = calculate_kid_age_months(record_dict.get('birth_date'))
    return render_template('kid_edit.html', record=record_dict)

@app.route('/kid_delete/<int:id>', methods=['POST'])
def kid_delete(id):
    db = get_db()
    db.execute('DELETE FROM kid_records WHERE id = ?', (id,))
    db.commit()
    flash('Kid record deleted successfully!', 'success')
    return redirect(url_for('kid'))

# VACCINE RECORDS EDIT & DELETE
@app.route('/vaccine_edit/<int:id>', methods=['GET', 'POST'])
def vaccine_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM vaccine_records WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('vaccine'))
    
    if request.method == 'POST':
        f = request.form
        db.execute('''
            UPDATE vaccine_records SET 
            sr_no = ?, tag_no = ?, vaccine_date = ?, vaccine_name = ?, amount_spent = ?,
            additional_vaccines = ?, additional_medicines = ?, required_vaccines = ?,
            required_medicines = ?, notes = ?, next_due_date = ? WHERE id = ?
        ''', (
            f.get('sr_no'), f.get('tag_no'), f.get('vaccine_date'), f.get('vaccine_name'),
            f.get('amount_spent') or 0.0, f.get('additional_vaccines'), f.get('additional_medicines'),
            f.get('required_vaccines'), f.get('required_medicines'), f.get('notes'), f.get('next_due_date'), id
        ))
        db.commit()
        flash('Vaccine record updated successfully!', 'success')
        return redirect(url_for('vaccine'))
    
    goats = db.execute('SELECT tag_no FROM master_records ORDER BY tag_no ASC').fetchall()
    return render_template('vaccine_edit.html', record=record, goats=goats)

@app.route('/vaccine_delete/<int:id>', methods=['POST'])
def vaccine_delete(id):
    db = get_db()
    db.execute('DELETE FROM vaccine_records WHERE id = ?', (id,))
    db.commit()
    flash('Vaccine record deleted successfully!', 'success')
    return redirect(url_for('vaccine'))

# PURCHASE RECORDS EDIT & DELETE (Redirects for Backward Compatibility)
@app.route('/purchase_edit/<int:id>', methods=['GET', 'POST'])
def purchase_edit(id):
    return redirect(url_for('voucher_edit', v_type='goat', id=id))

@app.route('/purchase_delete/<int:id>', methods=['POST'])
def purchase_delete(id):
    return redirect(url_for('voucher_delete', v_type='goat', id=id))

@app.route('/health')
def health():
    db = get_db()
    vaccine_count = db.execute('SELECT COUNT(*) FROM vaccine_records').fetchone()[0]
    doctor_count = db.execute('SELECT COUNT(*) FROM doctor_details').fetchone()[0]
    return render_template('health.html', vaccine_count=vaccine_count, doctor_count=doctor_count)

@app.route('/healthz')
def healthz():
    try:
        db = get_db()
        db.execute('SELECT 1').fetchone()
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {
                "database": "connected"
            }
        }), 200
    except Exception as e:
        app.logger.critical(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }), 500

@app.route('/eligible_to_sell')
def eligible_to_sell():
    db = get_db()
    # Get all goats marked as eligible to sell
    # Explicitly select ets.tag_id and use COALESCE to prevent empty joins or column shadowing from wiping out tag id and weight
    eligible_goats_raw = db.execute('''
        SELECT ets.tag_id, 
               COALESCE(mr.breed, ets.breed) as breed, 
               COALESCE(mr.gender, ets.gender) as gender, 
               COALESCE(mr.weight_kg, ets.weight_kg) as weight_kg, 
               COALESCE(mr.status, 'Active') as status,
               ets.date_added
        FROM eligible_to_sell ets
        LEFT JOIN master_records mr ON ets.tag_id = mr.tag_no
        ORDER BY ets.date_added DESC
    ''').fetchall()
    eligible_goats = [dict(row) for row in eligible_goats_raw]
    return render_template('eligible_to_sell.html', eligible_goats=eligible_goats)

@app.route('/populate_eligible', methods=['POST'])
def populate_eligible():
    """Auto-populate eligible goats - those weighing more than 25 kg and not yet sold"""
    db = get_db()
    
    # Get all goats with weight > 25 kg and status != 'Sold'
    goats = db.execute('''
        SELECT tag_no, breed, gender, weight_kg
        FROM master_records
        WHERE weight_kg > 25 AND status != 'Sold' AND status IS NOT NULL
    ''').fetchall()
    
    today = datetime.now().strftime('%Y-%m-%d')
    count_added = 0
    
    for goat in goats:
        try:
            db.execute('''
                INSERT INTO eligible_to_sell (tag_id, tag_no, breed, gender, weight_kg, date_added)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (goat['tag_no'], goat['tag_no'], goat['breed'], goat['gender'], goat['weight_kg'], today))
            count_added += 1
        except sqlite3.IntegrityError:
            # Already exists, skip
            pass
    
    db.commit()
    flash(f'{count_added} eligible goat(s) added to the list!', 'success')
    return redirect(url_for('eligible_to_sell'))

@app.route('/add_to_eligible/<tag_id>', methods=['POST'])
def add_to_eligible(tag_id):
    """Manually add a goat to eligible list"""
    db = get_db()
    
    # Get goat details
    goat = db.execute('SELECT tag_no, breed, gender, weight_kg FROM master_records WHERE tag_no = ?', (tag_id,)).fetchone()
    
    if not goat:
        flash('Goat not found!', 'danger')
        return redirect(url_for('master'))
    
    if goat['weight_kg'] is None or goat['weight_kg'] < 25:
        flash('Goat must weigh more than 25 kg to be eligible for sale!', 'warning')
        return redirect(url_for('master'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        db.execute('''
            INSERT INTO eligible_to_sell (tag_id, tag_no, breed, gender, weight_kg, date_added)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (goat['tag_no'], goat['tag_no'], goat['breed'], goat['gender'], goat['weight_kg'], today))
        db.commit()
        flash(f'Goat {tag_id} added to eligible for sale list!', 'success')
    except sqlite3.IntegrityError:
        flash(f'Goat {tag_id} is already in the eligible list!', 'info')
    
    return redirect(url_for('eligible_to_sell'))

@app.route('/remove_eligible/<tag_id>', methods=['POST'])
def remove_eligible(tag_id):
    """Remove a goat from eligible list"""
    db = get_db()
    db.execute('DELETE FROM eligible_to_sell WHERE tag_id = ?', (tag_id,))
    db.commit()
    flash(f'Goat {tag_id} removed from eligible for sale list!', 'success')
    return redirect(url_for('eligible_to_sell'))

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        flash('Please enter a search term.', 'warning')
        return redirect(url_for('dashboard'))
        
    db = get_db()
    
    # Check if exact tag match in master
    tag_master = db.execute("SELECT * FROM master_records WHERE tag_no = ?", (query,)).fetchone()
    # Or in goats_data
    tag_goats = db.execute("SELECT * FROM goats_data WHERE tag_number = ?", (query,)).fetchone()
    
    if tag_master or tag_goats:
        return redirect(url_for('goat_detail', tag_number=query))
        
    flash(f"No records found for '{query}'", 'info')
    return redirect(url_for('dashboard'))
@app.route('/vouchers')
def vouchers():
    db = get_db()
    # Fetch counts and sums for the cards
    count_goat = db.execute("SELECT COUNT(*) FROM purchases").fetchone()[0] or 0
    sum_goat = db.execute("SELECT SUM(price) FROM purchases").fetchone()[0] or 0.0
    
    count_feed = db.execute("SELECT COUNT(*) FROM feed_purchases").fetchone()[0] or 0
    sum_feed = db.execute("SELECT SUM(cost) FROM feed_purchases").fetchone()[0] or 0.0
    
    count_med = db.execute("SELECT COUNT(*) FROM medicine_purchases").fetchone()[0] or 0
    sum_med = db.execute("SELECT SUM(cost) FROM medicine_purchases").fetchone()[0] or 0.0
    count_vac = db.execute("SELECT COUNT(*) FROM vaccine_purchases").fetchone()[0] or 0
    sum_vac = db.execute("SELECT SUM(cost) FROM vaccine_purchases").fetchone()[0] or 0.0
    
    count_health = count_med + count_vac
    sum_health = sum_med + sum_vac
    
    count_other = db.execute("SELECT COUNT(*) FROM equipment").fetchone()[0] or 0
    sum_other = db.execute("SELECT SUM(purchase_cost) FROM equipment").fetchone()[0] or 0.0
    
    return render_template('vouchers.html', 
                           count_goat=count_goat, sum_goat=sum_goat,
                           count_feed=count_feed, sum_feed=sum_feed,
                           count_health=count_health, sum_health=sum_health,
                           count_other=count_other, sum_other=sum_other)

@app.route('/vouchers/<v_type>')
def voucher_register(v_type):
    if v_type not in ['goat', 'feed', 'health', 'other']:
        flash('Invalid voucher type!', 'danger')
        return redirect(url_for('vouchers'))
        
    db = get_db()
    records = []
    
    if v_type == 'goat':
        raw_records = db.execute('SELECT * FROM purchases ORDER BY purchase_date DESC').fetchall()
        for r in raw_records:
            records.append({
                'id': r['id'],
                'title': f"Goat Tag: {r['tag_id']}",
                'subtitle': f"Seller: {r['seller_name']}",
                'date': r['purchase_date'],
                'amount': r['price'],
                'notes': r['invoice_details'] or "No details"
            })
            
    elif v_type == 'feed':
        raw_records = db.execute('SELECT * FROM feed_purchases ORDER BY purchase_date DESC').fetchall()
        for r in raw_records:
            records.append({
                'id': r['id'],
                'title': f"Feed: {r['feed_name']}",
                'subtitle': f"Qty: {r['quantity']} {r['unit']} | Supplier: {r['supplier']}",
                'date': r['purchase_date'],
                'amount': r['cost'],
                'notes': f"Feed inventory stock replenishment"
            })
            
    elif v_type == 'health':
        med_records = db.execute('SELECT * FROM medicine_purchases').fetchall()
        for r in med_records:
            records.append({
                'id': r['id'],
                'sub_type': 'medicine',
                'title': f"Medicine: {r['medicine_name']}",
                'subtitle': f"Qty: {r['quantity']} {r['dose_unit']} | Supplier: {r['supplier']}",
                'date': r['purchase_date'],
                'amount': r['cost'],
                'notes': "Medicine stock replenishment"
            })
        vac_records = db.execute('SELECT * FROM vaccine_purchases').fetchall()
        for r in vac_records:
            records.append({
                'id': r['id'],
                'sub_type': 'vaccine',
                'title': f"Vaccine: {r['vaccine_name']}",
                'subtitle': f"Qty: {r['quantity']} doses | Supplier: {r['supplier']}",
                'date': r['purchase_date'],
                'amount': r['cost'],
                'notes': "Vaccine stock replenishment"
            })
        records.sort(key=lambda x: x['date'], reverse=True)
        
    elif v_type == 'other':
        raw_records = db.execute('SELECT * FROM other_vouchers ORDER BY voucher_date DESC').fetchall()
        for r in raw_records:
            records.append({
                'id': r['id'],
                'title': f"Expense: {r['particular_name'] or 'General'}",
                'subtitle': f"Supplier: {r['supplier_name'] or 'N/A'} | Bill No: {r['bill_no'] or 'N/A'} | Qty: {r['quantity'] or '-'} {r['unit_name'] or ''}",
                'date': r['voucher_date'],
                'amount': r['amount'] or 0.0,
                'notes': r['notes'] or f"Bill Date: {r['bill_date'] or 'N/A'}"
            })
            
    # Group month-wise
    from collections import defaultdict
    grouped_records = defaultdict(list)
    for r in records:
        try:
            date_obj = datetime.strptime(r['date'], '%Y-%m-%d')
            month_str = date_obj.strftime('%B %Y')
        except:
            month_str = "Other / Unknown Date"
        grouped_records[month_str].append(r)
        
    return render_template('voucher_register.html', v_type=v_type, grouped_records=grouped_records)

@app.route('/vouchers/<v_type>/add', methods=['GET', 'POST'])
def voucher_add(v_type):
    if v_type not in ['goat', 'feed', 'health', 'other']:
        flash('Invalid voucher type!', 'danger')
        return redirect(url_for('vouchers'))
        
    db = get_db()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        f = request.form
        p_date = f.get('purchase_date') or today_str
        pnl_cat = f.get('pnl_category', 'Direct Expenses' if v_type == 'other' else 'Purchase')
        
        # Parse particulars for all voucher types
        particular_id = f.get('particular_id') or None
        particular_id = int(particular_id) if particular_id else None
        particular_name = f.get('particular_name', '').strip()
        if particular_id and not particular_name:
            p = db.execute('SELECT name FROM expense_particulars WHERE id=?', (particular_id,)).fetchone()
            particular_name = p['name'] if p else ''

        if v_type == 'goat':
            tag_id = f.get('tag_id')
            price = float(f.get('price') or 0)
            
            # 1. Save to purchases
            db.execute('''
                INSERT INTO purchases (seller_name, invoice_details, purchase_date, tag_id, price, pnl_category, bill_date, bill_no, particular_id, particular_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (f.get('seller_name'), f.get('notes'), p_date, tag_id, price, pnl_cat, f.get('bill_date') or None, f.get('bill_no', '').strip(), particular_id, particular_name))
            
            # 2. Add to master_records
            breed = f.get('breed', 'Unknown')
            gender = f.get('gender', 'Unknown')
            weight = float(f.get('weight') or 0)
            res_si = db.execute('SELECT MAX(CAST(si_no AS INTEGER)) FROM master_records').fetchone()[0]
            next_si = (res_si or 0) + 1
            db.execute('''
                INSERT INTO master_records (si_no, tag_no, breed, gender, purchase_date, weight_kg, purchase_amount, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')
            ''', (str(next_si), tag_id, breed, gender, p_date, weight, price))
            
            # 3. Add to goats_data (Goat Directory Financial Records)
            goat_desc = f"Goat Purchase: Tag {tag_id} from {f.get('seller_name') or 'Supplier'}. {f.get('notes') or ''}".strip('. ')
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES (?, ?, 'expense', 'Goat Purchase', ?, ?)
            ''', (tag_id, p_date, price, goat_desc))
            
            # 4. Add to expenses so it appears in Expenses Management page
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status, bill_date, bill_no, particular_id, pnl_category)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid', ?, ?, ?, ?)
            ''', (particular_name or pnl_cat or 'Livestock Purchase', price, p_date, goat_desc, f.get('seller_name'), f.get('bill_date') or None, f.get('bill_no', '').strip(), particular_id, pnl_cat))
            
            db.commit()
            flash('Goat Purchase Voucher created successfully!', 'success')
            
        elif v_type == 'feed':
            feed_name = f.get('feed_name') or particular_name
            qty = float(f.get('quantity') or 0)
            cost = float(f.get('cost') or 0)
            unit = f.get('unit', 'KG')
            supplier = f.get('supplier')
            bill_date = f.get('bill_date') or None
            bill_no = f.get('bill_no', '').strip()
            notes = f.get('notes', '').strip()
            
            cursor = db.execute('''
                INSERT INTO feed_purchases (feed_name, quantity, unit, cost, purchase_date, supplier, pnl_category, bill_date, bill_no, notes, particular_id, particular_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (feed_name, qty, unit, cost, p_date, supplier, pnl_cat, bill_date, bill_no, notes, particular_id, particular_name))
            purchase_id = cursor.lastrowid
            
            # Fetch last closing stock
            last = db.execute("SELECT closing_stock FROM feed_inventory WHERE feed_name = ? ORDER BY id DESC LIMIT 1", (feed_name,)).fetchone()
            opening = last['closing_stock'] if last else 0.0
            closing = opening + qty
            cost_per_unit = cost / qty if qty > 0 else 0.0
            
            db.execute('''
                INSERT INTO feed_inventory (feed_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
                VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
            ''', (feed_name, opening, qty, closing, unit, cost_per_unit, cost, p_date, supplier, purchase_id))
            
            # Expenses and goats_data logging
            desc = f"Purchased {qty} {unit} of {feed_name} from {supplier}. Notes: {notes}".strip('. ')
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', 'Feed', ?, ?)
            ''', (p_date, cost, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status, bill_date, bill_no, particular_id, pnl_category)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid', ?, ?, ?, ?)
            ''', (particular_name or pnl_cat, cost, p_date, desc, supplier, bill_date, bill_no, particular_id, pnl_cat))
            
            db.commit()
            flash('Feed Purchase Voucher created successfully!', 'success')
            
        elif v_type == 'health':
            sub_type = f.get('sub_type', 'medicine')
            name = f.get('health_name') or particular_name
            qty = float(f.get('quantity') or 0)
            cost = float(f.get('cost') or 0)
            supplier = f.get('supplier')
            bill_date = f.get('bill_date') or None
            bill_no = f.get('bill_no', '').strip()
            notes = f.get('notes', '').strip()
            
            if sub_type == 'medicine':
                dose_unit = f.get('dose_unit', 'ml')
                cursor = db.execute('''
                    INSERT INTO medicine_purchases (medicine_name, dose_unit, quantity, cost, purchase_date, supplier, pnl_category, bill_date, bill_no, notes, particular_id, particular_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, dose_unit, qty, cost, p_date, supplier, pnl_cat, bill_date, bill_no, notes, particular_id, particular_name))
                purchase_id = cursor.lastrowid
                
                # Fetch last closing stock
                last = db.execute("SELECT closing_stock FROM medicine_inventory WHERE medicine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
                opening = last['closing_stock'] if last else 0.0
                closing = opening + qty
                cost_per_unit = cost / qty if qty > 0 else 0.0
                
                db.execute('''
                    INSERT INTO medicine_inventory (medicine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
                    VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, opening, qty, closing, 'Doses', cost_per_unit, cost, p_date, supplier, purchase_id))
            else:
                cursor = db.execute('''
                    INSERT INTO vaccine_purchases (vaccine_name, quantity, cost, purchase_date, supplier, pnl_category, bill_date, bill_no, notes, particular_id, particular_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, qty, cost, p_date, supplier, pnl_cat, bill_date, bill_no, notes, particular_id, particular_name))
                purchase_id = cursor.lastrowid
                
                # Fetch last closing stock
                last = db.execute("SELECT closing_stock FROM vaccine_inventory WHERE vaccine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
                opening = last['closing_stock'] if last else 0.0
                closing = opening + qty
                cost_per_unit = cost / qty if qty > 0 else 0.0
                
                db.execute('''
                    INSERT INTO vaccine_inventory (vaccine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
                    VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, opening, qty, closing, 'Doses', cost_per_unit, cost, p_date, supplier, purchase_id))
            
            # Expenses and goats_data logging
            desc = f"Purchased {qty} Doses of {name} from {supplier}. Notes: {notes}".strip('. ')
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', ?, ?, ?)
            ''', (p_date, sub_type.capitalize(), cost, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status, bill_date, bill_no, particular_id, pnl_category)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid', ?, ?, ?, ?)
            ''', (particular_name or pnl_cat, cost, p_date, desc, supplier, bill_date, bill_no, particular_id, pnl_cat))
            
            db.commit()
            flash('Health Supplies Voucher created successfully!', 'success')
            
        elif v_type == 'other':
            supplier_name = f.get('supplier_name', '').strip()
            particular_id = f.get('particular_id') or None
            particular_name = f.get('particular_name', '').strip()
            bill_date = f.get('bill_date') or None
            bill_no = f.get('bill_no', '').strip()
            quantity = f.get('quantity') or None
            quantity = float(quantity) if quantity else None
            unit_id = f.get('unit_id') or None
            unit_name = f.get('unit_name', '').strip()
            amount = float(f.get('amount') or 0)
            notes = f.get('notes', '').strip()

            # Resolve particular_name from DB if only id given
            if particular_id and not particular_name:
                p = db.execute('SELECT name FROM expense_particulars WHERE id=?', (particular_id,)).fetchone()
                particular_name = p['name'] if p else ''
            # Resolve unit_name from DB if only id given
            if unit_id and not unit_name:
                u = db.execute('SELECT unit_name FROM expense_units WHERE id=?', (unit_id,)).fetchone()
                unit_name = u['unit_name'] if u else ''

            db.execute('''
                INSERT INTO other_vouchers
                (voucher_date, supplier_name, particular_id, particular_name, bill_date, bill_no, quantity, unit_id, unit_name, amount, notes, pnl_category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (p_date, supplier_name, particular_id, particular_name, bill_date, bill_no, quantity, unit_id, unit_name, amount, notes, pnl_cat or 'Direct Expenses'))

            # Log to expenses
            exp_desc = f"Other Voucher: {particular_name or 'Expense'} from {supplier_name or 'Supplier'}. Bill No: {bill_no or 'N/A'}. {notes or ''}".strip('. ')
            if amount > 0:
                db.execute('''
                    INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                    VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid')
                ''', (pnl_cat or particular_name or 'Direct Expenses', amount, p_date, exp_desc, supplier_name))

            db.commit()
            flash('Other Voucher created successfully!', 'success')

        return redirect(url_for('voucher_register', v_type=v_type))

    # Pre-fill record with GET parameters if provided
    record = None
    if v_type == 'feed' and request.args.get('feed_name'):
        record = {
            'feed_name': request.args.get('feed_name'),
            'unit': request.args.get('unit', 'KG'),
            'purchase_date': today_str,
            'pnl_category': 'Purchase'
        }
    elif v_type == 'health' and request.args.get('health_name'):
        record = {
            'sub_type': request.args.get('sub_type', 'medicine'),
            'health_name': request.args.get('health_name'),
            'dose_unit': request.args.get('dose_unit', 'Doses'),
            'unit': request.args.get('unit', 'Doses'),
            'purchase_date': today_str,
            'pnl_category': 'Purchase'
        }

    particulars = db.execute("""
        SELECT ep.* FROM expense_particulars ep
        LEFT JOIN expense_ledgers el ON ep.ledger_id = el.id
        LEFT JOIN ledger_groups lg ON el.ledger_group = lg.group_name
        WHERE lg.group_type IS NULL OR lg.group_type = 'Expense'
        ORDER BY ep.name
    """).fetchall()
    expense_units = db.execute('SELECT * FROM expense_units ORDER BY unit_name').fetchall()
    ledgers = db.execute('SELECT * FROM expense_ledgers ORDER BY ledger_name').fetchall()
    ledger_groups = db.execute("SELECT * FROM ledger_groups WHERE group_type = 'Expense' ORDER BY group_name").fetchall()
    return render_template('voucher_form.html', v_type=v_type, action='Add', record=record, today=today_str, particulars=particulars, expense_units=expense_units, ledgers=ledgers, ledger_groups=ledger_groups)

@app.route('/vouchers/<v_type>/edit/<int:id>', methods=['GET', 'POST'])
@app.route('/vouchers/<v_type>/edit/<sub_type>/<int:id>', methods=['GET', 'POST'])
def voucher_edit(v_type, id, sub_type=None):
    if v_type not in ['goat', 'feed', 'health', 'other']:
        flash('Invalid voucher type!', 'danger')
        return redirect(url_for('vouchers'))
        
    db = get_db()
    record = None
    
    if v_type == 'goat':
        record_raw = db.execute('SELECT * FROM purchases WHERE id = ?', (id,)).fetchone()
        if record_raw:
            master = db.execute('SELECT * FROM master_records WHERE tag_no = ?', (record_raw['tag_id'],)).fetchone()
            record = {
                'id': record_raw['id'],
                'tag_id': record_raw['tag_id'],
                'seller_name': record_raw['seller_name'],
                'purchase_date': record_raw['purchase_date'],
                'price': record_raw['price'],
                'notes': record_raw['invoice_details'],
                'breed': master['breed'] if master else 'Unknown',
                'gender': master['gender'] if master else 'Unknown',
                'weight': master['weight_kg'] if master else 0.0,
                'pnl_category': record_raw['pnl_category'] or 'Purchase',
                'bill_date': record_raw['bill_date'] if 'bill_date' in record_raw.keys() else '',
                'bill_no': record_raw['bill_no'] if 'bill_no' in record_raw.keys() else '',
                'particular_id': record_raw['particular_id'] if 'particular_id' in record_raw.keys() else None,
                'particular_name': record_raw['particular_name'] if 'particular_name' in record_raw.keys() else ''
            }
            
    elif v_type == 'feed':
        record_raw = db.execute('SELECT * FROM feed_purchases WHERE id = ?', (id,)).fetchone()
        if record_raw:
            record = dict(record_raw)
            record['pnl_category'] = record_raw['pnl_category'] or 'Purchase'
            
    elif v_type == 'health':
        if sub_type == 'medicine':
            record_raw = db.execute('SELECT * FROM medicine_purchases WHERE id = ?', (id,)).fetchone()
            if record_raw:
                record = {
                    'id': record_raw['id'],
                    'sub_type': 'medicine',
                    'health_name': record_raw['medicine_name'],
                    'dose_unit': record_raw['dose_unit'],
                    'quantity': record_raw['quantity'],
                    'cost': record_raw['cost'],
                    'purchase_date': record_raw['purchase_date'],
                    'supplier': record_raw['supplier'],
                    'pnl_category': record_raw['pnl_category'] or 'Purchase',
                    'bill_date': record_raw['bill_date'] if 'bill_date' in record_raw.keys() else '',
                    'bill_no': record_raw['bill_no'] if 'bill_no' in record_raw.keys() else '',
                    'notes': record_raw['notes'] if 'notes' in record_raw.keys() else '',
                    'particular_id': record_raw['particular_id'] if 'particular_id' in record_raw.keys() else None,
                    'particular_name': record_raw['particular_name'] if 'particular_name' in record_raw.keys() else ''
                }
        else:
            record_raw = db.execute('SELECT * FROM vaccine_purchases WHERE id = ?', (id,)).fetchone()
            if record_raw:
                record = {
                    'id': record_raw['id'],
                    'sub_type': 'vaccine',
                    'health_name': record_raw['vaccine_name'],
                    'quantity': record_raw['quantity'],
                    'cost': record_raw['cost'],
                    'purchase_date': record_raw['purchase_date'],
                    'supplier': record_raw['supplier'],
                    'pnl_category': record_raw['pnl_category'] or 'Purchase',
                    'bill_date': record_raw['bill_date'] if 'bill_date' in record_raw.keys() else '',
                    'bill_no': record_raw['bill_no'] if 'bill_no' in record_raw.keys() else '',
                    'notes': record_raw['notes'] if 'notes' in record_raw.keys() else '',
                    'particular_id': record_raw['particular_id'] if 'particular_id' in record_raw.keys() else None,
                    'particular_name': record_raw['particular_name'] if 'particular_name' in record_raw.keys() else ''
                }
                
    elif v_type == 'other':
        record_raw = db.execute('SELECT * FROM other_vouchers WHERE id = ?', (id,)).fetchone()
        if record_raw:
            record = {
                'id': record_raw['id'],
                'voucher_date': record_raw['voucher_date'],
                'supplier_name': record_raw['supplier_name'],
                'particular_id': record_raw['particular_id'],
                'particular_name': record_raw['particular_name'],
                'bill_date': record_raw['bill_date'],
                'bill_no': record_raw['bill_no'],
                'quantity': record_raw['quantity'],
                'unit_id': record_raw['unit_id'],
                'unit_name': record_raw['unit_name'],
                'amount': record_raw['amount'],
                'notes': record_raw['notes'],
                'pnl_category': record_raw['pnl_category'] or 'Direct Expenses'
            }
            
    if not record:
        flash('Voucher record not found!', 'danger')
        return redirect(url_for('voucher_register', v_type=v_type))

    if request.method == 'POST':
        f = request.form
        # For 'other' vouchers the date field is voucher_date, others use purchase_date
        if v_type == 'other':
            p_date = f.get('voucher_date') or record.get('voucher_date', today_str)
        else:
            p_date = f.get('purchase_date') or record.get('purchase_date', today_str)
        pnl_cat = f.get('pnl_category', 'Direct Expenses' if v_type == 'other' else 'Purchase')
        
        # Parse particulars for all voucher types
        particular_id = f.get('particular_id') or None
        particular_id = int(particular_id) if particular_id else None
        particular_name = f.get('particular_name', '').strip()
        if particular_id and not particular_name:
            p = db.execute('SELECT name FROM expense_particulars WHERE id=?', (particular_id,)).fetchone()
            particular_name = p['name'] if p else ''

        if v_type == 'goat':
            tag_id = f.get('tag_id')
            price = float(f.get('price') or 0)
            old_tag_id = record['tag_id']
            
            db.execute('''
                UPDATE purchases SET seller_name = ?, invoice_details = ?, purchase_date = ?, tag_id = ?, price = ?, pnl_category = ?, bill_date = ?, bill_no = ?, particular_id = ?, particular_name = ?
                WHERE id = ?
            ''', (f.get('seller_name'), f.get('notes'), p_date, tag_id, price, pnl_cat, f.get('bill_date') or None, f.get('bill_no', '').strip(), particular_id, particular_name, id))
            
            db.execute('''
                UPDATE master_records SET tag_no = ?, breed = ?, gender = ?, purchase_date = ?, weight_kg = ?, purchase_amount = ?
                WHERE tag_no = ?
            ''', (tag_id, f.get('breed'), f.get('gender'), p_date, float(f.get('weight') or 0), price, old_tag_id))
            
            # Sync with goats_data (Goat Directory Financial Records)
            goat_desc_edit = f"Goat Purchase: Tag {tag_id} from {f.get('seller_name') or 'Supplier'}. {f.get('notes') or ''}".strip('. ')
            exists_gd = db.execute("SELECT 1 FROM goats_data WHERE tag_number = ? AND type = 'Goat Purchase'", (old_tag_id,)).fetchone()
            if exists_gd:
                db.execute('''
                    UPDATE goats_data 
                    SET tag_number = ?, date = ?, amount = ?, notes = ?
                    WHERE tag_number = ? AND type = 'Goat Purchase'
                ''', (tag_id, p_date, price, goat_desc_edit, old_tag_id))
            else:
                db.execute('''
                    INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                    VALUES (?, ?, 'expense', 'Goat Purchase', ?, ?)
                ''', (tag_id, p_date, price, goat_desc_edit))
            
            # Sync expenses entry: remove old, insert updated
            old_goat = db.execute('SELECT * FROM purchases WHERE id = ?', (id,)).fetchone()
            if old_goat:
                db.execute("DELETE FROM expenses WHERE date = ? AND vendor_name = ? AND amount = ? AND category NOT LIKE '%Labor%' AND category NOT LIKE '%Labour%'",
                           (record.get('purchase_date'), record.get('seller_name'), record.get('price')))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status, bill_date, bill_no, particular_id, pnl_category)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid', ?, ?, ?, ?)
            ''', (particular_name or pnl_cat or 'Livestock Purchase', price, p_date, goat_desc_edit, f.get('seller_name'), f.get('bill_date') or None, f.get('bill_no', '').strip(), particular_id, pnl_cat))
            
            db.commit()
            flash('Goat Purchase Voucher updated successfully!', 'success')
            
        elif v_type == 'feed':
            qty = float(f.get('quantity') or 0)
            cost = float(f.get('cost') or 0)
            feed_name = f.get('feed_name') or particular_name
            
            # Get old voucher details first
            old = db.execute("SELECT * FROM feed_purchases WHERE id = ?", (id,)).fetchone()
            if old:
                # Delete old matching goats_data
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Feed' AND amount = ?", (old['purchase_date'], old['cost']))
                # Delete old matching expenses (using the old pnl_category or feed purchase)
                db.execute("DELETE FROM expenses WHERE date = ? AND category = ? AND amount = ? AND vendor_name = ?", (old['purchase_date'], old['pnl_category'] or 'Feed Purchase', old['cost'], old['supplier']))
            
            db.execute('''
                UPDATE feed_purchases SET feed_name = ?, quantity = ?, unit = ?, cost = ?, purchase_date = ?, supplier = ?, pnl_category = ?, bill_date = ?, bill_no = ?, notes = ?, particular_id = ?, particular_name = ?
                WHERE id = ?
            ''', (feed_name, qty, f.get('unit'), cost, p_date, f.get('supplier'), pnl_cat, f.get('bill_date') or None, f.get('bill_no', '').strip(), f.get('notes', '').strip(), particular_id, particular_name, id))
            
            # Recalculate feed inventory row
            row = db.execute("SELECT opening_stock, used_qty, wastage_qty FROM feed_inventory WHERE purchase_id = ?", (id,)).fetchone()
            if row:
                opening = row['opening_stock'] or 0.0
                used = row['used_qty'] or 0.0
                wastage = row['wastage_qty'] or 0.0
                closing = opening + qty - used
                cost_per_unit = cost / qty if qty > 0 else 0.0
                db.execute('''
                    UPDATE feed_inventory 
                    SET feed_name = ?, purchased_qty = ?, closing_stock = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ?
                    WHERE purchase_id = ?
                ''', (feed_name, qty, closing, cost_per_unit, cost, p_date, f.get('supplier'), id))
                
            # Now insert the new goats_data and expenses rows!
            desc = f"Purchased {qty} {f.get('unit')} of {feed_name} from {f.get('supplier')}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', 'Feed', ?, ?)
            ''', (p_date, cost, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status, bill_date, bill_no, particular_id, pnl_category)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid', ?, ?, ?, ?)
            ''', (particular_name or pnl_cat, cost, p_date, desc, f.get('supplier'), f.get('bill_date') or None, f.get('bill_no', '').strip(), particular_id, pnl_cat))
            
            db.commit()
            flash('Feed Purchase Voucher updated successfully!', 'success')
            
        elif v_type == 'health':
            name = f.get('health_name') or particular_name
            qty = float(f.get('quantity') or 0)
            cost = float(f.get('cost') or 0)
            supplier = f.get('supplier')
            cost_per_unit = cost / qty if qty > 0 else 0.0
            
            # Get old voucher details first
            if sub_type == 'medicine':
                old = db.execute("SELECT * FROM medicine_purchases WHERE id = ?", (id,)).fetchone()
            else:
                old = db.execute("SELECT * FROM vaccine_purchases WHERE id = ?", (id,)).fetchone()
                
            if old:
                # Delete old matching goats_data
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = ? AND amount = ?", (old['purchase_date'], sub_type.capitalize(), old['cost']))
                # Delete old matching expenses
                db.execute("DELETE FROM expenses WHERE date = ? AND category = ? AND amount = ? AND vendor_name = ?", (old['purchase_date'], old['pnl_category'] or (sub_type.capitalize() + ' Purchase'), old['cost'], old['supplier']))
            
            if sub_type == 'medicine':
                db.execute('''
                    UPDATE medicine_purchases SET medicine_name = ?, dose_unit = ?, quantity = ?, cost = ?, purchase_date = ?, supplier = ?, pnl_category = ?, bill_date = ?, bill_no = ?, notes = ?, particular_id = ?, particular_name = ?
                    WHERE id = ?
                ''', (name, f.get('dose_unit'), qty, cost, p_date, supplier, pnl_cat, f.get('bill_date') or None, f.get('bill_no', '').strip(), f.get('notes', '').strip(), particular_id, particular_name, id))
                
                # Check if inventory row exists
                inv_row = db.execute("SELECT id, opening_stock, used_qty, wastage_qty FROM medicine_inventory WHERE purchase_id = ?", (id,)).fetchone()
                if inv_row:
                    opening = inv_row['opening_stock'] or 0.0
                    used = inv_row['used_qty'] or 0.0
                    wastage = inv_row['wastage_qty'] or 0.0
                    closing = opening + qty - used - wastage
                    db.execute('''
                        UPDATE medicine_inventory 
                        SET medicine_name = ?, purchased_qty = ?, closing_stock = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ?
                        WHERE purchase_id = ?
                    ''', (name, qty, closing, cost_per_unit, cost, p_date, supplier, id))
                else:
                    # Insert new inventory row if it didn't exist
                    last = db.execute("SELECT closing_stock FROM medicine_inventory WHERE medicine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
                    opening = last['closing_stock'] if last else 0.0
                    closing = opening + qty
                    db.execute('''
                        INSERT INTO medicine_inventory (medicine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
                        VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, opening, qty, closing, 'Doses', cost_per_unit, cost, p_date, supplier, id))
            else:
                db.execute('''
                    UPDATE vaccine_purchases SET vaccine_name = ?, quantity = ?, cost = ?, purchase_date = ?, supplier = ?, pnl_category = ?, bill_date = ?, bill_no = ?, notes = ?, particular_id = ?, particular_name = ?
                    WHERE id = ?
                ''', (name, qty, cost, p_date, supplier, pnl_cat, f.get('bill_date') or None, f.get('bill_no', '').strip(), f.get('notes', '').strip(), particular_id, particular_name, id))
                
                # Check if inventory row exists
                inv_row = db.execute("SELECT id, opening_stock, used_qty, wastage_qty FROM vaccine_inventory WHERE purchase_id = ?", (id,)).fetchone()
                if inv_row:
                    opening = inv_row['opening_stock'] or 0.0
                    used = inv_row['used_qty'] or 0.0
                    wastage = inv_row['wastage_qty'] or 0.0
                    closing = opening + qty - used - wastage
                    db.execute('''
                        UPDATE vaccine_inventory 
                        SET vaccine_name = ?, purchased_qty = ?, closing_stock = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ?
                        WHERE purchase_id = ?
                    ''', (name, qty, closing, cost_per_unit, cost, p_date, supplier, id))
                else:
                    # Insert new inventory row if it didn't exist
                    last = db.execute("SELECT closing_stock FROM vaccine_inventory WHERE vaccine_name = ? ORDER BY id DESC LIMIT 1", (name,)).fetchone()
                    opening = last['closing_stock'] if last else 0.0
                    closing = opening + qty
                    db.execute('''
                        INSERT INTO vaccine_inventory (vaccine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
                        VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, opening, qty, closing, 'Doses', cost_per_unit, cost, p_date, supplier, id))
            
            # Now insert the new goats_data and expenses rows!
            desc = f"Purchased {qty} Doses of {name} from {supplier}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', ?, ?, ?)
            ''', (p_date, sub_type.capitalize(), cost, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status, bill_date, bill_no, particular_id, pnl_category)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid', ?, ?, ?, ?)
            ''', (particular_name or pnl_cat, cost, p_date, desc, supplier, f.get('bill_date') or None, f.get('bill_no', '').strip(), particular_id, pnl_cat))
            
            db.commit()
            flash('Health Supplies Voucher updated successfully!', 'success')
            
        elif v_type == 'other':
            # Get old record to delete its expense entry
            old_ov = db.execute('SELECT * FROM other_vouchers WHERE id = ?', (id,)).fetchone()
            if old_ov:
                db.execute("DELETE FROM expenses WHERE date = ? AND vendor_name = ? AND amount = ? AND status = 'Paid'",
                           (old_ov['voucher_date'], old_ov['supplier_name'], old_ov['amount'] or 0))

            new_supplier = f.get('supplier_name', '').strip()
            new_particular_id = f.get('particular_id') or None
            new_particular_name = f.get('particular_name', '').strip()
            if new_particular_id and not new_particular_name:
                p = db.execute('SELECT name FROM expense_particulars WHERE id=?', (new_particular_id,)).fetchone()
                new_particular_name = p['name'] if p else ''
            new_bill_date = f.get('bill_date') or None
            new_bill_no = f.get('bill_no', '').strip()
            new_qty = f.get('quantity') or None
            new_qty = float(new_qty) if new_qty else None
            new_unit_id = f.get('unit_id') or None
            new_unit_name = f.get('unit_name', '').strip()
            if new_unit_id and not new_unit_name:
                u = db.execute('SELECT unit_name FROM expense_units WHERE id=?', (new_unit_id,)).fetchone()
                new_unit_name = u['unit_name'] if u else ''
            new_amount = float(f.get('amount') or 0)
            new_notes = f.get('notes', '').strip()

            db.execute('''
                UPDATE other_vouchers
                SET voucher_date=?, supplier_name=?, particular_id=?, particular_name=?,
                    bill_date=?, bill_no=?, quantity=?, unit_id=?, unit_name=?,
                    amount=?, notes=?, pnl_category=?
                WHERE id=?
            ''', (p_date, new_supplier, new_particular_id, new_particular_name,
                  new_bill_date, new_bill_no, new_qty, new_unit_id, new_unit_name,
                  new_amount, new_notes, pnl_cat or 'Direct Expenses', id))

            # Re-insert expense entry
            exp_desc_edit = f"Other Voucher: {new_particular_name or 'Expense'} from {new_supplier or 'Supplier'}. Bill No: {new_bill_no or 'N/A'}. {new_notes or ''}".strip('. ')
            if new_amount > 0:
                db.execute('''
                    INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                    VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid')
                ''', (pnl_cat or new_particular_name or 'Direct Expenses', new_amount, p_date, exp_desc_edit, new_supplier))

            db.commit()
            flash('Other Voucher updated successfully!', 'success')

        return redirect(url_for('voucher_register', v_type=v_type))

    particulars = db.execute("""
        SELECT ep.* FROM expense_particulars ep
        LEFT JOIN expense_ledgers el ON ep.ledger_id = el.id
        LEFT JOIN ledger_groups lg ON el.ledger_group = lg.group_name
        WHERE lg.group_type IS NULL OR lg.group_type = 'Expense'
        ORDER BY ep.name
    """).fetchall()
    expense_units = db.execute('SELECT * FROM expense_units ORDER BY unit_name').fetchall()
    ledgers = db.execute('SELECT * FROM expense_ledgers ORDER BY ledger_name').fetchall()
    ledger_groups = db.execute("SELECT * FROM ledger_groups WHERE group_type = 'Expense' ORDER BY group_name").fetchall()
    today_str = datetime.now().strftime('%Y-%m-%d')
    edit_date = record.get('voucher_date') if v_type == 'other' else record.get('purchase_date', '')
    return render_template('voucher_form.html', v_type=v_type, sub_type=sub_type, action='Edit', record=record, today=edit_date, particulars=particulars, expense_units=expense_units, ledgers=ledgers, ledger_groups=ledger_groups)

@app.route('/vouchers/<v_type>/delete/<int:id>', methods=['POST'])
@app.route('/vouchers/<v_type>/delete/<sub_type>/<int:id>', methods=['POST'])
def voucher_delete(v_type, id, sub_type=None):
    if v_type not in ['goat', 'feed', 'health', 'other']:
        flash('Invalid voucher type!', 'danger')
        return redirect(url_for('vouchers'))
        
    db = get_db()
    
    if v_type == 'goat':
        record = db.execute('SELECT * FROM purchases WHERE id = ?', (id,)).fetchone()
        if record:
            tag_id = record['tag_id']
            # Delete linked expense entry
            db.execute("DELETE FROM expenses WHERE date = ? AND amount = ? AND vendor_name = ? AND status = 'Paid'",
                       (record['purchase_date'], record['price'], record['seller_name']))
            db.execute('DELETE FROM purchases WHERE id = ?', (id,))
            db.execute('DELETE FROM master_records WHERE tag_no = ?', (tag_id,))
            db.execute('DELETE FROM goats_data WHERE tag_number = ?', (tag_id,))
            db.execute('DELETE FROM eligible_to_sell WHERE tag_id = ?', (tag_id,))
            db.commit()
            flash('Goat Purchase Voucher and connected logs deleted successfully!', 'success')
            
    elif v_type == 'feed':
        old = db.execute("SELECT * FROM feed_purchases WHERE id = ?", (id,)).fetchone()
        if old:
            db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Feed' AND amount = ?", (old['purchase_date'], old['cost']))
            db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Feed Purchase' AND amount = ? AND vendor_name = ?", (old['purchase_date'], old['cost'], old['supplier']))
        db.execute('DELETE FROM feed_purchases WHERE id = ?', (id,))
        db.execute('DELETE FROM feed_inventory WHERE purchase_id = ?', (id,))
        db.commit()
        flash('Feed Purchase Voucher, linked inventory, and connected expense records deleted!', 'success')
        
    elif v_type == 'health':
        if sub_type == 'medicine':
            old = db.execute("SELECT * FROM medicine_purchases WHERE id = ?", (id,)).fetchone()
            if old:
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Medicine' AND amount = ?", (old['purchase_date'], old['cost']))
                db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Medicine Purchase' AND amount = ? AND vendor_name = ?", (old['purchase_date'], old['cost'], old['supplier']))
            db.execute('DELETE FROM medicine_purchases WHERE id = ?', (id,))
            db.execute('DELETE FROM medicine_inventory WHERE purchase_id = ?', (id,))
            flash('Medicine Voucher, linked inventory, and connected expense records deleted!', 'success')
        else:
            old = db.execute("SELECT * FROM vaccine_purchases WHERE id = ?", (id,)).fetchone()
            if old:
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Vaccine' AND amount = ?", (old['purchase_date'], old['cost']))
                db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Vaccine Purchase' AND amount = ? AND vendor_name = ?", (old['purchase_date'], old['cost'], old['supplier']))
            db.execute('DELETE FROM vaccine_purchases WHERE id = ?', (id,))
            db.execute('DELETE FROM vaccine_inventory WHERE purchase_id = ?', (id,))
            flash('Vaccine Voucher, linked inventory, and connected expense records deleted!', 'success')
        db.commit()
        
    elif v_type == 'other':
        old_ov = db.execute('SELECT * FROM other_vouchers WHERE id = ?', (id,)).fetchone()
        if old_ov:
            # Delete linked expense entry
            db.execute("DELETE FROM expenses WHERE date = ? AND vendor_name = ? AND amount = ? AND status = 'Paid'",
                       (old_ov['voucher_date'], old_ov['supplier_name'], old_ov['amount'] or 0))
        db.execute('DELETE FROM other_vouchers WHERE id = ?', (id,))
        db.commit()
        flash('Other Voucher deleted successfully!', 'success')
        
    return redirect(url_for('voucher_register', v_type=v_type))

# BACKWARD COMPATIBILITY REDIRECTS FOR OLD PURCHASES
@app.route('/purchases')
def purchases():
    return redirect(url_for('vouchers'))

@app.route('/purchase_goat', methods=['GET', 'POST'])
def purchase_goat():
    return redirect(url_for('voucher_add', v_type='goat'))

@app.route('/purchase_feed', methods=['GET', 'POST'])
def purchase_feed():
    return redirect(url_for('voucher_add', v_type='feed'))

@app.route('/purchase_medicine', methods=['GET', 'POST'])
def purchase_medicine():
    return redirect(url_for('voucher_add', v_type='health'))

@app.route('/purchase_vaccine', methods=['GET', 'POST'])
def purchase_vaccine():
    return redirect(url_for('voucher_add', v_type='health'))

@app.route('/feed_purchase_edit/<int:id>', methods=['GET', 'POST'])
def feed_purchase_edit(id):
    return redirect(url_for('voucher_edit', v_type='feed', id=id))

@app.route('/feed_purchase_delete/<int:id>', methods=['POST'])
def feed_purchase_delete(id):
    return redirect(url_for('voucher_delete', v_type='feed', id=id))

@app.route('/med_purchase_edit/<int:id>', methods=['GET', 'POST'])
def med_purchase_edit(id):
    return redirect(url_for('voucher_edit', v_type='health', sub_type='medicine', id=id))

@app.route('/med_purchase_delete/<int:id>', methods=['POST'])
def med_purchase_delete(id):
    return redirect(url_for('voucher_delete', v_type='health', sub_type='medicine', id=id))

@app.route('/vac_purchase_edit/<int:id>', methods=['GET', 'POST'])
def vac_purchase_edit(id):
    return redirect(url_for('voucher_edit', v_type='health', sub_type='vaccine', id=id))

@app.route('/vac_purchase_delete/<int:id>', methods=['POST'])
def vac_purchase_delete(id):
    return redirect(url_for('voucher_delete', v_type='health', sub_type='vaccine', id=id))

@app.route('/farm_settings', methods=['GET', 'POST'])
def farm_settings():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db.execute('''INSERT OR REPLACE INTO farm_settings (id, farm_name, address, phone, email, bank_name, account_no, ifsc_code, gst_no)
                      VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (f.get('farm_name'), f.get('address'), f.get('phone'), f.get('email'),
             f.get('bank_name'), f.get('account_no'), f.get('ifsc_code'), f.get('gst_no')))
        db.commit()
        flash('Settings updated!', 'success')
        return redirect(url_for('farm_settings'))
    settings = db.execute('SELECT * FROM farm_settings WHERE id = 1').fetchone()
    user = db.execute('SELECT mfa_enabled FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    mfa_enabled = user['mfa_enabled'] if user else 0
    return render_template('farm_settings.html', settings=settings, mfa_enabled=mfa_enabled)

@app.route('/reports_list')
def reports_list():
    db = get_db()
    records = db.execute('SELECT * FROM reports ORDER BY generated_date DESC').fetchall()
    return render_template('reports.html', records=records)

@app.route('/invoice')
@app.route('/invoice/<int:sales_id>')
def generate_invoice(sales_id=None):
    if sales_id is None:
        return redirect(url_for('sales'))
    return redirect(url_for('sales_invoice', s_type='goat', id=sales_id))

@app.route('/invoice_txt/<int:sales_id>')
def generate_invoice_txt(sales_id):
    return redirect(url_for('sales_invoice_txt', s_type='goat', id=sales_id))

@app.route('/invoice_pdf/<int:sales_id>')
def generate_invoice_pdf(sales_id):
    return redirect(url_for('sales_invoice', s_type='goat', id=sales_id))

@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    """Clear all data from the database. Requires confirmation."""
    confirmation = request.form.get('confirmation', '').strip().lower()
    
    if confirmation != 'yes':
        flash('Confirmation failed. Data not cleared.', 'danger')
        return redirect(url_for('farm_settings'))
    
    db = get_db()
    try:
        # Delete from referencing (child) tables first to avoid foreign key violations
        db.execute('DELETE FROM eligible_to_sell')
        db.execute('DELETE FROM other_vouchers')
        db.execute('DELETE FROM other_sales_records')
        db.execute('DELETE FROM medicine_inventory')
        db.execute('DELETE FROM vaccine_inventory')
        db.execute('DELETE FROM batch_reminders')
        db.execute('DELETE FROM user_login_tracking')
        
        # Delete from all other transactional and master tables
        db.execute('DELETE FROM goats_data')
        db.execute('DELETE FROM master_records')
        db.execute('DELETE FROM sales_records')
        db.execute('DELETE FROM medicine_records')
        db.execute('DELETE FROM medicine_history')
        db.execute('DELETE FROM mortality_records')
        db.execute('DELETE FROM feed_inventory')
        db.execute('DELETE FROM kid_records')
        db.execute('DELETE FROM purchases')
        db.execute('DELETE FROM vaccine_records')
        db.execute('DELETE FROM doctor_details')
        db.execute('DELETE FROM expenses')
        db.execute('DELETE FROM equipment')
        db.execute('DELETE FROM equipment_services')
        db.execute('DELETE FROM salary_payments')
        db.execute('DELETE FROM attendance')
        db.execute('DELETE FROM employee_wages')
        db.execute('DELETE FROM tasks')
        db.execute('DELETE FROM leaves')
        db.execute('DELETE FROM finances')
        db.execute('DELETE FROM medicine_purchases')
        db.execute('DELETE FROM vaccine_purchases')
        db.execute('DELETE FROM feed_purchases')
        db.execute('DELETE FROM employees')
        db.execute('DELETE FROM reports')
        db.execute('DELETE FROM breeds')
        db.execute('DELETE FROM suppliers')
        
        db.commit()
        flash('All data has been successfully cleared!', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error clearing data: {str(e)}', 'danger')
    
    return redirect(url_for('farm_settings'))

# ── EMPLOYEES ──────────────────────────────────────────────────────────────────
def init_employee_tables():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, role TEXT, phone TEXT, address TEXT,
            join_date DATE, wage_type TEXT, wage_rate REAL DEFAULT 0,
            status TEXT DEFAULT 'Active', notes TEXT,
            aadhar_no TEXT, pan_no TEXT, bank_name TEXT, account_no TEXT, ifsc_code TEXT)''')
        
        # Use add_column to update existing tables
        def add_col(table, col, typ):
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError: pass

        add_col("employees", "sr_no", "INTEGER")
        add_col("employees", "aadhar_no", "TEXT")
        add_col("employees", "pan_no", "TEXT")
        add_col("employees", "bank_name", "TEXT")
        add_col("employees", "account_no", "TEXT")
        add_col("employees", "ifsc_code", "TEXT")
        
        # Populate sr_no if empty/null
        conn.execute('UPDATE employees SET sr_no = id WHERE sr_no IS NULL OR sr_no = 0')
        add_col("expenses", "bill_file", "TEXT")
        add_col("expenses", "status", "TEXT DEFAULT 'Pending'")
        add_col("expenses", "pnl_category", "TEXT DEFAULT 'Direct Expenses'")
        conn.execute('''CREATE TABLE IF NOT EXISTS employee_wages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER UNIQUE, daily_wage REAL DEFAULT 0,
            weekly_salary REAL DEFAULT 0, monthly_salary REAL DEFAULT 0,
            overtime_rate REAL DEFAULT 0, bonus REAL DEFAULT 0,
            advance_salary REAL DEFAULT 0, pending_payment REAL DEFAULT 0,
            last_updated DATE)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, date DATE, status TEXT, notes TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS salary_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, month INTEGER, year INTEGER,
            total_days INTEGER, present_days INTEGER, gross_salary REAL,
            deductions REAL, net_salary REAL, paid_date DATE,
            payment_mode TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, task_name TEXT, description TEXT,
            assigned_date DATE, due_date DATE, priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending', completion_percentage INTEGER DEFAULT 0)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS leaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER, leave_type TEXT, start_date DATE,
            end_date DATE, reason TEXT, status TEXT DEFAULT 'Pending')''')
        conn.execute('''CREATE TABLE IF NOT EXISTS expense_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category_name TEXT UNIQUE)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT, amount REAL, date DATE,
            description TEXT, vendor_name TEXT, payment_mode TEXT,
            receipt_no TEXT, notes TEXT, status TEXT DEFAULT 'Pending',
            pnl_category TEXT DEFAULT 'Direct Expenses')''')
        conn.execute('''CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, type TEXT, purchase_date DATE, purchase_cost REAL,
            supplier TEXT, status TEXT DEFAULT 'Good', notes TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS equipment_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER,
            vendor_name TEXT,
            service_date DATE NOT NULL,
            service_cost REAL DEFAULT 0,
            description TEXT,
            status TEXT,
            notes TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS finances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT, category TEXT, amount REAL, date DATE,
            description TEXT, reference_id TEXT, notes TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS farm_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farm_name TEXT, address TEXT, phone TEXT, email TEXT,
            bank_name TEXT, account_no TEXT, ifsc_code TEXT,
            gst_no TEXT, logo_path TEXT
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_type TEXT, generated_date DATE,
            from_date DATE, to_date DATE, file_path TEXT, notes TEXT
        )''')
        conn.commit()


with app.app_context():
    if not db_connection_error:
        init_employee_tables()

@app.route('/employees')
def employees():
    db = get_db()
    records = db.execute('SELECT * FROM employees ORDER BY CAST(sr_no AS INTEGER) ASC').fetchall()
    return render_template('employees.html', records=records)

@app.route('/employee_add', methods=['GET', 'POST'])
def employee_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        role = f.get('role', '').strip()
        if not role:
            flash('role is needed', 'danger')
            res = db.execute("SELECT MAX(CAST(sr_no AS INTEGER)) FROM employees").fetchone()[0]
            next_sr = (res or 0) + 1
            return render_template('employee_add.html', next_sr=next_sr, form_data=f)
            
        db.execute('''INSERT INTO employees (sr_no, name, role, phone, address, join_date, wage_type, wage_rate, status, notes, 
                                             aadhar_no, pan_no, bank_name, account_no, ifsc_code) 
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (f.get('sr_no'), f.get('name'), role, f.get('phone'), f.get('address'), f.get('joining_date'),
             f.get('wage_type'), f.get('wage_rate', 0), 'Active', f.get('notes'),
             f.get('aadhar_no'), f.get('pan_no'), f.get('bank_name'), f.get('account_no'), f.get('ifsc_code')))
        db.commit()
        flash('Employee added!', 'success')
        return redirect(url_for('employees'))
        
    res = db.execute("SELECT MAX(CAST(sr_no AS INTEGER)) FROM employees").fetchone()[0]
    next_sr = (res or 0) + 1
    return render_template('employee_add.html', next_sr=next_sr)

@app.route('/employee_edit/<int:emp_id>', methods=['GET', 'POST'])
def employee_edit(emp_id):
    db = get_db()
    record = db.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    if not record:
        flash('Employee record not found or has been deleted.', 'danger')
        return redirect(url_for('employees'))
    if request.method == 'POST':
        f = request.form
        role = f.get('role', '').strip()
        if not role:
            flash('role is needed', 'danger')
            return render_template('employee_edit.html', record=record)
            
        db.execute('''UPDATE employees SET sr_no=?, name=?, role=?, phone=?, address=?, join_date=?, wage_type=?, wage_rate=?, status=?, notes=?,
                                           aadhar_no=?, pan_no=?, bank_name=?, account_no=?, ifsc_code=? WHERE id=?''',
            (f.get('sr_no'), f.get('name'), role, f.get('phone'), f.get('address'), f.get('joining_date'),
             f.get('wage_type'), f.get('wage_rate', 0), f.get('status'), f.get('notes'),
             f.get('aadhar_no'), f.get('pan_no'), f.get('bank_name'), f.get('account_no'), f.get('ifsc_code'), emp_id))
        db.commit()
        flash('Employee updated!', 'success')
        return redirect(url_for('employees'))
    return render_template('employee_edit.html', record=record)

@app.route('/employee_detail/<int:emp_id>')
def employee_detail(emp_id):
    db = get_db()
    emp = db.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    if not emp:
        flash('Not found.', 'danger')
        return redirect(url_for('employees'))
        
    # Calculate attendance statistics
    stats = db.execute('''
        SELECT 
            SUM(CASE WHEN status IN ('P', 'Present') THEN 1 ELSE 0 END) as present_cnt,
            SUM(CASE WHEN status IN ('L', 'Leave', 'On Leave') THEN 1 ELSE 0 END) as leave_cnt
        FROM attendance WHERE employee_id = ?
    ''', (emp_id,)).fetchone()
    
    total_present = stats['present_cnt'] or 0
    total_absent = 0
    total_leaves = stats['leave_cnt'] or 0
    
    wages = db.execute('SELECT * FROM employee_wages WHERE employee_id=?', (emp_id,)).fetchone()
    attendance = db.execute('SELECT * FROM attendance WHERE employee_id=? ORDER BY date DESC LIMIT 30', (emp_id,)).fetchall()
    payments = db.execute('SELECT * FROM salary_payments WHERE employee_id=? ORDER BY paid_date DESC', (emp_id,)).fetchall()
    
    return render_template('employee_detail.html', employee=emp, attendance=attendance, payments=payments,
                           total_present=total_present, total_absent=total_absent, total_leaves=total_leaves, wages=wages)

@app.route('/employee_delete/<int:emp_id>', methods=['POST'])
def employee_delete(emp_id):
    db = get_db()
    db.execute('DELETE FROM employees WHERE id=?', (emp_id,))
    db.execute('DELETE FROM attendance WHERE employee_id=?', (emp_id,))
    db.execute('DELETE FROM salary_payments WHERE employee_id=?', (emp_id,))
    db.execute('DELETE FROM leaves WHERE employee_id=?', (emp_id,))
    db.execute('DELETE FROM tasks WHERE employee_id=?', (emp_id,))
    db.execute('DELETE FROM employee_wages WHERE employee_id=?', (emp_id,))
    db.commit()
    flash('Employee and all related attendance, leaves, wages, and salary logs deleted successfully!', 'success')
    return redirect(url_for('employees'))


# ── ATTENDANCE ──────────────────────────────────────────────────────────────────
@app.route('/attendance')
def attendance_view():
    db = get_db()
    date_filter = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Fetch all active employees
    emps = db.execute("SELECT * FROM employees WHERE status='Active' ORDER BY CAST(sr_no AS INTEGER) ASC").fetchall()
    
    # Fetch existing attendance records for the selected date
    existing = db.execute('SELECT * FROM attendance WHERE date = ?', (date_filter,)).fetchall()
    existing_map = {r['employee_id']: r for r in existing}
    
    return render_template('attendance.html', employees=emps, existing_map=existing_map, date_filter=date_filter)

@app.route('/attendance_save', methods=['POST'])
def attendance_save():
    db = get_db()
    date_val = request.form.get('date')
    if not date_val:
        flash('Date is required!', 'danger')
        return redirect(url_for('attendance_view'))
        
    emps = db.execute("SELECT id FROM employees WHERE status='Active'").fetchall()
    for emp in emps:
        emp_id = emp['id']
        status = request.form.get(f'status_{emp_id}', 'Present')
        notes = request.form.get(f'notes_{emp_id}', '').strip()
        
        # Check if record exists for this employee and date
        existing = db.execute('SELECT id FROM attendance WHERE employee_id=? AND date=?', (emp_id, date_val)).fetchone()
        if existing:
            db.execute('UPDATE attendance SET status=?, notes=? WHERE id=?', (status, notes, existing['id']))
        else:
            db.execute('INSERT INTO attendance (employee_id, date, status, notes) VALUES (?, ?, ?, ?)',
                       (emp_id, date_val, status, notes))
                       
    db.commit()
    flash(f'Attendance sheet for {date_val} successfully saved!', 'success')
    return redirect(url_for('attendance_view', date=date_val))

@app.route('/attendance_summary')
def attendance_summary():
    db = get_db()
    month = request.args.get('month', datetime.now().strftime('%m'))
    year = request.args.get('year', datetime.now().strftime('%Y'))
    data = db.execute('''SELECT e.id, e.name, e.sr_no, 
        SUM(CASE WHEN a.status IN ('P', 'Present') THEN 1 ELSE 0 END) as present,
        SUM(CASE WHEN a.status IN ('L', 'Leave', 'On Leave') THEN 1 ELSE 0 END) as leave
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id
            AND TO_CHAR(a.date, 'MM') = ? AND TO_CHAR(a.date, 'YYYY') = ?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (month, year)).fetchall()
    farm = db.execute('SELECT * FROM farm_info LIMIT 1').fetchone()
    return render_template('attendance_summary.html', data=data, month=month, year=year, farm=farm)

@app.route('/salary_calculate', methods=['GET', 'POST'])
def salary_calculate():
    db = get_db()
    import calendar
    from datetime import datetime, timedelta
    
    today = datetime.now()
    
    month = request.args.get('month') or request.form.get('month')
    year = request.args.get('year') or request.form.get('year')
    start_day = request.args.get('start_day') or request.form.get('start_day') or '1'
    
    if not year:
        year = str(today.year)
    if not month:
        month = f"{today.month:02d}"
    else:
        try:
            month = f"{int(month):02d}"
        except ValueError:
            month = f"{today.month:02d}"
            
    try:
        year_int = int(year)
        month_int = int(month)
    except ValueError:
        year_int = today.year
        month_int = today.month
        year = str(year_int)
        month = f"{month_int:02d}"
        
    last_day_val = calendar.monthrange(year_int, month_int)[1]
    
    end_day = request.args.get('end_day') or request.form.get('end_day') or str(last_day_val)
    
    try:
        start_day_int = min(max(1, int(start_day)), last_day_val)
    except ValueError:
        start_day_int = 1
        
    try:
        end_day_int = min(max(1, int(end_day)), last_day_val)
    except ValueError:
        end_day_int = last_day_val
        
    if start_day_int > end_day_int:
        start_day_int, end_day_int = end_day_int, start_day_int
        
    start_date = f"{year}-{month}-{start_day_int:02d}"
    end_date = f"{year}-{month}-{end_day_int:02d}"
    today_date = today.strftime('%Y-%m-%d')
    
    total_days = (end_day_int - start_day_int) + 1
    
    # Query attendance strictly for the selected period
    data = db.execute('''SELECT e.id, e.name, e.role, e.wage_type, e.wage_rate, e.sr_no,
        SUM(CASE WHEN a.status IN ('P', 'Present') THEN 1 ELSE 0 END) as present_days
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id AND a.date BETWEEN ? AND ?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (start_date, end_date)).fetchall()
        
    salaries = []
    for emp in data:
        present = emp['present_days'] or 0
        wage_type = emp['wage_type']
        wage_rate = emp['wage_rate'] or 0
        
        computed = 0.0
        if wage_type == 'Monthly':
            computed = (wage_rate / float(total_days)) * present
        elif wage_type == 'Weekly':
            computed = (wage_rate / 7.0) * present
        elif wage_type == 'Daily':
            computed = wage_rate * present
            
        # Get paid amount in this period range
        paid = db.execute('''SELECT SUM(net_salary) FROM salary_payments 
                             WHERE employee_id=? AND paid_date BETWEEN ? AND ?''', 
                           (emp['id'], start_date, end_date)).fetchone()[0] or 0.0
        
        salaries.append({
            'id': emp['id'],
            'sr_no': emp['sr_no'],
            'name': emp['name'],
            'role': emp['role'],
            'present': present,
            'wage_type': wage_type,
            'wage_rate': wage_rate,
            'computed': computed,
            'paid': paid,
            'balance': max(0.0, computed - paid)
        })
        
    return render_template('salary_calculate.html', 
                           salaries=salaries, 
                           month=month, 
                           year=year, 
                           start_day=start_day_int,
                           end_day=end_day_int,
                           start_date=start_date,
                           end_date=end_date,
                           total_days=total_days,
                           today_date=today_date)

@app.route('/pay_salary', methods=['POST'])
def pay_salary():
    db = get_db()
    emp_id = request.form.get('employee_id')
    amount = float(request.form.get('amount') or 0)
    date = request.form.get('payment_date') or datetime.now().strftime('%Y-%m-%d')
    method = request.form.get('payment_mode') or 'Cash'
    
    month = int(request.form.get('month', datetime.now().month))
    year = int(request.form.get('year', datetime.now().year))
    
    db.execute('''INSERT INTO salary_payments (employee_id, month, year, net_salary, paid_date, payment_mode) 
                  VALUES (?, ?, ?, ?, ?, ?)''',
               (emp_id, month, year, amount, date, method))
    
    # Also insert into expenses to reflect in P&L
    emp = db.execute('SELECT name FROM employees WHERE id=?', (emp_id,)).fetchone()
    db.execute('''INSERT INTO expenses (date, category, amount, description, status) 
                  VALUES (?, 'Labor', ?, ?, 'Approved')''',
               (date, amount, f"Salary payment for {emp['name']} ({month}/{year})"))
               
    db.commit()
    flash('Salary paid successfully.', 'success')
    return redirect(url_for('salary_calculate'))

# ── WAGES ──────────────────────────────────────────────────────────────────────
@app.route('/wages_list')
def wages_list():
    db = get_db()
    search = request.args.get('search', '')
    q = '''SELECT e.*, w.daily_wage, w.weekly_salary, w.monthly_salary,
           w.bonus, w.pending_payment, w.last_updated
           FROM employees e LEFT JOIN employee_wages w ON e.id=w.employee_id WHERE 1=1'''
    p = []
    if search:
        q += ' AND (e.id LIKE ? OR e.name LIKE ?)'
        p += [f'%{search}%', f'%{search}%']
    wages_data = db.execute(q, p).fetchall()
    return render_template('wages.html', wages_data=wages_data, search=search)

@app.route('/wages_edit/<int:emp_id>', methods=['GET', 'POST'])
def wages_edit(emp_id):
    db = get_db()
    emp = db.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    if not emp:
        flash('Not found.', 'danger')
        return redirect(url_for('wages_list'))
    db.execute('INSERT OR IGNORE INTO employee_wages (employee_id) VALUES (?)', (emp_id,))
    db.commit()
    wages = db.execute('SELECT * FROM employee_wages WHERE employee_id=?', (emp_id,)).fetchone()
    if request.method == 'POST':
        f = request.form
        db.execute('''UPDATE employee_wages SET daily_wage=?,weekly_salary=?,monthly_salary=?,
            overtime_rate=?,bonus=?,advance_salary=?,pending_payment=?,last_updated=?
            WHERE employee_id=?''',
            (f.get('daily_wage') or 0, f.get('weekly_salary') or 0, f.get('monthly_salary') or 0,
             f.get('overtime_rate') or 0, f.get('bonus') or 0, f.get('advance_salary') or 0,
             f.get('pending_payment') or 0, datetime.now().strftime('%Y-%m-%d'), emp_id))
        db.commit()
        flash('Wages updated!', 'success')
        return redirect(url_for('wages_list'))
    return render_template('wages_edit.html', employee=emp, wages=wages)

# ── TASKS ──────────────────────────────────────────────────────────────────────
@app.route('/tasks')
def tasks():
    db = get_db()
    status_filter = request.args.get('status', '')
    q = '''SELECT t.*, e.id as employee_id, e.name FROM tasks t
           JOIN employees e ON t.employee_id=e.id WHERE 1=1'''
    p = []
    if status_filter:
        q += ' AND t.status=?'
        p.append(status_filter)
    q += ' ORDER BY t.due_date ASC'
    records = db.execute(q, p).fetchall()
    emps = db.execute("SELECT * FROM employees WHERE status='Active' ORDER BY name").fetchall()
    statuses = ['Pending', 'In Progress', 'Completed']
    return render_template('tasks.html', records=records, employees=emps, statuses=statuses, status_filter=status_filter)

@app.route('/task_add', methods=['POST'])
def task_add():
    db = get_db()
    f = request.form
    db.execute('INSERT INTO tasks (employee_id,task_name,description,assigned_date,due_date,priority,status,completion_percentage) VALUES (?,?,?,?,?,?,?,?)',
        (f.get('employee_id'), f.get('task_name'), f.get('description'),
         f.get('assigned_date') or datetime.now().strftime('%Y-%m-%d'),
         f.get('due_date'), f.get('priority', 'Medium'), 'Pending', 0))
    db.commit()
    flash('Task assigned!', 'success')
    return redirect(url_for('tasks'))

@app.route('/task_update/<int:task_id>', methods=['POST'])
def task_update(task_id):
    db = get_db()
    status = request.form.get('status', 'Pending')
    pct = 100 if status == 'Completed' else (50 if status == 'In Progress' else 0)
    db.execute('UPDATE tasks SET status=?, completion_percentage=? WHERE id=?', (status, pct, task_id))
    db.commit()
    flash('Task updated!', 'success')
    return redirect(url_for('tasks'))

# ── LEAVES ──────────────────────────────────────────────────────────────────────
@app.route('/leaves')
def leaves():
    db = get_db()
    status_filter = request.args.get('status', '')
    q = '''SELECT l.*, e.id as employee_id, e.name FROM leaves l
           JOIN employees e ON l.employee_id=e.id WHERE 1=1'''
    p = []
    if status_filter:
        q += ' AND l.status=?'
        p.append(status_filter)
    q += ' ORDER BY l.start_date DESC'
    records = db.execute(q, p).fetchall()
    emps = db.execute("SELECT * FROM employees WHERE status='Active' ORDER BY name").fetchall()
    statuses = ['Pending', 'Approved', 'Rejected']
    return render_template('leaves.html', records=records, employees=emps, statuses=statuses, status_filter=status_filter)

@app.route('/leave_add', methods=['POST'])
def leave_add():
    db = get_db()
    f = request.form
    db.execute('INSERT INTO leaves (employee_id,leave_type,start_date,end_date,reason,status) VALUES (?,?,?,?,?,?)',
        (f.get('employee_id'), f.get('leave_type'), f.get('start_date'), f.get('end_date'), f.get('reason'), 'Pending'))
    db.commit()
    flash('Leave request submitted!', 'success')
    return redirect(url_for('leaves'))

@app.route('/leave_status/<int:leave_id>/<status>', methods=['POST'])
def leave_status(leave_id, status):
    db = get_db()
    db.execute('UPDATE leaves SET status=? WHERE id=?', (status, leave_id))
    db.commit()
    flash(f'Leave {status}.', 'success')
    return redirect(url_for('leaves'))



# ── EXPENSES ──────────────────────────────────────────────────────────────────
@app.route('/expenses')
def expenses():
    db = get_db()
    category = request.args.get('category', '')
    month = request.args.get('month', '')
    year = request.args.get('year', '')
    
    q = 'SELECT * FROM expenses WHERE 1=1'
    p = []
    
    if category:
        q += ' AND (category LIKE ? OR vendor_name LIKE ? OR description LIKE ? OR notes LIKE ? OR pnl_category LIKE ?)'
        p.append(f'%{category}%')
        p.append(f'%{category}%')
        p.append(f'%{category}%')
        p.append(f'%{category}%')
        p.append(f'%{category}%')
        
    if month and month != 'All':
        q += " AND TO_CHAR(date, 'MM') = ?"
        p.append(f"{int(month):02d}")
        
    if year and year != 'All':
        q += " AND TO_CHAR(date, 'YYYY') = ?"
        p.append(str(year))
        
    q += ' ORDER BY date DESC'
    records = db.execute(q, p).fetchall()
    
    return render_template('expenses.html', records=records, category=category, month=month, year=year)

@app.route('/expense_add', methods=['GET', 'POST'])
def expense_add():
    db = get_db()
    today_str = datetime.now().strftime('%Y-%m-%d')
    if request.method == 'POST':
        f = request.form
        
        # Handle file upload for the bill
        bill_file_path = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                if not is_secure_file(file, file.filename):
                    log_security_event('UPLOAD_REJECTED', f"Rejected malicious or unsafe file upload: {file.filename}", filename=file.filename)
                    flash('Invalid or unsafe file format. Only JPG, PNG, and PDF are allowed.', 'danger')
                    return redirect(url_for('expense_add'))
                
                import os
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'bills')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
                bill_file_path = f"/static/uploads/bills/{filename}"
                log_security_event('UPLOAD_SUCCESS', f"File uploaded successfully: {filename}", filename=filename)
        
        p_date = f.get('voucher_date') or today_str
        supplier_name = f.get('supplier_name', '').strip()
        particular_id = f.get('particular_id') or None
        particular_id = int(particular_id) if particular_id else None
        particular_name = f.get('particular_name', '').strip()
        bill_date = f.get('bill_date') or None
        bill_no = f.get('bill_no', '').strip()
        quantity = f.get('quantity') or None
        quantity = float(quantity) if quantity else None
        unit_id = f.get('unit_id') or None
        unit_id = int(unit_id) if unit_id else None
        unit_name = f.get('unit_name', '').strip()
        amount = float(f.get('amount') or 0.0)
        notes = f.get('notes', '').strip()
        pnl_cat = f.get('pnl_category', 'Direct Expenses')

        # Resolve names from DB if only id given
        if particular_id and not particular_name:
            p = db.execute('SELECT name FROM expense_particulars WHERE id=?', (particular_id,)).fetchone()
            particular_name = p['name'] if p else ''
        if unit_id and not unit_name:
            u = db.execute('SELECT unit_name FROM expense_units WHERE id=?', (unit_id,)).fetchone()
            unit_name = u['unit_name'] if u else ''

        exp_desc = f"Expense: {particular_name or 'General'} from {supplier_name or 'Supplier'}. Bill No: {bill_no or 'N/A'}. {notes or ''}".strip('. ')

        db.execute('''
            INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, receipt_no, notes, status, bill_file, pnl_category, particular_id, bill_date, quantity, unit_id, unit_name) 
            VALUES (?, ?, ?, ?, ?, 'Cash', ?, ?, 'Approved', ?, ?, ?, ?, ?, ?, ?)
        ''', (
            particular_name,
            amount,
            p_date,
            exp_desc,
            supplier_name,
            bill_no,
            notes,
            bill_file_path,
            pnl_cat,
            particular_id,
            bill_date,
            quantity,
            unit_id,
            unit_name
        ))
        db.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expenses'))

    particulars = db.execute("""
        SELECT ep.* FROM expense_particulars ep
        LEFT JOIN expense_ledgers el ON ep.ledger_id = el.id
        LEFT JOIN ledger_groups lg ON el.ledger_group = lg.group_name
        WHERE lg.group_type IS NULL OR lg.group_type = 'Expense'
        ORDER BY ep.name
    """).fetchall()
    expense_units = db.execute('SELECT * FROM expense_units ORDER BY unit_name').fetchall()
    ledgers = db.execute('SELECT * FROM expense_ledgers ORDER BY ledger_name').fetchall()
    ledger_groups = db.execute("SELECT * FROM ledger_groups WHERE group_type = 'Expense' ORDER BY group_name").fetchall()
    return render_template('expense_add.html', particulars=particulars, expense_units=expense_units, ledgers=ledgers, ledger_groups=ledger_groups, today=today_str)

@app.route('/expense_approve/<int:expense_id>', methods=['POST'])
def expense_approve(expense_id):
    action = request.form.get('action', 'approve')
    status = 'Approved' if action == 'approve' else 'Rejected'
    db = get_db()
    db.execute('UPDATE expenses SET status=? WHERE id=?', (status, expense_id))
    db.commit()
    flash(f'Expense {status}.', 'success')
    return redirect(url_for('expenses'))

# ── P&L FINANCE MODULE ────────────────────────────────────────────────────────
@app.route('/expense_delete/<int:expense_id>', methods=['POST'])
def expense_delete(expense_id):
    db = get_db()
    db.execute('DELETE FROM expenses WHERE id=?', (expense_id,))
    db.commit()
    flash('Expense record deleted successfully!', 'success')
    return redirect(url_for('expenses'))

@app.route('/expense_edit/<int:expense_id>', methods=['GET', 'POST'])
def expense_edit(expense_id):
    db = get_db()
    record = db.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,)).fetchone()
    
    if not record:
        flash('Expense record not found.', 'danger')
        return redirect(url_for('expenses'))
        
    if request.method == 'POST':
        f = request.form
        
        # Handle file upload for the bill
        bill_file_path = record['bill_file']
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                if not is_secure_file(file, file.filename):
                    log_security_event('UPLOAD_REJECTED', f"Rejected malicious or unsafe file upload: {file.filename}", filename=file.filename)
                    flash('Invalid or unsafe file format. Only JPG, PNG, and PDF are allowed.', 'danger')
                    return redirect(url_for('expense_edit', expense_id=expense_id))
                
                import os
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'bills')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
                bill_file_path = f"/static/uploads/bills/{filename}"
                log_security_event('UPLOAD_SUCCESS', f"File uploaded successfully: {filename}", filename=filename)
                
        p_date = f.get('voucher_date') or datetime.now().strftime('%Y-%m-%d')
        supplier_name = f.get('supplier_name', '').strip()
        particular_id = f.get('particular_id') or None
        particular_id = int(particular_id) if particular_id else None
        particular_name = f.get('particular_name', '').strip()
        bill_date = f.get('bill_date') or None
        bill_no = f.get('bill_no', '').strip()
        quantity = f.get('quantity') or None
        quantity = float(quantity) if quantity else None
        unit_id = f.get('unit_id') or None
        unit_id = int(unit_id) if unit_id else None
        unit_name = f.get('unit_name', '').strip()
        amount = float(f.get('amount') or 0.0)
        notes = f.get('notes', '').strip()
        pnl_cat = f.get('pnl_category', 'Direct Expenses')

        # Resolve names from DB if only id given
        if particular_id and not particular_name:
            p = db.execute('SELECT name FROM expense_particulars WHERE id=?', (particular_id,)).fetchone()
            particular_name = p['name'] if p else ''
        if unit_id and not unit_name:
            u = db.execute('SELECT unit_name FROM expense_units WHERE id=?', (unit_id,)).fetchone()
            unit_name = u['unit_name'] if u else ''

        exp_desc = f"Expense: {particular_name or 'General'} from {supplier_name or 'Supplier'}. Bill No: {bill_no or 'N/A'}. {notes or ''}".strip('. ')

        db.execute('''
            UPDATE expenses 
            SET category = ?, amount = ?, date = ?, description = ?, vendor_name = ?, receipt_no = ?, notes = ?, bill_file = ?, pnl_category = ?, particular_id = ?, bill_date = ?, quantity = ?, unit_id = ?, unit_name = ?
            WHERE id = ?
        ''', (
            particular_name, 
            amount, 
            p_date, 
            exp_desc, 
            supplier_name,
            bill_no,
            notes,
            bill_file_path,
            pnl_cat,
            particular_id,
            bill_date,
            quantity,
            unit_id,
            unit_name,
            expense_id
        ))
        db.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('expenses'))
        
    particulars = db.execute("""
        SELECT ep.* FROM expense_particulars ep
        LEFT JOIN expense_ledgers el ON ep.ledger_id = el.id
        LEFT JOIN ledger_groups lg ON el.ledger_group = lg.group_name
        WHERE lg.group_type IS NULL OR lg.group_type = 'Expense'
        ORDER BY ep.name
    """).fetchall()
    expense_units = db.execute('SELECT * FROM expense_units ORDER BY unit_name').fetchall()
    ledgers = db.execute('SELECT * FROM expense_ledgers ORDER BY ledger_name').fetchall()
    ledger_groups = db.execute("SELECT * FROM ledger_groups WHERE group_type = 'Expense' ORDER BY group_name").fetchall()
    return render_template('expense_edit.html', record=record, particulars=particulars, expense_units=expense_units, ledgers=ledgers, ledger_groups=ledger_groups)

# ── EXPENSES MASTER MODULE ────────────────────────────────────────────────────
@app.route('/expenses_master')
def expenses_master():
    db = get_db()
    ledger_count = db.execute('SELECT COUNT(*) FROM expense_ledgers').fetchone()[0] or 0
    group_count = db.execute('SELECT COUNT(*) FROM ledger_groups').fetchone()[0] or 0
    particular_count = db.execute('SELECT COUNT(*) FROM expense_particulars').fetchone()[0] or 0
    unit_count = db.execute('SELECT COUNT(*) FROM expense_units').fetchone()[0] or 0
    other_voucher_count = db.execute('SELECT COUNT(*) FROM other_vouchers').fetchone()[0] or 0
    other_voucher_sum = db.execute('SELECT SUM(amount) FROM other_vouchers').fetchone()[0] or 0.0
    expense_count = db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0] or 0
    expense_sum = db.execute("SELECT SUM(amount) FROM expenses WHERE status='Approved' OR status='Paid'").fetchone()[0] or 0.0
    return render_template('expenses_master.html',
        ledger_count=ledger_count, group_count=group_count, particular_count=particular_count,
        unit_count=unit_count, other_voucher_count=other_voucher_count,
        other_voucher_sum=other_voucher_sum, expense_count=expense_count,
        expense_sum=expense_sum)

@app.route('/expense_ledgers', methods=['GET', 'POST'])
def expense_ledgers():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            lname = request.form.get('ledger_name', '').strip()
            lgrp = request.form.get('ledger_group', 'Direct Expenses').strip()
            ldesc = request.form.get('description', '').strip()
            if lname:
                try:
                    db.execute('INSERT INTO expense_ledgers (ledger_name, ledger_group, description) VALUES (?, ?, ?)', (lname, lgrp, ldesc))
                    db.commit()
                    flash(f'Ledger "{lname}" created successfully!', 'success')
                except Exception:
                    flash('Ledger name already exists!', 'danger')
            else:
                flash('Ledger name is required.', 'danger')
        return redirect(url_for('expense_ledgers', tab='ledgers'))
    ledgers = db.execute('SELECT * FROM expense_ledgers ORDER BY ledger_group, ledger_name').fetchall()
    groups = [dict(g) for g in db.execute('SELECT * FROM ledger_groups ORDER BY group_name').fetchall()]
    for g in groups:
        g['ledger_count'] = sum(1 for l in ledgers if l['ledger_group'] == g['group_name'])
    group_names = {g['group_name'] for g in groups}
    unassigned_ledgers = [l for l in ledgers if l['ledger_group'] not in group_names or not l['ledger_group']]
    particulars = db.execute('''
        SELECT ep.*, el.ledger_name, el.ledger_group, lg.group_type
        FROM expense_particulars ep
        LEFT JOIN expense_ledgers el ON ep.ledger_id = el.id
        LEFT JOIN ledger_groups lg ON el.ledger_group = lg.group_name
        ORDER BY ep.name
    ''').fetchall()
    return render_template('expense_ledgers.html', ledgers=ledgers, groups=groups, unassigned_ledgers=unassigned_ledgers, particulars=particulars)

@app.route('/expense_ledger_edit/<int:lid>', methods=['GET', 'POST'])
def expense_ledger_edit(lid):
    db = get_db()
    ledger = db.execute('SELECT * FROM expense_ledgers WHERE id=?', (lid,)).fetchone()
    if not ledger:
        flash('Ledger not found.', 'danger')
        return redirect(url_for('expense_ledgers', tab='ledgers'))
    if request.method == 'POST':
        lname = request.form.get('ledger_name', '').strip()
        lgrp = request.form.get('ledger_group', 'Direct Expenses').strip()
        ldesc = request.form.get('description', '').strip()
        if lname:
            try:
                db.execute('UPDATE expense_ledgers SET ledger_name=?, ledger_group=?, description=? WHERE id=?', (lname, lgrp, ldesc, lid))
                db.commit()
                flash('Ledger updated!', 'success')
            except Exception:
                flash('Ledger name already exists!', 'danger')
        return redirect(url_for('expense_ledgers', tab='ledgers'))
    ledger_groups = [g['group_name'] for g in db.execute('SELECT group_name FROM ledger_groups ORDER BY group_name').fetchall()]
    return render_template('expense_ledger_edit.html', ledger=ledger, ledger_groups=ledger_groups)

@app.route('/expense_ledger_delete/<int:lid>', methods=['POST'])
def expense_ledger_delete(lid):
    db = get_db()
    db.execute('DELETE FROM expense_ledgers WHERE id=?', (lid,))
    db.commit()
    flash('Ledger deleted.', 'success')
    return redirect(url_for('expense_ledgers', tab='ledgers'))

@app.route('/ledger_groups', methods=['GET', 'POST'])
def ledger_groups():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            gname = request.form.get('group_name', '').strip()
            gdesc = request.form.get('description', '').strip()
            gtype = request.form.get('group_type', 'Expense').strip()
            if gname:
                try:
                    db.execute('INSERT INTO ledger_groups (group_name, description, group_type) VALUES (?, ?, ?)', (gname, gdesc, gtype))
                    db.commit()
                    flash(f'Ledger Group "{gname}" created successfully!', 'success')
                except Exception:
                    flash('Ledger Group name already exists!', 'danger')
            else:
                flash('Ledger Group name is required.', 'danger')
        return redirect(url_for('expense_ledgers', tab='groups'))
    return redirect(url_for('expense_ledgers', tab='groups'))

@app.route('/ledger_group_edit/<int:gid>', methods=['GET', 'POST'])
def ledger_group_edit(gid):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = get_db()
    group = db.execute('SELECT * FROM ledger_groups WHERE id=?', (gid,)).fetchone()
    if not group:
        flash('Ledger Group not found.', 'danger')
        return redirect(url_for('expense_ledgers', tab='groups'))
        
    default_groups = ['Direct Expenses', 'Indirect Expenses', 'Capital Account', 'Administrative Expenses', 'Selling Expenses', 'Direct Income', 'Indirect Income', 'Sales']
    is_default = group['group_name'] in default_groups

    if request.method == 'POST':
        gname = request.form.get('group_name', '').strip()
        gdesc = request.form.get('description', '').strip()
        gtype = request.form.get('group_type', 'Expense').strip()
        if gname:
            try:
                old_name = group['group_name']
                db.execute('UPDATE ledger_groups SET group_name=?, description=?, group_type=? WHERE id=?', (gname, gdesc, gtype, gid))
                # Propagate name change to expense_ledgers
                if gname != old_name:
                    db.execute('UPDATE expense_ledgers SET ledger_group=? WHERE ledger_group=?', (gname, old_name))
                db.commit()
                flash('Ledger Group updated successfully!', 'success')
            except Exception:
                flash('Ledger Group name already exists!', 'danger')
        else:
            flash('Group name cannot be empty.', 'danger')
        return redirect(url_for('expense_ledgers', tab='groups'))
        
    return render_template('ledger_group_edit.html', group=group, is_default=is_default)

@app.route('/ledger_group_delete/<int:gid>', methods=['POST'])
def ledger_group_delete(gid):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = get_db()
    group = db.execute('SELECT * FROM ledger_groups WHERE id=?', (gid,)).fetchone()
    if not group:
        flash('Ledger Group not found.', 'danger')
        return redirect(url_for('expense_ledgers', tab='groups'))
        
    default_groups = ['Direct Expenses', 'Indirect Expenses', 'Capital Account', 'Administrative Expenses', 'Selling Expenses', 'Direct Income', 'Indirect Income', 'Sales']
    if group['group_name'] in default_groups:
        flash('Cannot delete default ledger groups.', 'danger')
        return redirect(url_for('expense_ledgers', tab='groups'))
        
    # Set any linked ledgers' group to NULL (they will become Unassigned)
    db.execute('UPDATE expense_ledgers SET ledger_group = NULL WHERE ledger_group = ?', (group['group_name'],))
    db.execute('DELETE FROM ledger_groups WHERE id=?', (gid,))
    db.commit()
    flash('Ledger Group deleted successfully. Any linked ledgers are now unassigned.', 'success')
    return redirect(url_for('expense_ledgers', tab='groups'))

@app.route('/expense_particulars', methods=['GET', 'POST'])
def expense_particulars():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            pname = request.form.get('name', '').strip()
            ledger_id = request.form.get('ledger_id') or None
            pdesc = request.form.get('description', '').strip()
            if pname:
                try:
                    db.execute('INSERT INTO expense_particulars (name, ledger_id, description) VALUES (?, ?, ?)', (pname, ledger_id, pdesc))
                    db.commit()
                    flash(f'Particular "{pname}" created!', 'success')
                except Exception:
                    flash('Particular name already exists!', 'danger')
            else:
                flash('Particular name is required.', 'danger')
        return redirect(url_for('expense_ledgers', tab='particulars'))
    return redirect(url_for('expense_ledgers', tab='particulars'))

@app.route('/expense_particular_edit/<int:pid>', methods=['GET', 'POST'])
def expense_particular_edit(pid):
    db = get_db()
    particular = db.execute('SELECT * FROM expense_particulars WHERE id=?', (pid,)).fetchone()
    if not particular:
        flash('Particular not found.', 'danger')
        return redirect(url_for('expense_ledgers', tab='particulars'))
    if request.method == 'POST':
        pname = request.form.get('name', '').strip()
        ledger_id = request.form.get('ledger_id') or None
        pdesc = request.form.get('description', '').strip()
        if pname:
            try:
                db.execute('UPDATE expense_particulars SET name=?, ledger_id=?, description=? WHERE id=?', (pname, ledger_id, pdesc, pid))
                db.commit()
                flash('Particular updated!', 'success')
            except Exception:
                flash('Particular name already exists!', 'danger')
        return redirect(url_for('expense_ledgers', tab='particulars'))
    ledgers = db.execute('SELECT * FROM expense_ledgers ORDER BY ledger_group, ledger_name').fetchall()
    return render_template('expense_particular_edit.html', particular=particular, ledgers=ledgers)

@app.route('/expense_particular_delete/<int:pid>', methods=['POST'])
def expense_particular_delete(pid):
    db = get_db()
    db.execute('DELETE FROM expense_particulars WHERE id=?', (pid,))
    db.commit()
    flash('Particular deleted.', 'success')
    return redirect(url_for('expense_ledgers', tab='particulars'))

@app.route('/expense_units', methods=['GET', 'POST'])
def expense_units_view():
    db = get_db()
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        if action == 'add':
            uname = request.form.get('unit_name', '').strip()
            usym = request.form.get('unit_symbol', '').strip()
            if uname:
                try:
                    db.execute('INSERT INTO expense_units (unit_name, unit_symbol) VALUES (?, ?)', (uname, usym))
                    db.commit()
                    flash(f'Unit "{uname}" created!', 'success')
                except Exception:
                    flash('Unit name already exists!', 'danger')
            else:
                flash('Unit name is required.', 'danger')
        return redirect(url_for('expense_units_view'))
    units = db.execute('SELECT * FROM expense_units ORDER BY unit_name').fetchall()
    return render_template('expense_units.html', units=units)

@app.route('/expense_unit_delete/<int:uid>', methods=['POST'])
def expense_unit_delete(uid):
    db = get_db()
    db.execute('DELETE FROM expense_units WHERE id=?', (uid,))
    db.commit()
    flash('Unit deleted.', 'success')
    return redirect(url_for('expense_units_view'))

@app.route('/equipment')
def equipment():
    db = get_db()
    name_filter = request.args.get('name', '')
    type_filter = request.args.get('type', '')
    status_filter = request.args.get('status', '')
    
    q = "SELECT * FROM equipment WHERE 1=1"
    p = []
    if name_filter:
        q += " AND name LIKE ?"; p.append(f'%{name_filter}%')
    if type_filter:
        q += " AND type LIKE ?"; p.append(f'%{type_filter}%')
    if status_filter:
        q += " AND status=?"; p.append(status_filter)
        
    records = db.execute(q, p).fetchall()
    return render_template('equipment.html', records=records, name_filter=name_filter, type_filter=type_filter, status_filter=status_filter)

@app.route('/equipment_add', methods=['GET', 'POST'])
def equipment_add():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('INSERT INTO equipment (name, type, purchase_date, purchase_cost, supplier, status, notes, assigned_employee, service_due_date) VALUES (?,?,?,?,?,?,?,?,?)',
            (f.get('equipment_name'), f.get('type'), f.get('purchase_date'), float(f.get('purchase_cost') or 0.0),
             f.get('supplier'), f.get('condition_status'), f.get('notes'), f.get('assigned_employee'), f.get('service_due_date')))
        db.commit()
        flash('Asset / Material added!', 'success')
        return redirect(url_for('equipment'))
    return render_template('equipment_add.html')

@app.route('/equipment_edit/<int:id>', methods=['GET', 'POST'])
def equipment_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM equipment WHERE id=?', (id,)).fetchone()
    if not record:
        flash('Asset / Material record not found or has been deleted.', 'danger')
        return redirect(url_for('equipment'))
    if request.method == 'POST':
        f = request.form
        db.execute('UPDATE equipment SET name=?, type=?, purchase_date=?, purchase_cost=?, supplier=?, status=?, notes=?, assigned_employee=?, service_due_date=? WHERE id=?',
            (f.get('equipment_name'), f.get('type'), f.get('purchase_date'), float(f.get('purchase_cost') or 0.0),
             f.get('supplier'), f.get('condition_status'), f.get('notes'), f.get('assigned_employee'), f.get('service_due_date'), id))
        db.commit()
        flash('Asset / Material updated!', 'success')
        return redirect(url_for('equipment'))
    record = db.execute('SELECT * FROM equipment WHERE id=?', (id,)).fetchone()
    return render_template('equipment_edit.html', record=record)

@app.route('/equipment_delete/<int:id>', methods=['POST'])
def equipment_delete(id):
    db = get_db()
    db.execute('DELETE FROM equipment WHERE id = ?', (id,))
    db.execute('DELETE FROM equipment_services WHERE equipment_id = ?', (id,))
    db.commit()
    flash('Asset / Material record and all its related maintenance records deleted successfully!', 'success')
    return redirect(url_for('equipment'))

@app.route('/equipment_detail/<int:id>')
def equipment_detail(id):
    db = get_db()
    record = db.execute('SELECT * FROM equipment WHERE id=?', (id,)).fetchone()
    if not record:
        flash('Equipment not found.', 'danger')
        return redirect(url_for('equipment'))
    maintenance = db.execute('SELECT * FROM equipment_services WHERE equipment_id=? ORDER BY service_date DESC', (id,)).fetchall()
    return render_template('equipment_detail.html', record=record, maintenance=maintenance)

@app.route('/equipment_maintenance_add/<int:equipment_id>', methods=['POST'])
def equipment_maintenance_add(equipment_id):
    db = get_db()
    f = request.form
    db.execute('INSERT INTO equipment_services (equipment_id, vendor_name, service_date, service_cost, description, status, notes) VALUES (?,?,?,?,?,?,?)',
        (equipment_id, f.get('vendor_name'), f.get('date'), f.get('cost') or 0.0, f.get('description'), 'Completed', f.get('notes', '')))
    db.commit()
    flash('Maintenance record added.', 'success')
    return redirect(url_for('equipment_detail', id=equipment_id))

@app.route('/supplier_add', methods=['GET', 'POST'])
def supplier_add():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('INSERT INTO equipment_suppliers (vendor_name,contact,email,address) VALUES (?,?,?,?)',
            (f.get('vendor_name'), f.get('contact'), f.get('email'), f.get('address')))
        db.commit()
        flash('Supplier added!', 'success')
        return redirect(url_for('equipment'))
    return render_template('supplier_add.html')

# ── REPORTS ──────────────────────────────────────────────────────────────────

@app.route('/salary_report')
def salary_report():
    db = get_db()
    month_str = request.args.get('month', datetime.now().strftime('%Y-%m'))
    try:
        parts = month_str.split('-')
        year = parts[0]
        month = parts[1]
    except Exception:
        year = datetime.now().strftime('%Y')
        month = datetime.now().strftime('%m')
        month_str = f"{year}-{month}"

    data = db.execute('''SELECT e.id, e.name, e.role, e.wage_type, e.wage_rate, e.sr_no,
        SUM(CASE WHEN a.status IN ('P', 'Present') THEN 1 ELSE 0 END) as present_days
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id
            AND TO_CHAR(a.date, 'MM') = ? AND TO_CHAR(a.date, 'YYYY') = ?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (month, year)).fetchall()

    employees = []
    total_payable = 0.0
    total_paid = 0.0
    total_pending = 0.0

    for emp in data:
        present = emp['present_days'] or 0
        wage_type = emp['wage_type']
        wage_rate = emp['wage_rate'] or 0
        
        import calendar
        try:
            days_in_month = calendar.monthrange(int(year), int(month))[1]
        except Exception:
            days_in_month = 30

        computed = 0.0
        if wage_type == 'Monthly':
            computed = (wage_rate / float(days_in_month)) * present
        elif wage_type == 'Weekly':
            computed = (wage_rate / 7.0) * present
        elif wage_type == 'Daily':
            computed = wage_rate * present
            
        paid = db.execute('''SELECT SUM(net_salary) FROM salary_payments 
                             WHERE employee_id=? AND month=? AND year=?''', 
                           (emp['id'], int(month), int(year))).fetchone()[0] or 0.0
        
        balance = max(0.0, computed - paid)
        
        status = 'Not Paid'
        if paid >= computed and computed > 0:
            status = 'Paid'
        elif paid > 0:
            status = 'Partially Paid'
            
        employees.append({
            'sr_no': emp['sr_no'],
            'name': emp['name'],
            'role': emp['role'],
            'daily_wage': wage_rate,
            'days_worked': present,
            'paying_amount': computed,
            'paid_amount': paid,
            'balance_due': balance,
            'status': status

        })
        
        total_payable += computed
        total_paid += paid
        total_pending += balance

    farm = db.execute('SELECT * FROM farm_info LIMIT 1').fetchone()
    return render_template('salary_report.html', 
                           employees=employees, 
                           total_payable=total_payable,
                           total_paid=total_paid,
                           total_pending=total_pending,
                           month=month_str, 
                           farm=farm)


@app.route('/pnl', methods=['GET', 'POST'])
def pnl():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    db = get_db()
    
    # 1. Date filter parameters: Month & Year
    selected_month = request.args.get('month') or request.form.get('month')
    selected_year = request.args.get('year') or request.form.get('year')
    
    now = datetime.now()
    if not selected_year:
        selected_year = str(now.year)
    if selected_month is None:
        selected_month = 'All' # Default to All Months to match dashboard's lifetime scope
        
    import calendar
    try:
        if selected_month == 'All':
            from_date = f"{selected_year}-01-01"
            to_date = f"{selected_year}-12-31"
        else:
            month_val = int(selected_month)
            if month_val < 1 or month_val > 12:
                raise ValueError()
            selected_month = f"{month_val:02d}"
            from_date = f"{selected_year}-{selected_month}-01"
            year_int = int(selected_year)
            last_day = calendar.monthrange(year_int, month_val)[1]
            to_date = f"{selected_year}-{selected_month}-{last_day:02d}"
    except Exception:
        # Fallback to current month if anything fails
        selected_month = f"{now.month:02d}"
        from_date = f"{selected_year}-{selected_month}-01"
        last_day = calendar.monthrange(now.year, now.month)[1]
        to_date = f"{selected_year}-{selected_month}-{last_day:02d}"
        
    # 2. Get manual stock overrides if submitted, otherwise dynamic default
    manual_opening = request.args.get('opening_stock', '') or request.form.get('opening_stock', '')
    manual_closing = request.args.get('closing_stock', '') or request.form.get('closing_stock', '')
    
    # Stock Valuation toggle (defaults to '0' / cash basis to match dashboard)
    if request.method == 'POST':
        include_stock = '1' if 'include_stock' in request.form else '0'
    else:
        include_stock = '1' if request.args.get('include_stock') == '1' else '0'
    
    # --- DYNAMIC STOCK CALCULATION ---
    # Calculates stock valuation for any date T (active goats + feed + medicine + vaccine inventory)
    def get_stock_val(target_date):
        # 1. Live Stock (Goats): Excluded as requested (default P&L does not include livestock valuation)
        goats_val = 0.0

        # 2. Feed Inventory Stock: latest record per feed up to target_date
        feed_val = db.execute("""
            SELECT SUM(f.closing_stock * f.cost_per_unit)
            FROM feed_inventory f
            INNER JOIN (
                SELECT feed_name, MAX(id) as max_id
                FROM feed_inventory
                WHERE purchase_date <= ?
                GROUP BY feed_name
            ) latest ON f.id = latest.max_id
        """, (target_date,)).fetchone()[0] or 0.0

        # 3. Medicine Inventory Stock: latest record per medicine up to target_date
        med_val = db.execute("""
            SELECT SUM(m.closing_stock * m.cost_per_unit)
            FROM medicine_inventory m
            INNER JOIN (
                SELECT medicine_name, MAX(id) as max_id
                FROM medicine_inventory
                WHERE purchase_date <= ?
                GROUP BY medicine_name
            ) latest ON m.id = latest.max_id
        """, (target_date,)).fetchone()[0] or 0.0

        # 4. Vaccine Inventory Stock: latest record per vaccine up to target_date
        vac_val = db.execute("""
            SELECT SUM(v.closing_stock * v.cost_per_unit)
            FROM vaccine_inventory v
            INNER JOIN (
                SELECT vaccine_name, MAX(id) as max_id
                FROM vaccine_inventory
                WHERE purchase_date <= ?
                GROUP BY vaccine_name
            ) latest ON v.id = latest.max_id
        """, (target_date,)).fetchone()[0] or 0.0

        return goats_val + feed_val + med_val + vac_val

    # Convert from_date to the last day of the previous calendar month (last month's closing stock is current opening stock)
    from datetime import timedelta
    try:
        from_date_dt = datetime.strptime(from_date, '%Y-%m-%d')
        first_day_curr_month = from_date_dt.replace(day=1)
        prev_month_close_dt = first_day_curr_month - timedelta(days=1)
        prev_date = prev_month_close_dt.strftime('%Y-%m-%d')
    except Exception:
        prev_date = from_date

    computed_opening_stock = get_stock_val(prev_date)
    computed_closing_stock = get_stock_val(to_date)
    
    if include_stock == '1':
        opening_stock = float(manual_opening) if manual_opening != '' else computed_opening_stock
        closing_stock = float(manual_closing) if manual_closing != '' else computed_closing_stock
    else:
        opening_stock = 0.0
        closing_stock = 0.0

    direct_expenses_tree = {}
    indirect_expenses_tree = {}
    sales_accounts_tree = {}
    direct_incomes_tree = {}
    indirect_incomes_tree = {}

    total_direct_expenses = 0.0
    total_indirect_expenses = 0.0
    total_purchases_sum = 0.0

    # Load lookup dictionaries
    groups_rows = db.execute("SELECT group_name, group_type FROM ledger_groups").fetchall()
    ledger_groups_dict = {r['group_name']: r['group_type'] for r in groups_rows}

    ledgers_rows = db.execute("SELECT id, ledger_name, ledger_group FROM expense_ledgers").fetchall()
    ledgers_by_name = {r['ledger_name'].strip().lower(): {
        'id': r['id'],
        'ledger_name': r['ledger_name'],
        'ledger_group': r['ledger_group']
    } for r in ledgers_rows}
    ledgers_by_id = {r['id']: {
        'ledger_name': r['ledger_name'],
        'ledger_group': r['ledger_group']
    } for r in ledgers_rows}

    particulars_rows = db.execute("SELECT id, name, ledger_id FROM expense_particulars").fetchall()
    particulars_by_id = {}
    for r in particulars_rows:
        ledger_info = ledgers_by_id.get(r['ledger_id'])
        particulars_by_id[r['id']] = {
            'name': r['name'],
            'ledger_name': ledger_info['ledger_name'] if ledger_info else 'Unassigned Ledger',
            'ledger_group': ledger_info['ledger_group'] if ledger_info else 'Direct Expenses'
        }

    def resolve_account_details(particular_id, pnl_category, fallback_ledger_name, fallback_particular_name):
        if particular_id and particular_id in particulars_by_id:
            p_info = particulars_by_id[particular_id]
            return p_info['ledger_group'], p_info['ledger_name'], p_info['name']
        l_name_search = (fallback_ledger_name or pnl_category or '').strip().lower()
        if l_name_search in ledgers_by_name:
            l_info = ledgers_by_name[l_name_search]
            return l_info['ledger_group'], l_info['ledger_name'], (fallback_particular_name or fallback_ledger_name or 'General')
        pnl_cat_strip = (pnl_category or '').strip()
        if pnl_cat_strip in ledger_groups_dict:
            return pnl_cat_strip, (fallback_ledger_name or 'General Ledger'), (fallback_particular_name or 'General')
        default_group = 'Direct Expenses'
        if pnl_category:
            pnl_cat_lower = pnl_category.lower()
            if 'indirect' in pnl_cat_lower or 'admin' in pnl_cat_lower or 'selling' in pnl_cat_lower:
                default_group = 'Indirect Expenses'
            elif 'sale' in pnl_cat_lower or 'revenue' in pnl_cat_lower:
                default_group = 'Sales'
            elif 'income' in pnl_cat_lower:
                default_group = 'Direct Income' if 'direct' in pnl_cat_lower else 'Indirect Income'
        return default_group, (fallback_ledger_name or 'General Ledger'), (fallback_particular_name or 'General')

    def add_to_tree(tree, ledger_group, ledger_account, particular, amount):
        if ledger_group not in tree:
            tree[ledger_group] = {
                'ledger_group_total': 0.0,
                'accounts': {}
            }
        tree[ledger_group]['ledger_group_total'] += amount
        
        accounts = tree[ledger_group]['accounts']
        if ledger_account not in accounts:
            accounts[ledger_account] = {
                'ledger_account_total': 0.0,
                'particulars': {}
            }
        accounts[ledger_account]['ledger_account_total'] += amount
        
        particulars = accounts[ledger_account]['particulars']
        if particular not in particulars:
            particulars[particular] = {
                'amount': 0.0,
                'particular_name': particular
            }
        particulars[particular]['amount'] += amount

    def classify_and_add(group, ledger, particular, amount):
        group_type = ledger_groups_dict.get(group, 'Expense')
        if group_type == 'Expense':
            if group == 'Direct Expenses':
                add_to_tree(direct_expenses_tree, group, ledger, particular, amount)
            else:
                add_to_tree(indirect_expenses_tree, group, ledger, particular, amount)
        else: # Income
            if group == 'Sales':
                add_to_tree(sales_accounts_tree, group, ledger, particular, amount)
            elif group == 'Direct Income':
                add_to_tree(direct_incomes_tree, group, ledger, particular, amount)
            else:
                add_to_tree(indirect_incomes_tree, group, ledger, particular, amount)

    # --- PURCHASES (COGS) ACCOUNT LEDGERS ---
    purchases_list = []
    
    # Goat purchases
    rows = db.execute("SELECT id, seller_name AS detail, purchase_date AS date, price AS amount, pnl_category, particular_id FROM purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
    for r in rows:
        purchases_list.append({'type': 'Goat', 'detail': r['detail'], 'date': r['date'], 'amount': r['amount'] or 0.0, 'pnl_category': r['pnl_category'] or 'Purchase', 'particular_id': r['particular_id']})
        
    # Feed purchases
    rows = db.execute("SELECT id, supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, particular_id FROM feed_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
    for r in rows:
        purchases_list.append({'type': 'Feed', 'detail': f"Feed: {r['pnl_category']} - Supplier: {r['detail']}", 'date': r['date'], 'amount': r['amount'] or 0.0, 'pnl_category': r['pnl_category'] or 'Purchase', 'particular_id': r['particular_id']})
        
    # Medicine purchases
    rows = db.execute("SELECT id, supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, particular_id FROM medicine_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
    for r in rows:
        purchases_list.append({'type': 'Medicine', 'detail': f"Medicine - Supplier: {r['detail']}", 'date': r['date'], 'amount': r['amount'] or 0.0, 'pnl_category': r['pnl_category'] or 'Purchase', 'particular_id': r['particular_id']})
        
    # Vaccine purchases
    rows = db.execute("SELECT id, supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, particular_id FROM vaccine_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
    for r in rows:
        purchases_list.append({'type': 'Vaccine', 'detail': f"Vaccine - Supplier: {r['detail']}", 'date': r['date'], 'amount': r['amount'] or 0.0, 'pnl_category': r['pnl_category'] or 'Purchase', 'particular_id': r['particular_id']})
        
    # Equipment purchases
    rows = db.execute("SELECT id, name AS detail, purchase_date AS date, purchase_cost AS amount, pnl_category FROM equipment WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
    for r in rows:
        purchases_list.append({'type': 'Equipment', 'detail': f"Asset: {r['detail']}", 'date': r['date'], 'amount': r['amount'] or 0.0, 'pnl_category': r['pnl_category'] or 'Purchase', 'particular_id': None})
        
    for p in purchases_list:
        amt = p['amount'] or 0.0
        group, ledger, particular = resolve_account_details(p['particular_id'], p['pnl_category'], 'Purchase', p['detail'])
        classify_and_add(group, ledger, particular, amt)
        
        group_type = ledger_groups_dict.get(group, 'Expense')
        if group_type == 'Expense':
            if group == 'Direct Expenses':
                total_direct_expenses += amt
            else:
                total_indirect_expenses += amt
        total_purchases_sum += amt
        
    # --- EXPENSES LEDGERS (DIRECT vs INDIRECT) ---
    expenses_rows = db.execute(
        "SELECT id, category, amount, date, description, vendor_name, pnl_category, particular_id FROM expenses WHERE status IN ('Approved','Paid') AND date BETWEEN ? AND ?",
        (from_date, to_date)
    ).fetchall()

    for r in expenses_rows:
        cat = r['category']
        pnl_cat = (r['pnl_category'] or '').strip()
        if cat and ('labor' in cat.lower() or 'labour' in cat.lower()):
            continue
        amt = r['amount'] or 0.0
        pid = r['particular_id']

        group, ledger, particular = resolve_account_details(pid, pnl_cat, cat, r['description'] or cat)
        if group == 'Capital Account':
            continue
            
        classify_and_add(group, ledger, particular, amt)
        
        group_type = ledger_groups_dict.get(group, 'Expense')
        if group_type == 'Expense':
            if group == 'Direct Expenses':
                total_direct_expenses += amt
            else:
                total_indirect_expenses += amt

    # ── OTHER VOUCHERS → P&L (from Expenses Master) ────────────────────────────
    ov_rows = db.execute(
        "SELECT ov.*, el.ledger_group FROM other_vouchers ov LEFT JOIN expense_particulars ep ON ov.particular_id = ep.id LEFT JOIN expense_ledgers el ON ep.ledger_id = el.id WHERE ov.voucher_date BETWEEN ? AND ?",
        (from_date, to_date)
    ).fetchall()

    ledger_pnl_summary = {}
    for ov in ov_rows:
        amt = ov['amount'] or 0.0
        pnl_cat = (ov['pnl_category'] or 'Direct Expenses').strip()
        ledger_grp = (ov['ledger_group'] or pnl_cat).strip()
        label = ov['particular_name'] or 'Other Voucher Expense'

        if label not in ledger_pnl_summary:
            ledger_pnl_summary[label] = {'group': ledger_grp, 'amount': 0.0}
        ledger_pnl_summary[label]['amount'] += amt

    # Fetch employee salary payments
    hr_salaries_row = db.execute("""
        SELECT SUM(net_salary)
        FROM salary_payments
        WHERE paid_date BETWEEN ? AND ?
    """, (from_date, to_date)).fetchone()
    hr_salaries = hr_salaries_row[0] or 0.0 if hr_salaries_row else 0.0

    if hr_salaries > 0:
        g, l, p = resolve_account_details(None, 'Direct Expenses', 'Staff Salary / Payments (HR)', 'Salary Payments')
        classify_and_add(g, l, p, hr_salaries)
        total_direct_expenses += hr_salaries

    # --- SALES & REVENUE ACCOUNT LEDGERS ---
    sales_list = []
    
    # Goat sales
    rows = db.execute("SELECT id, tag_id AS detail, date_of_sale AS date, sold_price AS amount, pnl_category FROM sales_records WHERE date_of_sale BETWEEN ? AND ?", (from_date, to_date)).fetchall()
    for r in rows:
        sales_list.append({'type': 'Goat Sale', 'detail': f"Goat tag {r['detail']}", 'date': r['date'], 'amount': r['amount'] or 0.0, 'pnl_category': r['pnl_category'] or 'Sales'})
        
    # Other sales
    rows = db.execute("SELECT id, item_name AS detail, date_of_sale AS date, total_amount AS amount, pnl_category FROM other_sales_records WHERE date_of_sale BETWEEN ? AND ?", (from_date, to_date)).fetchall()
    for r in rows:
        sales_list.append({'type': 'Other Sale', 'detail': r['detail'], 'date': r['date'], 'amount': r['amount'] or 0.0, 'pnl_category': r['pnl_category'] or 'Sales'})
        
    total_sales_sum = 0.0
    total_direct_income = 0.0
    total_indirect_income = 0.0
    
    for s in sales_list:
        amt = s['amount'] or 0.0
        pnl_cat = s['pnl_category']
        
        group, ledger, particular = resolve_account_details(None, pnl_cat, pnl_cat or 'Sales', s['detail'])
        
        # Force default groups if resolved to default/unassigned or direct expenses
        if group == 'Direct Expenses' or group not in ledger_groups_dict:
            if pnl_cat in ['Discount Received', 'FD-Interest Received', 'Interest Received'] or (pnl_cat and 'indirect' in pnl_cat.lower()):
                group = 'Indirect Income'
            elif pnl_cat == 'Other Income':
                group = 'Direct Income'
            else:
                group = 'Sales'
                
        classify_and_add(group, ledger, particular, amt)
        
        if group == 'Sales':
            total_sales_sum += amt
        elif group == 'Direct Income':
            total_direct_income += amt
        else: # Indirect Income
            total_indirect_income += amt
            
    # --- P&L MATHEMATICS ---
    total_debits = opening_stock + total_purchases_sum + total_direct_expenses
    total_credits = total_sales_sum + total_direct_income + closing_stock
    
    gross_profit = total_credits - total_debits
    net_profit = gross_profit - total_indirect_expenses + total_indirect_income
    
    left_total = total_debits + (net_profit if net_profit >= 0 else 0) + (total_indirect_expenses if net_profit < 0 else 0)
    right_total = total_credits + (abs(net_profit) if net_profit < 0 else 0) + (total_indirect_income if net_profit >= 0 else 0)
    
    is_profit = net_profit >= 0
    net_val = abs(net_profit)
    
    return render_template('pnl.html',
                           from_date=from_date,
                           to_date=to_date,
                           selected_month=selected_month or 'All',
                           selected_year=selected_year,
                           opening_stock=opening_stock,
                           closing_stock=closing_stock,
                           computed_opening=computed_opening_stock,
                           computed_closing=computed_closing_stock,
                           include_stock=(include_stock == '1'),
                           total_purchases=total_purchases_sum,
                           total_direct_expenses=total_direct_expenses,
                           total_indirect_expenses=total_indirect_expenses,
                           total_sales=total_sales_sum,
                           total_direct_income=total_direct_income,
                           total_indirect_income=total_indirect_income,
                           gross_profit=gross_profit,
                           net_profit=net_val,
                           is_profit=is_profit,
                           left_total=max(left_total, right_total),
                           right_total=max(left_total, right_total),
                           ledger_pnl_summary=ledger_pnl_summary,
                           direct_expenses_tree=direct_expenses_tree,
                           indirect_expenses_tree=indirect_expenses_tree,
                           sales_accounts_tree=sales_accounts_tree,
                           direct_incomes_tree=direct_incomes_tree,
                           indirect_incomes_tree=indirect_incomes_tree)


@app.route('/api/pnl/drilldown')
def api_pnl_drilldown():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
        
    db = get_db()
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    category = request.args.get('category', '')
    
    if not from_date or not to_date or not category:
        return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
    transactions = []
    
    # 1. Opening & Closing Stock
    if category in ('Opening Stock', 'Closing Stock'):
        from datetime import datetime, timedelta
        if category == 'Opening Stock':
            try:
                from_date_dt = datetime.strptime(from_date, '%Y-%m-%d')
                first_day_curr_month = from_date_dt.replace(day=1)
                prev_month_close_dt = first_day_curr_month - timedelta(days=1)
                target_date = prev_month_close_dt.strftime('%Y-%m-%d')
            except Exception:
                target_date = from_date
        else:
            target_date = to_date

        # Fetch feed inventory
        feed_rows = db.execute("""
            SELECT f.feed_name, f.closing_stock, f.cost_per_unit, f.purchase_date
            FROM feed_inventory f
            INNER JOIN (
                SELECT feed_name, MAX(id) as max_id
                FROM feed_inventory
                WHERE purchase_date <= ?
                GROUP BY feed_name
            ) latest ON f.id = latest.max_id
            WHERE f.closing_stock > 0
        """, (target_date,)).fetchall()
        for r in feed_rows:
            transactions.append({
                'date': r['purchase_date'],
                'reference': f"Feed: {r['feed_name']}",
                'detail': f"Closing Stock: {r['closing_stock']} @ ₹{r['cost_per_unit']}/unit",
                'amount': r['closing_stock'] * r['cost_per_unit']
            })

        # Fetch medicine inventory
        med_rows = db.execute("""
            SELECT m.medicine_name, m.closing_stock, m.cost_per_unit, m.purchase_date
            FROM medicine_inventory m
            INNER JOIN (
                SELECT medicine_name, MAX(id) as max_id
                FROM medicine_inventory
                WHERE purchase_date <= ?
                GROUP BY medicine_name
            ) latest ON m.id = latest.max_id
            WHERE m.closing_stock > 0
        """, (target_date,)).fetchall()
        for r in med_rows:
            transactions.append({
                'date': r['purchase_date'],
                'reference': f"Med: {r['medicine_name']}",
                'detail': f"Closing Stock: {r['closing_stock']} @ ₹{r['cost_per_unit']}/unit",
                'amount': r['closing_stock'] * r['cost_per_unit']
            })

        # Fetch vaccine inventory
        vac_rows = db.execute("""
            SELECT v.vaccine_name, v.closing_stock, v.cost_per_unit, v.purchase_date
            FROM vaccine_inventory v
            INNER JOIN (
                SELECT vaccine_name, MAX(id) as max_id
                FROM vaccine_inventory
                WHERE purchase_date <= ?
                GROUP BY vaccine_name
            ) latest ON v.id = latest.max_id
            WHERE v.closing_stock > 0
        """, (target_date,)).fetchall()
        for r in vac_rows:
            transactions.append({
                'date': r['purchase_date'],
                'reference': f"Vac: {r['vaccine_name']}",
                'detail': f"Closing Stock: {r['closing_stock']} @ ₹{r['cost_per_unit']}/unit",
                'amount': r['closing_stock'] * r['cost_per_unit']
            })
        transactions.sort(key=lambda x: x['date'], reverse=True)
        return jsonify({'success': True, 'transactions': transactions})

    # 2. General Ledger / Transaction aggregation & filtration
    else:
        # Load lookup structures
        groups_rows = db.execute("SELECT group_name, group_type FROM ledger_groups").fetchall()
        ledger_groups_dict = {r['group_name']: r['group_type'] for r in groups_rows}

        ledgers_rows = db.execute("SELECT id, ledger_name, ledger_group FROM expense_ledgers").fetchall()
        ledgers_by_name = {r['ledger_name'].strip().lower(): {
            'id': r['id'],
            'ledger_name': r['ledger_name'],
            'ledger_group': r['ledger_group']
        } for r in ledgers_rows}
        ledgers_by_id = {r['id']: {
            'ledger_name': r['ledger_name'],
            'ledger_group': r['ledger_group']
        } for r in ledgers_rows}

        particulars_rows = db.execute("SELECT id, name, ledger_id FROM expense_particulars").fetchall()
        particulars_by_id = {}
        for r in particulars_rows:
            ledger_info = ledgers_by_id.get(r['ledger_id'])
            particulars_by_id[r['id']] = {
                'name': r['name'],
                'ledger_name': ledger_info['ledger_name'] if ledger_info else 'Unassigned Ledger',
                'ledger_group': ledger_info['ledger_group'] if ledger_info else 'Direct Expenses'
            }

        def resolve_account_details(particular_id, pnl_category, fallback_ledger_name, fallback_particular_name):
            if particular_id and particular_id in particulars_by_id:
                p_info = particulars_by_id[particular_id]
                return p_info['ledger_group'], p_info['ledger_name'], p_info['name']
            l_name_search = (fallback_ledger_name or pnl_category or '').strip().lower()
            if l_name_search in ledgers_by_name:
                l_info = ledgers_by_name[l_name_search]
                return l_info['ledger_group'], l_info['ledger_name'], (fallback_particular_name or fallback_ledger_name or 'General')
            pnl_cat_strip = (pnl_category or '').strip()
            if pnl_cat_strip in ledger_groups_dict:
                return pnl_cat_strip, (fallback_ledger_name or 'General Ledger'), (fallback_particular_name or 'General')
            default_group = 'Direct Expenses'
            if pnl_category:
                pnl_cat_lower = pnl_category.lower()
                if 'indirect' in pnl_cat_lower or 'admin' in pnl_cat_lower or 'selling' in pnl_cat_lower:
                    default_group = 'Indirect Expenses'
                elif 'sale' in pnl_cat_lower or 'revenue' in pnl_cat_lower:
                    default_group = 'Sales'
                elif 'income' in pnl_cat_lower:
                    default_group = 'Direct Income' if 'direct' in pnl_cat_lower else 'Indirect Income'
            return default_group, (fallback_ledger_name or 'General Ledger'), (fallback_particular_name or 'General')

        # 1. Staff Salary
        rows = db.execute("""
            SELECT s.paid_date AS date, e.name AS reference, s.payment_mode AS detail, s.net_salary AS amount 
            FROM salary_payments s
            JOIN employees e ON s.employee_id = e.id
            WHERE s.paid_date BETWEEN ? AND ? 
            ORDER BY date DESC
        """, (from_date, to_date)).fetchall()
        for r in rows:
            g, l, p = resolve_account_details(None, 'Direct Expenses', 'Staff Salary / Payments (HR)', 'Salary Payments')
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': f"Salary: {r['reference']}", 'detail': f"HR Payroll - paid via {r['detail']}", 'amount': r['amount'], 'category': l, 'type': 'expense'})

        # 2. Goat purchases
        rows = db.execute("SELECT id, seller_name AS detail, purchase_date AS date, price AS amount, pnl_category, tag_id, particular_id FROM purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
        for r in rows:
            r_cat = r['pnl_category'] or 'Purchase'
            g, l, p = resolve_account_details(r['particular_id'], r_cat, 'Purchase', 'Goat Purchases')
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': f"Goat: {r['tag_id']}", 'detail': f"Purchased from {r['detail']}", 'amount': r['amount'], 'category': l, 'type': 'expense'})
            
        # 3. Feed purchases
        rows = db.execute("SELECT id, supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, feed_name, particular_id FROM feed_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
        for r in rows:
            r_cat = r['pnl_category'] or 'Purchase'
            g, l, p = resolve_account_details(r['particular_id'], r_cat, 'Purchase', 'Feed Purchases')
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': f"Feed: {r['feed_name']}", 'detail': f"Supplier: {r['detail']}", 'amount': r['amount'], 'category': l, 'type': 'expense'})
            
        # 4. Medicine purchases
        rows = db.execute("SELECT id, supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, medicine_name, particular_id FROM medicine_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
        for r in rows:
            r_cat = r['pnl_category'] or 'Purchase'
            g, l, p = resolve_account_details(r['particular_id'], r_cat, 'Purchase', 'Medicine Purchases')
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': f"Med: {r['medicine_name']}", 'detail': f"Supplier: {r['detail']}", 'amount': r['amount'], 'category': l, 'type': 'expense'})
            
        # 5. Vaccine purchases
        rows = db.execute("SELECT id, supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, vaccine_name, particular_id FROM vaccine_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
        for r in rows:
            r_cat = r['pnl_category'] or 'Purchase'
            g, l, p = resolve_account_details(r['particular_id'], r_cat, 'Purchase', 'Vaccine Purchases')
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': f"Vac: {r['vaccine_name']}", 'detail': f"Supplier: {r['detail']}", 'amount': r['amount'], 'category': l, 'type': 'expense'})
            
        # 6. Equipment purchases
        rows = db.execute("SELECT id, name AS detail, purchase_date AS date, purchase_cost AS amount, pnl_category FROM equipment WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchall()
        for r in rows:
            r_cat = r['pnl_category'] or 'Purchase'
            g, l, p = resolve_account_details(None, r_cat, 'Purchase', f"Asset: {r['detail']}")
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': f"Asset: {r['detail']}", 'detail': f"Asset Purchase", 'amount': r['amount'] or 0.0, 'category': l, 'type': 'expense'})

        # 7. Goat sales
        rows = db.execute("SELECT tag_id AS reference, date_of_sale AS date, sold_price AS amount, pnl_category, buyer_name FROM sales_records WHERE date_of_sale BETWEEN ? AND ?", (from_date, to_date)).fetchall()
        for r in rows:
            r_cat = r['pnl_category'] or 'Sales'
            g, l, p = resolve_account_details(None, r_cat, r_cat, 'Goat Sales')
            if g == 'Direct Expenses' or g not in ledger_groups_dict:
                g = 'Sales'
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': f"Goat: {r['reference']}", 'detail': f"Sold to {r['buyer_name']}", 'amount': r['amount'], 'category': l, 'type': 'income'})
            
        # 8. Other sales
        rows = db.execute("SELECT item_name AS reference, date_of_sale AS date, total_amount AS amount, pnl_category, buyer_name, notes FROM other_sales_records WHERE date_of_sale BETWEEN ? AND ?", (from_date, to_date)).fetchall()
        for r in rows:
            r_cat = r['pnl_category'] or 'Sales'
            g, l, p = resolve_account_details(None, r_cat, r_cat, r['reference'])
            if g == 'Direct Expenses' or g not in ledger_groups_dict:
                g = 'Sales'
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': r['reference'], 'detail': f"Sold to {r['buyer_name']} - {r['notes'] or ''}", 'amount': r['amount'], 'category': l, 'type': 'income'})

        # 9. Expenses
        rows = db.execute("SELECT id, date, category AS reference, description AS detail, amount, pnl_category, particular_id FROM expenses WHERE status IN ('Approved', 'Paid') AND date BETWEEN ? AND ? ORDER BY date DESC", (from_date, to_date)).fetchall()
        for r in rows:
            if r['reference'] and ('labor' in r['reference'].lower() or 'labour' in r['reference'].lower()):
                continue
            g, l, p = resolve_account_details(r['particular_id'], r['pnl_category'], r['reference'], r['detail'] or r['reference'])
            if category == 'All' or category in (g, l, p):
                transactions.append({'date': r['date'], 'reference': r['reference'], 'detail': r['detail'] or 'General Expense', 'amount': r['amount'], 'category': l, 'type': 'expense'})
            
        transactions.sort(key=lambda x: x['date'], reverse=True)
        return jsonify({'success': True, 'transactions': transactions})


@app.route('/breeds', methods=['GET', 'POST'])
def breeds():
    db = get_db()
    if request.method == 'POST':
        db.execute('INSERT INTO breeds (breed_name, description) VALUES (?, ?)',
                   (request.form.get('breed_name'), request.form.get('description')))
        db.commit()
        flash('Breed added successfully!', 'success')
        return redirect(url_for('breeds'))
    records = db.execute('SELECT * FROM breeds ORDER BY breed_name ASC').fetchall()
    return render_template('breeds.html', records=records)

@app.route('/breed_delete/<int:id>', methods=['POST'])
def breed_delete(id):
    db = get_db()
    db.execute('DELETE FROM breeds WHERE id = ?', (id,))
    db.commit()
    flash('Breed deleted successfully!', 'success')
    return redirect(url_for('breeds'))

@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db.execute('''INSERT INTO suppliers (supplier_name, contact_person, phone, address, supplier_type) 
                      VALUES (?, ?, ?, ?, ?)''',
                   (f.get('supplier_name'), f.get('contact_person'), f.get('phone'), 
                    f.get('address'), f.get('supplier_type')))
        db.commit()
        flash('Supplier added successfully!', 'success')
        return redirect(url_for('suppliers'))
    records = db.execute('SELECT * FROM suppliers ORDER BY supplier_name ASC').fetchall()
    return render_template('suppliers.html', records=records)

@app.route('/supplier_delete/<int:id>', methods=['POST'])
def supplier_delete(id):
    db = get_db()
    db.execute('DELETE FROM suppliers WHERE id = ?', (id,))
    db.commit()
    flash('Supplier deleted successfully!', 'success')
    return redirect(url_for('suppliers'))

@app.route('/inventory')
def inventory():
    db = get_db()
    # Feed Stock: from feed_inventory closing stock
    feed_stock = db.execute('SELECT feed_name, SUM(closing_stock) as stock FROM feed_inventory GROUP BY feed_name').fetchall()
    
    # Medicine Stock: Total purchased minus total used (from medicine_history)
    med_purchases = db.execute('SELECT medicine_name, SUM(quantity) as stock FROM medicine_purchases GROUP BY medicine_name').fetchall()
    
    # Vaccine Stock
    vac_purchases = db.execute('SELECT vaccine_name, SUM(quantity) as stock FROM vaccine_purchases GROUP BY vaccine_name').fetchall()
    
    return render_template('inventory.html', feed_stock=feed_stock, med_purchases=med_purchases, vac_purchases=vac_purchases)

@app.route('/kit')
def kit():
    db = get_db()
    records = db.execute("SELECT * FROM master_records WHERE kit_status = 1 OR kit_status = 'Yes' ORDER BY id DESC").fetchall()
    return render_template('kit.html', records=records)


@app.route('/equipment_purchases')
def equipment_purchases():
    db = get_db()
    records = db.execute("SELECT * FROM equipment ORDER BY purchase_date DESC").fetchall()
    return render_template('equipment_purchases.html', records=records)


@app.context_processor
def inject_eligible_goats_count():
    try:
        db = get_db()
        count = db.execute("SELECT COUNT(*) FROM master_records WHERE weight_kg >= 25 AND status != 'Sold' AND status IS NOT NULL").fetchone()[0] or 0
        return dict(eligible_sales_count=count)
    except Exception:
        return dict(eligible_sales_count=0)

@app.context_processor
def inject_user_admin_status():
    if 'user_id' in session:
        try:
            db = get_db()
            user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            if user and int(user['is_admin']) == 1:
                return dict(is_admin_session=True)
        except Exception:
            pass
    return dict(is_admin_session=False)

@app.route('/api/goat_lookup/<tag_id>')
def api_goat_lookup(tag_id):
    db = get_db()
    exclude_sr_no = request.args.get('exclude_sr_no')
    goat = db.execute('SELECT breed, breed_percent, gender, weight_kg, status FROM master_records WHERE tag_no = ?', (tag_id,)).fetchone()
    if not goat:
        return jsonify({'found': False})
    
    already_sold = goat['status'] == 'Sold'
    if already_sold and exclude_sr_no:
        was_sold_here = db.execute('SELECT 1 FROM sales_records WHERE tag_id = ? AND sr_no = ?', (tag_id, exclude_sr_no)).fetchone()
        if was_sold_here:
            already_sold = False
            
    return jsonify({
        'found': True,
        'breed': goat['breed'],
        'breed_percent': goat['breed_percent'],
        'gender': goat['gender'],
        'weight_kg': goat['weight_kg'],
        'status': goat['status'],
        'already_sold': already_sold,
        'already_expired': goat['status'] == 'Expired'
    })

@app.route('/api/notifications')
def api_notifications():
    if 'user_id' not in session:
        return jsonify({'weight_alerts': [], 'low_stock_alerts': [], 'batch_alerts': []})
        
    db = get_db()
    user_id = session['user_id']
    
    # 1. Weight Alerts (only if just logged in / has_seen_weight_notification is 0)
    weight_alerts = []
    tracking = db.execute('SELECT has_seen_weight_notification FROM user_login_tracking WHERE user_id = ?', (user_id,)).fetchone()
    if tracking and tracking['has_seen_weight_notification'] == 0:
        # Fetch goats >= 25 kg
        goats = db.execute('''
            SELECT tag_no, color, weight_kg 
            FROM master_records 
            WHERE weight_kg >= 25 AND (status != 'Sold' OR status IS NULL)
        ''').fetchall()
        
        # Check if already added to eligible to sell to avoid redundant prompt or to handle UI gracefully
        eligible_tags = {r['tag_id'] for r in db.execute('SELECT tag_id FROM eligible_to_sell').fetchall()}
        
        for g in goats:
            weight_alerts.append({
                'tag_no': g['tag_no'],
                'color': g['color'] or 'N/A',
                'weight_kg': g['weight_kg'],
                'already_eligible': g['tag_no'] in eligible_tags
            })
            
        # Update tracking to 1 so they don't see it again during this login session
        db.execute('UPDATE user_login_tracking SET has_seen_weight_notification = 1 WHERE user_id = ?', (user_id,))
        db.commit()

    # 2. Low Stock Alerts (check closing_stock vs alert_level)
    low_stock_alerts = []
    
    # Feed Stock
    feeds = db.execute('''
        SELECT f.feed_name, f.closing_stock, f.alert_level, f.unit
        FROM feed_inventory f
        INNER JOIN (
            SELECT feed_name, MAX(id) as max_id
            FROM feed_inventory
            GROUP BY feed_name
        ) latest ON f.id = latest.max_id
    ''').fetchall()
    for f in feeds:
        if f['alert_level'] and f['alert_level'] > 0 and f['closing_stock'] <= f['alert_level']:
            low_stock_alerts.append({
                'item_type': 'Feed',
                'item_name': f['feed_name'],
                'closing_stock': f['closing_stock'],
                'alert_level': f['alert_level'],
                'unit': f['unit'] or 'KG'
            })
            
    # Medicine Stock
    meds = db.execute('''
        SELECT m.medicine_name, m.closing_stock, m.alert_level, m.unit
        FROM medicine_inventory m
        INNER JOIN (
            SELECT medicine_name, MAX(id) as max_id
            FROM medicine_inventory
            GROUP BY medicine_name
        ) latest ON m.id = latest.max_id
    ''').fetchall()
    for m in meds:
        if m['alert_level'] and m['alert_level'] > 0 and m['closing_stock'] <= m['alert_level']:
            low_stock_alerts.append({
                'item_type': 'Medicine',
                'item_name': m['medicine_name'],
                'closing_stock': m['closing_stock'],
                'alert_level': m['alert_level'],
                'unit': m['unit'] or 'Doses'
            })

    # Vaccine Stock
    vacs = db.execute('''
        SELECT v.vaccine_name, v.closing_stock, v.alert_level, v.unit
        FROM vaccine_inventory v
        INNER JOIN (
            SELECT vaccine_name, MAX(id) as max_id
            FROM vaccine_inventory
            GROUP BY vaccine_name
        ) latest ON v.id = latest.max_id
    ''').fetchall()
    for v in vacs:
        if v['alert_level'] and v['alert_level'] > 0 and v['closing_stock'] <= v['alert_level']:
            low_stock_alerts.append({
                'item_type': 'Vaccine',
                'item_name': v['vaccine_name'],
                'closing_stock': v['closing_stock'],
                'alert_level': v['alert_level'],
                'unit': v['unit'] or 'Doses'
            })

    # 3. Batch Reminders (reminder_date <= today and is_completed == 0)
    batch_alerts = []
    today_str = datetime.now().strftime('%Y-%m-%d')
    reminders = db.execute('''
        SELECT id, batch_name, reminder_type, item_name, reminder_date
        FROM batch_reminders
        WHERE reminder_date <= ? AND is_completed = 0
    ''', (today_str,)).fetchall()
    
    for r in reminders:
        batch_alerts.append({
            'id': r['id'],
            'batch_name': r['batch_name'],
            'reminder_type': r['reminder_type'],
            'item_name': r['item_name'],
            'reminder_date': r['reminder_date']
        })
        
    return jsonify({
        'weight_alerts': weight_alerts,
        'low_stock_alerts': low_stock_alerts,
        'batch_alerts': batch_alerts
    })

@app.route('/api/add_to_eligible/<tag_id>', methods=['POST'])
def api_add_to_eligible(tag_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    db = get_db()
    goat = db.execute('SELECT tag_no, breed, gender, weight_kg FROM master_records WHERE tag_no = ?', (tag_id,)).fetchone()
    if not goat:
        return jsonify({'success': False, 'error': 'Goat not found'}), 444
    
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        db.execute('''
            INSERT INTO eligible_to_sell (tag_id, tag_no, breed, gender, weight_kg, date_added)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (goat['tag_no'], goat['tag_no'], goat['breed'], goat['gender'], goat['weight_kg'], today))
        db.commit()
        return jsonify({'success': True, 'message': f'Goat {tag_id} added to eligible list'})
    except sqlite3.IntegrityError:
        return jsonify({'success': True, 'message': 'Already in eligible list'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/complete_batch_reminder/<int:id>', methods=['POST'])
def api_complete_batch_reminder(id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    db = get_db()
    db.execute('UPDATE batch_reminders SET is_completed = 1 WHERE id = ?', (id,))
    db.commit()
    return jsonify({'success': True, 'message': 'Reminder marked as completed'})

@app.route('/update_stock_limit', methods=['POST'])
def update_stock_limit():
    db = get_db()
    item_type = request.form.get('item_type')
    item_name = request.form.get('item_name')
    try:
        limit = float(request.form.get('limit') or 0)
    except ValueError:
        limit = 0.0
    
    if item_type == 'feed':
        db.execute('UPDATE feed_inventory SET alert_level = ? WHERE feed_name = ?', (limit, item_name))
    elif item_type == 'medicine':
        db.execute('UPDATE medicine_inventory SET alert_level = ? WHERE medicine_name = ?', (limit, item_name))
    elif item_type == 'vaccine':
        db.execute('UPDATE vaccine_inventory SET alert_level = ? WHERE vaccine_name = ?', (limit, item_name))
        
    db.commit()
    flash(f'Low stock limit for {item_name} set to {limit} successfully.', 'success')
    return redirect(url_for('stock_inventory'))

@app.route('/add_batch_reminder', methods=['POST'])
def add_batch_reminder():
    db = get_db()
    batch_name = request.form.get('batch_name')
    reminder_type = request.form.get('reminder_type')
    item_name = request.form.get('item_name')
    reminder_date = request.form.get('reminder_date')
    db.execute('''
        INSERT INTO batch_reminders (batch_name, reminder_type, item_name, reminder_date, is_completed)
        VALUES (?, ?, ?, ?, 0)
    ''', (batch_name, reminder_type, item_name, reminder_date))
    db.commit()
    
    flash(f'{reminder_type} reminder for {batch_name} set for {reminder_date} successfully.', 'success')
    return redirect(url_for('goat_batches'))

@app.route('/delete_batch_reminder/<int:id>', methods=['POST'])
def delete_batch_reminder(id):
    db = get_db()
    db.execute('DELETE FROM batch_reminders WHERE id = ?', (id,))
    db.commit()
    flash('Batch reminder deleted successfully.', 'success')
    return redirect(url_for('goat_batches'))

if __name__ == '__main__':
    # Default to production-safe settings when running directly.
    # Debug mode is configured via Config classes and environment variable validation.
    flask_env = os.environ.get('FLASK_ENV', 'production').lower()
    is_debug = (flask_env == 'development')
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=is_debug)
