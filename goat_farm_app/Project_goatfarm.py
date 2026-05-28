import os
import sqlite3
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev_secret_key_for_goat_farm'
DB_FILE = os.path.join(app.root_path, 'database.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_FILE, timeout=30.0)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL;")
        except Exception:
            pass
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def calculate_age_str(dob_str):
    if not dob_str:
        return 'N/A'
    try:
        from datetime import datetime
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
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
        from datetime import datetime
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
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

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS goats_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                si_no TEXT, tag_no TEXT NOT NULL, breed TEXT, breed_percent TEXT,
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
            conn.execute('ALTER TABLE master_records ADD COLUMN vaccination_next_due DATE')
        except Exception:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sales_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            conn.execute('ALTER TABLE feed_inventory ADD COLUMN wastage_qty REAL DEFAULT 0')
        except sqlite3.OperationalError:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS kid_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            except sqlite3.OperationalError:
                pass
                
        add_column("kid_records", "mother_id", "TEXT")
        add_column("kid_records", "father_id", "TEXT")
        add_column("kid_records", "insurance_policy_no", "TEXT")
        add_column("kid_records", "insurance_company", "TEXT")
        add_column("kid_records", "insurance_expiry", "DATE")
        add_column("kid_records", "insurance_amount", "REAL")

        try:
            conn.execute("ALTER TABLE master_records ADD COLUMN kit_status TEXT DEFAULT 'No'")
        except sqlite3.OperationalError:
            pass

        try:
            conn.execute("ALTER TABLE master_records ADD COLUMN dob DATE")
        except sqlite3.OperationalError:
            pass

        add_column("feed_inventory", "purchase_id", "INTEGER")
        add_column("medicine_inventory", "purchase_id", "INTEGER")
        add_column("vaccine_inventory", "purchase_id", "INTEGER")

        # Ensure equipment table has all required fields
        conn.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                breed_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT UNIQUE NOT NULL,
                contact_person TEXT,
                phone TEXT,
                address TEXT,
                supplier_type TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feed_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vaccine_name TEXT NOT NULL,
                quantity REAL NOT NULL,
                cost REAL NOT NULL,
                purchase_date DATE NOT NULL,
                supplier TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_name TEXT NOT NULL,
                invoice_details TEXT,
                purchase_date DATE NOT NULL,
                tag_id TEXT NOT NULL,
                price REAL NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS farm_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            conn.execute("ALTER TABLE vaccine_records ADD COLUMN next_due_date DATE")
        except sqlite3.OperationalError:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS doctor_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                last_login_date DATE DEFAULT NULL,
                has_seen_weight_notification INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        # Check if admin user exists
        user = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
        if not user:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         ('admin', generate_password_hash('admin123')))
        conn.commit()

# Initialize DB on startup
with app.app_context():
    init_db()

@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'register', 'verify_otp', 'goats', 'goat_detail']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))
        
    # Progress toast status for single pop-up per login session
    status = session.get('show_eligible_toast')
    if status == 'showing':
        session['show_eligible_toast'] = 'shown'
    elif status == 'shown':
        session['show_eligible_toast'] = 'done'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            # Setup toast popups to display exactly once per login session
            session['show_eligible_toast'] = 'showing'
            session['show_weight_notification'] = True
            
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
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if existing:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
            
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        print(f"\n" + "="*50)
        print(f" MOCK OTP NOTIFICATION")
        print(f" Registration OTP for '{username}' is: {otp}")
        print("="*50 + "\n")
        
        session['reg_username'] = username
        session['reg_password'] = generate_password_hash(password)
        session['reg_otp'] = otp
        
        flash('We have generated an OTP for you. Since this is a demo, please check the console for the code.', 'info')
        return redirect(url_for('verify_otp'))
        
    return render_template('register.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if 'reg_otp' not in session:
        flash('Session expired. Please register again.', 'warning')
        return redirect(url_for('register'))
        
    if request.method == 'POST':
        user_otp = request.form['otp'].strip()
        if user_otp == session['reg_otp']:
            # OTP matches, create user
            username = session['reg_username']
            password_hash = session['reg_password']
            
            db = get_db()
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
            db.commit()
            
            # Clear registration session data
            session.pop('reg_username', None)
            session.pop('reg_password', None)
            session.pop('reg_otp', None)
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please try again.', 'danger')
            
    return render_template('verify_otp.html')

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
    
    # Income = sales
    income = db.execute("SELECT SUM(sold_price) FROM sales_records").fetchone()[0] or 0.0
    
    # Detailed expense calculation for dashboard
    # 1. Purchases (Goats, Feed, Med, Vac)
    exp_goat = db.execute("SELECT SUM(price) FROM purchases").fetchone()[0] or 0.0
    exp_feed = db.execute("SELECT SUM(total_cost) FROM feed_inventory").fetchone()[0] or 0.0
    exp_med = db.execute("SELECT SUM(cost) FROM medicine_purchases").fetchone()[0] or 0.0
    exp_vac = db.execute("SELECT SUM(cost) FROM vaccine_purchases").fetchone()[0] or 0.0
    
    # 2. Operations (Maintenance + Salaries + General Expenses)
    exp_salary = db.execute("SELECT SUM(net_salary) FROM salary_payments").fetchone()[0] or 0.0
    exp_maint = db.execute("SELECT SUM(service_cost) FROM equipment_services").fetchone()[0] or 0.0
    exp_gen = db.execute("SELECT SUM(amount) FROM expenses WHERE status='Approved'").fetchone()[0] or 0.0
    
    expense = exp_goat + exp_feed + exp_med + exp_vac + exp_salary + exp_maint + exp_gen
    profit = income - expense
    
    # 3. Weight Notification Logic
    heavy_goats = []
    show_weight_notification = session.get('show_weight_notification', False)
    if show_weight_notification:
        heavy_goats = db.execute("SELECT tag_no, color, weight_kg FROM master_records WHERE weight_kg >= 25 AND status = 'Active' ORDER BY weight_kg DESC").fetchall()
        # Clear the notification flag after displaying
        if 'user_id' in session:
            db.execute('UPDATE user_login_tracking SET has_seen_weight_notification = 1 WHERE user_id = ?', (session['user_id'],))
            db.commit()
        session.pop('show_weight_notification', None)
    
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
        db.commit()
        flash('Record updated successfully.', 'success')
        return redirect(url_for('records'))
        
    return render_template('edit_record.html', record=record)

@app.route('/delete_record/<int:id>', methods=['POST'])
def delete_record(id):
    db = get_db()
    db.execute('DELETE FROM goats_data WHERE id = ?', (id,))
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
        GROUP BY m.tag_no
        ORDER BY CAST(m.tag_no AS INTEGER) ASC
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
    
    income = sum(r['amount'] for r in history if r['category'] == 'income')
    expense = sum(r['amount'] for r in history if r['category'] == 'expense')
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
        if dob_str:
            try:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
                days_old = (today - dob_date).days
            except Exception:
                pass
        animal['days_old'] = days_old
        animal['age_str'] = calculate_age_str(dob_str)
        all_animals.append(animal)
        
    for row in kids_raw:
        animal = dict(row)
        dob_str = animal.get('dob')
        days_old = 9999
        if dob_str:
            try:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
                days_old = (today - dob_date).days
            except Exception:
                pass
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
    
    return render_template('goat_batches.html',
                           batch_0_6m=batch_0_6m,
                           batch_6m_1y=batch_6m_1y,
                           batch_1y_2y=batch_1y_2y,
                           batch_above_2y=batch_above_2y)

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
        raw_records = db.execute('SELECT * FROM sales_records ORDER BY date_of_sale DESC').fetchall()
        for r in raw_records:
            records.append({
                'id': r['id'],
                'sr_no': r['sr_no'],
                'title': f"Goat Sale - Tag: {r['tag_id']}",
                'subtitle': f"Breed: {r['breed']} ({r['breed_percent']}%) | Weight: {r['weight']} kg | Buyer: {r['buyer_name']}",
                'date': r['date_of_sale'],
                'amount': r['sold_price'],
                'buyer_name': r['buyer_name'],
                'buyer_city': r['buyer_city'],
                'buyer_contact': r['buyer_contact'],
                'notes': f"Sold {r['gender']} Goat with Tag ID {r['tag_id']}."
            })
    elif s_type == 'other':
        raw_records = db.execute('SELECT * FROM other_sales_records ORDER BY date_of_sale DESC').fetchall()
        for r in raw_records:
            records.append({
                'id': r['id'],
                'sr_no': r['sr_no'],
                'title': f"Other Sale: {r['item_name']}",
                'subtitle': f"Quantity: {r['quantity']} {r['unit']} @ ₹{r['price_per_unit']}/unit | Buyer: {r['buyer_name']}",
                'date': r['date_of_sale'],
                'amount': r['total_amount'],
                'buyer_name': r['buyer_name'],
                'buyer_city': r['buyer_city'],
                'buyer_contact': r['buyer_contact'],
                'notes': r['notes']
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
    today_str = datetime.now().strftime('%Y-%m-%d')
    res = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM sales_records').fetchone()[0]
    next_sr = str((res or 0) + 1)
    
    if request.method == 'POST':
        f = request.form
        p_date = f.get('date_of_sale') or today_str
        
        # Get next serial number
        if s_type == 'goat':
            tag_id = f.get('tag_id')
            goat = db.execute('SELECT 1 FROM master_records WHERE tag_no = ?', (tag_id,)).fetchone()
            if not goat:
                flash(f'No goat exists with this tag id "{tag_id}"', 'danger')
                goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' ORDER BY tag_no ASC").fetchall()
                return render_template('sales_form.html', s_type=s_type, action='Create', today=today_str, next_sr=next_sr, record=f, goats=goats)
                
            db.execute('''
                INSERT INTO sales_records (
                    sr_no, tag_id, breed, breed_percent, gender, weight, sold_price, 
                    date_of_sale, buyer_name, buyer_city, buyer_contact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                next_sr, f.get('tag_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'),
                float(f.get('weight') or 0), float(f.get('sold_price') or 0), p_date,
                f.get('buyer_name'), f.get('buyer_city'), f.get('buyer_contact')
            ))
            
            # Update status in master_records
            db.execute("UPDATE master_records SET status = 'Sold', selling_date = ?, selling_price = ? WHERE tag_no = ?",
                       (p_date, float(f.get('sold_price') or 0), f.get('tag_id')))
            
            # Remove from eligible_to_sell list
            db.execute("DELETE FROM eligible_to_sell WHERE tag_id = ?", (f.get('tag_id'),))
            
        elif s_type == 'other':
            qty = float(f.get('quantity') or 0)
            price_per = float(f.get('price_per_unit') or 0)
            total = qty * price_per
            
            db.execute('''
                INSERT INTO other_sales_records (
                    sr_no, item_name, quantity, unit, price_per_unit, total_amount,
                    date_of_sale, buyer_name, buyer_city, buyer_contact, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                next_sr, f.get('item_name'), qty, f.get('unit'), price_per, total,
                p_date, f.get('buyer_name'), f.get('buyer_city'), f.get('buyer_contact'), f.get('notes')
            ))
            
        db.commit()
        flash('Sales record added successfully!', 'success')
        return redirect(url_for('sales_register', s_type=s_type))
        
    goats = []
    if s_type == 'goat':
        goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' ORDER BY tag_no ASC").fetchall()
    return render_template('sales_form.html', s_type=s_type, action='Create', today=today_str, next_sr=next_sr, goats=goats)

@app.route('/sales/<s_type>/edit/<int:id>', methods=['GET', 'POST'])
def sales_edit(s_type, id):
    db = get_db()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    if s_type == 'goat':
        record = db.execute('SELECT * FROM sales_records WHERE id = ?', (id,)).fetchone()
    else:
        record = db.execute('SELECT * FROM other_sales_records WHERE id = ?', (id,)).fetchone()
        
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('sales_register', s_type=s_type))
        
    if request.method == 'POST':
        f = request.form
        p_date = f.get('date_of_sale') or today_str
        
        if s_type == 'goat':
            tag_id = f.get('tag_id')
            goat = db.execute('SELECT 1 FROM master_records WHERE tag_no = ?', (tag_id,)).fetchone()
            if not goat:
                flash(f'No goat exists with this tag id "{tag_id}"', 'danger')
                goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' OR tag_no = ? ORDER BY tag_no ASC", (record['tag_id'],)).fetchall()
                return render_template('sales_form.html', s_type=s_type, action='Edit', today=today_str, record=record, goats=goats)
                
            # Revert old goat status to Active first (in case tag_id changed)
            old_tag = record['tag_id']
            db.execute("UPDATE master_records SET status = 'Active', selling_date = NULL, selling_price = NULL WHERE tag_no = ?", (old_tag,))
            
            db.execute('''
                UPDATE sales_records SET 
                tag_id = ?, breed = ?, breed_percent = ?, gender = ?, weight = ?,
                sold_price = ?, date_of_sale = ?, buyer_name = ?, buyer_city = ?, buyer_contact = ?
                WHERE id = ?
            ''', (
                f.get('tag_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'),
                float(f.get('weight') or 0), float(f.get('sold_price') or 0), p_date,
                f.get('buyer_name'), f.get('buyer_city'), f.get('buyer_contact'), id
            ))
            
            # Set new goat status to Sold
            db.execute("UPDATE master_records SET status = 'Sold', selling_date = ?, selling_price = ? WHERE tag_no = ?",
                       (p_date, float(f.get('sold_price') or 0), f.get('tag_id')))
                       
        elif s_type == 'other':
            qty = float(f.get('quantity') or 0)
            price_per = float(f.get('price_per_unit') or 0)
            total = qty * price_per
            
            db.execute('''
                UPDATE other_sales_records SET 
                item_name = ?, quantity = ?, unit = ?, price_per_unit = ?, total_amount = ?,
                date_of_sale = ?, buyer_name = ?, buyer_city = ?, buyer_contact = ?, notes = ?
                WHERE id = ?
            ''', (
                f.get('item_name'), qty, f.get('unit'), price_per, total,
                p_date, f.get('buyer_name'), f.get('buyer_city'), f.get('buyer_contact'), f.get('notes'), id
            ))
            
        db.commit()
        flash('Sales record updated successfully!', 'success')
        return redirect(url_for('sales_register', s_type=s_type))
        
    goats = []
    if s_type == 'goat':
        goats = db.execute("SELECT tag_no, breed, weight_kg FROM master_records WHERE status = 'Active' OR tag_no = ? ORDER BY tag_no ASC", (record['tag_id'],)).fetchall()
    return render_template('sales_form.html', s_type=s_type, action='Edit', record=record, today=today_str, goats=goats)

@app.route('/sales/<s_type>/delete/<int:id>', methods=['POST'])
def sales_delete(s_type, id):
    db = get_db()
    if s_type == 'goat':
        record = db.execute('SELECT tag_id FROM sales_records WHERE id = ?', (id,)).fetchone()
        if record:
            tag_id = record['tag_id']
            db.execute('DELETE FROM sales_records WHERE id = ?', (id,))
            db.execute("UPDATE master_records SET status = 'Active', selling_date = NULL, selling_price = NULL WHERE tag_no = ?", (tag_id,))
            db.execute("INSERT OR IGNORE INTO eligible_to_sell (tag_id, tag_no, breed, gender, weight_kg) SELECT tag_no, tag_no, breed, gender, weight_kg FROM master_records WHERE tag_no = ?", (tag_id,))
    elif s_type == 'other':
        db.execute('DELETE FROM other_sales_records WHERE id = ?', (id,))
        
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
        sale = {
            'id': sale_raw['id'],
            'date_of_sale': sale_raw['date_of_sale'],
            'buyer_name': sale_raw['buyer_name'],
            'buyer_city': sale_raw['buyer_city'],
            'buyer_contact': sale_raw['buyer_contact'],
            'total_amount': sale_raw['sold_price'],
            'tag_id': sale_raw['tag_id'],
            'breed': sale_raw['breed'],
            'breed_percent': sale_raw['breed_percent'],
            'gender': sale_raw['gender'],
            'weight': sale_raw['weight']
        }
        particulars = [
            {'label': 'Tag/ID Number', 'value': sale_raw['tag_id']},
            {'label': 'Gender', 'value': sale_raw['gender']},
            {'label': 'Weight (kg)', 'value': f"{sale_raw['weight']} kg"},
            {'label': 'Breed', 'value': f"{sale_raw['breed']} ({sale_raw['breed_percent']}%)"}
        ]
    else:
        sale_raw = db.execute('SELECT * FROM other_sales_records WHERE id = ?', (id,)).fetchone()
        if not sale_raw:
            flash('Sales record not found.', 'danger')
            return redirect(url_for('sales_register', s_type=s_type))
        sale = {
            'id': sale_raw['id'],
            'date_of_sale': sale_raw['date_of_sale'],
            'buyer_name': sale_raw['buyer_name'],
            'buyer_city': sale_raw['buyer_city'],
            'buyer_contact': sale_raw['buyer_contact'],
            'total_amount': sale_raw['total_amount'],
            'item_name': sale_raw['item_name'],
            'quantity': sale_raw['quantity'],
            'unit': sale_raw['unit'],
            'price_per_unit': sale_raw['price_per_unit'],
            'notes': sale_raw['notes']
        }
        particulars = [
            {'label': 'Item Sold', 'value': sale_raw['item_name']},
            {'label': 'Quantity', 'value': f"{sale_raw['quantity']} {sale_raw['unit']}"},
            {'label': 'Price per Unit', 'value': f"₹{sale_raw['price_per_unit']}"},
            {'label': 'Additional Notes', 'value': sale_raw['notes'] or 'N/A'}
        ]
        
    return render_template('sales_invoice.html', sale=sale, particulars=particulars, farm_info=farm_info, s_type=s_type, current_date=datetime.now())

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
        sale = db.execute('SELECT * FROM sales_records WHERE id = ?', (id,)).fetchone()
    else:
        sale = db.execute('SELECT * FROM other_sales_records WHERE id = ?', (id,)).fetchone()
        
    if not sale:
        flash('Sales record not found.', 'danger')
        return redirect(url_for('sales_register', s_type=s_type))
        
    # Generate text bill
    bill_text = ""
    bill_text += "=" * 70 + "\n"
    bill_text += f"{(farm_info['farm_name'] if farm_info and farm_info['farm_name'] else 'Ranga Farms'):^70}\n"
    bill_text += "=" * 70 + "\n"
    bill_text += f"{('SALES INVOICE (' + s_type.upper() + ')'):^70}\n"
    bill_text += "=" * 70 + "\n\n"
    
    bill_text += f"Invoice #: INV-{s_type.upper()[:3]}-{sale['id']}\n"
    bill_text += f"Date of Issue: {sale['date_of_sale']}\n\n"
    
    bill_text += "BILL TO:\n"
    bill_text += f"Buyer Name: {sale['buyer_name']}\n"
    bill_text += f"City: {sale['buyer_city']}\n"
    bill_text += f"Contact: {sale['buyer_contact']}\n\n"
    
    bill_text += "-" * 70 + "\n"
    if s_type == 'goat':
        bill_text += f"{'Particulars':<45} | {'Details':<20}\n"
        bill_text += "-" * 70 + "\n"
        bill_text += f"{'Goat Tag ID':<45} | {sale['tag_id']:<20}\n"
        bill_text += f"{'Breed':<45} | {sale['breed'] + ' (' + sale['breed_percent'] + '%)':<20}\n"
        bill_text += f"{'Gender':<45} | {sale['gender']:<20}\n"
        bill_text += f"{'Weight':<45} | {str(sale['weight']) + ' kg':<20}\n"
        amount = sale['sold_price']
    else:
        bill_text += f"{'Particulars':<45} | {'Details':<20}\n"
        bill_text += "-" * 70 + "\n"
        bill_text += f"{'Item Name':<45} | {sale['item_name']:<20}\n"
        bill_text += f"{'Quantity':<45} | {str(sale['quantity']) + ' ' + sale['unit']:<20}\n"
        bill_text += f"{'Price per Unit':<45} | {'INR ' + str(sale['price_per_unit']):<20}\n"
        amount = sale['total_amount']
        
    bill_text += "-" * 70 + "\n"
    bill_text += f"{'TOTAL AMOUNT':<45} | INR {amount:.2f}\n"
    bill_text += "=" * 70 + "\n\n"
    bill_text += "Thank you for your business!\n"
    
    # Download file response
    mem_file = BytesIO()
    mem_file.write(bill_text.encode('utf-8'))
    mem_file.seek(0)
    
    return send_file(
        mem_file,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"Invoice_{s_type}_{sale['id']}.txt"
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
        q += ' AND strftime("%Y-%m", consultation_date) = ?'
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
        if dob_str:
            try:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
                days_old = (today - dob_date).days
            except Exception:
                pass
        animal['days_old'] = days_old
        all_animals.append(animal)
        
    for row in kids_raw:
        animal = dict(row)
        dob_str = animal.get('dob')
        days_old = 9999
        if dob_str:
            try:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
                days_old = (today - dob_date).days
            except Exception:
                pass
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
        if dob_str:
            try:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
                days = (today - dob_date).days
                if days <= 182:
                    batch_counts[1] += 1
                elif days <= 365:
                    batch_counts[2] += 1
                elif days <= 730:
                    batch_counts[3] += 1
                else:
                    batch_counts[4] += 1
            except Exception:
                pass
                
    for row in kids_raw:
        dob_str = row['dob']
        if dob_str:
            try:
                dob_date = datetime.strptime(dob_str, '%Y-%m-%d').date()
                days = (today - dob_date).days
                if days <= 182:
                    batch_counts[1] += 1
                elif days <= 365:
                    batch_counts[2] += 1
                elif days <= 730:
                    batch_counts[3] += 1
                else:
                    batch_counts[4] += 1
            except Exception:
                pass
                
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
            INSERT INTO feed_inventory (feed_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
            VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_name, opening, qty, closing, unit, cost_per_unit, cost, date_str, supplier, purchase_id))
        
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
            INSERT INTO medicine_inventory (medicine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
            VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_name, opening, qty, closing, unit, cost_per_unit, cost, date_str, supplier, purchase_id))
        
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
            INSERT INTO vaccine_inventory (vaccine_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
            VALUES (?, ?, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
        ''', (item_name, opening, qty, closing, unit, cost_per_unit, cost, date_str, supplier, purchase_id))
        
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
        
    closing = max(0.0, opening - qty - wastage)
    
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
        records = db.execute('SELECT * FROM kid_records WHERE kid_id LIKE ? ORDER BY birth_date DESC', 
             (f"%{kid_search}%",)).fetchall()
    else:
        records = db.execute('SELECT * FROM kid_records ORDER BY birth_date DESC').fetchall()
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
        q += ' AND strftime("%Y-%m", vaccine_date) = ?'
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
        closing = opening - consumption - wastage
        
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
    
    return render_template('kid_edit.html', record=record)

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
        raw_records = db.execute('SELECT * FROM equipment ORDER BY purchase_date DESC').fetchall()
        for r in raw_records:
            records.append({
                'id': r['id'],
                'title': f"Asset: {r['name']}",
                'subtitle': f"Type: {r['type']} | Supplier: {r['supplier']}",
                'date': r['purchase_date'],
                'amount': r['purchase_cost'] or 0.0,
                'notes': r['notes'] or "No details"
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
        
        if v_type == 'goat':
            tag_id = f.get('tag_id')
            price = float(f.get('price') or 0)
            
            # 1. Save to purchases
            db.execute('''
                INSERT INTO purchases (seller_name, invoice_details, purchase_date, tag_id, price)
                VALUES (?, ?, ?, ?, ?)
            ''', (f.get('seller_name'), f.get('notes'), p_date, tag_id, price))
            
            # 2. Add to master_records
            breed = f.get('breed', 'Unknown')
            gender = f.get('gender', 'Unknown')
            weight = float(f.get('weight') or 0)
            db.execute('''
                INSERT INTO master_records (tag_no, breed, gender, purchase_date, weight_kg, purchase_amount, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Active')
            ''', (tag_id, breed, gender, p_date, weight, price))
            db.commit()
            flash('Goat Purchase Voucher created successfully!', 'success')
            
        elif v_type == 'feed':
            feed_name = f.get('feed_name')
            qty = float(f.get('quantity') or 0)
            cost = float(f.get('cost') or 0)
            unit = f.get('unit', 'KG')
            supplier = f.get('supplier')
            
            cursor = db.execute('''
                INSERT INTO feed_purchases (feed_name, quantity, unit, cost, purchase_date, supplier)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (feed_name, qty, unit, cost, p_date, supplier))
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
            desc = f"Purchased {qty} {unit} of {feed_name} from {supplier}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', 'Feed', ?, ?)
            ''', (p_date, cost, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                VALUES ('Feed Purchase', ?, ?, ?, ?, 'Cash', 'Paid')
            ''', (cost, p_date, desc, supplier))
            
            db.commit()
            flash('Feed Purchase Voucher created successfully!', 'success')
            
        elif v_type == 'health':
            sub_type = f.get('sub_type', 'medicine')
            name = f.get('health_name')
            qty = float(f.get('quantity') or 0)
            cost = float(f.get('cost') or 0)
            supplier = f.get('supplier')
            
            if sub_type == 'medicine':
                dose_unit = f.get('dose_unit', 'ml')
                cursor = db.execute('''
                    INSERT INTO medicine_purchases (medicine_name, dose_unit, quantity, cost, purchase_date, supplier)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, dose_unit, qty, cost, p_date, supplier))
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
                    INSERT INTO vaccine_purchases (vaccine_name, quantity, cost, purchase_date, supplier)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name, qty, cost, p_date, supplier))
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
            desc = f"Purchased {qty} Doses of {name} from {supplier}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', ?, ?, ?)
            ''', (p_date, sub_type.capitalize(), cost, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid')
            ''', (sub_type.capitalize() + ' Purchase', cost, p_date, desc, supplier))
            
            db.commit()
            flash('Health Supplies Voucher created successfully!', 'success')
            
        elif v_type == 'other':
            name = f.get('name')
            asset_type = f.get('type')
            cost = float(f.get('cost') or 0)
            supplier = f.get('supplier')
            notes = f.get('notes')
            status = f.get('status', 'Active')
            
            db.execute('''
                INSERT INTO equipment (name, type, purchase_date, purchase_cost, supplier, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, asset_type, p_date, cost, supplier, status, notes))
            db.commit()
            flash('Asset Purchase Voucher created successfully!', 'success')
            
        return redirect(url_for('voucher_register', v_type=v_type))
        
    return render_template('voucher_form.html', v_type=v_type, action='Add', record=None, today=today_str)

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
                'weight': master['weight_kg'] if master else 0.0
            }
            
    elif v_type == 'feed':
        record = db.execute('SELECT * FROM feed_purchases WHERE id = ?', (id,)).fetchone()
        
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
                    'supplier': record_raw['supplier']
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
                    'supplier': record_raw['supplier']
                }
                
    elif v_type == 'other':
        record_raw = db.execute('SELECT * FROM equipment WHERE id = ?', (id,)).fetchone()
        if record_raw:
            record = {
                'id': record_raw['id'],
                'name': record_raw['name'],
                'type': record_raw['type'],
                'cost': record_raw['purchase_cost'],
                'purchase_date': record_raw['purchase_date'],
                'supplier': record_raw['supplier'],
                'status': record_raw['status'],
                'notes': record_raw['notes']
            }
            
    if not record:
        flash('Voucher record not found!', 'danger')
        return redirect(url_for('voucher_register', v_type=v_type))
        
    if request.method == 'POST':
        f = request.form
        p_date = f.get('purchase_date') or record['purchase_date']
        
        if v_type == 'goat':
            tag_id = f.get('tag_id')
            price = float(f.get('price') or 0)
            old_tag_id = record['tag_id']
            
            db.execute('''
                UPDATE purchases SET seller_name = ?, invoice_details = ?, purchase_date = ?, tag_id = ?, price = ?
                WHERE id = ?
            ''', (f.get('seller_name'), f.get('notes'), p_date, tag_id, price, id))
            
            db.execute('''
                UPDATE master_records SET tag_no = ?, breed = ?, gender = ?, purchase_date = ?, weight_kg = ?, purchase_amount = ?
                WHERE tag_no = ?
            ''', (tag_id, f.get('breed'), f.get('gender'), p_date, float(f.get('weight') or 0), price, old_tag_id))
            db.commit()
            flash('Goat Purchase Voucher updated successfully!', 'success')
            
        elif v_type == 'feed':
            qty = float(f.get('quantity') or 0)
            cost = float(f.get('cost') or 0)
            
            # Get old voucher details first
            old = db.execute("SELECT * FROM feed_purchases WHERE id = ?", (id,)).fetchone()
            if old:
                # Delete old matching goats_data
                db.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Feed' AND amount = ?", (old['purchase_date'], old['cost']))
                # Delete old matching expenses
                db.execute("DELETE FROM expenses WHERE date = ? AND category = 'Feed Purchase' AND amount = ? AND vendor_name = ?", (old['purchase_date'], old['cost'], old['supplier']))
            
            db.execute('''
                UPDATE feed_purchases SET feed_name = ?, quantity = ?, unit = ?, cost = ?, purchase_date = ?, supplier = ?
                WHERE id = ?
            ''', (f.get('feed_name'), qty, f.get('unit'), cost, p_date, f.get('supplier'), id))
            
            # Recalculate feed inventory row
            row = db.execute("SELECT opening_stock, used_qty, wastage_qty FROM feed_inventory WHERE purchase_id = ?", (id,)).fetchone()
            if row:
                opening = row['opening_stock'] or 0.0
                used = row['used_qty'] or 0.0
                wastage = row['wastage_qty'] or 0.0
                closing = opening + qty - used - wastage
                cost_per_unit = cost / qty if qty > 0 else 0.0
                db.execute('''
                    UPDATE feed_inventory 
                    SET feed_name = ?, purchased_qty = ?, closing_stock = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ?
                    WHERE purchase_id = ?
                ''', (f.get('feed_name'), qty, closing, cost_per_unit, cost, p_date, f.get('supplier'), id))
                
            # Now insert the new goats_data and expenses rows!
            desc = f"Purchased {qty} {f.get('unit')} of {f.get('feed_name')} from {f.get('supplier')}"
            db.execute('''
                INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
                VALUES ('All', ?, 'expense', 'Feed', ?, ?)
            ''', (p_date, cost, desc))
            db.execute('''
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                VALUES ('Feed Purchase', ?, ?, ?, ?, 'Cash', 'Paid')
            ''', (cost, p_date, desc, f.get('supplier')))
            
            db.commit()
            flash('Feed Purchase Voucher updated successfully!', 'success')
            
        elif v_type == 'health':
            name = f.get('health_name')
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
                db.execute("DELETE FROM expenses WHERE date = ? AND category = ? AND amount = ? AND vendor_name = ?", (old['purchase_date'], sub_type.capitalize() + ' Purchase', old['cost'], old['supplier']))
            
            if sub_type == 'medicine':
                db.execute('''
                    UPDATE medicine_purchases SET medicine_name = ?, dose_unit = ?, quantity = ?, cost = ?, purchase_date = ?, supplier = ?
                    WHERE id = ?
                ''', (name, f.get('dose_unit'), qty, cost, p_date, supplier, id))
                
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
                    UPDATE vaccine_purchases SET vaccine_name = ?, quantity = ?, cost = ?, purchase_date = ?, supplier = ?
                    WHERE id = ?
                ''', (name, qty, cost, p_date, supplier, id))
                
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
                INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
                VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid')
            ''', (sub_type.capitalize() + ' Purchase', cost, p_date, desc, supplier))
            
            db.commit()
            flash('Health Supplies Voucher updated successfully!', 'success')
            
        elif v_type == 'other':
            db.execute('''
                UPDATE equipment SET name = ?, type = ?, purchase_date = ?, purchase_cost = ?, supplier = ?, status = ?, notes = ?
                WHERE id = ?
            ''', (f.get('name'), f.get('type'), p_date, float(f.get('cost') or 0), f.get('supplier'), f.get('status'), f.get('notes'), id))
            db.commit()
            flash('Asset Purchase Voucher updated successfully!', 'success')
            
        return redirect(url_for('voucher_register', v_type=v_type))
        
    return render_template('voucher_form.html', v_type=v_type, sub_type=sub_type, action='Edit', record=record, today=record.get('purchase_date', ''))

@app.route('/vouchers/<v_type>/delete/<int:id>', methods=['POST'])
@app.route('/vouchers/<v_type>/delete/<sub_type>/<int:id>', methods=['POST'])
def voucher_delete(v_type, id, sub_type=None):
    if v_type not in ['goat', 'feed', 'health', 'other']:
        flash('Invalid voucher type!', 'danger')
        return redirect(url_for('vouchers'))
        
    db = get_db()
    
    if v_type == 'goat':
        record = db.execute('SELECT tag_id FROM purchases WHERE id = ?', (id,)).fetchone()
        if record:
            tag_id = record['tag_id']
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
        db.execute('DELETE FROM equipment WHERE id = ?', (id,))
        db.commit()
        flash('Asset Purchase Voucher deleted successfully!', 'success')
        
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
    return render_template('farm_settings.html', settings=settings)

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
    confirmation = request.form.get('confirmation', '').lower()
    
    if confirmation != 'yes':
        flash('Confirmation failed. Data not cleared.', 'danger')
        return redirect(url_for('farm_settings'))
    
    db = get_db()
    try:
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
        db.execute('DELETE FROM eligible_to_sell')
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
            receipt_no TEXT, notes TEXT, status TEXT DEFAULT 'Pending')''')
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
    emps = db.execute('SELECT * FROM employees WHERE status="Active" ORDER BY CAST(sr_no AS INTEGER) ASC').fetchall()
    
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
        
    emps = db.execute('SELECT id FROM employees WHERE status="Active"').fetchall()
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
        LEFT JOIN attendance a ON e.id=a.employee_id AND strftime('%m', a.date)=? AND strftime('%Y', a.date)=?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (month, year)).fetchall()
    farm = db.execute('SELECT * FROM farm_info LIMIT 1').fetchone()
    return render_template('attendance_summary.html', data=data, month=month, year=year, farm=farm)

@app.route('/salary_calculate', methods=['GET', 'POST'])
def salary_calculate():
    db = get_db()
    
    month = request.args.get('month', datetime.now().strftime('%m'))
    year = request.args.get('year', datetime.now().strftime('%Y'))
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    # Query attendance strictly for the selected month/year
    data = db.execute('''SELECT e.id, e.name, e.role, e.wage_type, e.wage_rate, e.sr_no,
        SUM(CASE WHEN a.status IN ('P', 'Present') THEN 1 ELSE 0 END) as present_days
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id AND strftime('%m', a.date)=? AND strftime('%Y', a.date)=?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (month, year)).fetchall()
        
    salaries = []
    for emp in data:
        present = emp['present_days'] or 0
        wage_type = emp['wage_type']
        wage_rate = emp['wage_rate'] or 0
        
        computed = 0
        if wage_type == 'Monthly':
            computed = (wage_rate / 30.0) * present
        elif wage_type == 'Weekly':
            computed = (wage_rate / 7.0) * present
        elif wage_type == 'Daily':
            computed = wage_rate * present
            
        # Get monthly paid amount
        paid = db.execute('''SELECT SUM(net_salary) FROM salary_payments 
                             WHERE employee_id=? AND month=? AND year=?''', 
                           (emp['id'], int(month), int(year))).fetchone()[0] or 0
        
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
            'balance': max(0, computed - paid)
        })
        
    return render_template('salary_calculate.html', 
                           salaries=salaries, 
                           month=month, 
                           year=year, 
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
    emps = db.execute('SELECT * FROM employees WHERE status="Active" ORDER BY name').fetchall()
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
    emps = db.execute('SELECT * FROM employees WHERE status="Active" ORDER BY name').fetchall()
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
        q += ' AND category LIKE ?'
        p.append(f'%{category}%')
        
    if month and month != 'All':
        q += " AND strftime('%m', date) = ?"
        p.append(f"{int(month):02d}")
        
    if year and year != 'All':
        q += " AND strftime('%Y', date) = ?"
        p.append(str(year))
        
    q += ' ORDER BY date DESC'
    records = db.execute(q, p).fetchall()
    
    return render_template('expenses.html', records=records, category=category, month=month, year=year)

@app.route('/expense_add', methods=['GET', 'POST'])
def expense_add():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        
        # Handle file upload for the bill
        bill_file_path = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename != '':
                import os
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'bills')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
                bill_file_path = f"/static/uploads/bills/{filename}"
        
        db.execute('''
            INSERT INTO expenses (category, amount, date, description, receipt_no, bill_file, status) 
            VALUES (?, ?, ?, ?, ?, ?, 'Approved')
        ''', (
            f.get('category'), 
            float(f.get('amount') or 0.0), 
            f.get('expense_date'), 
            f.get('description'), 
            f.get('bill_reference'), 
            bill_file_path
        ))
        db.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('expenses'))
    return render_template('expense_add.html')

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
                import os
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{timestamp}_{filename}"
                upload_dir = os.path.join(app.root_path, 'static', 'uploads', 'bills')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, filename))
                bill_file_path = f"/static/uploads/bills/{filename}"
                
        db.execute('''
            UPDATE expenses 
            SET category = ?, amount = ?, date = ?, description = ?, receipt_no = ?, bill_file = ?
            WHERE id = ?
        ''', (
            f.get('category'), 
            float(f.get('amount') or 0.0), 
            f.get('expense_date'), 
            f.get('description'), 
            f.get('bill_reference'), 
            bill_file_path,
            expense_id
        ))
        db.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('expenses'))
        
    return render_template('expense_edit.html', record=record)

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
        q += " AND type=?"; p.append(type_filter)
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
        LEFT JOIN attendance a ON e.id=a.employee_id AND strftime('%m', a.date)=? AND strftime('%Y', a.date)=?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (month, year)).fetchall()

    employees = []
    total_payable = 0.0
    total_paid = 0.0
    total_pending = 0.0

    for emp in data:
        present = emp['present_days'] or 0
        wage_type = emp['wage_type']
        wage_rate = emp['wage_rate'] or 0
        
        computed = 0.0
        if wage_type == 'Monthly':
            computed = (wage_rate / 30.0) * present
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

@app.route('/api/goat_lookup/<tag_id>')
def api_goat_lookup(tag_id):
    db = get_db()
    goat = db.execute('SELECT breed, breed_percent, gender, weight_kg, status FROM master_records WHERE tag_no = ?', (tag_id,)).fetchone()
    if not goat:
        return jsonify({'found': False})
    
    return jsonify({
        'found': True,
        'breed': goat['breed'],
        'breed_percent': goat['breed_percent'],
        'gender': goat['gender'],
        'weight_kg': goat['weight_kg'],
        'status': goat['status'],
        'already_sold': goat['status'] == 'Sold',
        'already_expired': goat['status'] == 'Expired'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)