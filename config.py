import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "arnob_bank")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))

    JWT_SECRET = os.getenv("JWT_SECRET", "change-this-secret-in-production")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "12"))

    DAILY_WITHDRAW_LIMIT = 50000.00
    DAILY_TRANSFER_LIMIT = 200000.00
