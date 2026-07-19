import os
import psycopg2
import psycopg2.extras

# Resolve root path
base_dir = os.path.dirname(os.path.abspath(__file__))

import sys

# Load environment variables from .env file if dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(base_dir, '.env'))
except ImportError:
    pass

def validate_env():
    required_vars = []
    if not os.environ.get('DATABASE_URL'):
        required_vars.extend(['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'])
    
    missing_or_placeholder = []
    for var in required_vars:
        val = os.environ.get(var)
        if not val or 'your_' in val.lower():
            missing_or_placeholder.append(var)
            
    if missing_or_placeholder:
        print(f"CRITICAL CONFIGURATION ERROR: Missing or placeholder environment variables: {', '.join(missing_or_placeholder)}")
        print("Please copy .env.example to .env and configure the actual connection settings.")
        sys.exit(1)

validate_env()


def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        return psycopg2.connect(db_url)
    
    db_name = os.environ.get('DB_NAME')
    try:
        return psycopg2.connect(
            host=os.environ.get('DB_HOST'),
            port=os.environ.get('DB_PORT'),
            database=db_name,
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            sslmode=os.environ.get('DB_SSLMODE', 'prefer')
        )
    except psycopg2.OperationalError as e:
        if "does not exist" in str(e):
            try:
                # Connect to default 'postgres' database to create the target database
                conn = psycopg2.connect(
                    host=os.environ.get('DB_HOST'),
                    port=os.environ.get('DB_PORT'),
                    database='postgres',
                    user=os.environ.get('DB_USER'),
                    password=os.environ.get('DB_PASSWORD'),
                    sslmode=os.environ.get('DB_SSLMODE', 'prefer')
                )
                conn.autocommit = True
                with conn.cursor() as cursor:
                    cursor.execute(f'CREATE DATABASE "{db_name}"')
                conn.close()
                # Retry connecting to the newly created database
                return psycopg2.connect(
                    host=os.environ.get('DB_HOST'),
                    port=os.environ.get('DB_PORT'),
                    database=db_name,
                    user=os.environ.get('DB_USER'),
                    password=os.environ.get('DB_PASSWORD'),
                    sslmode=os.environ.get('DB_SSLMODE', 'prefer')
                )
            except Exception:
                raise e
        else:
            raise e

# Mock sqlite3 exception namespace for compatibility if we catch errors
class SqliteExceptionCompat:
    OperationalError = psycopg2.OperationalError
    IntegrityError = psycopg2.IntegrityError
    Error = psycopg2.Error

sqlite3 = SqliteExceptionCompat

def migrate():
    print("Connecting to PostgreSQL database...")
    conn = get_db_connection()
    # Set autocommit to True so each schema creation runs in its own transaction block.
    # This prevents the whole transaction from aborting if a statement fails.
    conn.autocommit = True
    cursor = conn.cursor()

    # Check/Create users table and add security columns
    print("Checking users table security columns...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    
    def add_user_column(col, col_type):
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {col_type}")
        except Exception as e:
            print(f"Error adding column {col} to users: {e}")
            
    add_user_column("mfa_secret", "TEXT")
    add_user_column("mfa_enabled", "INTEGER DEFAULT 0")
    add_user_column("backup_codes", "TEXT")
    add_user_column("login_attempts", "INTEGER DEFAULT 0")
    add_user_column("locked_until", "TIMESTAMP DEFAULT NULL")
    add_user_column("password_history", "TEXT")


    def get_columns(table_name):
        try:
            # Query information_schema for column names
            cursor.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (table_name.lower(),)
            )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting columns for {table_name}: {e}")
            return []

    def add_column(table_name, column_name, column_type):
        cols = get_columns(table_name)
        if column_name.lower() not in [c.lower() for c in cols]:
            print(f"Adding column {column_name} to {table_name}...")
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_type}")
            except Exception as e:
                print(f"Error adding column {column_name}: {e}")

    # --- 1. EQUIPMENT ---
    print("Checking equipment table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipment (
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
    )''')
    for col in ['name', 'type', 'purchase_date', 'purchase_cost', 'supplier', 'status', 'notes', 'assigned_employee', 'service_due_date']:
        add_column('equipment', col, 'TEXT' if col not in ['purchase_cost', 'purchase_date', 'service_due_date'] else 'REAL' if col == 'purchase_cost' else 'DATE')

    # --- 2. EQUIPMENT SERVICES (es) ---
    print("Checking equipment_services table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS equipment_services (
        id SERIAL PRIMARY KEY,
        equipment_id INTEGER,
        vendor_name TEXT,
        service_date DATE,
        service_cost REAL,
        description TEXT,
        status TEXT,
        notes TEXT
    )''')
    for col in ['vendor_name', 'service_date', 'service_cost', 'description', 'status', 'notes']:
        add_column('equipment_services', col, 'TEXT' if col != 'service_cost' else 'REAL')

    # --- 3. EXPENSES ---
    print("Checking expenses table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
        id SERIAL PRIMARY KEY,
        category TEXT,
        amount REAL,
        date DATE,
        description TEXT,
        vendor_name TEXT,
        payment_mode TEXT,
        receipt_no TEXT,
        notes TEXT,
        status TEXT,
        pnl_category TEXT
    )''')
    for col in ['category', 'amount', 'date', 'description', 'vendor_name', 'payment_mode', 'receipt_no', 'notes', 'status', 'pnl_category']:
        add_column('expenses', col, 'TEXT' if col != 'amount' else 'REAL')

    # --- 4. FEED INVENTORY ---
    print("Checking feed_inventory table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS feed_inventory (
        id SERIAL PRIMARY KEY,
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
    for col in ['feed_name', 'opening_stock', 'purchased_qty', 'used_qty', 'closing_stock', 'unit', 'cost_per_unit', 'total_cost', 'purchase_date', 'supplier', 'alert_level']:
        add_column('feed_inventory', col, 'TEXT' if col in ['feed_name', 'unit', 'purchase_date', 'supplier'] else 'REAL')

    # --- 5. FINANCES ---
    print("Checking finances table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS finances (
        id SERIAL PRIMARY KEY,
        type TEXT,
        category TEXT,
        amount REAL,
        date DATE,
        description TEXT,
        reference_id TEXT,
        notes TEXT
    )''')
    for col in ['type', 'category', 'amount', 'date', 'description', 'reference_id', 'notes']:
        add_column('finances', col, 'TEXT' if col != 'amount' else 'REAL')

    # --- 6. EMPLOYEES ---
    print("Checking employees table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
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
    for col in ['name', 'role', 'phone', 'address', 'join_date', 'wage_type', 'wage_rate', 'status', 'notes']:
        add_column('employees', col, 'TEXT' if col != 'wage_rate' else 'REAL')

    # --- 7. ATTENDANCE ---
    print("Checking attendance table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY,
        employee_id INTEGER,
        date DATE,
        status TEXT,
        notes TEXT
    )''')
    for col in ['employee_id', 'date', 'status', 'notes']:
        add_column('attendance', col, 'INTEGER' if col == 'employee_id' else 'TEXT')

    # --- 8. SALARY PAYMENTS ---
    print("Checking salary_payments table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS salary_payments (
        id SERIAL PRIMARY KEY,
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
    for col in ['employee_id', 'month', 'year', 'total_days', 'present_days', 'gross_salary', 'deductions', 'net_salary', 'paid_date', 'payment_mode']:
        add_column('salary_payments', col, 'REAL' if 'salary' in col or 'deductions' in col else 'INTEGER' if 'days' in col or col in ['employee_id', 'month', 'year'] else 'TEXT')

    # --- 9. FARM SETTINGS ---
    print("Checking farm_settings table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS farm_settings (
        id SERIAL PRIMARY KEY,
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
    for col in ['farm_name', 'address', 'phone', 'email', 'bank_name', 'account_no', 'ifsc_code', 'gst_no', 'logo_path']:
        add_column('farm_settings', col, 'TEXT')

    # --- 10. REPORTS ---
    print("Checking reports table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        report_type TEXT,
        generated_date DATE,
        from_date DATE,
        to_date DATE,
        file_path TEXT,
        notes TEXT
    )''')
    for col in ['report_type', 'generated_date', 'from_date', 'to_date', 'file_path', 'notes']:
        add_column('reports', col, 'TEXT')

    # --- 11. VOUCHERS PARTICULARS & LEDGERS ---
    print("Checking voucher tables for particulars and ledger columns...")
    for table_name in ['purchases', 'feed_purchases', 'medicine_purchases', 'vaccine_purchases']:
        add_column(table_name, 'particular_id', 'INTEGER')
        add_column(table_name, 'particular_name', 'TEXT')
        add_column(table_name, 'pnl_category', 'TEXT')
        add_column(table_name, 'bill_date', 'DATE')
        add_column(table_name, 'bill_no', 'TEXT')

    # --- 12. GOAT WEIGHTS ---
    print("Checking goat_weights table and indexes...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS goat_weights (
        id SERIAL PRIMARY KEY,
        goat_tag_no TEXT NOT NULL REFERENCES master_records(tag_no) ON DELETE CASCADE,
        weight REAL NOT NULL,
        unit TEXT NOT NULL DEFAULT 'kg',
        recorded_date DATE NOT NULL,
        recorded_by TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    try:
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_goat_weights_tag_no ON goat_weights(goat_tag_no)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_goat_weights_recorded_date ON goat_weights(recorded_date)')
    except Exception as e:
        print(f"Error creating indexes on goat_weights: {e}")

    # --- 13. EMPLOYEE ROLES ---
    print("Checking employee_roles table...")
    cursor.execute('''CREATE TABLE IF NOT EXISTS employee_roles (
        id SERIAL PRIMARY KEY,
        role_name TEXT UNIQUE NOT NULL,
        description TEXT
    )''')
    cursor.execute("SELECT COUNT(*) FROM employee_roles")
    if cursor.fetchone()[0] == 0:
        default_roles = [
            ('Manager', 'Manages farm operations and staff coordination'),
            ('Veterinarian', 'Animal health, breeding assistance, and veterinary care'),
            ('Handler', 'General animal handling, moving, and care'),
            ('Cleaner', 'Cleaning pens, maintaining hygiene and sanitation'),
            ('Feeder', 'Preparing and distributing feed and supplements'),
            ('Laborer', 'General physical labor on the farm'),
            ('Other', 'Miscellaneous roles and assignments')
        ]
        for r_name, r_desc in default_roles:
            cursor.execute("INSERT INTO employee_roles (role_name, description) VALUES (%s, %s)", (r_name, r_desc))
        print("Seeded default employee roles.")

    # --- 14. HISTORICAL ATTENDANCE STATUS MIGRATION ---
    print("Migrating historical attendance records...")
    cursor.execute("UPDATE attendance SET status = 'P' WHERE status = 'Present'")
    cursor.execute("UPDATE attendance SET status = 'L' WHERE status IN ('Leave', 'On Leave')")
    cursor.execute("UPDATE attendance SET status = 'A' WHERE status = 'Absent'")

    print("Database migration successfully completed.")
    conn.close()

if __name__ == '__main__':
    try:
        migrate()
    except psycopg2.OperationalError as e:
        import sys
        print("\n" + "="*80)
        print("  MIGRATION DATABASE CONNECTION ERROR")
        print("="*80)
        print(f"Could not connect to PostgreSQL database: {e}")
        print("\nPlease verify your connection parameters in the '.env' file located in the 'goat_farm_app' directory.")
        print("Specifically, make sure 'DB_PASSWORD' matches your PostgreSQL user's password.")
        print("="*80 + "\n")
        sys.exit(1)
