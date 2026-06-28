import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

# ============================
# KONFIGURASI
# ============================

# File SQLite
SQLITE_DB = "kosmetik.db"

# Ganti dengan External Database URL dari Render
POSTGRES_URL = "postgresql://admin:jwOTsiolyq7fuDJOBBXJ65Yxd3VTiGSq@dpg-d90ib83eo5us73c44sm0-a.oregon-postgres.render.com/kosmetik"

# ============================

print("=" * 60)
print("MIGRASI SQLITE -> POSTGRESQL")
print("=" * 60)

# koneksi sqlite
sqlite_conn = sqlite3.connect(SQLITE_DB)

# koneksi postgres
pg_engine = create_engine(POSTGRES_URL)

# ambil semua tabel sqlite
tables = pd.read_sql("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name NOT LIKE 'sqlite_%'
""", sqlite_conn)

print("\nTabel ditemukan:")
print(tables)

for table in tables["name"]:

    print(f"\nMigrasi tabel : {table}")

    try:

        df = pd.read_sql(f"SELECT * FROM {table}", sqlite_conn)

        print(f"Jumlah data : {len(df)}")

        df.to_sql(
            table,
            pg_engine,
            if_exists="replace",
            index=False
        )

        print("Berhasil")

    except Exception as e:

        print("Gagal")
        print(e)

print("\nMigrasi selesai.")

# ============================
# UPDATE SEQUENCE POSTGRES
# ============================

with pg_engine.begin() as conn:

    for table in tables["name"]:

        try:

            cols = pd.read_sql(
                f"SELECT * FROM {table} LIMIT 1",
                sqlite_conn
            ).columns

            if "id" in cols:

                conn.execute(text(f"""
                SELECT setval(
                    pg_get_serial_sequence('{table}','id'),
                    COALESCE(MAX(id),1)
                )
                FROM {table};
                """))

                print(f"Sequence {table} diperbaiki.")

        except:
            pass

sqlite_conn.close()

print("=" * 60)
print("SELESAI")
print("=" * 60)