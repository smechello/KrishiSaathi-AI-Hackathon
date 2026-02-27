#!/usr/bin/env python3
"""One-time script: create the 'krishisaathi' database on RDS if it doesn't exist,
then verify the app tables can be created."""
import psycopg2, os, sys

HOST = os.getenv("RDS_HOST", "krishisaathidb.cfi2y6ow42zi.ap-south-1.rds.amazonaws.com")
PORT = int(os.getenv("RDS_PORT", "5432"))
USER = os.getenv("RDS_USER", "postgres")
PASS = os.getenv("RDS_PASSWORD", os.getenv("DB_PASSWORD", ""))
DBNAME = os.getenv("RDS_DBNAME", "krishisaathi")

def main():
    # Step 1: connect to default 'postgres' database
    print(f"Connecting to RDS at {HOST}:{PORT} as {USER} ...")
    conn = psycopg2.connect(
        host=HOST, port=PORT, dbname="postgres",
        user=USER, password=PASS, sslmode="require", connect_timeout=10,
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT version()")
    print(f"  PostgreSQL: {cur.fetchone()[0][:80]}")

    # Step 2: create target database if missing
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DBNAME,))
    if cur.fetchone():
        print(f"  Database '{DBNAME}' already exists.")
    else:
        print(f"  Creating database '{DBNAME}' ...")
        cur.execute(f'CREATE DATABASE "{DBNAME}"')
        print(f"  Database '{DBNAME}' created!")
    cur.close()
    conn.close()

    # Step 3: Connect to the new database & verify
    print(f"\nConnecting to '{DBNAME}' database ...")
    conn2 = psycopg2.connect(
        host=HOST, port=PORT, dbname=DBNAME,
        user=USER, password=PASS, sslmode="require", connect_timeout=10,
    )
    conn2.autocommit = True
    cur2 = conn2.cursor()
    cur2.execute("SELECT current_database()")
    print(f"  Connected to: {cur2.fetchone()[0]}")
    cur2.close()
    conn2.close()

    print("\n✅ RDS setup complete! Database is ready.")

if __name__ == "__main__":
    main()
