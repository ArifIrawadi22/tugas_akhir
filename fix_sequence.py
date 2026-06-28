from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# Jika dijalankan di lokal
if DATABASE_URL is None:
    DATABASE_URL = "postgresql://admin:jwOTsiolyq7fuDJOBBXJ65Yxd3VTiGSq@dpg-d90ib83eo5us73c44sm0-a.oregon-postgres.render.com/kosmetik"

engine = create_engine(DATABASE_URL)

tables = [
    "produk",
    "pesanan",
    "pesanan_item",
    "transaksi",
    "review"
]

with engine.begin() as conn:

    for tabel in tables:

        print(f"Memperbaiki {tabel}...")

        # buat sequence
        conn.execute(text(f"""
        CREATE SEQUENCE IF NOT EXISTS {tabel}_id_seq;
        """))

        # set default id
        conn.execute(text(f"""
        ALTER TABLE {tabel}
        ALTER COLUMN id
        SET DEFAULT nextval('{tabel}_id_seq');
        """))

        # sinkronkan sequence
        conn.execute(text(f"""
        SELECT setval(
            '{tabel}_id_seq',
            COALESCE((SELECT MAX(id) FROM {tabel}),1)
        );
        """))

        # jadikan NOT NULL
        conn.execute(text(f"""
        ALTER TABLE {tabel}
        ALTER COLUMN id
        SET NOT NULL;
        """))

print("================================")
print("SEMUA TABLE BERHASIL DIPERBAIKI")
print("================================")