import psycopg2
import os
import random
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

    year = 2024
    print("Inserting mock finances and expenses records...")
    for month in range(1, 13):
        for _ in range(random.randint(1, 2)):
            date_str = f'{year}-{month:02d}-{random.randint(1, 28):02d}'
            
            # Incomes
            c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (%s, %s, %s, %s, %s)",
                ('Income', 'Milk Sales', random.uniform(5000, 15000), date_str, 'Monthly milk sale'))
            c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (%s, %s, %s, %s, %s)",
                ('Income', 'Breeding Income', random.uniform(10000, 30000), date_str, 'Breeding service'))
            c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (%s, %s, %s, %s, %s)",
                ('Income', 'Organic Manure Sales', random.uniform(2000, 5000), date_str, 'Manure bulk sale'))
            if random.random() > 0.7:
                c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (%s, %s, %s, %s, %s)",
                    ('Income', 'Online Marketplace Income', random.uniform(20000, 50000), date_str, 'Online goats sale'))
            if random.random() > 0.9:
                c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (%s, %s, %s, %s, %s)",
                    ('Income', 'Government Subsidies', random.uniform(50000, 100000), date_str, 'Yearly subsidy'))
                    
            # Expenses
            c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (%s, %s, %s, %s, %s)",
                ('Electricity and Water', random.uniform(3000, 8000), date_str, 'Utility bills', 'Approved'))
            c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (%s, %s, %s, %s, %s)",
                ('Transport', random.uniform(2000, 6000), date_str, 'Logistics', 'Approved'))
            c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (%s, %s, %s, %s, %s)",
                ('Farm Rent', random.uniform(10000, 15000), date_str, 'Monthly rent', 'Approved'))
            if random.random() > 0.8:
                c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (%s, %s, %s, %s, %s)",
                    ('Insurance', random.uniform(10000, 20000), date_str, 'Premium payment', 'Approved'))
            c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (%s, %s, %s, %s, %s)",
                ('Miscellaneous', random.uniform(1000, 3000), date_str, 'Misc items', 'Approved'))

    conn.commit()
    conn.close()
    print('Mock data inserted successfully.')

if __name__ == '__main__':
    seed()
