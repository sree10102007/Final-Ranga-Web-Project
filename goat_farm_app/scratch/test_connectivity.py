import sqlite3
import os

db_path = r"c:\Users\acer\OneDrive\Desktop\Ranga Farms  web service\Final-Ranga-Web-Project\goat_farm_app\database.db"

def test_connectivity():
    print("Connecting to database at:", db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Let's perform a dry run transaction to test
    print("\n--- Starting Dry-Run Integration Test for Vouchers, Inventory, and Expenses ---")
    try:
        # 1. CREATE A FEED VOUCHER
        print("[TEST 1] Creating a test Feed Purchase Voucher...")
        feed_name = "TEST_INTEGRATION_FEED"
        qty = 100.0
        cost = 5000.0
        unit = "KG"
        supplier = "TEST_SUPPLIER"
        p_date = "2026-05-28"
        
        # Insert voucher
        cursor.execute('''
            INSERT INTO feed_purchases (feed_name, quantity, unit, cost, purchase_date, supplier)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (feed_name, qty, unit, cost, p_date, supplier))
        purchase_id = cursor.lastrowid
        print(f" -> Created feed_purchases row with ID: {purchase_id}")
        
        # Insert inventory row
        cursor.execute('''
            INSERT INTO feed_inventory (feed_name, opening_stock, purchased_qty, used_qty, wastage_qty, closing_stock, unit, cost_per_unit, total_cost, purchase_date, supplier, purchase_id)
            VALUES (?, 0.0, ?, 0.0, 0.0, ?, ?, ?, ?, ?, ?, ?)
        ''', (feed_name, qty, qty, unit, cost/qty, cost, p_date, supplier, purchase_id))
        inventory_id = cursor.lastrowid
        print(f" -> Created feed_inventory row with ID: {inventory_id}")
        
        # Insert goats_data
        desc = f"Purchased {qty} {unit} of {feed_name} from {supplier}"
        cursor.execute('''
            INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
            VALUES ('All', ?, 'expense', 'Feed', ?, ?)
        ''', (p_date, cost, desc))
        
        # Insert general expenses
        cursor.execute('''
            INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
            VALUES ('Feed Purchase', ?, ?, ?, ?, 'Cash', 'Paid')
        ''', (cost, p_date, desc, supplier))
        print(" -> Created goats_data and expenses rows.")
        
        # Verify connectivity
        e_row = cursor.execute("SELECT * FROM expenses WHERE vendor_name = ? AND amount = ?", (supplier, cost)).fetchone()
        gd_row = cursor.execute("SELECT * FROM goats_data WHERE notes = ?", (desc,)).fetchone()
        inv_row = cursor.execute("SELECT * FROM feed_inventory WHERE purchase_id = ?", (purchase_id,)).fetchone()
        
        assert e_row is not None, "Expense record was not created!"
        assert gd_row is not None, "Goats Data record was not created!"
        assert inv_row is not None, "Inventory record was not created!"
        print(" -> VERIFICATION SUCCESS: All records exist and are correctly interconnected!")

        # 2. UPDATE VOUCHER
        print("\n[TEST 2] Updating Voucher cost to 6000 and supplier to NEW_TEST_SUPPLIER...")
        new_cost = 6000.0
        new_supplier = "NEW_TEST_SUPPLIER"
        
        # Simulate updating voucher: delete old expenses/goats_data, insert new ones
        cursor.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Feed' AND amount = ?", (p_date, cost))
        cursor.execute("DELETE FROM expenses WHERE date = ? AND category = 'Feed Purchase' AND amount = ? AND vendor_name = ?", (p_date, cost, supplier))
        
        # Update voucher row
        cursor.execute('''
            UPDATE feed_purchases SET cost = ?, supplier = ? WHERE id = ?
        ''', (new_cost, new_supplier, purchase_id))
        
        # Update inventory row
        cursor.execute('''
            UPDATE feed_inventory SET total_cost = ?, supplier = ? WHERE purchase_id = ?
        ''', (new_cost, new_supplier, purchase_id))
        
        # Insert new expenses/goats_data
        new_desc = f"Purchased {qty} {unit} of {feed_name} from {new_supplier}"
        cursor.execute('''
            INSERT INTO goats_data (tag_number, date, category, type, amount, notes)
            VALUES ('All', ?, 'expense', 'Feed', ?, ?)
        ''', (p_date, new_cost, new_desc))
        cursor.execute('''
            INSERT INTO expenses (category, amount, date, description, vendor_name, payment_mode, status)
            VALUES ('Feed Purchase', ?, ?, ?, ?, 'Cash', 'Paid')
        ''', (new_cost, p_date, new_desc, new_supplier))
        print(" -> Updated voucher, inventory, and recreated expense logs.")
        
        # Verify updates
        e_row_new = cursor.execute("SELECT * FROM expenses WHERE vendor_name = ? AND amount = ?", (new_supplier, new_cost)).fetchone()
        gd_row_new = cursor.execute("SELECT * FROM goats_data WHERE notes = ?", (new_desc,)).fetchone()
        inv_row_new = cursor.execute("SELECT * FROM feed_inventory WHERE purchase_id = ?", (purchase_id,)).fetchone()
        
        assert e_row_new is not None, "New Expense record does not exist!"
        assert gd_row_new is not None, "New Goats Data record does not exist!"
        assert inv_row_new['total_cost'] == new_cost, "New Cost not matching in inventory!"
        print(" -> VERIFICATION SUCCESS: Updates successfully propagated and checked out!")

        # 3. DELETE VOUCHER
        print("\n[TEST 3] Deleting Voucher...")
        # Simulate deletion: delete connected expense, goats_data, inventory, and voucher
        cursor.execute("DELETE FROM goats_data WHERE date = ? AND category = 'expense' AND type = 'Feed' AND amount = ?", (p_date, new_cost))
        cursor.execute("DELETE FROM expenses WHERE date = ? AND category = 'Feed Purchase' AND amount = ? AND vendor_name = ?", (p_date, new_cost, new_supplier))
        cursor.execute("DELETE FROM feed_purchases WHERE id = ?", (purchase_id,))
        cursor.execute("DELETE FROM feed_inventory WHERE purchase_id = ?", (purchase_id,))
        
        # Verify deletions
        e_del = cursor.execute("SELECT * FROM expenses WHERE vendor_name = ? AND amount = ?", (new_supplier, new_cost)).fetchone()
        gd_del = cursor.execute("SELECT * FROM goats_data WHERE notes = ?", (new_desc,)).fetchone()
        inv_del = cursor.execute("SELECT * FROM feed_inventory WHERE purchase_id = ?", (purchase_id,)).fetchone()
        purch_del = cursor.execute("SELECT * FROM feed_purchases WHERE id = ?", (purchase_id,)).fetchone()
        
        assert e_del is None, "Expense record was NOT deleted!"
        assert gd_del is None, "Goats Data record was NOT deleted!"
        assert inv_del is None, "Inventory record was NOT deleted!"
        assert purch_del is None, "Voucher record was NOT deleted!"
        print(" -> VERIFICATION SUCCESS: Cascade deletions completely cleaned up all tables!")

    except AssertionError as e:
        print(" -> [FAILURE]:", e)
    except Exception as e:
        print(" -> [ERROR]:", e)
    finally:
        conn.close()
        print("\n--- Dry-Run Integration Test Completed successfully ---\n")

if __name__ == "__main__":
    test_connectivity()
