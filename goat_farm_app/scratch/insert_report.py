import os

file_path = r"c:\Users\Suressvar\Documents\GitHub\Final-Ranga-Web-Project\goat_farm_app\templates\pnl.html"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update style section to hide #traditional-container on print, hide #print-report-container on screen, and style the print report
style_search = """    @media print {
        #sidebar, #topbar, .d-print-none, form, .btn, .collapse, footer, #notification-toast-container {
            display: none !important;
        }"""

style_replace = """    #print-report-container {
        display: none;
    }

    @media print {
        #sidebar, #topbar, .d-print-none, form, .btn, .collapse, footer, #notification-toast-container, #traditional-container {
            display: none !important;
        }
        
        #print-report-container {
            display: block !important;
        }
        
        .report-table th, .report-table td {
            padding: 8px 12px !important;
            font-size: 0.85rem !important;
            border: 1px solid #cbd5e1 !important;
            color: #000000 !important;
        }
        
        .report-section-header td {
            background-color: #f1f5f9 !important;
            font-weight: bold !important;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }
        
        .print-signatures {
            margin-top: 80px !important;
        }"""

if style_search in content:
    content = content.replace(style_search, style_replace)
    print("Updated print styles.")
else:
    # Let's try matching with space padding just in case
    print("Error: Could not find print style search block.")

# 2. Insert `#print-report-container` HTML
target_search = """        <!-- P&L Totals Row -->
        {% set pnl_grand_total = (gross_profit|abs if gross_profit < 0 else 0) + total_indirect_expenses + (net_profit if is_profit else 0) %}
        <div class="row g-0 bg-white fw-bold" style="font-size: 0.95rem; border-top: 2px solid #000000; border-bottom: 4px double #000000;">
            <div class="col-md-6 border-end py-3 px-4 d-flex justify-content-between align-items-center" style="background-color: #ffffff; color: #000000;">
                <span class="text-uppercase" style="letter-spacing: 0.5px;">Total</span>
                <span class="font-monospace">₹{{ "%.2f"|format(pnl_grand_total) }}</span>
            </div>
            <div class="col-md-6 py-3 px-4 d-flex justify-content-between align-items-center" style="background-color: #ffffff; color: #000000;">
                <span class="text-uppercase" style="letter-spacing: 0.5px;">Total</span>
                <span class="font-monospace">₹{{ "%.2f"|format(pnl_grand_total) }}</span>
            </div>
        </div>
    </div>
</div>"""

report_html = """        <!-- P&L Totals Row -->
        {% set pnl_grand_total = (gross_profit|abs if gross_profit < 0 else 0) + total_indirect_expenses + (net_profit if is_profit else 0) %}
        <div class="row g-0 bg-white fw-bold" style="font-size: 0.95rem; border-top: 2px solid #000000; border-bottom: 4px double #000000;">
            <div class="col-md-6 border-end py-3 px-4 d-flex justify-content-between align-items-center" style="background-color: #ffffff; color: #000000;">
                <span class="text-uppercase" style="letter-spacing: 0.5px;">Total</span>
                <span class="font-monospace">₹{{ "%.2f"|format(pnl_grand_total) }}</span>
            </div>
            <div class="col-md-6 py-3 px-4 d-flex justify-content-between align-items-center" style="background-color: #ffffff; color: #000000;">
                <span class="text-uppercase" style="letter-spacing: 0.5px;">Total</span>
                <span class="font-monospace">₹{{ "%.2f"|format(pnl_grand_total) }}</span>
            </div>
        </div>
    </div>

    <!-- PRINT ONLY VERTICAL FINANCIAL REPORT STATEMENT -->
    <div class="print-only-report mt-4" id="print-report-container">
        <div class="report-header text-center mb-5">
            <h3 class="fw-bold text-uppercase" style="letter-spacing: 1px; color: #15803d; margin-bottom: 5px;">Ranga Farms</h3>
            <h5 class="text-secondary text-uppercase mb-3" style="font-size: 0.85rem; letter-spacing: 2px;">Profit & Loss Statement</h5>
            <div class="font-monospace small text-muted" style="border-top: 1px solid #ddd; border-bottom: 1px solid #ddd; display: inline-block; padding: 5px 20px;">
                Period: {% if selected_month == 'All' %}Full Year {{ selected_year }}{% else %}{{ from_date }} to {{ to_date }}{% endif %}
            </div>
        </div>
        
        <table class="table table-bordered report-table">
            <thead>
                <tr style="background-color: #f1f5f9;">
                    <th style="width: 50%; font-weight: 800; color: #000000;">Particulars</th>
                    <th style="width: 25%; text-align: right; font-weight: 800; color: #000000;">Amount (₹)</th>
                    <th style="width: 25%; text-align: right; font-weight: 800; color: #000000;">Total (₹)</th>
                </tr>
            </thead>
            <tbody>
                <!-- A. Revenue -->
                <tr class="report-section-header">
                    <td>A. REVENUE & DIRECT INCOMES</td>
                    <td></td>
                    <td></td>
                </tr>
                <!-- Sales Accounts -->
                <tr>
                    <td class="ps-4">Sales Accounts</td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(total_sales) }}</td>
                    <td></td>
                </tr>
                {% for sub_cat, amount in sales_accounts.items() %}
                    {% if amount > 0 %}
                    <tr class="text-muted small">
                        <td class="ps-5"><em>{{ sub_cat }}</em></td>
                        <td class="text-end font-monospace">₹{{ "%.2f"|format(amount) }}</td>
                        <td></td>
                    </tr>
                    {% endif %}
                {% endfor %}
                <!-- Direct Incomes -->
                {% if total_direct_income > 0 %}
                <tr>
                    <td class="ps-4">Direct Incomes</td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(total_direct_income) }}</td>
                    <td></td>
                </tr>
                {% for sub_cat, amount in direct_incomes.items() %}
                    {% if amount > 0 %}
                    <tr class="text-muted small">
                        <td class="ps-5"><em>{{ sub_cat }}</em></td>
                        <td class="text-end font-monospace">₹{{ "%.2f"|format(amount) }}</td>
                        <td></td>
                    </tr>
                    {% endif %}
                {% endfor %}
                {% endif %}
                <tr class="fw-bold" style="background-color: #f8fafc;">
                    <td class="ps-3">Total Revenue & Direct Income (A)</td>
                    <td></td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(total_sales + total_direct_income) }}</td>
                </tr>
                
                <!-- B. Cost of Sales -->
                <tr class="report-section-header">
                    <td>B. COST OF SALES & DIRECT COSTS</td>
                    <td></td>
                    <td></td>
                </tr>
                <tr>
                    <td class="ps-4">Opening Stock</td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(opening_stock) }}</td>
                    <td></td>
                </tr>
                <tr>
                    <td class="ps-4">Add: Purchases Accounts</td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(total_purchases) }}</td>
                    <td></td>
                </tr>
                {% for sub_cat, amount in purchase_accounts.items() %}
                    {% if amount > 0 %}
                    <tr class="text-muted small">
                        <td class="ps-5"><em>{{ sub_cat }}</em></td>
                        <td class="text-end font-monospace">₹{{ "%.2f"|format(amount) }}</td>
                        <td></td>
                    </tr>
                    {% endif %}
                {% endfor %}
                {% if total_direct_expenses > 0 %}
                <tr>
                    <td class="ps-4">Add: Direct Expenses</td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(total_direct_expenses) }}</td>
                    <td></td>
                </tr>
                {% for sub_cat, amount in direct_expenses.items() %}
                    {% if amount > 0 %}
                    <tr class="text-muted small">
                        <td class="ps-5"><em>{{ sub_cat }}</em></td>
                        <td class="text-end font-monospace">₹{{ "%.2f"|format(amount) }}</td>
                        <td></td>
                    </tr>
                    {% endif %}
                {% endfor %}
                {% endif %}
                <tr>
                    <td class="ps-4">Less: Closing Stock</td>
                    <td class="text-end font-monospace">(₹{{ "%.2f"|format(closing_stock) }})</td>
                    <td></td>
                </tr>
                {% set cost_of_sales = opening_stock + total_purchases + total_direct_expenses - closing_stock %}
                <tr class="fw-bold" style="background-color: #f8fafc;">
                    <td class="ps-3">Total Cost of Sales & Direct Costs (B)</td>
                    <td></td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(cost_of_sales) }}</td>
                </tr>
                
                <!-- C. Gross Profit -->
                <tr class="fw-bold" style="background-color: #e2e8f0; font-size: 0.95rem; border-top: 1.5px solid #000; border-bottom: 1.5px solid #000;">
                    <td><strong>C. GROSS PROFIT (A - B)</strong></td>
                    <td></td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(gross_profit) }}</td>
                </tr>
                
                <!-- D. Indirect Expenses -->
                {% if total_indirect_expenses > 0 %}
                <tr class="report-section-header">
                    <td>D. LESS: INDIRECT EXPENSES</td>
                    <td></td>
                    <td></td>
                </tr>
                {% for sub_cat, amount in indirect_expenses.items() %}
                    {% if amount > 0 %}
                    <tr>
                        <td class="ps-4">{{ sub_cat }}</td>
                        <td class="text-end font-monospace">₹{{ "%.2f"|format(amount) }}</td>
                        <td></td>
                    </tr>
                    {% endif %}
                {% endfor %}
                <tr class="fw-bold" style="background-color: #f8fafc;">
                    <td class="ps-3">Total Indirect Expenses (D)</td>
                    <td></td>
                    <td class="text-end font-monospace">(₹{{ "%.2f"|format(total_indirect_expenses) }})</td>
                </tr>
                {% endif %}
                
                <!-- E. Indirect Incomes -->
                {% if total_indirect_income > 0 %}
                <tr class="report-section-header">
                    <td>E. ADD: INDIRECT INCOMES</td>
                    <td></td>
                    <td></td>
                </tr>
                {% for sub_cat, amount in indirect_incomes.items() %}
                    {% if amount > 0 %}
                    <tr>
                        <td class="ps-4">{{ sub_cat }}</td>
                        <td class="text-end font-monospace">₹{{ "%.2f"|format(amount) }}</td>
                        <td></td>
                    </tr>
                    {% endif %}
                {% endfor %}
                <tr class="fw-bold" style="background-color: #f8fafc;">
                    <td class="ps-3">Total Indirect Incomes (E)</td>
                    <td></td>
                    <td class="text-end font-monospace">₹{{ "%.2f"|format(total_indirect_income) }}</td>
                </tr>
                {% endif %}
                
                <!-- F. Net Profit -->
                <tr class="fw-bold" style="background-color: #d1fae5; border-top: 2px solid #000000; border-bottom: 4px double #000000; font-size: 1.05rem;">
                    <td>F. NET PROFIT / (LOSS) (C - D + E)</td>
                    <td></td>
                    <td class="text-end font-monospace">
                        {% if is_profit %}
                        ₹{{ "%.2f"|format(net_profit) }}
                        {% else %}
                        (₹{{ "%.2f"|format(net_profit) }})
                        {% endif %}
                    </td>
                </tr>
            </tbody>
        </table>
        
        <!-- Signature Section -->
        <div class="row print-signatures" style="margin-top: 80px;">
            <div class="col-6 text-center" style="width: 50%; float: left; display: inline-block;">
                <div style="width: 200px; margin: 0 auto; border-top: 1px solid #000000; padding-top: 5px; font-weight: bold; font-size: 0.9rem;">Prepared By</div>
            </div>
            <div class="col-6 text-center" style="width: 50%; float: right; display: inline-block;">
                <div style="width: 200px; margin: 0 auto; border-top: 1px solid #000000; padding-top: 5px; font-weight: bold; font-size: 0.9rem;">Authorized Signatory</div>
            </div>
        </div>
    </div>
</div>"""

if target_search in content:
    content = content.replace(target_search, report_html)
    print("Inserted print report HTML.")
else:
    print("Error: Could not find target HTML search block.")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done!")
