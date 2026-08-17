-- =========================================================
-- Arnob Special Bank — SQLite / SQLCipher Database Schema
-- =========================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------
-- Users
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    password_hash TEXT NOT NULL,

    role TEXT NOT NULL DEFAULT 'customer'
        CHECK (role IN ('customer', 'teller', 'admin')),

    national_id TEXT,
    address TEXT,

    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'frozen', 'closed')),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ---------------------------------------------------------
-- Accounts
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    account_number TEXT NOT NULL UNIQUE,

    user_id INTEGER NOT NULL,

    account_type TEXT NOT NULL DEFAULT 'savings'
        CHECK (
            account_type IN (
                'savings',
                'current',
                'fixed_deposit'
            )
        ),

    balance NUMERIC NOT NULL DEFAULT 0.00,
    interest_rate NUMERIC NOT NULL DEFAULT 3.50,
    min_balance NUMERIC NOT NULL DEFAULT 500.00,

    status TEXT NOT NULL DEFAULT 'active'
        CHECK (
            status IN (
                'active',
                'frozen',
                'closed'
            )
        ),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_accounts_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- ---------------------------------------------------------
-- Transactions
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    ref_id TEXT NOT NULL UNIQUE,

    account_id INTEGER NOT NULL,

    related_account_id INTEGER,

    type TEXT NOT NULL
        CHECK (
            type IN (
                'deposit',
                'withdraw',
                'transfer_in',
                'transfer_out'
            )
        ),

    amount NUMERIC NOT NULL,

    balance_after NUMERIC NOT NULL,

    note TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_txn_account
        FOREIGN KEY (account_id)
        REFERENCES accounts(id),

    CONSTRAINT fk_txn_related
        FOREIGN KEY (related_account_id)
        REFERENCES accounts(id)
);


-- ---------------------------------------------------------
-- Loans
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS loans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    user_id INTEGER NOT NULL,

    amount NUMERIC NOT NULL,

    interest_rate NUMERIC NOT NULL DEFAULT 9.00,

    term_months INTEGER NOT NULL,

    monthly_emi NUMERIC NOT NULL,

    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (
            status IN (
                'pending',
                'approved',
                'rejected',
                'closed'
            )
        ),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_loans_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
);


-- ---------------------------------------------------------
-- Audit Logs
-- ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    actor_id INTEGER,

    action TEXT NOT NULL,

    target TEXT,

    details TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);