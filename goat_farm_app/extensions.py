import os
import sys
import json
import base64
import secrets
import logging
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional, Tuple, Union
from cryptography.fernet import Fernet
import psycopg2
import psycopg2.extras
from flask import g, request, session
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Resolve root path to handle Windows folder redirection (e.g. OneDrive)
base_dir = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(base_dir, 'templates')):
    alt_dir = base_dir.replace('\\Documents\\', '\\OneDrive\\Documents\\').replace('/Documents/', '/OneDrive/Documents/')
    if os.path.exists(os.path.join(alt_dir, 'templates')):
        base_dir = alt_dir

# Database Audit Logger configuration
log_dir = os.path.join(base_dir, 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

db_audit_log_path = os.path.join(log_dir, 'db_audit.log')
db_audit_handler = RotatingFileHandler(db_audit_log_path, maxBytes=10*1024*1024, backupCount=5)
db_audit_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

db_logger = logging.getLogger('db_audit')
db_logger.setLevel(logging.INFO)
db_logger.addHandler(db_audit_handler)

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

security_log_path = os.path.join(log_dir, 'security.json')
security_handler = RotatingFileHandler(security_log_path, maxBytes=10*1024*1024, backupCount=5)
security_handler.setFormatter(JsonFormatter())

security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)
security_logger.addHandler(security_handler)

def log_security_event(event_type, message, **kwargs):
    correlation_id = 'unknown'
    try:
        correlation_id = getattr(g, 'correlation_id', 'unknown')
    except Exception:
        pass
        
    try:
        user_id = session.get('user_id', 'anonymous')
        ip_address = request.remote_addr
        user_agent = request.user_agent.string
        path = request.path
        method = request.method
    except Exception:
        user_id = 'system'
        ip_address = '127.0.0.1'
        user_agent = 'internal'
        path = '/'
        method = 'SYSTEM'
        
    log_payload = {
        "event_type": event_type,
        "message": message,
        "correlation_id": correlation_id,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "path": path,
        "method": method
    }
    log_payload.update(kwargs)
    
    # Scrub sensitive fields (passwords, pins, secrets, keys)
    sensitive_keys = {'password', 'secret', 'token', 'mfa_secret', 'key', 'backup_codes'}
    for k in list(log_payload.keys()):
        if any(sk in k.lower() for sk in sensitive_keys):
            log_payload[k] = '[REDACTED]'
            
    security_logger.info(log_payload)

# Database column-level encryption utility class
class DatabaseEncryptor:
    fernet: Fernet

    def __init__(self) -> None:
        # Load key from environment or fallback to developer key
        key: Union[str, bytes] = os.environ.get('DB_ENCRYPTION_KEY', '')
        if not key:
            key = base64.urlsafe_b64encode(b"development_fallback_key_32bytes")
            if os.environ.get('FLASK_ENV', 'production').lower() == 'production':
                db_logger.warning("DB_ENCRYPTION_KEY is not set in production! Falling back to unsafe development key.")
        else:
            try:
                base64.urlsafe_b64decode(key)
            except Exception:
                key = base64.urlsafe_b64encode(key.ljust(32)[:32].encode())
        self.fernet = Fernet(key)

    def encrypt(self, val: Any) -> Optional[str]:
        if val is None:
            return None
        val_str = str(val)
        if val_str.startswith("ENC:"):
            return val_str
        try:
            return "ENC:" + self.fernet.encrypt(val_str.encode('utf-8')).decode('utf-8')
        except Exception as e:
            db_logger.error(f"Encryption failed: {str(e)}")
            return val_str

    def decrypt(self, val: Any) -> Any:
        if val is None:
            return None
        val_str = str(val)
        if not val_str.startswith("ENC:"):
            return val
        try:
            return self.fernet.decrypt(val_str[4:].encode('utf-8')).decode('utf-8')
        except Exception as e:
            db_logger.error(f"Decryption failed: {str(e)}")
            return val_str

db_encryptor = DatabaseEncryptor()

# Decrypted row wrapper to transparently decrypt DictRow or tuple access on-the-fly
class DecryptedRow:
    def __init__(self, row):
        self._row = row

    def __getitem__(self, key):
        val = self._row[key]
        if isinstance(val, str) and val.startswith("ENC:"):
            return db_encryptor.decrypt(val)
        return val

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getattr__(self, name):
        try:
            val = getattr(self._row, name)
            if isinstance(val, str) and val.startswith("ENC:"):
                return db_encryptor.decrypt(val)
            return val
        except AttributeError:
            try:
                return self[name]
            except KeyError:
                raise AttributeError(f"'DecryptedRow' object has no attribute '{name}'")

    def keys(self):
        if hasattr(self._row, 'keys'):
            return self._row.keys()
        return []

    def values(self):
        return [self[k] for k in self.keys()]

    def items(self):
        return [(k, self[k]) for k in self.keys()]

    def __iter__(self):
        for val in self._row:
            if isinstance(val, str) and val.startswith("ENC:"):
                yield db_encryptor.decrypt(val)
            else:
                yield val

    def __len__(self):
        return len(self._row)

    def __str__(self):
        return str(self._row)

    def __repr__(self):
        return repr(self._row)

# Parameter encryption parser helper
def encrypt_query_params(sql: str, params: Optional[Tuple[Any, ...]]) -> Optional[Tuple[Any, ...]]:
    if not params:
        return params
        
    sensitive_columns = {'aadhar_no', 'pan_no', 'account_no', 'ifsc_code', 'mfa_secret', 'backup_codes', 'bank_name', 'gst_no'}
    sql_upper = sql.upper().strip()
    params_list = list(params)
    
    if sql_upper.startswith('INSERT'):
        start_idx = sql.find('(')
        end_idx = sql.find(')', start_idx)
        if start_idx != -1 and end_idx != -1:
            cols_str = sql[start_idx+1:end_idx]
            cols = [c.strip().lower() for c in cols_str.split(',')]
            for i, col in enumerate(cols):
                if col in sensitive_columns and i < len(params_list):
                    params_list[i] = db_encryptor.encrypt(params_list[i])
                    
    elif sql_upper.startswith('UPDATE'):
        set_idx = sql_upper.find('SET')
        where_idx = sql_upper.find('WHERE')
        if set_idx != -1:
            set_clause = sql[set_idx+3:where_idx] if where_idx != -1 else sql[set_idx+3:]
            parts = set_clause.split(',')
            param_idx = 0
            for part in parts:
                if '=' in part:
                    col_name = part.split('=')[0].strip().lower()
                    placeholders = part.count('?') + part.count('%s')
                    for _ in range(placeholders):
                        if col_name in sensitive_columns and param_idx < len(params_list):
                            params_list[param_idx] = db_encryptor.encrypt(params_list[param_idx])
                        param_idx += 1
                        
    return tuple(params_list)

# Map SQLite exceptions to psycopg2 exceptions for backward compatibility in catch blocks
class DummySqlite3:
    OperationalError = (psycopg2.OperationalError, psycopg2.ProgrammingError)
    IntegrityError = psycopg2.IntegrityError
    Error = psycopg2.Error
    Row = object

sqlite3 = DummySqlite3
sys.modules['sqlite3'] = DummySqlite3

# Postgres Connection Wrapper classes
class PostgresCursorWrapper:
    def __init__(self, cursor, conn_wrapper):
        self.cursor = cursor
        self.conn_wrapper = conn_wrapper
        self.lastrowid = None

    def execute(self, sql, params=None):
        import re
        translated_sql = sql.replace('?', '%s')
        translated_sql = re.sub(r'\bIFNULL\b', 'COALESCE', translated_sql, flags=re.IGNORECASE)
        translated_sql = re.sub(r'\bLIKE\b', 'ILIKE', translated_sql, flags=re.IGNORECASE)
        translated_sql = re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b', 'SERIAL PRIMARY KEY', translated_sql, flags=re.IGNORECASE)
        
        is_insert = translated_sql.strip().upper().startswith('INSERT')
        has_returning = 'RETURNING' in translated_sql.upper()
        
        if is_insert and not has_returning:
            stripped = translated_sql.strip()
            if stripped.endswith(';'):
                translated_sql = stripped[:-1] + ' RETURNING id;'
            else:
                translated_sql = stripped + ' RETURNING id'
        
        if params is not None:
            if not isinstance(params, (tuple, list)):
                params = (params,)
            new_params = []
            for p in params:
                if p == '':
                    new_params.append(None)
                else:
                    new_params.append(p)
            params = tuple(new_params)
            
        params = encrypt_query_params(translated_sql, params)
        
        try:
            user_id = session.get('user_id', 'anonymous')
        except Exception:
            user_id = 'system'
        param_count = len(params) if params else 0
        db_logger.info(f"User: {user_id} | Query: {translated_sql.strip()} | Param Count: {param_count}")
                 
        in_transaction = (self.conn_wrapper.conn.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_INTRANS)
        
        savepoint_name = None
        if in_transaction:
            savepoint_name = f"sp_{secrets.randbelow(9000000) + 1000000}"
            with self.conn_wrapper.conn.cursor() as sp_cur:
                sp_cur.execute(f"SAVEPOINT {savepoint_name}")
            
        try:
            self.cursor.execute(translated_sql, params)
            if is_insert and not has_returning:
                row = self.cursor.fetchone()
                if row:
                    self.lastrowid = row[0]
            if savepoint_name:
                with self.conn_wrapper.conn.cursor() as sp_cur:
                    sp_cur.execute(f"RELEASE SAVEPOINT {savepoint_name}")
        except Exception as e:
            if savepoint_name:
                try:
                    with self.conn_wrapper.conn.cursor() as sp_cur:
                        sp_cur.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                except Exception:
                    pass
            raise e
            
        return self

    def fetchone(self):
        try:
            row = self.cursor.fetchone()
            return DecryptedRow(row) if row else None
        except psycopg2.ProgrammingError:
            return None

    def fetchall(self):
        try:
            rows = self.cursor.fetchall()
            return [DecryptedRow(r) for r in rows] if rows else []
        except psycopg2.ProgrammingError:
            return []

    def fetchmany(self, size=None):
        try:
            if size is None:
                rows = self.cursor.fetchmany()
            else:
                rows = self.cursor.fetchmany(size)
            return [DecryptedRow(r) for r in rows] if rows else []
        except psycopg2.ProgrammingError:
            return []

    @property
    def description(self):
        return self.cursor.description

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def __iter__(self):
        try:
            for row in self.cursor:
                yield DecryptedRow(row)
        except psycopg2.ProgrammingError:
            pass

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def cursor(self):
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(cur, self)

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    flask_env = os.environ.get('FLASK_ENV', 'production').lower()
    default_ssl = 'require' if flask_env == 'production' else 'prefer'
    sslmode = os.environ.get('DB_SSLMODE', default_ssl)
    
    if db_url:
        if 'sslmode=' not in db_url and 'sqlite:' not in db_url:
            separator = '&' if '?' in db_url else '?'
            db_url = f"{db_url}{separator}sslmode={sslmode}"
        return psycopg2.connect(db_url)
    
    db_name = os.environ.get('DB_NAME')
    try:
        return psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            database=db_name,
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            sslmode=sslmode
        )
    except psycopg2.OperationalError as e:
        if "does not exist" in str(e):
            try:
                conn = psycopg2.connect(
                    host=os.environ.get('DB_HOST'),
                    port=os.environ.get('DB_PORT'),
                    database='postgres',
                    user=os.environ.get('DB_USER'),
                    password=os.environ.get('DB_PASSWORD'),
                    sslmode=sslmode
                )
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute(f'CREATE DATABASE "{db_name}"')
                conn.close()
                return psycopg2.connect(
                    host=os.environ.get('DB_HOST'),
                    port=os.environ.get('DB_PORT'),
                    database=db_name,
                    user=os.environ.get('DB_USER'),
                    password=os.environ.get('DB_PASSWORD'),
                    sslmode=sslmode
                )
            except Exception as ex:
                raise ex
        raise e

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = PostgresConnectionWrapper(get_db_connection())
    return db

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

import re
def validate_password_strength(password: str) -> Tuple[bool, str]:
    if len(password) < 12 or len(password) > 128:
        return False, "Password must be between 12 and 128 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character."
    return True, ""

