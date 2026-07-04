# 🐐 Ranga Farms — Goat Farm Management System

A comprehensive full-stack web application for managing all operations of a goat farm, built with **Flask**, **PostgreSQL**, and **Bootstrap**.

## ✨ Features

### 🐐 Livestock Management
- **Goat Master Registry** — Full CRUD with tag IDs, breeds, age, and health records
- **Goat Profile Cards** — Detailed individual goat profiles
- **Kid Tracking** — Birth records and lineage management
- **Breed Management** — Track and categorize breeds
- **Mortality Records** — Log and analyze mortality events

### 💰 Financial Management
- **Profit & Loss Dashboard** — Real-time P&L reporting
- **Purchases Module** — Track goat, feed, medicine, vaccine, and equipment purchases
- **Sales Module** — Record and manage all sales transactions
- **Expense Tracking** — Categorize and monitor farm expenses
- **Invoice Generation** — Create and manage invoices
- **Recurring Expenses** — Automate recurring cost entries

### 👥 Employee Management
- **Employee Directory** — Add, edit, and manage farm workers
- **Attendance Tracking** — Daily attendance with summary reports
- **Leave Management** — Track employee leave records
- **Salary Calculation** — Compute wages and generate salary reports
- **Work Logs** — Log daily work activities

### 🏥 Health & Veterinary
- **Health Records** — Track goat health status and history
- **Doctor Management** — Manage veterinarian contacts and visits
- **Medicine Inventory** — Track medicine stock and usage
- **Vaccine Schedule** — Manage vaccination records

### 🍽️ Feed & Inventory
- **Feed Management** — Track feed types, quantities, and purchases
- **Equipment Tracking** — Manage farm equipment with supplier info
- **Inventory Dashboard** — Overview of all farm inventory

### 📊 Reporting & Analytics
- **Financial Reports** — Detailed P&L and expense reports
- **Performance Reports** — Farm performance analytics
- **Salary Reports** — Employee compensation summaries

### ⚙️ System
- **User Authentication** — Login, registration, and OTP verification
- **Farm Settings** — Configurable farm parameters
- **Task Management** — Farm task tracking and assignment

## 📁 Project Structure

```
Final-Ranga-Web-Project/
├── LICENSE
├── README.md
├── .gitignore
└── goat_farm_app/
    ├── Project_goatfarm.py     # Main Flask application with PostgreSQL support
    ├── db_migration.py         # Dynamic PostgreSQL schema migrations
    ├── seed_mock_data.py       # PostgreSQL sample data seeder
    ├── requirements.txt        # Python dependencies (includes psycopg2-binary)
    ├── static/
    │   ├── css/style.css       # Custom styles
    │   └── js/main.js          # Client-side JavaScript
    └── templates/              # 77 Jinja2 HTML templates
        ├── layout.html         # Base layout template
        ├── dashboard.html      # Main dashboard
        ├── login.html          # Authentication
        └── ...                 # All feature templates
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL database instance
- pip

### Database Configuration
Before running the application, make sure PostgreSQL is running. 

By default, the application connects to a local PostgreSQL instance using:
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `goat_farm`
- **User**: `postgres`
- **Password**: `postgres`

To customize these connection credentials (both locally and when deploying online), configure them directly in your environment variables:
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_SSLMODE` (defaults to `prefer`)

Or set a single connection URI:
- `DATABASE_URL` (e.g. `postgresql://user:password@host:port/database_name`)

Create a new PostgreSQL database matching your configuration name (defaults to `goat_farm`).

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/Final-Ranga-Web-Project.git
cd Final-Ranga-Web-Project

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r goat_farm_app/requirements.txt
```

### Run the Application
```bash
python goat_farm_app/Project_goatfarm.py
```
The app will be available at `http://localhost:5001`.

### Seed Sample Data (Optional, for clean databases)
```bash
python goat_farm_app/seed_mock_data.py
```

## 🛠️ Tech Stack

| Layer      | Technology       |
|------------|------------------|
| Backend    | Flask 3.0        |
| Database   | PostgreSQL       |
| Frontend   | Bootstrap + Jinja2 |
| Auth       | Werkzeug 3.0     |
| Language   | Python 3         |

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

> Built for **Ranga Farms**