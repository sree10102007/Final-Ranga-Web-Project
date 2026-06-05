import sqlite3

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Backfill existing goat purchases into expenses (if not already there)
purchases = cur.execute('SELECT * FROM purchases').fetchall()
for p in purchases:
    tag = p['tag_id']
    seller = p['seller_name'] or 'Supplier'
    desc = f'Goat Purchase: Tag {tag} from {seller}'
    cat = p['pnl_category'] or 'Livestock Purchase'
    amt = p['price']
    dt = p['purchase_date']
    existing = cur.execute(
        "SELECT 1 FROM expenses WHERE date=? AND amount=? AND status='Paid' AND description LIKE 'Goat Purchase%'",
        (dt, amt)
    ).fetchone()
    if not existing:
        cur.execute(
            "INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status) VALUES (?, ?, ?, ?, ?, 'Cash', 'Paid')",
            (cat, amt, dt, desc, p['seller_name'])
        )
        print(f'Added: {desc} - Rs.{amt}')
    else:
        print(f'Already exists: {desc}')

conn.commit()
conn.close()
print('Done backfilling goat purchases to expenses.')
