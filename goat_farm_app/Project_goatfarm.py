import os
import sqlite3
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev_secret_key_for_goat_farm'
DB_FILE = os.path.join(app.root_path, 'database.db')

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

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
                vaccination TEXT, vaccination_period TEXT, medicine TEXT, medicine_period TEXT,
                feed TEXT, feed_amount TEXT, mating_date DATE, mating_goat_no TEXT,
                goat_week_period TEXT, delivery_date DATE, new_goat_gender TEXT,
                new_goat_color TEXT, birth_weight REAL, selling_date DATE, selling_weight REAL,
                selling_price REAL, mortality_date DATE, mortality_weight REAL,
                mortality_reason TEXT, insurance_claim_amount REAL, insurance_inform_date DATE,
                insurance_claim_date DATE
            )
        ''')
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

        add_column("feed_inventory", "purchase_id", "INTEGER")

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
init_db()

@app.before_request
def require_login():
    allowed_routes = ['login', 'static', 'register', 'verify_otp', 'goats', 'goat_detail']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

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
            
            # Update login tracking
            login_tracking = db.execute('SELECT * FROM user_login_tracking WHERE user_id = ?', (user['id'],)).fetchone()
            today = datetime.now().strftime('%Y-%m-%d')
            
            if not login_tracking:
                # First login ever - create tracking record
                db.execute('INSERT INTO user_login_tracking (user_id, last_login_date, has_seen_weight_notification) VALUES (?, ?, ?)',
                          (user['id'], today, 0))
                session['show_weight_notification'] = True
            else:
                # Check if this is a different day
                last_login = login_tracking['last_login_date']
                if last_login != today:
                    # New day login - reset notification flag
                    db.execute('UPDATE user_login_tracking SET last_login_date = ?, has_seen_weight_notification = ? WHERE user_id = ?',
                              (today, 0, user['id']))
                    session['show_weight_notification'] = True
                else:
                    session['show_weight_notification'] = False
            
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
    
    # 4. Goat Search Logic - Enhanced to support last 4 digits and pattern matching
    searched_goat = None
    if search_q:
        search_q_stripped = search_q.strip()
        # Check for exact tag match first
        searched_goat = db.execute("SELECT * FROM master_records WHERE tag_no = ?", (search_q_stripped,)).fetchone()
        
        # If no exact match, try searching by last 4 digits
        if not searched_goat and len(search_q_stripped) == 4 and search_q_stripped.isdigit():
            searched_goat = db.execute("SELECT * FROM master_records WHERE tag_no LIKE ? ORDER BY tag_no DESC LIMIT 1", (f"%{search_q_stripped}",)).fetchone()
        
        # General list search with tag_no LIKE and breed LIKE
        goats = db.execute("SELECT * FROM master_records WHERE tag_no LIKE ? OR breed LIKE ? ORDER BY id ASC", 
                          (f"%{search_q_stripped}%", f"%{search_q_stripped}%")).fetchall()
        
        # Also search by last 4 digits if search_q is 4 digits
        if len(search_q_stripped) == 4 and search_q_stripped.isdigit():
            last_4_digits_goats = db.execute("SELECT * FROM master_records WHERE tag_no LIKE ? ORDER BY id ASC", (f"%{search_q_stripped}",)).fetchall()
            # Merge results, avoiding duplicates
            goat_tag_nos = {g['tag_no'] for g in goats}
            for g in last_4_digits_goats:
                if g['tag_no'] not in goat_tag_nos:
                    goats = list(goats) + [g]
                    goat_tag_nos.add(g['tag_no'])
    else:
        goats = db.execute("SELECT * FROM master_records ORDER BY id ASC LIMIT 10").fetchall()
        
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
    goats_summary = db.execute('''
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
               COUNT(a.amount) as total_records,
               IFNULL(SUM(CASE WHEN a.category = 'income' THEN a.amount ELSE 0 END), 0) as total_income,
               IFNULL(SUM(CASE WHEN a.category = 'expense' THEN a.amount ELSE 0 END), 0) as total_expense
        FROM master_records m
        LEFT JOIN AllRecords a ON m.tag_no = a.tag_no
        GROUP BY m.tag_no
        ORDER BY CAST(m.tag_no AS INTEGER) ASC
    ''').fetchall()
    
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
    
    return render_template('goat_detail.html', tag_number=tag_number, income=income, expense=expense, profit=profit, history=history)

@app.route('/master_add', methods=['GET', 'POST'])
def master_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('''
            INSERT INTO master_records (
                si_no, tag_no, breed, breed_percent, status, sold, expired, gender, purchase_date, color,
                weight_kg, purchase_amount, insurance_date, vaccination, vaccination_period, medicine,
                medicine_period, feed, feed_amount, mating_date, mating_goat_no, goat_week_period,
                delivery_date, new_goat_gender, new_goat_color, birth_weight, selling_date,
                selling_weight, selling_price, mortality_date, mortality_weight, mortality_reason,
                insurance_claim_amount, insurance_inform_date, insurance_claim_date, kit_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('si_no'), f.get('tag_no'), f.get('breed'), f.get('breed_percent'), f.get('status'),
            f.get('sold'), f.get('expired'), f.get('gender'), f.get('purchase_date'), f.get('color'),
            f.get('weight_kg'), f.get('purchase_amount'), f.get('insurance_date'), f.get('vaccination'),
            f.get('vaccination_period'), f.get('medicine'), f.get('medicine_period'), f.get('feed'),
            f.get('feed_amount'), f.get('mating_date'), f.get('mating_goat_no'), f.get('goat_week_period'),
            f.get('delivery_date'), f.get('new_goat_gender'), f.get('new_goat_color'), f.get('birth_weight'),
            f.get('selling_date'), f.get('selling_weight'), f.get('selling_price'), f.get('mortality_date'),
            f.get('mortality_weight'), f.get('mortality_reason'), f.get('insurance_claim_amount'),
            f.get('insurance_inform_date'), f.get('insurance_claim_date'), 1 if f.get('kit_status') else 0
        ))
        db.commit()
        flash('Master record added successfully!', 'success')
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
        records = db.execute('SELECT * FROM master_records WHERE tag_no LIKE ? OR si_no LIKE ? ORDER BY id ASC', 
             (f"%{tag_search}%", f"%{tag_search}%")).fetchall()
    else:
        records = db.execute('SELECT * FROM master_records ORDER BY id ASC').fetchall()
    return render_template('master.html', records=records)

@app.route('/sales_add', methods=['GET', 'POST'])
def sales_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('''
            INSERT INTO sales_records (
                sr_no, tag_id, breed, breed_percent, gender, weight, sold_price, 
                date_of_sale, buyer_name, buyer_city, buyer_contact
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f.get('sr_no'), f.get('tag_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'),
            f.get('weight'), f.get('sold_price'), f.get('date_of_sale'), f.get('buyer_name'),
            f.get('buyer_city'), f.get('buyer_contact')
        ))
        
        # LOGIC FIX: Update status in master_records
        db.execute("UPDATE master_records SET status = 'Sold', selling_date = ?, selling_price = ? WHERE tag_no = ?",
                   (f.get('date_of_sale'), f.get('sold_price'), f.get('tag_id')))
        
        # Remove from eligible_to_sell list when sold
        db.execute("DELETE FROM eligible_to_sell WHERE tag_id = ?", (f.get('tag_id'),))
        
        db.commit()
        flash('Sales record added successfully!', 'success')
        return redirect(url_for('sales'))
    # Get next serial number
    res = db.execute('SELECT MAX(CAST(sr_no AS INTEGER)) FROM sales_records').fetchone()[0]
    next_sr = (res or 0) + 1
    return render_template('sales_add.html', next_sr=next_sr)

@app.route('/sales')
def sales():
    db = get_db()
    tag_search = request.args.get('tag_id', '')
    if tag_search:
        records = db.execute('SELECT * FROM sales_records WHERE tag_id LIKE ? OR buyer_name LIKE ? ORDER BY date_of_sale DESC', 
             (f"%{tag_search}%", f"%{tag_search}%")).fetchall()
    else:
        records = db.execute('SELECT * FROM sales_records ORDER BY date_of_sale DESC').fetchall()
    return render_template('sales.html', records=records)

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
        
    q += ' ORDER BY consultation_date DESC'
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
        records = db.execute('SELECT * FROM mortality_records WHERE tag_id LIKE ? ORDER BY expired_date DESC', 
             (f"%{tag_search}%",)).fetchall()
    else:
        records = db.execute('SELECT * FROM mortality_records ORDER BY expired_date DESC').fetchall()
    return render_template('mortality.html', records=records)

@app.route('/feed')
def feed():
    db = get_db()
    records = db.execute('SELECT * FROM feed_inventory ORDER BY id DESC').fetchall()
    summary = db.execute('SELECT SUM(opening_stock) as opening, SUM(purchased_qty) as total_purchased, SUM(used_qty) as total_used, SUM(total_cost) as total_cost, SUM(closing_stock) as closing FROM feed_inventory').fetchone()
    return render_template('feed.html', records=records, summary=summary)

@app.route('/feed_add', methods=['GET', 'POST'])
def feed_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        # Calculate closing stock: opening + purchased - used
        opening = float(f.get('opening_stock') or 0)
        purchased = float(f.get('purchase_qty') or 0)
        used = float(f.get('used_qty') or 0)
        closing = opening + purchased - used
        
        db.execute('''INSERT INTO feed_inventory (feed_name, opening_stock, purchased_qty, used_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier)
                      VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (f.get('feed_name'), opening, purchased, used, closing, f.get('unit'), f.get('purchase_amount', 0), f.get('total_cost', 0), f.get('date'), f.get('supplier')))
        db.commit()
        flash('Feed record added!', 'success')
        return redirect(url_for('feed'))
    return render_template('feed_add.html')

@app.route('/kid_add', methods=['GET', 'POST'])
def kid_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db = get_db()
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
        
    q += ' ORDER BY vaccine_date DESC'
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
        db.execute('''
            UPDATE master_records SET 
            si_no = ?, tag_no = ?, breed = ?, breed_percent = ?, status = ?, sold = ?, expired = ?, gender = ?,
            purchase_date = ?, color = ?, weight_kg = ?, purchase_amount = ?, insurance_date = ?,
            vaccination = ?, vaccination_period = ?, medicine = ?, medicine_period = ?, feed = ?,
            feed_amount = ?, mating_date = ?, mating_goat_no = ?, goat_week_period = ?,
            delivery_date = ?, new_goat_gender = ?, new_goat_color = ?, birth_weight = ?,
            selling_date = ?, selling_weight = ?, selling_price = ?, mortality_date = ?,
            mortality_weight = ?, mortality_reason = ?, insurance_claim_amount = ?,
            insurance_inform_date = ?, insurance_claim_date = ?, kit_status = ? WHERE id = ?
        ''', (
            f.get('si_no'), f.get('tag_no'), f.get('breed'), f.get('breed_percent'), f.get('status'),
            f.get('sold'), f.get('expired'), f.get('gender'), f.get('purchase_date'), f.get('color'),
            f.get('weight_kg'), f.get('purchase_amount'), f.get('insurance_date'), f.get('vaccination'),
            f.get('vaccination_period'), f.get('medicine'), f.get('medicine_period'), f.get('feed'),
            f.get('feed_amount'), f.get('mating_date'), f.get('mating_goat_no'), f.get('goat_week_period'),
            f.get('delivery_date'), f.get('new_goat_gender'), f.get('new_goat_color'), f.get('birth_weight'),
            f.get('selling_date'), f.get('selling_weight'), f.get('selling_price'), f.get('mortality_date'),
            f.get('mortality_weight'), f.get('mortality_reason'), f.get('insurance_claim_amount'),
            f.get('insurance_inform_date'), f.get('insurance_claim_date'), 1 if f.get('kit_status') else 0, id
        ))
        db.commit()
        flash('Master record updated successfully!', 'success')
        return redirect(url_for('master'))
    
    return render_template('master_edit.html', record=record)

@app.route('/master_delete/<int:id>', methods=['POST'])
def master_delete(id):
    db = get_db()
    db.execute('DELETE FROM master_records WHERE id = ?', (id,))
    db.commit()
    flash('Master record deleted successfully!', 'success')
    return redirect(url_for('master'))

# SALES RECORDS EDIT & DELETE
@app.route('/sales_edit/<int:id>', methods=['GET', 'POST'])
def sales_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM sales_records WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('sales'))
    
    if request.method == 'POST':
        f = request.form
        db.execute('''
            UPDATE sales_records SET 
            sr_no = ?, tag_id = ?, breed = ?, breed_percent = ?, gender = ?, weight = ?,
            sold_price = ?, date_of_sale = ?, buyer_name = ?, buyer_city = ?, buyer_contact = ? WHERE id = ?
        ''', (
            f.get('sr_no'), f.get('tag_id'), f.get('breed'), f.get('breed_percent'), f.get('gender'),
            f.get('weight'), f.get('sold_price'), f.get('date_of_sale'), f.get('buyer_name'),
            f.get('buyer_city'), f.get('buyer_contact'), id
        ))
        db.commit()
        flash('Sales record updated successfully!', 'success')
        return redirect(url_for('sales'))
    
    return render_template('sales_edit.html', record=record)

@app.route('/sales_delete/<int:id>', methods=['POST'])
def sales_delete(id):
    db = get_db()
    db.execute('DELETE FROM sales_records WHERE id = ?', (id,))
    db.commit()
    flash('Sales record deleted successfully!', 'success')
    return redirect(url_for('sales'))

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
    db.execute('DELETE FROM mortality_records WHERE id = ?', (id,))
    db.commit()
    flash('Mortality record deleted successfully!', 'success')
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
        # Recalculate
        opening = float(f.get('opening_stock') or 0)
        purchased = float(f.get('purchase_qty') or 0)
        used = float(f.get('used_qty') or 0)
        closing = opening + purchased - used
        
        db.execute('''
            UPDATE feed_inventory SET 
            feed_name = ?, opening_stock = ?, purchased_qty = ?, used_qty = ?, closing_stock = ?,
            unit = ?, cost_per_unit = ?, total_cost = ?, purchase_date = ?, supplier = ? WHERE id = ?
        ''', (
            f.get('feed_name'), opening, purchased, used, closing, f.get('unit'), 
            f.get('purchase_amount', 0), f.get('total_cost', 0), f.get('date'), f.get('supplier'), id
        ))
        db.commit()
        flash('Feed record updated successfully!', 'success')
        return redirect(url_for('feed'))
    
    return render_template('feed_edit.html', record=record)

@app.route('/feed_delete/<int:id>', methods=['POST'])
def feed_delete(id):
    db = get_db()
    db.execute('DELETE FROM feed_inventory WHERE id = ?', (id,))
    db.commit()
    flash('Feed record deleted successfully!', 'success')
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

# PURCHASE RECORDS EDIT & DELETE
@app.route('/purchase_edit/<int:id>', methods=['GET', 'POST'])
def purchase_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM purchases WHERE id = ?', (id,)).fetchone()
    
    if not record:
        flash('Record not found.', 'danger')
        return redirect(url_for('purchases'))
    
    if request.method == 'POST':
        f = request.form
        # Get old tag_id before update
        old_record = db.execute('SELECT tag_id FROM purchases WHERE id=?', (id,)).fetchone()
        old_tag_id = old_record['tag_id'] if old_record else None
        
        db.execute('''
            UPDATE purchases SET 
            seller_name = ?, invoice_details = ?, purchase_date = ?, tag_id = ?, price = ? WHERE id = ?
        ''', (
            f.get('seller_name'), f.get('invoice_details'), f.get('purchase_date'),
            f.get('tag_id'), f.get('price'), id
        ))
        
        # Update corresponding master record if it exists
        if old_tag_id:
            db.execute('''UPDATE master_records 
                         SET tag_no=?, purchase_date=?, purchase_amount=? 
                         WHERE tag_no=?''', 
                      (f.get('tag_id'), f.get('purchase_date'), f.get('price'), old_tag_id))
        
        db.commit()
        flash('Purchase record and Master Record updated successfully!', 'success')
        return redirect(url_for('purchases'))
    
    return render_template('purchase_edit.html', record=record)

@app.route('/purchase_delete/<int:id>', methods=['POST'])
def purchase_delete(id):
    db = get_db()
    # Get tag_id before deletion to clean up master_records
    record = db.execute('SELECT tag_id FROM purchases WHERE id=?', (id,)).fetchone()
    if record:
        tag_id = record['tag_id']
        db.execute('DELETE FROM purchases WHERE id = ?', (id,))
        # Also remove from master_records to keep data clean
        db.execute('DELETE FROM master_records WHERE tag_no = ?', (tag_id,))
        db.commit()
        flash('Purchase and corresponding Master Record deleted successfully!', 'success')
    else:
        flash('Record not found.', 'danger')
    return redirect(url_for('purchases'))

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
    eligible_goats = db.execute('''
        SELECT ets.*, mr.breed, mr.gender, mr.weight_kg, mr.status
        FROM eligible_to_sell ets
        LEFT JOIN master_records mr ON ets.tag_id = mr.tag_no
        ORDER BY ets.date_added DESC
    ''').fetchall()
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
@app.route('/purchases')
def purchases():
    db = get_db()
    # Fetch recent purchases across all 4 categories for the dashboard
    recent_goats = db.execute('SELECT * FROM purchases ORDER BY purchase_date DESC LIMIT 5').fetchall()
    recent_feed = db.execute('SELECT * FROM feed_purchases ORDER BY purchase_date DESC LIMIT 5').fetchall()
    recent_meds = db.execute('SELECT * FROM medicine_purchases ORDER BY purchase_date DESC LIMIT 5').fetchall()
    recent_vacs = db.execute('SELECT * FROM vaccine_purchases ORDER BY purchase_date DESC LIMIT 5').fetchall()
    return render_template('purchases.html', goats=recent_goats, feed=recent_feed, meds=recent_meds, vacs=recent_vacs)

@app.route('/purchase_goat', methods=['GET', 'POST'])
def purchase_goat():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        tag_id = f.get('tag_id')
        
        # 1. Add to purchases
        db.execute('''
            INSERT INTO purchases (
                seller_name, invoice_details, purchase_date, tag_id, price
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            f.get('seller_name'), f.get('invoice_details'), f.get('purchase_date'), 
            tag_id, f.get('price')
        ))
        
        # 2. Auto-add to master_records
        breed = f.get('breed', 'Unknown')
        gender = f.get('gender', 'Unknown')
        weight = f.get('weight', 0)
        
        db.execute('''
            INSERT INTO master_records (
                tag_no, breed, gender, purchase_date, weight_kg, purchase_amount, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'Active')
        ''', (tag_id, breed, gender, f.get('purchase_date'), weight, f.get('price')))
        
        db.commit()
        flash('Goat purchased and added to Master Records successfully!', 'success')
        return redirect(url_for('purchases'))
    return render_template('purchase_goat.html')

@app.route('/purchase_feed', methods=['GET', 'POST'])
def purchase_feed():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        qty = float(f.get('quantity') or 0)
        cost = float(f.get('cost') or 0)
        feed_name = f.get('feed_name')
        
        # 1. Log purchase
        cursor = db.execute('''
            INSERT INTO feed_purchases (
                feed_name, quantity, unit, cost, purchase_date, supplier
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            feed_name, qty, f.get('unit'), cost, f.get('purchase_date'), f.get('supplier')
        ))
        purchase_id = cursor.lastrowid
        
        # 2. Update feed inventory
        today = f.get('purchase_date')
        
        db.execute('''
            INSERT INTO feed_inventory (feed_name, purchased_qty, closing_stock, total_cost, purchase_date, purchase_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (feed_name, qty, qty, cost, today, purchase_id))
            
        db.commit()
        flash('Feed purchased and inventory updated!', 'success')
        return redirect(url_for('purchases'))
    return render_template('purchase_feed.html')

@app.route('/purchase_medicine', methods=['GET', 'POST'])
def purchase_medicine():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('''
            INSERT INTO medicine_purchases (
                medicine_name, dose_unit, quantity, cost, purchase_date, supplier
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            f.get('medicine_name'), f.get('dose_unit'), f.get('quantity'), 
            f.get('cost'), f.get('purchase_date'), f.get('supplier')
        ))
        db.commit()
        flash('Medicine purchased successfully!', 'success')
        return redirect(url_for('purchases'))
    return render_template('purchase_medicine.html')

@app.route('/purchase_vaccine', methods=['GET', 'POST'])
def purchase_vaccine():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('''
            INSERT INTO vaccine_purchases (
                vaccine_name, quantity, cost, purchase_date, supplier
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            f.get('vaccine_name'), f.get('quantity'), f.get('cost'), 
            f.get('purchase_date'), f.get('supplier')
        ))
        db.commit()
        flash('Vaccine purchased successfully!', 'success')
        return redirect(url_for('purchases'))
    return render_template('purchase_vaccine.html')

@app.route('/feed_purchase_edit/<int:id>', methods=['GET', 'POST'])
def feed_purchase_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM feed_purchases WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        f = request.form
        db.execute('''UPDATE feed_purchases SET feed_name=?, quantity=?, unit=?, cost=?, purchase_date=?, supplier=? WHERE id=?''',
            (f.get('feed_name'), f.get('quantity'), f.get('unit'), f.get('cost'), f.get('purchase_date'), f.get('supplier'), id))
        
        # Update linked inventory
        db.execute('''UPDATE feed_inventory SET feed_name=?, purchased_qty=?, closing_stock=?, total_cost=?, purchase_date=? WHERE purchase_id=?''',
            (f.get('feed_name'), f.get('quantity'), f.get('quantity'), f.get('cost'), f.get('purchase_date'), id))
        
        db.commit()
        flash('Feed purchase and Inventory updated successfully!', 'success')
        return redirect(url_for('purchases'))
    return render_template('generic_purchase_edit.html', record=record, p_type='feed')

@app.route('/feed_purchase_delete/<int:id>', methods=['POST'])
def feed_purchase_delete(id):
    db = get_db()
    db.execute('DELETE FROM feed_purchases WHERE id = ?', (id,))
    # Also delete linked inventory
    db.execute('DELETE FROM feed_inventory WHERE purchase_id = ?', (id,))
    db.commit()
    flash('Feed purchase and linked Inventory record deleted!', 'success')
    return redirect(url_for('purchases'))

@app.route('/med_purchase_edit/<int:id>', methods=['GET', 'POST'])
def med_purchase_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM medicine_purchases WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        f = request.form
        db.execute('''UPDATE medicine_purchases SET medicine_name=?, dose_unit=?, quantity=?, cost=?, purchase_date=?, supplier=? WHERE id=?''',
            (f.get('medicine_name'), f.get('dose_unit'), f.get('quantity'), f.get('cost'), f.get('purchase_date'), f.get('supplier'), id))
        db.commit()
        flash('Medicine purchase updated successfully!', 'success')
        return redirect(url_for('purchases'))
    return render_template('generic_purchase_edit.html', record=record, p_type='med')

@app.route('/med_purchase_delete/<int:id>', methods=['POST'])
def med_purchase_delete(id):
    db = get_db()
    db.execute('DELETE FROM medicine_purchases WHERE id = ?', (id,))
    db.commit()
    flash('Medicine purchase deleted!', 'success')
    return redirect(url_for('purchases'))

@app.route('/vac_purchase_edit/<int:id>', methods=['GET', 'POST'])
def vac_purchase_edit(id):
    db = get_db()
    record = db.execute('SELECT * FROM vaccine_purchases WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        f = request.form
        db.execute('''UPDATE vaccine_purchases SET vaccine_name=?, quantity=?, cost=?, purchase_date=?, supplier=? WHERE id=?''',
            (f.get('vaccine_name'), f.get('quantity'), f.get('cost'), f.get('purchase_date'), f.get('supplier'), id))
        db.commit()
        flash('Vaccine purchase updated successfully!', 'success')
        return redirect(url_for('purchases'))
    return render_template('generic_purchase_edit.html', record=record, p_type='vac')

@app.route('/vac_purchase_delete/<int:id>', methods=['POST'])
def vac_purchase_delete(id):
    db = get_db()
    db.execute('DELETE FROM vaccine_purchases WHERE id = ?', (id,))
    db.commit()
    flash('Vaccine purchase deleted!', 'success')
    return redirect(url_for('purchases'))

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
    db = get_db()
    if sales_id is None:
        sales = db.execute('SELECT * FROM sales_records ORDER BY date_of_sale DESC').fetchall()
        return render_template('invoice_list.html', sales=sales)

    sale = db.execute('SELECT * FROM sales_records WHERE id = ?', (sales_id,)).fetchone()
    
    if not sale:
        flash('Sales record not found.', 'danger')
        return redirect(url_for('generate_invoice'))
    
    farm_info = db.execute('SELECT * FROM farm_info WHERE id = 1').fetchone()
    
    # Ensure farm_info exists with default values
    if not farm_info:
        db.execute('''
            INSERT INTO farm_info (id, farm_name, farm_address, farm_city, farm_phone, bank_name, account_number, ifsc_code)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Ranga Goat Farm', 'Aandigounder Street, Pachapalayam, Perur', 'Coimbatore 641010', '', '', '', ''))
        db.commit()
        farm_info = db.execute('SELECT * FROM farm_info WHERE id = 1').fetchone()
    
    # Get goat details from master records
    goat = db.execute('SELECT * FROM master_records WHERE tag_no = ?', (sale['tag_id'],)).fetchone()
    
    return render_template('invoice.html', sale=sale, farm_info=farm_info, goat=goat, current_date=datetime.now())

@app.route('/invoice_txt/<int:sales_id>')
def generate_invoice_txt(sales_id):
    from io import BytesIO
    
    db = get_db()
    sale = db.execute('SELECT * FROM sales_records WHERE id = ?', (sales_id,)).fetchone()
    
    if not sale:
        flash('Sales record not found.', 'danger')
        return redirect(url_for('sales'))
    
    farm_info = db.execute('SELECT * FROM farm_info WHERE id = 1').fetchone()
    goat = db.execute('SELECT * FROM master_records WHERE tag_no = ?', (sale['tag_id'],)).fetchone()
    
    # Generate text bill
    bill_text = ""
    bill_text += "=" * 70 + "\n"
    bill_text += f"{(farm_info['farm_name'] if farm_info and farm_info['farm_name'] else 'Goat Farm Pro'):^70}\n"
    bill_text += "=" * 70 + "\n"
    bill_text += f"{('SALES INVOICE'):^70}\n"
    bill_text += "=" * 70 + "\n\n"
    
    # Farm Information
    if farm_info:
        bill_text += "FROM: FARM DETAILS\n"
        bill_text += "-" * 70 + "\n"
        bill_text += f"Farm Name     : {farm_info['farm_name'] or 'N/A'}\n"
        bill_text += f"Address       : {farm_info['farm_address'] or 'N/A'}\n"
        bill_text += f"City          : {farm_info['farm_city'] or 'N/A'}\n"
        bill_text += f"Phone         : {farm_info['farm_phone'] or 'N/A'}\n"
    else:
        bill_text += "FROM: FARM DETAILS\n"
        bill_text += "-" * 70 + "\n"
        bill_text += "Farm details not configured\n"
    
    bill_text += "\n"
    
    # Buyer Information
    bill_text += "TO: BUYER INFORMATION\n"
    bill_text += "-" * 70 + "\n"
    bill_text += f"Buyer Name    : {sale['buyer_name'] or 'N/A'}\n"
    bill_text += f"City          : {sale['buyer_city'] or 'N/A'}\n"
    bill_text += f"Contact       : {sale['buyer_contact'] or 'N/A'}\n"
    bill_text += "\n"
    
    # Invoice Details
    bill_text += "INVOICE DETAILS\n"
    bill_text += "-" * 70 + "\n"
    bill_text += f"Invoice Number: {sale['id']}\n"
    bill_text += f"Invoice Date  : {sale['date_of_sale'] or 'N/A'}\n"
    bill_text += f"Bill Date     : {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
    bill_text += "\n"
    
    # Particulars - Goat Details
    bill_text += "GOAT PARTICULARS\n"
    bill_text += "-" * 70 + "\n"
    bill_text += f"{'Item':<20} {'Details':<50}\n"
    bill_text += "-" * 70 + "\n"
    bill_text += f"{'Tag/ID Number':<20} {sale['tag_id']:<50}\n"
    bill_text += f"{'Gender':<20} {(sale['gender'] or (goat['gender'] if goat else 'N/A')):<50}\n"
    bill_text += f"{'Weight (kg)':<20} {str(sale['weight'] or (goat['weight_kg'] if goat else 'N/A')):<50}\n"
    bill_text += f"{'Breed':<20} {(sale['breed'] or (goat['breed'] if goat else 'N/A')):<50}\n"
    bill_text += f"{'Breed Percent':<20} {(sale['breed_percent'] or (goat['breed_percent'] if goat else 'N/A')):<50}\n"
    bill_text += "\n"
    
    # Price Details
    bill_text += "PRICE DETAILS\n"
    bill_text += "-" * 70 + "\n"
    bill_text += f"{'Price per Unit':<40} ₹ {sale['sold_price']:>15.2f}\n"
    bill_text += f"{'Total Amount':<40} ₹ {sale['sold_price']:>15.2f}\n"
    bill_text += "-" * 70 + "\n"
    bill_text += f"{'GRAND TOTAL':<40} ₹ {sale['sold_price']:>15.2f}\n"
    bill_text += "-" * 70 + "\n"
    bill_text += "\n"
    
    # Bank Details
    if farm_info and farm_info['bank_name']:
        bill_text += "BANK DETAILS\n"
        bill_text += "-" * 70 + "\n"
        bill_text += f"Bank Name     : {farm_info['bank_name'] or 'N/A'}\n"
        bill_text += f"Account No    : {farm_info['account_number'] or 'N/A'}\n"
        bill_text += f"IFSC Code     : {farm_info['ifsc_code'] or 'N/A'}\n"
        bill_text += "\n"
    
    # Footer
    bill_text += "=" * 70 + "\n"
    bill_text += "Thank you for your business!\n"
    bill_text += f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}\n"
    bill_text += "=" * 70 + "\n"
    
    # Create BytesIO object and write bill text
    bill_bytes = BytesIO(bill_text.encode('utf-8'))
    bill_bytes.seek(0)
    
    try:
        return send_file(
            bill_bytes,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'Invoice_{sale["id"]}_Bill.txt'
        )
    except TypeError:
        # Fallback for older Flask versions
        return send_file(
            bill_bytes,
            mimetype='text/plain',
            as_attachment=True,
            attachment_filename=f'Invoice_{sale["id"]}_Bill.txt'
        )

@app.route('/invoice_pdf/<int:sales_id>')
def generate_invoice_pdf(sales_id):
    from io import BytesIO
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except ImportError:
        flash('PDF generation requires reportlab. Install it with pip install reportlab.', 'warning')
        return redirect(url_for('generate_invoice', sales_id=sales_id))

    db = get_db()
    sale = db.execute('SELECT * FROM sales_records WHERE id = ?', (sales_id,)).fetchone()
    if not sale:
        flash('Sales record not found.', 'danger')
        return redirect(url_for('sales'))

    farm_info = db.execute('SELECT * FROM farm_info WHERE id = 1').fetchone()
    
    # Ensure farm_info exists with default values
    if not farm_info:
        db.execute('''
            INSERT INTO farm_info (id, farm_name, farm_address, farm_city, farm_phone, bank_name, account_number, ifsc_code)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        ''', ('Ranga Goat Farm', 'Aandigounder Street, Pachapalayam, Perur', 'Coimbatore 641010', '', '', '', ''))
        db.commit()
        farm_info = db.execute('SELECT * FROM farm_info WHERE id = 1').fetchone()
    
    goat = db.execute('SELECT * FROM master_records WHERE tag_no = ?', (sale['tag_id'],)).fetchone()

    buffer = BytesIO()
    width, height = A4
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"Invoice_{sale['id']}")

    margin = 25 * mm
    line_height = 9 * mm
    y = height - margin

    farm_name = farm_info['farm_name'] if farm_info and farm_info['farm_name'] else 'Ranga Goat Farm'
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(margin, y, farm_name)
    y -= line_height
    pdf.setFont('Helvetica', 10)
    if farm_info:
        pdf.drawString(margin, y, f"{farm_info['farm_address'] or 'Address not configured'}")
        y -= 5 * mm
        pdf.drawString(margin, y, f"{farm_info['farm_city'] or ''} | Phone: {farm_info['farm_phone'] or 'N/A'}")
    else:
        pdf.drawString(margin, y, 'Farm details not configured')
    y -= 12 * mm

    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(margin, y, 'INVOICE')
    pdf.setFont('Helvetica', 10)
    pdf.drawString(width - margin - 100 * mm, y, f"Invoice #: {sale['id']}")
    y -= line_height
    pdf.drawString(width - margin - 100 * mm, y, f"Date: {sale['date_of_sale'] or 'N/A'}")
    y -= 12 * mm

    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(margin, y, 'Bill To:')
    pdf.setFont('Helvetica', 10)
    pdf.drawString(margin, y - 6 * mm, f"{sale['buyer_name'] or 'N/A'}")
    pdf.drawString(margin, y - 12 * mm, f"{sale['buyer_city'] or 'N/A'}")
    pdf.drawString(margin, y - 18 * mm, f"Contact: {sale['buyer_contact'] or 'N/A'}")

    bank_y = y
    if farm_info and farm_info['bank_name']:
        pdf.setFont('Helvetica-Bold', 12)
        pdf.drawString(width / 2 + 10 * mm, bank_y, 'Bank Details:')
        pdf.setFont('Helvetica', 10)
        pdf.drawString(width / 2 + 10 * mm, bank_y - 6 * mm, f"Bank: {farm_info['bank_name']}")
        pdf.drawString(width / 2 + 10 * mm, bank_y - 12 * mm, f"A/C: {farm_info['account_number'] or 'N/A'}")
        pdf.drawString(width / 2 + 10 * mm, bank_y - 18 * mm, f"IFSC: {farm_info['ifsc_code'] or 'N/A'}")

    y -= 32 * mm
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(margin, y, 'Goat Particulars')
    y -= 8 * mm
    pdf.setFont('Helvetica', 10)
    fields = [
        ('Tag/ID Number', sale['tag_id']),
        ('Gender', sale['gender'] or (goat['gender'] if goat else 'N/A')),
        ('Weight (kg)', f"{sale['weight'] if sale['weight'] else (goat['weight_kg'] if goat else 'N/A')}"),
        ('Breed', sale['breed'] or (goat['breed'] if goat else 'N/A')),
        ('Breed Percent', sale['breed_percent'] or (goat['breed_percent'] if goat else 'N/A'))
    ]
    for label, value in fields:
        pdf.drawString(margin, y, f"{label}: {value}")
        y -= 7 * mm

    y -= 6 * mm
    pdf.setFont('Helvetica-Bold', 12)
    pdf.drawString(margin, y, 'Price Summary')
    y -= 8 * mm
    pdf.setFont('Helvetica', 10)
    pdf.drawString(margin, y, f"Price per Unit: ₹ {sale['sold_price']:.2f}")
    y -= 7 * mm
    pdf.drawString(margin, y, f"Total Amount: ₹ {sale['sold_price']:.2f}")
    y -= 12 * mm
    pdf.setFont('Helvetica-Bold', 11)
    pdf.drawString(margin, y, f"Grand Total: ₹ {sale['sold_price']:.2f}")

    y -= 18 * mm
    pdf.setFont('Helvetica-Oblique', 9)
    pdf.drawString(margin, y, f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")
    pdf.drawString(margin, y - 7 * mm, 'Thank you for your business!')

    # Digital Signature Block
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(width - margin - 50 * mm, y, "Digital Signature")
    pdf.setLineWidth(0.5)
    pdf.line(width - margin - 60 * mm, y - 5 * mm, width - margin, y - 5 * mm)
    pdf.setFont('Helvetica', 9)
    pdf.drawString(width - margin - 55 * mm, y - 10 * mm, "(Authorized Signatory)")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)

    try:
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Invoice_{sale["id"]}.pdf'
        )
    except TypeError:
        # Fallback for older Flask versions
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            attachment_filename=f'Invoice_{sale["id"]}.pdf'
        )

@app.route('/clear_all_data', methods=['POST'])
def clear_all_data():
    """Clear all data from the database. Requires confirmation."""
    confirmation = request.form.get('confirmation', '').lower()
    
    if confirmation != 'yes':
        flash('Confirmation failed. Data not cleared.', 'danger')
        return redirect(url_for('farm_settings'))
    
    db = get_db()
    try:
        # Delete all records from all tables
        db.execute('DELETE FROM goats_data')
        db.execute('DELETE FROM master_records')
        db.execute('DELETE FROM sales_records')
        db.execute('DELETE FROM medicine_records')
        db.execute('DELETE FROM mortality_records')
        db.execute('DELETE FROM feed_inventory')
        db.execute('DELETE FROM kid_records')
        db.execute('DELETE FROM purchases')
        db.execute('DELETE FROM vaccine_records')
        db.execute('DELETE FROM doctor_details')
        
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

        add_col("employees", "aadhar_no", "TEXT")
        add_col("employees", "pan_no", "TEXT")
        add_col("employees", "bank_name", "TEXT")
        add_col("employees", "account_no", "TEXT")
        add_col("employees", "ifsc_code", "TEXT")
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


init_employee_tables()

@app.route('/employees')
def employees():
    db = get_db()
    records = db.execute('SELECT * FROM employees ORDER BY name ASC').fetchall()
    return render_template('employees.html', records=records)

@app.route('/employee_add', methods=['GET', 'POST'])
def employee_add():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('''INSERT INTO employees (name, role, phone, address, join_date, wage_type, wage_rate, status, notes, 
                                             aadhar_no, pan_no, bank_name, account_no, ifsc_code) 
                      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (f.get('name'), f.get('role'), f.get('phone'), f.get('address'), f.get('joining_date'),
             f.get('wage_type'), f.get('wage_rate', 0), 'Active', f.get('notes'),
             f.get('aadhar_no'), f.get('pan_no'), f.get('bank_name'), f.get('account_no'), f.get('ifsc_code')))
        db.commit()
        flash('Employee added!', 'success')
        return redirect(url_for('employees'))
    return render_template('employee_add.html')

@app.route('/employee_edit/<int:emp_id>', methods=['GET', 'POST'])
def employee_edit(emp_id):
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db.execute('''UPDATE employees SET name=?, role=?, phone=?, address=?, join_date=?, wage_type=?, wage_rate=?, status=?, notes=?,
                                           aadhar_no=?, pan_no=?, bank_name=?, account_no=?, ifsc_code=? WHERE id=?''',
            (f.get('name'), f.get('role'), f.get('phone'), f.get('address'), f.get('joining_date'),
             f.get('wage_type'), f.get('wage_rate', 0), f.get('status'), f.get('notes'),
             f.get('aadhar_no'), f.get('pan_no'), f.get('bank_name'), f.get('account_no'), f.get('ifsc_code'), emp_id))
        db.commit()
        flash('Employee updated!', 'success')
        return redirect(url_for('employees'))
    record = db.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    return render_template('employee_edit.html', record=record)

@app.route('/employee_detail/<int:emp_id>')
def employee_detail(emp_id):
    db = get_db()
    emp = db.execute('SELECT * FROM employees WHERE id=?', (emp_id,)).fetchone()
    if not emp:
        flash('Not found.', 'danger')
        return redirect(url_for('employees'))
    attendance = db.execute('SELECT * FROM attendance WHERE employee_id=? ORDER BY date DESC LIMIT 30', (emp_id,)).fetchall()
    payments = db.execute('SELECT * FROM salary_payments WHERE employee_id=? ORDER BY paid_date DESC', (emp_id,)).fetchall()
    return render_template('employee_detail.html', employee=emp, attendance=attendance, payments=payments)

@app.route('/employee_delete/<int:emp_id>', methods=['POST'])
def employee_delete(emp_id):
    db = get_db()
    db.execute('DELETE FROM employees WHERE id=?', (emp_id,))
    db.commit()
    flash('Employee deleted.', 'success')
    return redirect(url_for('employees'))


# ── ATTENDANCE ──────────────────────────────────────────────────────────────────
@app.route('/attendance')
def attendance_view():
    db = get_db()
    date_filter = request.args.get('date', '')
    q = '''SELECT a.*, e.name, e.role FROM attendance a
           JOIN employees e ON a.employee_id = e.id WHERE 1=1'''
    p = []
    if date_filter:
        q += ' AND a.date = ?'
        p.append(date_filter)
    q += ' ORDER BY a.date DESC'
    records = db.execute(q, p).fetchall()
    emps = db.execute('SELECT * FROM employees WHERE status="Active" ORDER BY name').fetchall()
    return render_template('attendance.html', records=records, employees=emps, date_filter=date_filter)

@app.route('/attendance_add', methods=['POST'])
def attendance_add():
    db = get_db()
    f = request.form
    db.execute('INSERT INTO attendance (employee_id, date, status, notes) VALUES (?, ?, ?, ?)',
        (f.get('employee_id'), f.get('date'), f.get('status'), f.get('notes')))
    db.commit()
    flash('Attendance marked!', 'success')
    return redirect(url_for('attendance_view'))

@app.route('/attendance_summary')
def attendance_summary():
    db = get_db()
    month = request.args.get('month', datetime.now().strftime('%m'))
    year = request.args.get('year', datetime.now().strftime('%Y'))
    data = db.execute('''SELECT e.name, 
        SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present,
        SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) as absent,
        SUM(CASE WHEN a.status='Leave' THEN 1 ELSE 0 END) as leave,
        SUM(CASE WHEN a.status='Half Day' THEN 1 ELSE 0 END) as half_day
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id AND strftime('%m', a.date)=? AND strftime('%Y', a.date)=?
        GROUP BY e.id ORDER BY e.name''', (month, year)).fetchall()
    return render_template('attendance_summary.html', data=data, month=month, year=year)

@app.route('/salary_calculate', methods=['GET', 'POST'])
def salary_calculate():
    db = get_db()
    month = request.args.get('month', datetime.now().strftime('%m'))
    year = request.args.get('year', datetime.now().strftime('%Y'))
    
    # Get attendance summary
    data = db.execute('''SELECT e.id, e.name, e.role, e.wage_type, e.wage_rate,
        SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present_days,
        SUM(CASE WHEN a.status='Half Day' THEN 0.5 ELSE 0 END) as half_days
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id AND strftime('%m', a.date)=? AND strftime('%Y', a.date)=?
        GROUP BY e.id ORDER BY e.name''', (month, year)).fetchall()
    
    salaries = []
    for emp in data:
        present = (emp['present_days'] or 0) + (emp['half_days'] or 0)
        wage_type = emp['wage_type']
        wage_rate = emp['wage_rate'] or 0
        
        computed = 0
        if wage_type == 'Monthly':
            computed = (wage_rate / 30.0) * present
        elif wage_type == 'Weekly':
            computed = (wage_rate / 7.0) * present
        elif wage_type == 'Daily':
            computed = wage_rate * present
            
        # Check if already paid
        paid = db.execute('''SELECT SUM(net_salary) FROM salary_payments 
                             WHERE employee_id=? AND month=? AND year=?''', 
                          (emp['id'], int(month), int(year))).fetchone()[0] or 0
        
        salaries.append({
            'id': emp['id'],
            'name': emp['name'],
            'role': emp['role'],
            'present': present,
            'wage_type': wage_type,
            'wage_rate': wage_rate,
            'computed': computed,
            'paid': paid,
            'balance': max(0, computed - paid)
        })
        
    return render_template('salary_calculate.html', salaries=salaries, month=month, year=year)

@app.route('/pay_salary', methods=['POST'])
def pay_salary():
    db = get_db()
    emp_id = request.form.get('employee_id')
    amount = float(request.form.get('amount') or 0)
    date = request.form.get('payment_date')
    method = request.form.get('payment_mode')
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
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    q = 'SELECT * FROM expenses WHERE 1=1'
    p = []
    if category:
        q += ' AND category=?'; p.append(category)
    if start_date:
        q += ' AND date>=?'; p.append(start_date)
    if end_date:
        q += ' AND date<=?'; p.append(end_date)
    q += ' ORDER BY date DESC'
    records = db.execute(q, p).fetchall()
    return render_template('expenses.html', records=records, category=category, start_date=start_date, end_date=end_date)

@app.route('/expense_add', methods=['GET', 'POST'])
def expense_add():
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute('INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, receipt_no, notes) VALUES (?,?,?,?,?,?,?,?)',
            (f.get('category'), f.get('amount'), f.get('expense_date'), f.get('description'),
             f.get('vendor_name'), f.get('payment_method'), f.get('bill_reference'), f.get('notes')))
        db.commit()
        flash('Expense added!', 'success')
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
@app.route('/pnl')
def pnl():
    db = get_db()
    year = request.args.get('year', datetime.now().strftime('%Y'))
    
    # Months for Chart.js
    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    sales_data = []
    expense_data = []
    profit_data = []
    cash_flow_data = []
    cumulative_cash = 0
    
    total_sales_yr = 0
    total_expenses_yr = 0
    
    # Advanced Breakdown Dictionaries
    revenue_breakdown = {
        'goat_sales': 0, 'milk_sales': 0, 'breeding': 0,
        'manure': 0, 'online': 0, 'subsidies': 0
    }
    
    expense_breakdown = {
        'feed': 0, 'vet': 0, 'vaccine': 0, 'elec_water': 0,
        'salaries': 0, 'transport': 0, 'maint': 0, 'rent': 0,
        'insurance': 0, 'misc': 0
    }
    
    for m in months:
        ym = f"{year}-{m}"
        
        # --- REVENUE ---
        goat_sales = db.execute('''SELECT SUM(sold_price) FROM sales_records WHERE strftime('%Y-%m', date_of_sale) = ?''', (ym,)).fetchone()[0] or 0
        milk_sales = db.execute('''SELECT SUM(amount) FROM finances WHERE type='Income' AND category='Milk Sales' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        breeding = db.execute('''SELECT SUM(amount) FROM finances WHERE type='Income' AND category='Breeding Income' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        manure = db.execute('''SELECT SUM(amount) FROM finances WHERE type='Income' AND category='Organic Manure Sales' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        online = db.execute('''SELECT SUM(amount) FROM finances WHERE type='Income' AND category='Online Marketplace Income' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        subsidies = db.execute('''SELECT SUM(amount) FROM finances WHERE type='Income' AND category='Government Subsidies' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        
        month_revenue = goat_sales + milk_sales + breeding + manure + online + subsidies
        
        revenue_breakdown['goat_sales'] += goat_sales
        revenue_breakdown['milk_sales'] += milk_sales
        revenue_breakdown['breeding'] += breeding
        revenue_breakdown['manure'] += manure
        revenue_breakdown['online'] += online
        revenue_breakdown['subsidies'] += subsidies
        
        # --- EXPENSES ---
        feed = db.execute('''SELECT SUM(total_cost) FROM feed_inventory WHERE strftime('%Y-%m', purchase_date) = ?''', (ym,)).fetchone()[0] or 0
        vet = db.execute('''SELECT SUM(cost) FROM medicine_purchases WHERE strftime('%Y-%m', purchase_date) = ?''', (ym,)).fetchone()[0] or 0
        vaccine = db.execute('''SELECT SUM(cost) FROM vaccine_purchases WHERE strftime('%Y-%m', purchase_date) = ?''', (ym,)).fetchone()[0] or 0
        
        elec_water = db.execute('''SELECT SUM(amount) FROM expenses WHERE status='Approved' AND category='Electricity and Water' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        transport = db.execute('''SELECT SUM(amount) FROM expenses WHERE status='Approved' AND category='Transport' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        rent = db.execute('''SELECT SUM(amount) FROM expenses WHERE status='Approved' AND category='Farm Rent' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        insurance = db.execute('''SELECT SUM(amount) FROM expenses WHERE status='Approved' AND category='Insurance' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        misc = db.execute('''SELECT SUM(amount) FROM expenses WHERE status='Approved' AND category NOT IN ('Electricity and Water', 'Transport', 'Farm Rent', 'Insurance') AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        
        salaries = db.execute('''SELECT SUM(net_salary) FROM salary_payments WHERE year = ? AND month = ?''', (year, int(m))).fetchone()[0] or 0
        maint = db.execute('''SELECT SUM(service_cost) FROM equipment_services WHERE strftime('%Y-%m', service_date) = ?''', (ym,)).fetchone()[0] or 0
        
        month_expense = feed + vet + vaccine + elec_water + transport + rent + insurance + misc + salaries + maint
        
        expense_breakdown['feed'] += feed
        expense_breakdown['vet'] += vet
        expense_breakdown['vaccine'] += vaccine
        expense_breakdown['elec_water'] += elec_water
        expense_breakdown['salaries'] += salaries
        expense_breakdown['transport'] += transport
        expense_breakdown['maint'] += maint
        expense_breakdown['rent'] += rent
        expense_breakdown['insurance'] += insurance
        expense_breakdown['misc'] += misc
        
        profit = month_revenue - month_expense
        cumulative_cash += profit
        
        sales_data.append(month_revenue)
        expense_data.append(month_expense)
        profit_data.append(profit)
        cash_flow_data.append(cumulative_cash)
        
        total_sales_yr += month_revenue
        total_expenses_yr += month_expense

    net_profit = total_sales_yr - total_expenses_yr
    profit_margin = (net_profit / total_sales_yr * 100) if total_sales_yr > 0 else 0
    roi = (net_profit / total_expenses_yr * 100) if total_expenses_yr > 0 else 0
    burn_rate = total_expenses_yr / 12
    ebitda = net_profit
    
    active_goats = db.execute('''SELECT COUNT(*) FROM master_records WHERE status = 'Active' ''').fetchone()[0] or 1
    rev_per_goat = total_sales_yr / active_goats
    feed_per_goat = expense_breakdown['feed'] / active_goats

    return render_template('pnl.html', year=year, month_names=month_names,
                           sales_data=sales_data, expense_data=expense_data, profit_data=profit_data,
                           cash_flow_data=cash_flow_data,
                           total_sales_yr=total_sales_yr, total_expenses_yr=total_expenses_yr,
                           revenue_breakdown=revenue_breakdown, expense_breakdown=expense_breakdown,
                           net_profit=net_profit, profit_margin=profit_margin, roi=roi,
                           rev_per_goat=rev_per_goat, feed_per_goat=feed_per_goat,
                           burn_rate=burn_rate, ebitda=ebitda)

# ── EQUIPMENT ──────────────────────────────────────────────────────────────────
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
        db.execute('INSERT INTO equipment (name, equipment_name, type, purchase_date, purchase_cost, supplier, status, notes, assigned_employee, service_due_date) VALUES (?,?,?,?,?,?,?,?,?,?)',
            (f.get('equipment_name'), f.get('equipment_name'), f.get('type'), f.get('purchase_date'), f.get('purchase_cost'),
             f.get('supplier'), f.get('condition_status'), f.get('notes'), f.get('assigned_employee'), f.get('service_due_date')))
        db.commit()
        flash('Equipment added!', 'success')
        return redirect(url_for('equipment'))
    return render_template('equipment_add.html')

@app.route('/equipment_edit/<int:id>', methods=['GET', 'POST'])
def equipment_edit(id):
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db.execute('UPDATE equipment SET name=?, equipment_name=?, type=?, purchase_date=?, purchase_cost=?, supplier=?, status=?, notes=?, assigned_employee=?, service_due_date=? WHERE id=?',
            (f.get('equipment_name'), f.get('equipment_name'), f.get('type'), f.get('purchase_date'), f.get('purchase_cost'),
             f.get('supplier'), f.get('condition_status'), f.get('notes'), f.get('assigned_employee'), f.get('service_due_date'), id))
        db.commit()
        flash('Equipment updated!', 'success')
        return redirect(url_for('equipment'))
    record = db.execute('SELECT * FROM equipment WHERE id=?', (id,)).fetchone()
    return render_template('equipment_edit.html', record=record)

@app.route('/equipment_delete/<int:id>', methods=['POST'])
def equipment_delete(id):
    db = get_db()
    db.execute('DELETE FROM equipment WHERE id = ?', (id,))
    db.commit()
    flash('Equipment record deleted!', 'success')
    return redirect(url_for('equipment_purchases'))

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
    month = request.args.get('month', datetime.now().strftime('%Y-%m'))
    data = db.execute('''SELECT e.employee_id, e.name, e.role,
        w.daily_wage, w.monthly_salary, w.bonus, w.advance_salary,
        w.pending_payment, w.overtime_rate,
        SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) as present_days,
        SUM(CASE WHEN a.status='Half Day' THEN 0.5 ELSE 0 END) as half_days
        FROM employees e
        LEFT JOIN employee_wages w ON e.id=w.employee_id
        LEFT JOIN attendance a ON e.id=a.employee_id AND strftime('%Y-%m', a.date)=?
        GROUP BY e.id ORDER BY e.name''', (month,)).fetchall()
    return render_template('salary_report.html', data=data, month=month)


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

@app.route('/pnl_report')
def pnl_report():
    db = get_db()
    year = request.args.get('year', datetime.now().strftime('%Y'))
    months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    data = []
    total_sales_yr = 0
    total_expenses_yr = 0
    
    breakdown = {
        'goat_purchases': 0, 'feed_purchases': 0, 'med_purchases': 0,
        'vac_purchases': 0, 'salaries': 0, 'maint': 0, 'gen_exp': 0
    }
    
    for i, m in enumerate(months):
        ym = f"{year}-{m}"
        sales = db.execute('''SELECT SUM(sold_price) FROM sales_records WHERE strftime('%Y-%m', date_of_sale) = ?''', (ym,)).fetchone()[0] or 0
        gen_exp = db.execute('''SELECT SUM(amount) FROM expenses WHERE status='Approved' AND strftime('%Y-%m', date) = ?''', (ym,)).fetchone()[0] or 0
        goat_purchases = db.execute('''SELECT SUM(purchase_amount) FROM master_records WHERE strftime('%Y-%m', purchase_date) = ?''', (ym,)).fetchone()[0] or 0
        feed_purchases = db.execute('''SELECT SUM(total_cost) FROM feed_inventory WHERE strftime('%Y-%m', purchase_date) = ?''', (ym,)).fetchone()[0] or 0
        med_purchases = db.execute('''SELECT SUM(cost) FROM medicine_purchases WHERE strftime('%Y-%m', purchase_date) = ?''', (ym,)).fetchone()[0] or 0
        vac_purchases = db.execute('''SELECT SUM(cost) FROM vaccine_purchases WHERE strftime('%Y-%m', purchase_date) = ?''', (ym,)).fetchone()[0] or 0
        maint = db.execute('''SELECT SUM(service_cost) FROM equipment_services WHERE strftime('%Y-%m', service_date) = ?''', (ym,)).fetchone()[0] or 0
        salaries = db.execute('''SELECT SUM(net_salary) FROM salary_payments WHERE year = ? AND month = ?''', (year, int(m))).fetchone()[0] or 0
        
        total_exp = gen_exp + goat_purchases + feed_purchases + med_purchases + vac_purchases + maint + salaries
        profit = sales - total_exp
        
        data.append({
            'month_name': month_names[i],
            'sales': sales,
            'total_exp': total_exp,
            'profit': profit
        })
        
        total_sales_yr += sales
        total_expenses_yr += total_exp
        
        breakdown['goat_purchases'] += goat_purchases
        breakdown['feed_purchases'] += feed_purchases
        breakdown['med_purchases'] += med_purchases
        breakdown['vac_purchases'] += vac_purchases
        breakdown['salaries'] += salaries
        breakdown['maint'] += maint
        breakdown['gen_exp'] += gen_exp

    return render_template('pnl_report.html', 
                           year=year, data=data, breakdown=breakdown,
                           total_sales_yr=total_sales_yr, total_expenses_yr=total_expenses_yr)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

