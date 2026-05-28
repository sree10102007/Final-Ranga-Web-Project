import sqlite3
import os

def migrate():
    # Detect the correct DB file path
    db_path = 'database.db'
    if not os.path.exists(db_path):
        # Check if it's in the same dir as the app
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, 'database.db')
        if not os.path.exists(db_path):
             print(f"Database {db_path} not found. A new one will be created.")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def get_columns(table_name):
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            return [row[1] for row in cursor.fetchall()]
        except:
            return []

    def add_column(table_name, column_name, column_type):
        cols = get_columns(table_name)
        if column_name not in cols:
            print(f"Adding column {column_name} to {table_name}...")
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                conn.commit()
            except sqlite3.OperationalError as e:
                print(f"Error adding column {column_name}: {e}")

    # --- 1. EQUIPMENT ---
    print("Checking equipment table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipment (
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
    )''')
    conn.commit()
    for col in ['name', 'type', 'purchase_date', 'purchase_cost', 'supplier', 'status', 'notes', 'assigned_employee', 'service_due_date']:
        add_column('equipment', col, 'TEXT' if col not in ['purchase_cost', 'purchase_date', 'service_due_date'] else 'REAL' if col == 'purchase_cost' else 'DATE')

    # --- 2. EQUIPMENT SERVICES (es) ---
    print("Checking equipment_services table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipment_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        equipment_id INTEGER,
        vendor_name TEXT,
        service_date DATE,
        service_cost REAL,
        description TEXT,
        status TEXT,
        notes TEXT
    )''')
    conn.commit()
    for col in ['vendor_name', 'service_date', 'service_cost', 'description', 'status', 'notes']:
        add_column('equipment_services', col, 'TEXT' if col != 'service_cost' else 'REAL')

    # --- 3. EXPENSES ---
    print("Checking expenses table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        amount REAL,
        date DATE,
        description TEXT,
        vendor_name TEXT,
        payment_mode TEXT,
        receipt_no TEXT,
        notes TEXT
    )''')
    conn.commit()
    for col in ['category', 'amount', 'date', 'description', 'vendor_name', 'payment_mode', 'receipt_no', 'notes']:
        add_column('expenses', col, 'TEXT' if col != 'amount' else 'REAL')

    # --- 4. FEED INVENTORY ---
    print("Checking feed_inventory table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS feed_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feed_name TEXT,
        opening_stock REAL,
        purchased_qty REAL,
        used_qty REAL,
        closing_stock REAL,
        unit TEXT,
        cost_per_unit REAL,
        total_cost REAL,
        purchase_date DATE,
        supplier TEXT,
        alert_level REAL
    )''')
    conn.commit()
    for col in ['feed_name', 'opening_stock', 'purchased_qty', 'used_qty', 'closing_stock', 'unit', 'cost_per_unit', 'total_cost', 'purchase_date', 'supplier', 'alert_level']:
        add_column('feed_inventory', col, 'TEXT' if col in ['feed_name', 'unit', 'purchase_date', 'supplier'] else 'REAL')

    # --- 5. FINANCES ---
    print("Checking finances table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS finances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        category TEXT,
        amount REAL,
        date DATE,
        description TEXT,
        reference_id TEXT,
        notes TEXT
    )''')
    conn.commit()
    for col in ['type', 'category', 'amount', 'date', 'description', 'reference_id', 'notes']:
        add_column('finances', col, 'TEXT' if col != 'amount' else 'REAL')

    # --- 6. EMPLOYEES ---
    print("Checking employees table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        phone TEXT,
        address TEXT,
        join_date DATE,
        wage_type TEXT,
        wage_rate REAL,
        status TEXT,
        notes TEXT
    )''')
    conn.commit()
    for col in ['name', 'role', 'phone', 'address', 'join_date', 'wage_type', 'wage_rate', 'status', 'notes']:
        add_column('employees', col, 'TEXT' if col != 'wage_rate' else 'REAL')

    # --- 7. ATTENDANCE ---
    print("Checking attendance table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        date DATE,
        status TEXT,
        notes TEXT
    )''')
    conn.commit()
    for col in ['employee_id', 'date', 'status', 'notes']:
        add_column('attendance', col, 'INTEGER' if col == 'employee_id' else 'TEXT')

    # --- 8. SALARY PAYMENTS ---
    print("Checking salary_payments table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS salary_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        month INTEGER,
        year INTEGER,
        total_days INTEGER,
        present_days INTEGER,
        gross_salary REAL,
        deductions REAL,
        net_salary REAL,
        paid_date DATE,
        payment_mode TEXT
    )''')
    conn.commit()
    for col in ['employee_id', 'month', 'year', 'total_days', 'present_days', 'gross_salary', 'deductions', 'net_salary', 'paid_date', 'payment_mode']:
        add_column('salary_payments', col, 'REAL' if 'salary' in col or 'deductions' in col else 'INTEGER' if 'days' in col or col in ['employee_id', 'month', 'year'] else 'TEXT')

    # --- 9. FARM SETTINGS ---
    print("Checking farm_settings table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS farm_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_name TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        bank_name TEXT,
        account_no TEXT,
        ifsc_code TEXT,
        gst_no TEXT,
        logo_path TEXT
    )''')
    conn.commit()
    for col in ['farm_name', 'address', 'phone', 'email', 'bank_name', 'account_no', 'ifsc_code', 'gst_no', 'logo_path']:
        add_column('farm_settings', col, 'TEXT')

    # --- 10. REPORTS ---
    print("Checking reports table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_type TEXT,
        generated_date DATE,
        from_date DATE,
        to_date DATE,
        file_path TEXT,
        notes TEXT
    )''')
    conn.commit()
    for col in ['report_type', 'generated_date', 'from_date', 'to_date', 'file_path', 'notes']:
        add_column('reports', col, 'TEXT')

    print("Database migration successfully completed.")
    conn.close()

if __name__ == '__main__':
    migrate()
