import psycopg2
import os
import secrets

class SecureRandom:
    @staticmethod
    def randint(a, b):
        return a + secrets.randbelow(b - a + 1)

    @staticmethod
    def uniform(a, b):
        return a + (b - a) * (secrets.randbelow(1000000) / 1000000.0)

    @staticmethod
    def random():
        return secrets.randbelow(1000000) / 1000000.0

random = SecureRandom()
from datetime import datetime, timedelta

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

def seed():
    print("Connecting to PostgreSQL database for seeding...")
    conn = get_db_connection()
    c = conn.cursor()

    # Clear tables first
    print("Clearing old records...")
    c.execute("DELETE FROM sales_records")
    c.execute("DELETE FROM other_sales_records")
    c.execute("DELETE FROM expenses")
    
    year = 2026
    print("Inserting mock sales and expenses records for 2026...")
    for month in range(1, 13):
        for idx in range(random.randint(1, 2)):
            date_str = f'{year}-{month:02d}-{random.randint(1, 28):02d}'
            
            # Goat Sales (sales_records)
            c.execute("""
                INSERT INTO sales_records 
                (sr_no, tag_id, breed, breed_percent, gender, weight, sold_price, date_of_sale, buyer_name, buyer_city, buyer_contact, pnl_category)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    f"SR-{month}-{idx}-{random.randint(10,99)}",
                    f"MOCK-{month}{idx}{random.randint(10,99)}",
                    'Sirohi', '100', 'Male',
                    random.uniform(25, 40),
                    random.uniform(12000, 22000),
                    date_str, 'General Buyer', 'Coimbatore', '9876543210', 'Sales'
                )
            )

            # Other Sales (other_sales_records)
            c.execute("""
                INSERT INTO other_sales_records 
                (sr_no, item_name, quantity, unit, price_per_unit, total_amount, date_of_sale, buyer_name, buyer_city, buyer_contact, pnl_category)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    f"OTH-{month}-{idx}-{random.randint(10,99)}",
                    'Milk' if idx % 2 == 0 else 'Manure Bag',
                    50.0 if idx % 2 == 0 else 20.0,
                    'liters' if idx % 2 == 0 else 'bags',
                    60.0 if idx % 2 == 0 else 150.0,
                    random.uniform(3000, 5000),
                    date_str, 'Diary Corp' if idx % 2 == 0 else 'Local Nurseries',
                    'Erode', '9998887776', 'Direct Income'
                )
            )
                    
            # Expenses
            c.execute("INSERT INTO expenses (category, amount, date, description, status, pnl_category) VALUES (%s, %s, %s, %s, %s, %s)",
                ('Electricity and Water', random.uniform(3000, 8000), date_str, 'Utility bills', 'Approved', 'Electricity Charges'))
            c.execute("INSERT INTO expenses (category, amount, date, description, status, pnl_category) VALUES (%s, %s, %s, %s, %s, %s)",
                ('Transport', random.uniform(2000, 6000), date_str, 'Logistics', 'Approved', 'Transport & Logistics'))
            c.execute("INSERT INTO expenses (category, amount, date, description, status, pnl_category) VALUES (%s, %s, %s, %s, %s, %s)",
                ('Farm Rent', random.uniform(10000, 15000), date_str, 'Monthly rent', 'Approved', 'Miscellaneous Expenses'))
            if random.random() > 0.8:
                c.execute("INSERT INTO expenses (category, amount, date, description, status, pnl_category) VALUES (%s, %s, %s, %s, %s, %s)",
                    ('Insurance', random.uniform(10000, 20000), date_str, 'Premium payment', 'Approved', 'Miscellaneous Expenses'))
            c.execute("INSERT INTO expenses (category, amount, date, description, status, pnl_category) VALUES (%s, %s, %s, %s, %s, %s)",
                ('Miscellaneous', random.uniform(1000, 3000), date_str, 'Misc items', 'Approved', 'Miscellaneous Expenses'))

    conn.commit()
    conn.close()
    print('Mock data inserted successfully.')

if __name__ == '__main__':
    seed()
