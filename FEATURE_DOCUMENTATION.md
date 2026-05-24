# New Features Documentation

## 1. Weight Notification Alert (25 kg or More)

### Overview
A notification popup displays on the first new login after the system update, alerting users about any goats that have reached 25 kg or more in weight.

### Features
- **Automatic Detection**: Checks all active goats with weight >= 25 kg
- **First Login Alert**: Displays only on the first login after the system update
- **Display Information**:
  - Tag ID of the heavy goat
  - Current weight in kg
  - Color of the goat
- **Modal Display**: Shows a professional modal alert with a "Heavy Goats Alert" header
- **One-time per day**: Once dismissed, the notification will not appear again on the same day

### User Interface
- Modal popup appears automatically on dashboard load
- Shows all heavy goats in a card-based layout
- Users can close the modal by clicking "Close" button or the X icon

### Technical Implementation
- Uses `user_login_tracking` table to track login dates and notification viewing
- New table created: `user_login_tracking` with columns:
  - `user_id`: References the user
  - `last_login_date`: Tracks the last login date
  - `has_seen_weight_notification`: Tracks if notification was seen
- Logic in `/login` route updates tracking information
- Dashboard route checks session flag and database to determine if notification should display

---

## 2. Enhanced Tag ID Search with Last 4 Digits Support

### Overview
Improved search functionality that allows users to find goats by searching the last 4 digits of their Tag ID, with better pattern matching.

### Features
- **Full Tag ID Search**: Search by complete tag ID (e.g., "UII1710000101")
- **Last 4 Digits Search**: Search using only the last 4 digits (e.g., "0101" finds "UII1710000101")
- **Breed Name Search**: Still supports searching by breed name
- **Pattern Matching**: Automatically detects 4-digit searches and applies last-digit matching
- **Applied to Two Pages**:
  1. **Dashboard** - In the "Goat Directory" section search box
  2. **Goats Directory Page** - In the main goat search box

### User Interface

#### Dashboard Search Box
- Placeholder: "Search by Tag No, Breed, or last 4 digits..."
- Helper text: "You can search by full Tag ID, Breed name, or the last 4 digits of Tag ID"

#### Goats Directory Page
- Placeholder: "Search by Tag ID or last 4 digits..."
- Helper text: "You can search by full Tag ID or the last 4 digits"

### How It Works
1. User enters search text
2. System checks if the input is exactly 4 digits
3. If 4 digits detected:
   - Searches for goats whose tag ID ends with those 4 digits
   - Also searches for partial matches in tag ID
4. Results are displayed with duplicates removed

### Examples
- Search "0101" → Finds "UII1710000101"
- Search "UII17" → Finds "UII1710000101"
- Search "Male" → Finds by breed or other attributes
- Search "UII1710000101" → Exact tag ID match

### Technical Implementation

#### Dashboard Route (`/dashboard`)
- Enhanced `search_q` parameter handling
- New logic:
  ```python
  if len(search_q_stripped) == 4 and search_q_stripped.isdigit():
      # Search by last 4 digits
      searched_goat = db.execute(
          "SELECT * FROM master_records WHERE tag_no LIKE ? ORDER BY tag_no DESC LIMIT 1", 
          (f"%{search_q_stripped}",)
      ).fetchone()
  ```

#### Goats Route (`/goats`)
- New search parameter: `search`
- Filters results based on:
  1. Last 4 digits if input is 4 digits
  2. Full tag ID match
  3. Removes duplicates
- Uses Python list comprehension for filtering

#### Templates Updated
- `dashboard.html`: Improved search form with helper text
- `goats.html`: Added new search form with helper text

---

## Database Changes

### New Table: `user_login_tracking`
```sql
CREATE TABLE user_login_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    last_login_date DATE DEFAULT NULL,
    has_seen_weight_notification INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
```

---

## How to Test

### Weight Notification
1. Log out and log back in
2. You should see the "Heavy Goats Alert" modal on first login
3. Close the modal
4. Navigate away and return to dashboard
5. Notification should not reappear on the same day

### Last 4 Digits Search
1. Go to Dashboard or Goats Directory page
2. In the search box, enter the last 4 digits of any goat's tag ID
3. The matching goat should be displayed
4. Try searching with different formats:
   - Last 4 digits only
   - Full tag ID
   - Breed name (still works)

---

## Future Enhancements
- Add email notifications for heavy goats
- Allow customization of weight threshold
- Add more sophisticated pattern matching
- Create reports for goats reaching target weights
- Add weight history tracking
