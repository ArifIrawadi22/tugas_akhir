"""
Script ini dijalankan SEKALI saat pertama kali deploy ke Render.
Fungsinya: buat semua tabel + import data dari data_export.json

Cara kerja:
- Render menjalankan ini lewat Build Command sebelum app jalan
- Kalau tabel sudah ada dan sudah terisi, script ini skip (tidak duplikat)
"""
import os, json, sys

# Setup Flask app context
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_admin import app, db, Produk, Transaksi, Pesanan, PesananItem, Review
from datetime import datetime

def import_dari_json():
    json_path = os.path.join(os.path.dirname(__file__), '..', 'data_export.json')

    if not os.path.exists(json_path):
        print("⚠️  data_export.json tidak ditemukan, skip import.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with app.app_context():
        # Buat semua tabel
        db.create_all()
        print("✅ Tabel berhasil dibuat")

        # ── Import Produk ──
        if Produk.query.count() == 0:
            for row in data.get('produk', []):
                p = Produk(
                    id          = row['id'],
                    brand       = row.get('brand',''),
                    nama        = row.get('nama',''),
                    tipe        = row.get('tipe',''),
                    ukuran      = row.get('ukuran',''),
                    harga       = float(row.get('harga', 0)),
                    stok        = int(row.get('stok', 0)),
                    terjual     = int(row.get('terjual', 0)),
                    rating      = float(row.get('rating', 0)),
                    bpom_id     = row.get('bpom_id',''),
                    url         = row.get('url',''),
                    deskripsi   = row.get('deskripsi',''),
                    ingredients = row.get('ingredients',''),
                    gambar      = row.get('gambar','')
                )
                db.session.add(p)
            db.session.commit()
            print(f"✅ Produk: {Produk.query.count()} baris diimport")
        else:
            print(f"⏩ Produk sudah ada ({Produk.query.count()} baris), skip")

        # ── Import Transaksi ──
        if Transaksi.query.count() == 0:
            for row in data.get('transaksi', []):
                t = Transaksi(
                    id        = row['id'],
                    produk_id = row['produk_id'],
                    jumlah    = int(row.get('jumlah', 0)),
                    total     = float(row.get('total', 0)),
                    tanggal   = row.get('tanggal','')
                )
                db.session.add(t)
            db.session.commit()
            print(f"✅ Transaksi: {Transaksi.query.count()} baris diimport")
        else:
            print(f"⏩ Transaksi sudah ada, skip")

        # ── Import Pesanan ──
        if Pesanan.query.count() == 0:
            for row in data.get('pesanan', []):
                p = Pesanan(
                    id           = row['id'],
                    kode         = row.get('kode',''),
                    nama_pembeli = row.get('nama_pembeli',''),
                    email        = row.get('email',''),
                    no_hp        = row.get('no_hp',''),
                    alamat       = row.get('alamat',''),
                    total_harga  = float(row.get('total_harga', 0)),
                    status       = row.get('status','Menunggu'),
                    status_bayar = row.get('status_bayar','Belum Bayar'),
                    tanggal      = row.get('tanggal',''),
                    metode_bayar = row.get('metode_bayar','')
                )
                db.session.add(p)
            db.session.commit()
            print(f"✅ Pesanan: {Pesanan.query.count()} baris diimport")
        else:
            print(f"⏩ Pesanan sudah ada, skip")

        # ── Import PesananItem ──
        if PesananItem.query.count() == 0:
            for row in data.get('pesanan_item', []):
                pi = PesananItem(
                    id         = row['id'],
                    pesanan_id = row['pesanan_id'],
                    produk_id  = row['produk_id'],
                    jumlah     = int(row.get('jumlah', 0)),
                    harga_saat = float(row.get('harga_saat', 0))
                )
                db.session.add(pi)
            db.session.commit()
            print(f"✅ PesananItem: {PesananItem.query.count()} baris diimport")
        else:
            print(f"⏩ PesananItem sudah ada, skip")

        # ── Import Review ──
        if Review.query.count() == 0:
            for row in data.get('review', []):
                r = Review(
                    id         = row['id'],
                    pesanan_id = row.get('pesanan_id'),
                    produk_id  = row.get('produk_id'),
                    nama       = row.get('nama',''),
                    rating     = int(row.get('rating', 5)),
                    komentar   = row.get('komentar',''),
                    tanggal    = row.get('tanggal','')
                )
                db.session.add(r)
            db.session.commit()
            print(f"✅ Review: {Review.query.count()} baris diimport")
        else:
            print(f"⏩ Review sudah ada, skip")

    print("\n🎉 Import selesai! Semua data sudah masuk ke PostgreSQL.")

if __name__ == '__main__':
    import_dari_json()
