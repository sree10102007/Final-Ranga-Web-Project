import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, g
from goat_farm_app.extensions import csrf, limiter
from flask_talisman import Talisman
import secrets

# Resolve root path to handle Windows folder redirection (e.g. OneDrive)
base_dir = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(base_dir, 'templates')):
    alt_dir = base_dir.replace('\\Documents\\', '\\OneDrive\\Documents\\').replace('/Documents/', '/OneDrive/Documents/')
    if os.path.exists(os.path.join(alt_dir, 'templates')):
        base_dir = alt_dir

# Structured JSON Formatter for SOC/auditing
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "message": record.getMessage()
        }
        if isinstance(record.msg, dict):
            log_data.update(record.msg)
            if "message" in record.msg:
                log_data["message"] = record.msg["message"]
        return json.dumps(log_data)

class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    TESTING = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    pass

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

def setup_logging():
    log_dir = os.path.join(base_dir, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    db_audit_log_path = os.path.join(log_dir, 'db_audit.log')
    db_audit_handler = RotatingFileHandler(db_audit_log_path, maxBytes=10*1024*1024, backupCount=5)
    db_audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    db_logger = logging.getLogger('db_audit')
    db_logger.setLevel(logging.INFO)
    db_logger.addHandler(db_audit_handler)

    security_log_path = os.path.join(log_dir, 'security.json')
    security_handler = RotatingFileHandler(security_log_path, maxBytes=10*1024*1024, backupCount=5)
    security_handler.setFormatter(JsonFormatter())
    
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_logger.addHandler(security_handler)

def create_app(config_name=None):
    setup_logging()
    
    app = Flask(__name__, root_path=base_dir)
    
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'production').lower()
        
    config_class = config_by_name.get(config_name, ProductionConfig)
    app.config.from_object(config_class)
    
    # Ensure SECRET_KEY is set dynamically
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-development-secret-key')
        
    # Initialize extensions
    csrf.init_app(app)
    
    # Configure and initialize rate limiter dynamically
    storage_uri = os.environ.get('LIMITER_STORAGE_URI', 'memory://')
    app.config["RATELIMIT_STORAGE_URI"] = storage_uri
    limiter.init_app(app)
    
    # Register database context teardown
    from goat_farm_app.extensions import close_connection
    app.teardown_appcontext(close_connection)

    # Register blueprints (to be imported and added)
    from goat_farm_app.blueprints.auth import auth_bp
    app.register_blueprint(auth_bp)
    
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com", "https://cdnjs.cloudflare.com"],
        'img-src': ["'self'", 'data:'],
        'font-src': ["'self'", "https://fonts.gstatic.com", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com"],
        'connect-src': ["'self'"],
    }
    Talisman(app, 
        content_security_policy=csp, 
        force_https=False
    )
    
    return app
