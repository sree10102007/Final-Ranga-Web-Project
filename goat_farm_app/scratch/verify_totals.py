import sys, sqlite3
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row
db = conn.cursor()

from_date = '2026-01-01'
to_date   = '2026-12-31'

# --- P&L sources ---
goat_p  = db.execute("SELECT SUM(price) FROM purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0] or 0
feed_p  = db.execute("SELECT SUM(cost)  FROM feed_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0] or 0
med_p   = db.execute("SELECT SUM(cost)  FROM medicine_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0] or 0
vac_p   = db.execute("SELECT SUM(cost)  FROM vaccine_purchases WHERE purchase_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0] or 0
salary  = db.execute("SELECT SUM(net_salary) FROM salary_payments WHERE paid_date BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0] or 0
approved_exp = db.execute(
    "SELECT SUM(amount) FROM expenses WHERE status='Approved' AND date BETWEEN ? AND ?"
    " AND LOWER(COALESCE(category,'')) NOT LIKE '%labor%'"
    " AND LOWER(COALESCE(category,'')) NOT LIKE '%labour%'",
    (from_date, to_date)
).fetchone()[0] or 0

sales   = db.execute("SELECT SUM(sold_price) FROM sales_records WHERE date_of_sale BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0] or 0
other_s = db.execute("SELECT SUM(total_amount) FROM other_sales_records WHERE date_of_sale BETWEEN ? AND ?", (from_date, to_date)).fetchone()[0] or 0

print('=== P&L Breakdown (no stock) ===')
print(f'  Income: sales={sales} + other={other_s} = {sales+other_s}')
print(f'  Purchases: goat={goat_p}, feed={feed_p}, med={med_p}, vac={vac_p}')
print(f'  Direct expenses: salary={salary}, approved non-labor expenses={approved_exp}')
total_purchases = goat_p + feed_p + med_p + vac_p
total_expenses  = total_purchases + salary + approved_exp
net = (sales + other_s) - total_expenses
print(f'  Total purchases = {total_purchases}')
print(f'  Total expenses  = {total_expenses}')
print(f'  Net P/L         = {net}')

# --- Dashboard sources ---
print()
print('=== Dashboard Breakdown ===')
exp_goat  = db.execute("SELECT SUM(price) FROM purchases").fetchone()[0] or 0
exp_feed  = db.execute("SELECT SUM(total_cost) FROM feed_inventory").fetchone()[0] or 0
exp_med2  = db.execute("SELECT SUM(cost) FROM medicine_purchases").fetchone()[0] or 0
exp_vac2  = db.execute("SELECT SUM(cost) FROM vaccine_purchases").fetchone()[0] or 0
exp_sal   = db.execute("SELECT SUM(net_salary) FROM salary_payments").fetchone()[0] or 0
exp_maint = db.execute("SELECT SUM(service_cost) FROM equipment_services").fetchone()[0] or 0
exp_gen   = db.execute(
    "SELECT SUM(amount) FROM expenses WHERE status='Approved'"
    " AND LOWER(COALESCE(category,'')) NOT LIKE '%labor%'"
    " AND LOWER(COALESCE(category,'')) NOT LIKE '%labour%'"
).fetchone()[0] or 0
inc = db.execute("SELECT SUM(sold_price) FROM sales_records").fetchone()[0] or 0
inc += db.execute("SELECT SUM(total_amount) FROM other_sales_records").fetchone()[0] or 0
total_dash_exp = exp_goat + exp_feed + exp_med2 + exp_vac2 + exp_sal + exp_maint + exp_gen
print(f'  Income: {inc}')
print(f'  Expenses: goat={exp_goat}, feed={exp_feed}, med={exp_med2}, vac={exp_vac2}, salary={exp_sal}, maint={exp_maint}, gen_approved={exp_gen}')
print(f'  Total expenses = {total_dash_exp}')
print(f'  Net P/L        = {inc - total_dash_exp}')

conn.close()
