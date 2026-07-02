import os
from fpdf import FPDF

class PRDPDF(FPDF):
    def header(self):
        # Draw header banner on pages after the first page
        if self.page_no() > 1:
            self.set_fill_color(30, 41, 59) # Slate 800
            self.rect(0, 0, 210, 25, "F")
            self.set_text_color(255, 255, 255)
            self.set_font("Helvetica", "B", 12)
            self.set_y(5)
            self.cell(0, 15, "RANGA FARMS - PRODUCT REQUIREMENT DOCUMENT", align="C")
            self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def create_prd_pdf(filename):
    pdf = PRDPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.alias_nb_pages()
    
    # Title Page
    pdf.add_page()
    # Override header on first page by drawing a cover page
    pdf.set_fill_color(30, 41, 59) # Slate 800
    pdf.rect(0, 0, 210, 297, "F")
    
    pdf.set_text_color(248, 250, 252) # Slate 50
    pdf.ln(50)
    pdf.set_font("Helvetica", "B", 32)
    pdf.cell(0, 15, "RANGA FARMS", align="C")
    pdf.ln(15)
    
    pdf.set_font("Helvetica", "", 18)
    pdf.set_text_color(148, 163, 184) # Slate 400
    pdf.cell(0, 10, "Goat Farm Management System", align="C")
    pdf.ln(20)
    
    pdf.set_fill_color(79, 70, 229) # Indigo 600 accent bar
    pdf.rect(85, 115, 40, 3, "F")
    
    pdf.ln(40)
    pdf.set_text_color(248, 250, 252)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Product Specification & Feature Documentation", align="C")
    pdf.ln(10)
    
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 10, "A comprehensive digital solution for livestock, operations, and financial tracking.", align="C")
    
    pdf.ln(60)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 10, "Generated: July 2026", align="C")
    
    # --- Content Page 1 ---
    pdf.add_page()
    pdf.set_text_color(30, 41, 59) # Restore dark color
    pdf.ln(15) # Clear the header
    
    # Introduction / Purpose
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 10, "1. Product Purpose & Overview")
    pdf.ln(12)
    
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(51, 65, 85)
    purpose_text = (
        "Ranga Farms - Goat Farm Management System is a comprehensive, full-stack web application designed "
        "specifically to streamline, digitize, and optimize all aspects of managing professional goat farm operations. "
        "Built using a robust Flask backend, PostgreSQL database, and responsive Bootstrap interface, the system "
        "acts as a single point of truth for farm owners, managers, veterinarians, and workers.\n\n"
        "By replacing paper logbooks and fragmented spreadsheets, Ranga Farms provides automated tracking of "
        "livestock lifecycles, real-time financial health monitoring, granular HR and work logs, veterinary medicine "
        "inventory control, feed planning, and rich reporting dashboards."
    )
    pdf.multi_cell(0, 6, purpose_text)
    pdf.ln(10)
    
    # Core Architecture
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, "1.1 Technology Stack")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(51, 65, 85)
    
    tech_text = (
        "- Backend: Flask 3.0.0 (Python 3)\n"
        "- Database: PostgreSQL (with dynamic schema migration and connection pooling)\n"
        "- Frontend: HTML5, CSS3, JavaScript, Jinja2 template engine, Bootstrap UI\n"
        "- Authentication: Secure password hashing (Werkzeug) & OTP-based verification (pyotp)"
    )
    pdf.multi_cell(0, 6, tech_text)
    pdf.ln(10)
    
    # --- Content Page 2 ---
    pdf.add_page()
    pdf.ln(15)
    
    # Core Features
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 10, "2. Core Features & Functional Modules")
    pdf.ln(12)
    
    modules = [
        ("2.1 Livestock Management", 
         "- Goat Master Registry: Comprehensive records of each goat, including Tag IDs, breed, age, status, gender, and parents.\n"
         "- Kid Tracking: Monitors newborn goats, births, and parental lineage.\n"
         "- Breed Management: Cataloging different goat breeds.\n"
         "- Mortality Records: Accurate logging of deaths with causes for analysis."),
        
        ("2.2 Financial Management", 
         "- Profit & Loss (P&L): Real-time analysis of income and expenses.\n"
         "- Sales & Purchases: Detailed logging of buying/selling goats, feed, medicine, vaccines, and equipment.\n"
         "- Invoicing: Generating professional bills and invoice documents.\n"
         "- Recurring Expenses: Automating monthly utilities, rent, or scheduled payments."),
        
        ("2.3 Employee Directory & HR", 
         "- Directory: Detailed worker roles, contacts, and metadata.\n"
         "- Attendance & Leaves: Daily clock-in/out tracking and vacation requests.\n"
         "- Salary Management: Automating monthly/daily wage calculations and payslip exports.\n"
         "- Work Logs: Assigning and tracking daily tasks across the farm."),
         
        ("2.4 Health & Veterinary Care", 
         "- Medical Logs: Individual treatment history, symptoms, and outcomes.\n"
         "- Doctor Management: Directory of visiting vets and schedules.\n"
         "- Vaccine Schedule: Tracking upcoming and historical vaccinations.\n"
         "- Medicine Inventory: Tracking stock levels and alerts for low inventory.")
    ]
    
    for title, desc in modules:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, title)
        pdf.ln(8)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 5.5, desc)
        pdf.ln(4)

    # --- Content Page 3 ---
    pdf.add_page()
    pdf.ln(15)
    
    # System Workflow & New Features
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(79, 70, 229)
    pdf.cell(0, 10, "3. System Workflow & Recent Enhancements")
    pdf.ln(12)
    
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(51, 65, 85)
    workflow_text = (
        "The system is designed with a standard daily operational workflow:\n"
        "1. Authenticate: Users sign in using credentials and optional OTP secondary authentication.\n"
        "2. Actionable Dashboard: Displays immediate metrics: total goats, monthly profit/loss, active tasks, and recent alerts.\n"
        "3. Live Search & Operations: Operations teams search goats or log transactions directly from the top interface.\n\n"
        "Recently, two major usability enhancements were added to improve daily productivity:"
    )
    pdf.multi_cell(0, 6, workflow_text)
    pdf.ln(8)
    
    enhancements = [
        ("Weight Notification Alert (25 kg or More)",
         "To identify market-ready goats, the system automatically checks goat weights upon login. "
         "If any active goat has reached 25 kg or more, a sleek, modern popup modal alert displays on the user's first "
         "login of the day. The alert showcases the goat's Tag ID, weight, and color, and will not reappear for that user "
         "until the next day once dismissed."),
         
        ("Enhanced Tag ID Search (Last 4 Digits Support)",
         "Finding a specific goat is fast and intuitive. Users can search the directory or dashboard using "
         "only the last 4 digits of the Tag ID (e.g., searching '0101' will match full Tag ID 'UII1710000101'). "
         "The search intelligently distinguishes between 4-digit numeric patterns, breed names, and full Tag IDs.")
    ]
    
    for title, desc in enhancements:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, title)
        pdf.ln(8)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 5.5, desc)
        pdf.ln(4)
        
    pdf.output(filename)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_prd_pdf("Ranga_Farms_Product_Documentation.pdf")
