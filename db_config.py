import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "hospital"),
    "port": int(os.getenv("DB_PORT", 3306))
}

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="hospital_pool",
    pool_size=5,
    pool_reset_session=True,
    **DB_CONFIG
)

def get_db():
    return connection_pool.get_connection()
