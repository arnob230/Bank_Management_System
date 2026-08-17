# Arnob Special Bank

A full-stack bank management system.

- **Frontend:** HTML / CSS / vanilla JS, served by a Node.js (Express) server that also proxies API calls
- **Backend:** Python (Flask) REST API
- **Database:** MySQL

## Features
- Customer signup/login (JWT auth, bcrypt password hashing)
- Multiple accounts per customer (savings / current)
- Deposit, withdraw, transfer — with row-level locking (`SELECT ... FOR UPDATE`) so concurrent transactions can't corrupt a balance, and full DB transactions (commit/rollback) so a transfer never leaves money "half-moved"
- Immutable transaction ledger with reference IDs
- Loan applications with reducing-balance EMI calculator (live preview)
- Admin console: bank-wide stats, customer search, freeze/unfreeze accounts, approve/reject loans
- Audit log of every sensitive action

## Project structure
```
arnob-bank/
├── backend/              # Python Flask API
│   ├── app.py            # entry point
│   ├── config.py
│   ├── db.py              # MySQL connection pool
│   ├── auth.py            # register/login, JWT
│   ├── accounts.py        # deposit/withdraw/transfer, history
│   ├── loans.py           # loan apply + EMI calculator
│   ├── admin.py           # admin stats, customers, loan decisions
│   ├── schema.sql         # MySQL schema
│   ├── requirements.txt
│   └── .env.example
└── frontend/              # Node/Express + static site
    ├── server.js          # serves /public, proxies /api → Flask
    ├── package.json
    └── public/
        ├── index.html      # login
        ├── register.html
        ├── dashboard.html
        ├── transactions.html
        ├── loans.html
        ├── admin.html
        ├── css/style.css
        └── js/*.js
```

## Setup

### 1. Database
```bash
mysql -u root -p < backend/schema.sql
```

### 2. Backend (Python)
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then edit .env with your MySQL password + a real JWT_SECRET
python app.py                   # runs on http://localhost:5000
```

### 3. Frontend (Node)
```bash
cd frontend
npm install
npm start                       # runs on http://localhost:3000
```

Open **http://localhost:3000** — that's the whole app. The Node server proxies every `/api/*` request to the Flask backend, so the browser only ever talks to one origin.

### First account
There's no seeded admin — sign up as a normal customer at `/register.html`, then promote that user to admin directly in MySQL:
```sql
UPDATE users SET role = 'admin' WHERE email = 'you@example.com';
```
Log out and back in; you'll land on the admin console instead of the customer dashboard.

## Design notes
The visual language is a "heritage ledger" theme built for the brand: deep ink-forest surfaces, a brass accent, a serif display face (Fraunces) for trust, and tabular mono numerals (IBM Plex Mono) for money so figures always align. The signature element is the **ledger card** — an embossed, passbook-style balance panel with an "ASB" wax-seal monogram as the recurring brand mark.

## Extending this
- Statement PDF export (there's a `pdf` skill available if you're building this with Claude)
- 2FA on login and high-value transfers
- Interest accrual as a scheduled job
- Fixed-deposit maturity handling
