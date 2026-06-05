import os

file_path = r"c:\Users\Suressvar\Documents\GitHub\Final-Ranga-Web-Project\goat_farm_app\Project_goatfarm.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Search for the "Staff Salary" section and the "Query expenses / else:" section
found = False
for idx, line in enumerate(lines):
    if "elif category == 'Staff Salary / Payments (HR)':" in line:
        # Look for the next "else:" block
        for j in range(idx+1, min(idx+40, len(lines))):
            if "else:" in lines[j] and "# Query expenses" in lines[j-1]:
                # We found the target slice to replace.
                # Let's see what is after the "else:" block. We want to find the next blank or non-indented line.
                # In our case, the body is 3 lines:
                # else:
                #     rows = db.execute(...)
                #     for r in rows:
                #         transactions.append(...)
                
                # Let's verify the exact lines:
                print("Target block to replace:")
                for k in range(j, j+5):
                    print(f"  {k+1}: {repr(lines[k])}")
                
                # Replace lines from j to j+4 (inclusive) with the complete Purchases & Sales & General Expenses block
                indent = "    "
                replacement = [
                    "    else:\n",
                    f"{indent}    # Goat purchases\n",
                    f"{indent}    rows = db.execute(\"SELECT seller_name AS detail, purchase_date AS date, price AS amount, pnl_category, tag_id FROM purchases WHERE purchase_date BETWEEN ? AND ?\", (from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        r_cat = r['pnl_category'] or 'Purchase'\n",
                    f"{indent}        if r_cat == category:\n",
                    f"{indent}            transactions.append({{'date': r['date'], 'reference': f\"Goat: {{r['tag_id']}}\", 'detail': r['detail'], 'amount': r['amount']}})\n",
                    f"{indent}            \n",
                    f"{indent}    # Feed purchases\n",
                    f"{indent}    rows = db.execute(\"SELECT supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, feed_name FROM feed_purchases WHERE purchase_date BETWEEN ? AND ?\", (from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        r_cat = r['pnl_category'] or 'Purchase'\n",
                    f"{indent}        if r_cat == category:\n",
                    f"{indent}            transactions.append({{'date': r['date'], 'reference': f\"Feed: {{r['feed_name']}}\", 'detail': f\"Supplier: {{r['detail']}}\", 'amount': r['amount']}})\n",
                    f"{indent}            \n",
                    f"{indent}    # Medicine purchases\n",
                    f"{indent}    rows = db.execute(\"SELECT supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, medicine_name FROM medicine_purchases WHERE purchase_date BETWEEN ? AND ?\", (from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        r_cat = r['pnl_category'] or 'Purchase'\n",
                    f"{indent}        if r_cat == category:\n",
                    f"{indent}            transactions.append({{'date': r['date'], 'reference': f\"Med: {{r['medicine_name']}}\", 'detail': f\"Supplier: {{r['detail']}}\", 'amount': r['amount']}})\n",
                    f"{indent}            \n",
                    f"{indent}    # Vaccine purchases\n",
                    f"{indent}    rows = db.execute(\"SELECT supplier AS detail, purchase_date AS date, cost AS amount, pnl_category, vaccine_name FROM vaccine_purchases WHERE purchase_date BETWEEN ? AND ?\", (from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        r_cat = r['pnl_category'] or 'Purchase'\n",
                    f"{indent}        if r_cat == category:\n",
                    f"{indent}            transactions.append({{'date': r['date'], 'reference': f\"Vac: {{r['vaccine_name']}}\", 'detail': f\"Supplier: {{r['detail']}}\", 'amount': r['amount']}})\n",
                    f"{indent}            \n",
                    f"{indent}    # Equipment purchases\n",
                    f"{indent}    rows = db.execute(\"SELECT name AS detail, purchase_date AS date, purchase_cost AS amount, pnl_category FROM equipment WHERE purchase_date BETWEEN ? AND ?\", (from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        r_cat = r['pnl_category'] or 'Purchase'\n",
                    f"{indent}        if r_cat == category:\n",
                    f"{indent}            transactions.append({{'date': r['date'], 'reference': f\"Asset: {{r['detail']}}\", 'detail': f\"Asset Purchase\", 'amount': r['amount'] or 0.0}})\n",
                    "\n",
                    f"{indent}    # Goat sales\n",
                    f"{indent}    rows = db.execute(\"SELECT tag_id AS reference, date_of_sale AS date, sold_price AS amount, pnl_category, buyer_name FROM sales_records WHERE date_of_sale BETWEEN ? AND ?\", (from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        r_cat = r['pnl_category'] or 'Sales'\n",
                    f"{indent}        sales_accounts = ['Sales', 'Pos SALES', 'sales@0%', 'sales@12%', 'sales@18%', 'sales@5%']\n",
                    f"{indent}        if r_cat not in sales_accounts and r_cat != 'Other Income' and r_cat not in ['Discount Received', 'FD-Interest Received', 'Interest Received']:\n",
                    f"{indent}            mapped_cat = 'Sales'\n",
                    f"{indent}        else:\n",
                    f"{indent}            mapped_cat = r_cat\n",
                    f"{indent}            \n",
                    f"{indent}        if mapped_cat == category:\n",
                    f"{indent}            transactions.append({{'date': r['date'], 'reference': f\"Goat: {{r['reference']}}\", 'detail': r['buyer_name'], 'amount': r['amount']}})\n",
                    f"{indent}            \n",
                    f"{indent}    # Other sales\n",
                    f"{indent}    rows = db.execute(\"SELECT item_name AS reference, date_of_sale AS date, total_amount AS amount, pnl_category, buyer_name, notes FROM other_sales_records WHERE date_of_sale BETWEEN ? AND ?\", (from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        r_cat = r['pnl_category'] or 'Sales'\n",
                    f"{indent}        sales_accounts = ['Sales', 'Pos SALES', 'sales@0%', 'sales@12%', 'sales@18%', 'sales@5%']\n",
                    f"{indent}        if r_cat not in sales_accounts and r_cat != 'Other Income' and r_cat not in ['Discount Received', 'FD-Interest Received', 'Interest Received']:\n",
                    f"{indent}            mapped_cat = 'Sales'\n",
                    f"{indent}        else:\n",
                    f"{indent}            mapped_cat = r_cat\n",
                    f"{indent}            \n",
                    f"{indent}        if mapped_cat == category:\n",
                    f"{indent}            transactions.append({{'date': r['date'], 'reference': r['reference'], 'detail': f\"{{r['buyer_name']}} - {{r['notes'] or ''}}\", 'amount': r['amount']}})\n",
                    "\n",
                    f"{indent}    # Expenses\n",
                    f"{indent}    rows = db.execute(\"SELECT date, category AS reference, description AS detail, amount FROM expenses WHERE status = 'Approved' AND category = ? AND date BETWEEN ? AND ? ORDER BY date DESC\", (category, from_date, to_date)).fetchall()\n",
                    f"{indent}    for r in rows:\n",
                    f"{indent}        transactions.append({{'date': r['date'], 'reference': r['reference'], 'detail': r['detail'] or 'General Expense', 'amount': r['amount']}})\n"
                ]
                
                lines[j:j+4] = replacement
                found = True
                break
        if found:
            break

if found:
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("Success! Replaced else: block with full purchase/sales/expense drilldown logic.")
else:
    print("Could not find the target slice.")
