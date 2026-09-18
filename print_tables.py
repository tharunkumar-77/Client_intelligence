import psycopg2

import os
import psycopg2

try:
    db_url = os.environ.get("DATABASE_URL", "postgresql://ci_user:ci_password@127.0.0.1:5432/client_intelligence")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    print("TABLES IN DB:")
    for row in cursor.fetchall():
        print(" -", row[0])
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error checking db: {e}")
