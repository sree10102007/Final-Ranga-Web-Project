import os

file_path = r"c:\Users\Suressvar\Documents\GitHub\Final-Ranga-Web-Project\goat_farm_app\Project_goatfarm.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Define the search block (using exact line contents)
search_block = """@app.route('/salary_calculate', methods=['GET', 'POST'])
def salary_calculate():
    db = get_db()
    import calendar
    from datetime import datetime, timedelta
    
    today = datetime.now()
    default_start = today.replace(day=1).strftime('%Y-%m-%d')
    last_day_val = calendar.monthrange(today.year, today.month)[1]
    default_end = today.replace(day=last_day_val).strftime('%Y-%m-%d')
    
    start_date = request.args.get('start_date') or request.form.get('start_date') or default_start
    end_date = request.args.get('end_date') or request.form.get('end_date') or default_end
    today_date = today.strftime('%Y-%m-%d')
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if start_dt > end_dt:
            start_date, end_date = end_date, start_date
            start_dt, end_dt = end_dt, start_dt
    except Exception:
        start_date = default_start
        end_date = default_end
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
    total_days = (end_dt - start_dt).days + 1
    
    # Query attendance strictly for the selected period
    data = db.execute('''SELECT e.id, e.name, e.role, e.wage_type, e.wage_rate, e.sr_no,
        SUM(CASE WHEN a.status IN ('P', 'Present') THEN 1 ELSE 0 END) as present_days
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id AND a.date BETWEEN ? AND ?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (start_date, end_date)).fetchall()
        
    # Extract month and year from end_date for database storage compatibility
    try:
        month_val = f"{end_dt.month:02d}"
        year_val = str(end_dt.year)
    except Exception:
        month_val = f"{today.month:02d}"
        year_val = str(today.year)
        
    salaries = []
    for emp in data:
        present = emp['present_days'] or 0
        wage_type = emp['wage_type']
        wage_rate = emp['wage_rate'] or 0
        
        computed = 0.0
        if wage_type == 'Monthly':
            computed = (wage_rate / float(total_days)) * present
        elif wage_type == 'Weekly':
            computed = (wage_rate / 7.0) * present
        elif wage_type == 'Daily':
            computed = wage_rate * present
            
        # Get paid amount in this period range
        paid = db.execute('''SELECT SUM(net_salary) FROM salary_payments 
                             WHERE employee_id=? AND paid_date BETWEEN ? AND ?''', 
                           (emp['id'], start_date, end_date)).fetchone()[0] or 0.0
        
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
            'balance': max(0.0, computed - paid)
        })
        
    return render_template('salary_calculate.html', 
                           salaries=salaries, 
                           month=month_val, 
                           year=year_val, 
                           start_date=start_date,
                           end_date=end_date,
                           total_days=total_days,
                           today_date=today_date)"""

# Define the replacement block
replacement_block = """@app.route('/salary_calculate', methods=['GET', 'POST'])
def salary_calculate():
    db = get_db()
    import calendar
    from datetime import datetime, timedelta
    
    today = datetime.now()
    
    month = request.args.get('month') or request.form.get('month')
    year = request.args.get('year') or request.form.get('year')
    start_day = request.args.get('start_day') or request.form.get('start_day') or '1'
    
    if not year:
        year = str(today.year)
    if not month:
        month = f"{today.month:02d}"
    else:
        try:
            month = f"{int(month):02d}"
        except ValueError:
            month = f"{today.month:02d}"
            
    try:
        year_int = int(year)
        month_int = int(month)
    except ValueError:
        year_int = today.year
        month_int = today.month
        year = str(year_int)
        month = f"{month_int:02d}"
        
    last_day_val = calendar.monthrange(year_int, month_int)[1]
    
    end_day = request.args.get('end_day') or request.form.get('end_day') or str(last_day_val)
    
    try:
        start_day_int = min(max(1, int(start_day)), last_day_val)
    except ValueError:
        start_day_int = 1
        
    try:
        end_day_int = min(max(1, int(end_day)), last_day_val)
    except ValueError:
        end_day_int = last_day_val
        
    if start_day_int > end_day_int:
        start_day_int, end_day_int = end_day_int, start_day_int
        
    start_date = f"{year}-{month}-{start_day_int:02d}"
    end_date = f"{year}-{month}-{end_day_int:02d}"
    today_date = today.strftime('%Y-%m-%d')
    
    total_days = (end_day_int - start_day_int) + 1
    
    # Query attendance strictly for the selected period
    data = db.execute('''SELECT e.id, e.name, e.role, e.wage_type, e.wage_rate, e.sr_no,
        SUM(CASE WHEN a.status IN ('P', 'Present') THEN 1 ELSE 0 END) as present_days
        FROM employees e
        LEFT JOIN attendance a ON e.id=a.employee_id AND a.date BETWEEN ? AND ?
        GROUP BY e.id ORDER BY CAST(e.sr_no AS INTEGER) ASC''', (start_date, end_date)).fetchall()
        
    salaries = []
    for emp in data:
        present = emp['present_days'] or 0
        wage_type = emp['wage_type']
        wage_rate = emp['wage_rate'] or 0
        
        computed = 0.0
        if wage_type == 'Monthly':
            computed = (wage_rate / float(total_days)) * present
        elif wage_type == 'Weekly':
            computed = (wage_rate / 7.0) * present
        elif wage_type == 'Daily':
            computed = wage_rate * present
            
        # Get paid amount in this period range
        paid = db.execute('''SELECT SUM(net_salary) FROM salary_payments 
                             WHERE employee_id=? AND paid_date BETWEEN ? AND ?''', 
                           (emp['id'], start_date, end_date)).fetchone()[0] or 0.0
        
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
            'balance': max(0.0, computed - paid)
        })
        
    return render_template('salary_calculate.html', 
                           salaries=salaries, 
                           month=month, 
                           year=year, 
                           start_day=start_day_int,
                           end_day=end_day_int,
                           start_date=start_date,
                           end_date=end_date,
                           total_days=total_days,
                           today_date=today_date)"""

# Clean lines to avoid mismatch
content_clean = content.replace("\r\n", "\n")
search_block_clean = search_block.replace("\r\n", "\n")
replacement_block_clean = replacement_block.replace("\r\n", "\n")

if search_block_clean in content_clean:
    content_clean = content_clean.replace(search_block_clean, replacement_block_clean)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content_clean)
    print("Success! Replaced salary_calculate in Project_goatfarm.py")
else:
    print("Error: Could not find search block in Project_goatfarm.py")
