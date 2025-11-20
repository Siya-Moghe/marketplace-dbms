# Marketplace-DBMS  
A database-driven e-commerce marketplace web application built using **Python (Flask)** and a relational **DBMS**.  
This project demonstrates end-to-end integration of web routes, HTML templates, and robust SQL features (triggers, functions, procedures, and schema creation).

---

## Overview

Marketplace-DBMS simulates a simple but complete online marketplace where users can:

- Register and log in  
- Browse and view products  
- Add products to their shopping cart  
- Proceed through checkout & payment  
- Place orders and view order history  

The database layer includes full SQL scripts defining:

- Table schemas  
- Triggers  
- Functions / stored procedures  
- Sample data  

---

## Features

### User System
- User registration & sign-in  
- Password validation  
- Session-based login  

### Marketplace
- Browse available products  
- Product detail pages  
- Add/remove items from the cart  

### Orders & Payments
- Checkout flow  
- Payment simulation  
- Order placement  
- View order details  
- Complete order history  

### SQL Database Layer  
Included SQL scripts define:

- Tables with proper relations  
- Triggers for maintaining consistency  
- Stored functions  
- Stored procedures  
- Test/sample data  

---

## Tech Stack

| Layer | Technology |
|------|------------|
| **Backend** | Python, Flask |
| **Frontend** | HTML, CSS, Jinja2 templates |
| **Database** | MySQL / MariaDB |
| **Other** | pip, npm |

---

## Project Structure
```
backend/
│
├── routes/                  # All Flask route handlers
│   ├── auth.py              # Login, registration
│   ├── cart.py              # Cart operations
│   ├── customers.py         # Customer-related endpoints
│   ├── orders.py            # Order placement & viewing
│   ├── payments.py          # Payment processing
│   └── products.py          # Product listing/management
│
├── static/                  # Frontend static files
│   ├── css/
│   └── imgs/
│
├── templates/               # HTML templates
│   ├── base.html
│   ├── home.html
│   ├── login.html
│   ├── register.html
│   ├── products.html
│   ├── cart.html
│   ├── checkout.html
│   ├── orders.html
│   ├── order_details.html
│   └── pay.html
│
├── app.py                   # Flask entry point
├── db.py                    # DB connection/config logic
├── config.py                # Environment/config variables
├── requirements.txt         # Python dependencies
└── retail_store.txt         # SQL schema, triggers, functions
```

## Getting Started

### Prerequisites
Make sure you have:
- Python **3.8+**  
- MySQL 
- pip  

---

### Installation

```bash
git clone https://github.com/Siya-Moghe/marketplace-dbms.git
cd marketplace-dbms/backend
pip install -r requirements.txt
```

## Database Setup
To set up the database, simply run the included SQL file.
1. Open your MySQL client.
2. Run the following command to execute the full database script:
```sql
SOURCE marketplace.sql;
```

This will automatically:
Drop the existing Retail_Store database (if it exists)
Create a new Retail_Store database
Create all tables
Insert any required data
Create triggers, functions, and procedures
No other database setup steps are required.


## Running the Application
After installing dependencies and setting up the database, from inside the backend directory run:
```bash
python app.py
```
By default, the application runs on:
```cpp
http://127.0.0.1:5000/
```

## Configuration
Update the following values inside backend/config.py:
```
DB_HOST = "localhost"
DB_USER = "your_mysql_username"
DB_PASSWORD = "your_mysql_password"
DB_NAME = "Retail_Store"
```
























