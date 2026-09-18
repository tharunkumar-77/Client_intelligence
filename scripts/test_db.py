import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

try:
    conn = psycopg2.connect(user="ci_user", password=os.environ.get("CI_PASSWORD", "ci_password"), host="localhost", port="5432", dbname="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE ci_test;")
    print("Created ci_test db")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error creating db (may already exist): {e}")


from run import app
from app.extensions import db

print("Registered tables in SQLAlchemy:")
with app.app_context():
    print(list(db.metadata.tables.keys()))
