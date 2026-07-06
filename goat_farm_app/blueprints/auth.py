import os
import secrets
import io
import base64
from datetime import datetime, timedelta
import pyotp
import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from goat_farm_app.extensions import (
    get_db,
    log_security_event,
    limiter,
    validate_password_strength
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user:
            # Check lockout
            now = datetime.now()
            if user['locked_until']:
                locked_until = user['locked_until']
                if isinstance(locked_until, str):
                    locked_until = datetime.fromisoformat(locked_until)
                # Strip timezone info for comparison if present
                if hasattr(locked_until, 'tzinfo') and locked_until.tzinfo is not None:
                    locked_until = locked_until.replace(tzinfo=None)
                if locked_until > now:
                    remaining = int((locked_until - now).total_seconds())
                    log_security_event('LOGIN_LOCKED', f"Locked user {username} attempted login", username=username)
                    flash(f'Account is locked due to too many failed attempts. Try again in {remaining} seconds.', 'danger')
                    return render_template('login.html')
                else:
                    # Lock has expired — auto-clear it so the account is no longer blocked
                    db.execute('UPDATE users SET login_attempts = 0, locked_until = NULL WHERE id = ?', (user['id'],))
                    db.commit()
            
            if check_password_hash(user['password'], password):
                # Reset login attempts
                db.execute('UPDATE users SET login_attempts = 0, locked_until = NULL WHERE id = ?', (user['id'],))
                db.commit()
                
                # Check MFA
                if user['mfa_enabled']:
                    session.clear()
                    session['temp_mfa_user_id'] = user['id']
                    log_security_event('MFA_CHALLENGE', f"MFA challenge presented to user {username}", username=username)
                    return redirect(url_for('auth.mfa_verify_login'))
                
                # Clear session to prevent fixation and rotate ID
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                
                log_security_event('LOGIN_SUCCESS', f"User {username} logged in successfully", username=username)
                
                # Update login tracking
                login_tracking = db.execute('SELECT * FROM user_login_tracking WHERE user_id = ?', (user['id'],)).fetchone()
                today = datetime.now().strftime('%Y-%m-%d')
                
                if not login_tracking:
                    db.execute('INSERT INTO user_login_tracking (user_id, last_login_date, has_seen_weight_notification) VALUES (?, ?, ?)',
                              (user['id'], today, 0))
                else:
                    db.execute('UPDATE user_login_tracking SET last_login_date = ?, has_seen_weight_notification = ? WHERE user_id = ?',
                              (today, 0, user['id']))
                
                db.commit()
                
                flash('Logged in successfully.', 'success')
                return redirect(url_for('dashboard'))
            else:
                # Increment failed attempts
                attempts = (user['login_attempts'] or 0) + 1
                locked_until_time = None
                if attempts >= 10:
                    locked_until_time = (now + timedelta(minutes=10)).isoformat()
                    log_security_event('ACCOUNT_LOCKOUT', f"Account locked (10 mins) for user {username} after 10 failures", username=username, failed_attempts=attempts)
                    flash('Too many failed attempts. Your account is locked for 10 minutes.', 'danger')
                elif attempts >= 5:
                    locked_until_time = (now + timedelta(minutes=1)).isoformat()
                    log_security_event('ACCOUNT_LOCKOUT', f"Account locked (1 min) for user {username} after 5 failures", username=username, failed_attempts=attempts)
                    flash('Too many failed attempts. Your account is locked for 1 minute.', 'danger')
                else:
                    log_security_event('LOGIN_FAILURE', f"Invalid credentials for user {username}", username=username, failed_attempts=attempts)
                    flash('Invalid username or password.', 'danger')
                
                db.execute('UPDATE users SET login_attempts = ?, locked_until = ? WHERE id = ?',
                           (attempts, locked_until_time, user['id']))
                db.commit()
        else:
            log_security_event('LOGIN_FAILURE', f"Attempted login with non-existent username: {username}", username=username)
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    username = session.get('username')
    log_security_event('LOGOUT', f"User {username or 'anonymous'} logged out", username=username)
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    db = get_db()
    current_user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not current_user or int(current_user['is_admin']) != 1:
        log_security_event('UNAUTHORIZED_ACCESS', f"Unauthorized access attempt to registration by user ID {session.get('user_id')}")
        flash('Only administrators can register new accounts.', 'danger')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        confirm_password = request.form.get('confirm_password')
        is_admin_flag = 1 if request.form.get('is_admin') else 0
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
            
        # Enforce password strength validation
        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            log_security_event('REGISTRATION_FAILURE', f"Failed password strength check for {username}", username=username)
            flash(msg, 'danger')
            return redirect(url_for('auth.register'))
            
        # Enforce account limit of 6
        user_count = db.execute('SELECT COUNT(*) FROM users').fetchone()[0] or 0
        if user_count >= 6:
            log_security_event('REGISTRATION_DENIED', f"Registration limit reached (6 accounts max). Attempt by: {username}", username=username)
            flash('Registration limit reached. A maximum of 6 accounts is allowed.', 'danger')
            return redirect(url_for('auth.register'))
            
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            log_security_event('REGISTRATION_FAILURE', f"Username {username} already exists", username=username)
            flash('Username already exists.', 'danger')
            return redirect(url_for('auth.register'))
            
        password_hash = generate_password_hash(password)
        # Explicitly set login_attempts=0 and locked_until=NULL so newly created
        # accounts are never accidentally locked from the start.
        db.execute(
            'INSERT INTO users (username, password, password_history, is_admin, login_attempts, locked_until) '
            'VALUES (?, ?, ?, ?, 0, NULL)',
            (username, password_hash, password_hash, is_admin_flag)
        )
        db.commit()
        
        log_security_event('USER_REGISTRATION', f"New user {username} (admin={is_admin_flag}) successfully registered by admin {session.get('username')}", username=username)
        flash('Registration successful!', 'success')
        return redirect(url_for('auth.manage_users'))
        
    return render_template('register.html', is_admin=True)

@auth_bp.route('/manage_users')
def manage_users():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = get_db()
    current_user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not current_user or int(current_user['is_admin']) != 1:
        log_security_event('UNAUTHORIZED_ACCESS', "Unauthorized access attempt to manage_users")
        flash('Administrator privileges required.', 'danger')
        return redirect(url_for('dashboard'))
        
    # One-shot cleanup: reset login_attempts for any account that has no active lock.
    # This fixes accounts that accumulated failed attempts without hitting the lockout
    # threshold, and any stale data from before this fix was applied.
    db.execute(
        'UPDATE users SET login_attempts = 0 WHERE login_attempts > 0 '
        'AND (locked_until IS NULL OR locked_until <= NOW())'
    )
    db.commit()

    raw_users = db.execute('SELECT id, username, is_admin, mfa_enabled, login_attempts, locked_until FROM users ORDER BY id').fetchall()
    
    # Compute a server-side is_locked flag so the template never mistakes an
    # expired lock timestamp for an active lock.
    now = datetime.now()
    users_with_status = []
    for u in raw_users:
        locked_until = u['locked_until']
        is_locked = False
        if locked_until:
            if isinstance(locked_until, str):
                locked_until = datetime.fromisoformat(locked_until)
            if hasattr(locked_until, 'tzinfo') and locked_until.tzinfo is not None:
                locked_until = locked_until.replace(tzinfo=None)
            if locked_until > now:
                is_locked = True
            else:
                # Expired lock — silently clear it in the background
                db.execute('UPDATE users SET login_attempts = 0, locked_until = NULL WHERE id = ?', (u['id'],))
        login_attempts = u['login_attempts'] or 0
        if locked_until and not is_locked:
            # Expired lock was cleared above — also zero out login_attempts in the dict
            login_attempts = 0
        users_with_status.append({
            'id': u['id'],
            'username': u['username'],
            'is_admin': u['is_admin'],
            'mfa_enabled': u['mfa_enabled'],
            'login_attempts': login_attempts,
            'locked_until': u['locked_until'],
            'is_locked': is_locked,
        })
    db.commit()
    
    return render_template('manage_users.html', users=users_with_status)

@auth_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = get_db()
    current_user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not current_user or int(current_user['is_admin']) != 1:
        log_security_event('UNAUTHORIZED_ACCESS', f"Unauthorized user deletion attempt by user ID {session.get('user_id')}")
        flash('Administrator privileges required.', 'danger')
        return redirect(url_for('dashboard'))
        
    if user_id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('auth.manage_users'))
        
    user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        db.execute('DELETE FROM user_login_tracking WHERE user_id = ?', (user_id,))
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        log_security_event('USER_DELETION', f"User {user['username']} deleted by admin {session.get('username')}", username=user['username'])
        flash('User deleted successfully.', 'success')
    else:
        flash('User not found.', 'danger')
        
    return redirect(url_for('auth.manage_users'))

@auth_bp.route('/unlock_user/<int:user_id>', methods=['POST'])
def unlock_user(user_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    db = get_db()
    current_user = db.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not current_user or int(current_user['is_admin']) != 1:
        log_security_event('UNAUTHORIZED_ACCESS', f"Unauthorized user unlock attempt by user ID {session.get('user_id')}")
        flash('Administrator privileges required.', 'danger')
        return redirect(url_for('dashboard'))
        
    user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
    if user:
        db.execute('UPDATE users SET login_attempts = 0, locked_until = NULL WHERE id = ?', (user_id,))
        db.commit()
        log_security_event('USER_UNLOCK', f"User {user['username']} unlocked by admin {session.get('username')}", username=user['username'])
        flash('User account unlocked successfully.', 'success')
    else:
        flash('User not found.', 'danger')
        
    return redirect(url_for('auth.manage_users'))

@auth_bp.route('/mfa/enroll', methods=['GET'])
def mfa_enroll():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if user['mfa_enabled']:
        flash('MFA is already enabled on your account.', 'info')
        return redirect(url_for('farm_settings'))
        
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user['username'], issuer_name="Ranga Farms")
    
    # Generate QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    try:
        img.save(buffered, format="PNG")
    except TypeError:
        img.save(buffered)
    qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    # Generate 10 one-time recovery codes
    backup_codes_raw = [f"{secrets.randbelow(900000) + 100000}" for _ in range(10)]
    backup_codes_hashed = [generate_password_hash(c) for c in backup_codes_raw]
    
    # Store temporary secret and recovery codes in session so we only save to DB when verified
    session['temp_mfa_secret'] = secret
    session['temp_backup_codes'] = backup_codes_hashed
    
    return render_template('mfa_enroll.html', secret=secret, qr_code=qr_base64, backup_codes=backup_codes_raw)

@auth_bp.route('/mfa/verify-setup', methods=['POST'])
def mfa_verify_setup():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    code = request.form.get('code', '').strip()
    secret = session.get('temp_mfa_secret')
    backup_codes = session.get('temp_backup_codes')
    
    if not secret or not backup_codes:
        flash('MFA session expired. Please try again.', 'danger')
        return redirect(url_for('auth.mfa_enroll'))
        
    totp = pyotp.TOTP(secret)
    if totp.verify(code):
        db = get_db()
        backup_codes_str = ",".join(backup_codes)
        db.execute('UPDATE users SET mfa_secret = ?, mfa_enabled = 1, backup_codes = ? WHERE id = ?',
                   (secret, backup_codes_str, session['user_id']))
        db.commit()
        
        session.pop('temp_mfa_secret', None)
        session.pop('temp_backup_codes', None)
        
        log_security_event('MFA_ENABLED', f"User ID {session['user_id']} successfully enabled MFA")
        flash('MFA enabled successfully! Please store your recovery codes securely.', 'success')
        return redirect(url_for('farm_settings'))
    else:
        log_security_event('MFA_SETUP_FAILURE', f"MFA setup code verification failed for user ID {session['user_id']}")
        flash('Invalid verification code. Please try again.', 'danger')
        return redirect(url_for('auth.mfa_enroll'))

@auth_bp.route('/mfa/verify-login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def mfa_verify_login():
    temp_user_id = session.get('temp_mfa_user_id')
    if not temp_user_id:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (temp_user_id,)).fetchone()
        
        # Check standard TOTP
        totp = pyotp.TOTP(user['mfa_secret'])
        if totp.verify(code):
            session.pop('temp_mfa_user_id', None)
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            log_security_event('MFA_LOGIN_SUCCESS', f"User {user['username']} logged in successfully with MFA TOTP", username=user['username'])
            
            login_tracking = db.execute('SELECT * FROM user_login_tracking WHERE user_id = ?', (user['id'],)).fetchone()
            today = datetime.now().strftime('%Y-%m-%d')
            if not login_tracking:
                db.execute('INSERT INTO user_login_tracking (user_id, last_login_date, has_seen_weight_notification) VALUES (?, ?, ?)',
                          (user['id'], today, 0))
            else:
                db.execute('UPDATE user_login_tracking SET last_login_date = ?, has_seen_weight_notification = ? WHERE user_id = ?',
                          (today, 0, user['id']))
            db.commit()
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
            
        # Check backup recovery codes
        if user['backup_codes']:
            codes_list = user['backup_codes'].split(',')
            for index, hashed_code in enumerate(codes_list):
                if check_password_hash(hashed_code, code):
                    codes_list.pop(index)
                    new_backup_codes_str = ",".join(codes_list)
                    db.execute('UPDATE users SET backup_codes = ? WHERE id = ?', (new_backup_codes_str, user['id']))
                    db.commit()
                    
                    session.pop('temp_mfa_user_id', None)
                    session.clear()
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    
                    log_security_event('MFA_RECOVERY_LOGIN_SUCCESS', f"User {user['username']} logged in using recovery backup code", username=user['username'])
                    flash('Logged in successfully using a recovery code. Note: this recovery code is now deactivated.', 'success')
                    return redirect(url_for('dashboard'))
                    
        log_security_event('MFA_LOGIN_FAILURE', f"MFA code verification failed for user {user['username']}", username=user['username'])
        flash('Invalid verification or recovery code.', 'danger')
        
    return render_template('mfa_verify.html')

@auth_bp.route('/mfa/disable', methods=['POST'])
def mfa_disable():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    db = get_db()
    db.execute('UPDATE users SET mfa_secret = NULL, mfa_enabled = 0, backup_codes = NULL WHERE id = ?', (session['user_id'],))
    db.commit()
    log_security_event('MFA_DISABLED', f"User ID {session['user_id']} disabled MFA")
    flash('MFA has been disabled on your account.', 'warning')
    return redirect(url_for('farm_settings'))
