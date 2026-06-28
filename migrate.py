import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

# =====================================================
# KONFIGURASI
# =====================================================

# File SQLite
SQLITE_DB = "kosmetik.db"

# Ganti dengan External Database URL dari Render
POSTGRES_URL = "postgresql://admin:jwOTsiolyq7fuDJOBBXJ65Yxd3VTiGSq@dpg-d90ib83eo5us73c44sm0-a.oregon-postgres.render.com/kosmetik"

# =====================================================

print("=" * 70)
print("MIGRASI SQLITE -> POSTGRESQL")
print("=" * 70)

# ===============================
# Cek file SQLite
# ===============================

print("\nLokasi SQLite :")
print(os.path.abspath(SQLITE_DB))

if not os.path.exists(SQLITE_DB):
    print("\nERROR : File SQLite tidak ditemukan!")
    exit()

sqlite_conn = sqlite3.connect(SQLITE_DB)

# ===============================
# PostgreSQL
# ===============================

pg_engine = create_engine(POSTGRES_URL)

# ===============================
# Daftar tabel SQLite
# ===============================

tables = pd.read_sql("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name NOT LIKE 'sqlite_%'
""", sqlite_conn)

print("\nTabel ditemukan:")
print(tables)

# ===============================
# Kosongkan PostgreSQL
# ===============================

print("\nMenghapus data lama PostgreSQL...")

try:
    with pg_engine.begin() as conn:

        conn.execute(text("""
        TRUNCATE TABLE
        review,
        pesanan_item,
        transaksi,
        pesanan,
        produk
        RESTART IDENTITY CASCADE;
        """))

    print("Berhasil menghapus data lama.\n")

except Exception as e:
    print("Tidak bisa TRUNCATE (kemungkinan tabel masih kosong).")
    print(e)

# ===============================
# Urutan Migrasi
# ===============================

urutan = [
    "produk",
    "pesanan",
    "transaksi",
    "pesanan_item",
    "review"
]

# ===============================
# Migrasi
# ===============================

for tabel in urutan:

    if tabel not in tables["name"].values:
        print(f"\nLewati {tabel} (tidak ada)")
        continue

    print("=" * 60)
    print("Migrasi :", tabel)

    df = pd.read_sql(f"SELECT * FROM {tabel}", sqlite_conn)

    print("Jumlah data :", len(df))

    if len(df) == 0:
        print("Tidak ada data.")
        continue

    try:

        df.to_sql(
            tabel,
            pg_engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=500
        )

        print("✓ Berhasil")

    except Exception as e:

        print("✗ Gagal")
        print(e)
        break

sqlite_conn.close()

print("\n")
print("=" * 70)
print("MIGRASI SELESAI")
print("=" * 70)