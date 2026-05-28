import sys
import os
from datetime import datetime, timedelta

# Add Flask app directory to import path
sys.path.append(r'c:\Users\acer\OneDrive\Desktop\Ranga Farms  web service\Final-Ranga-Web-Project\goat_farm_app')

import Project_goatfarm
from Project_goatfarm import app, get_db, calculate_age_str, parse_dob_to_age_dict

def run_tests():
    print("Starting integration tests for goat age tracking...")
    today = datetime.now().date()
    
    # 1. Case 1: Under 30 days -> Show exact age in days till only 30
    print("\n--- Testing Case 1: Under 30 Days ---")
    dob_under_30 = (today - timedelta(days=25)).strftime('%Y-%m-%d')
    age_str_under_30 = calculate_age_str(dob_under_30)
    print(f"25 days old -> '{age_str_under_30}'")
    assert age_str_under_30 == "25 days", f"Expected '25 days', got '{age_str_under_30}'"
    
    # 2. Case 2: Over 30 days but under 1 year -> Show months only (no days!)
    print("\n--- Testing Case 2: 30 Days to 1 Year ---")
    # 45 days is roughly 1 month and 15 days (depending on month length)
    dob_mid = (today - timedelta(days=45)).strftime('%Y-%m-%d')
    age_str_mid = calculate_age_str(dob_mid)
    print(f"45 days old -> '{age_str_mid}'")
    assert "mo" in age_str_mid, "Should display month(s)"
    assert "day" not in age_str_mid, "Should strictly exclude days from under 1 year older goats!"
    
    # 3. Case 3: Over 1 year -> Show years and current remaining months (strictly no days!)
    print("\n--- Testing Case 3: Over 1 Year ---")
    # 2 years, 3 months, 15 days
    dob_over_1y = (today - timedelta(days=2*365 + 3*30 + 15)).strftime('%Y-%m-%d')
    age_str_over_1y = calculate_age_str(dob_over_1y)
    print(f"2y 3m 15d old -> '{age_str_over_1y}'")
    assert "2 yr" in age_str_over_1y or "1 yr" in age_str_over_1y, "Should display year(s)"
    assert "mo" in age_str_over_1y, "Should display month(s)"
    assert "day" not in age_str_over_1y, "Should not display day(s) when over 1 year!"
    
    # 4. Verify DB persistence and retrieval
    print("\n--- Testing DB persistence ---")
    with app.test_request_context():
        db = get_db()
        db.execute("DELETE FROM master_records WHERE tag_no = 'TAG-TEST-999'")
        db.commit()
        
        db.execute('''
            INSERT INTO master_records (tag_no, breed, gender, dob, status)
            VALUES (?, ?, ?, ?, ?)
        ''', ('TAG-TEST-999', 'Boer', 'M', dob_over_1y, 'Active'))
        db.commit()
        
        record = db.execute("SELECT * FROM master_records WHERE tag_no = 'TAG-TEST-999'").fetchone()
        assert record is not None, "Failed to persist record!"
        computed_age = calculate_age_str(record['dob'])
        print(f"DB retrieved computed age: {computed_age}")
        assert "day" not in computed_age, "Should strictly exclude days from older goats in DB retrieval"
        
        db.execute("DELETE FROM master_records WHERE tag_no = 'TAG-TEST-999'")
        db.commit()
        
    print("\nAll integration tests passed successfully!")

if __name__ == '__main__':
    run_tests()
