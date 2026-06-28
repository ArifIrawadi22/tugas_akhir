import sqlite3
import psycopg2

# SQLite
sqlite_conn = sqlite3.connect("kosmetik.db")
sqlite_conn.row_factory = sqlite3.Row
sqlite_cur = sqlite_conn.cursor()

# PostgreSQL
pg_conn = psycopg2.connect(
    host="dpg-d90ib83eo5us73c44sm0-a",
    database="kosmetik",
    user="admin",
    password="jwOTsiolyq7fuDJOBBXJ65Yxd3VTiGSq",
    port=5432
)

pg_cur = pg_conn.cursor()

tables = [
    "produk",
    "pesanan",
    "transaksi",
    "pesanan_item",
    "review"
]

for table in tables:

    sqlite_cur.execute(f"SELECT * FROM {table}")
    rows = sqlite_cur.fetchall()

    if not rows:
        continue

    cols = rows[0].keys()

    col_string = ",".join(cols)
    place = ",".join(["%s"] * len(cols))

    sql = f"""
    INSERT INTO {table}
    ({col_string})
    VALUES ({place})
    """

    for row in rows:
        pg_cur.execute(sql, tuple(row))

    pg_conn.commit()

    print(f"{table} selesai ({len(rows)} data)")

sqlite_conn.close()
pg_conn.close()

print("Migrasi selesai")