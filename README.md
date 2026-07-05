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
- `DATABASE_URL` (e.g. `postgresql://<username>:<password>@<host>:<port>/<database_name>`)

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

## 🔒 Security Baseline

We use `detect-secrets` to prevent credentials from leaking into the repository. 

> [!IMPORTANT]
> **Path Separator Normalization:**
> Always regenerate or update the `.secrets.baseline` file using a **Linux environment** (such as WSL, a Docker container, or Unix/macOS shells) so that path separators are written as forward slashes (`/`). Running `detect-secrets` on native Windows generates backslashes (`\`), which will fail the GitHub Actions CI pipeline because GitHub runner environments are Linux-based.

---

> Built for **Ranga Farms**

## 🐳 Docker & Dockploy Deployment on Hostinger

This project is fully dockerized and optimized for deployment on Hostinger VPS using Dockploy or standard Docker Compose.

### Dockploy Configuration Details
- **Repository URL**: `https://github.com/sree10102007/Final-Ranga-Web-Project`
- **Branch**: `main`
- **Dockerfile Path**: `Dockerfile`
- **Exposed App Port**: `5001`

### Required Environment Variables
Configure these variables in your Hostinger / Dockploy dashboard (or a local `.env` file for local runs):
- `SECRET_KEY` — A secure, random secret key for Flask session signing.
- `DB_ENCRYPTION_KEY` — A Fernet key for column-level database encryption.
- `DB_PASSWORD` — Password for the PostgreSQL database user.
- `ADMIN_PASSWORD` — Password for the initial administrator user.

To generate a secure `DB_ENCRYPTION_KEY`, run this in your terminal:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Local Testing with Docker Compose
To build and run the entire stack (Flask app, PostgreSQL, Redis) locally using Docker:
```bash
# 1. Create a .env file from the example
cp goat_farm_app/.env.example .env

# 2. Edit .env to set your secrets/passwords

# 3. Build and launch the services
docker compose build --no-cache
docker compose up
```