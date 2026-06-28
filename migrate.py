import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise Exception("DATABASE_URL belum ada.")

sqlite_db = "kosmetik.db"

sqlite_conn = sqlite3.connect(sqlite_db)

postgres_engine = create_engine(DATABASE_URL)

tables = [
    "produk",
    "transaksi",
    "pesanan",
    "pesanan_item",
    "review"
]

for table in tables:

    print(f"Memindahkan {table}...")

    df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)

    df.to_sql(
        table,
        postgres_engine,
        if_exists="replace",
        index=False
    )

    print(f"{table} selesai ({len(df)} data)")

sqlite_conn.close()

print("===================================")
print("MIGRASI BERHASIL")
print("===================================")