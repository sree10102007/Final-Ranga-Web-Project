import sqlite3
import random
from datetime import datetime, timedelta

conn = sqlite3.connect('database.db')
c = conn.cursor()

year = 2024
for month in range(1, 13):
    for _ in range(random.randint(1, 2)):
        date_str = f'{year}-{month:02d}-{random.randint(1, 28):02d}'
        
        # Incomes
        c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
            ('Income', 'Milk Sales', random.uniform(5000, 15000), date_str, 'Monthly milk sale'))
        c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
            ('Income', 'Breeding Income', random.uniform(10000, 30000), date_str, 'Breeding service'))
        c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
            ('Income', 'Organic Manure Sales', random.uniform(2000, 5000), date_str, 'Manure bulk sale'))
        if random.random() > 0.7:
            c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
                ('Income', 'Online Marketplace Income', random.uniform(20000, 50000), date_str, 'Online goats sale'))
        if random.random() > 0.9:
            c.execute("INSERT INTO finances (type, category, amount, date, description) VALUES (?, ?, ?, ?, ?)",
                ('Income', 'Government Subsidies', random.uniform(50000, 100000), date_str, 'Yearly subsidy'))
                
        # Expenses
        c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (?, ?, ?, ?, ?)",
            ('Electricity and Water', random.uniform(3000, 8000), date_str, 'Utility bills', 'Approved'))
        c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (?, ?, ?, ?, ?)",
            ('Transport', random.uniform(2000, 6000), date_str, 'Logistics', 'Approved'))
        c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (?, ?, ?, ?, ?)",
            ('Farm Rent', random.uniform(10000, 15000), date_str, 'Monthly rent', 'Approved'))
        if random.random() > 0.8:
            c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (?, ?, ?, ?, ?)",
                ('Insurance', random.uniform(10000, 20000), date_str, 'Premium payment', 'Approved'))
        c.execute("INSERT INTO expenses (category, amount, date, description, status) VALUES (?, ?, ?, ?, ?)",
            ('Miscellaneous', random.uniform(1000, 3000), date_str, 'Misc items', 'Approved'))

conn.commit()
print('Mock data inserted.')
