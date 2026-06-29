"""
==============================================
  APLIKASI USER / TOKO - Port 5002
  Jalankan: python app_user.py
  Buka: http://127.0.0.1:5002
==============================================
"""
from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'user_rahasia_2024')

# ── Database: PostgreSQL di Render, SQLite di lokal ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, '..', 'kosmetik.db')

DATABASE_URL = os.environ.get('DATABASE_URL', f'sqlite:///{DB_PATH}')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =====================
# MODEL DATABASE (sama persis dengan admin)
# =====================
class Produk(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    brand       = db.Column(db.String(100))
    nama        = db.Column(db.String(200))
    tipe        = db.Column(db.String(50))
    ukuran      = db.Column(db.String(50))
    harga       = db.Column(db.Float)
    stok        = db.Column(db.Integer, default=0)
    terjual     = db.Column(db.Integer, default=0)
    rating      = db.Column(db.Float, default=0)
    bpom_id     = db.Column(db.String(50))
    url         = db.Column(db.String(300))
    deskripsi   = db.Column(db.Text)
    ingredients = db.Column(db.Text)
    gambar      = db.Column(db.String(200))

class Pesanan(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    kode         = db.Column(db.String(30), unique=True)
    nama_pembeli = db.Column(db.String(100))
    email        = db.Column(db.String(100))
    no_hp        = db.Column(db.String(20))
    alamat       = db.Column(db.Text)
    total_harga  = db.Column(db.Float)
    status       = db.Column(db.String(20), default='Menunggu')
    status_bayar = db.Column(db.String(20), default='Belum Bayar')
    tanggal      = db.Column(db.String(30))
    metode_bayar = db.Column(db.String(50), default='')  # ← baru
    items        = db.relationship('PesananItem', backref='pesanan')

class PesananItem(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    pesanan_id = db.Column(db.Integer, db.ForeignKey('pesanan.id'))
    produk_id  = db.Column(db.Integer, db.ForeignKey('produk.id'))
    jumlah     = db.Column(db.Integer)
    harga_saat = db.Column(db.Float)
    produk     = db.relationship('Produk')


class Review(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    pesanan_id   = db.Column(db.Integer, db.ForeignKey('pesanan.id'))
    produk_id    = db.Column(db.Integer, db.ForeignKey('produk.id'))
    nama         = db.Column(db.String(100))
    rating       = db.Column(db.Integer)  # 1-5
    komentar     = db.Column(db.Text)
    tanggal      = db.Column(db.String(30))
    produk       = db.relationship('Produk', backref='reviews')
    pesanan      = db.relationship('Pesanan', backref='reviews')

# =====================
# ROUTES USER
# =====================

@app.route('/')
def index():
    return redirect('/katalog')

@app.route('/katalog')
def katalog():
    cari = request.args.get('cari','')
    tipe = request.args.get('tipe','')
    sort = request.args.get('sort','terlaris')
    query = Produk.query.filter()
    if cari: query = query.filter(Produk.nama.ilike(f'%{cari}%')|Produk.brand.ilike(f'%{cari}%'))
    if tipe: query = query.filter(Produk.tipe==tipe)
    if sort=='termurah': query = query.order_by(Produk.harga.asc())
    elif sort=='termahal': query = query.order_by(Produk.harga.desc())
    elif sort=='rating': query = query.order_by(Produk.rating.desc())
    else: query = query.order_by(Produk.terjual.desc())
    produk = query.all()
    tipe_list = [r[0] for r in db.session.query(func.distinct(Produk.tipe)).all()]
    return render_template('katalog.html', produk=produk,
                           tipe_list=tipe_list, cari=cari, tipe=tipe, sort=sort)

@app.route('/produk/<int:id>')
def detail(id):
    p = Produk.query.get_or_404(id)
    rekomendasi = Produk.query.filter(Produk.tipe==p.tipe, Produk.id!=p.id)\
                              .order_by(Produk.rating.desc()).limit(4).all()
    return render_template('detail.html', produk=p, rekomendasi=rekomendasi)


@app.route('/berhasil/<kode>')
def berhasil(kode):
    pesanan = Pesanan.query.filter_by(kode=kode).first_or_404()
    return render_template('berhasil.html', pesanan=pesanan)

@app.route('/cek-status-bayar/<kode>')
def cek_status_bayar(kode):
    """API untuk browser cek apakah admin sudah konfirmasi bayar"""
    pesanan = Pesanan.query.filter_by(kode=kode).first()
    if not pesanan:
        return jsonify({'sudah_bayar': False})
    return jsonify({'sudah_bayar': pesanan.status_bayar == 'Sudah Bayar'})

@app.route('/bayar/<kode>')
def bayar(kode):
    """Halaman selesaikan pembayaran — untuk transfer bank dan QRIS"""
    pesanan = Pesanan.query.filter_by(kode=kode).first_or_404()
    # Kalau sudah dibayar (admin konfirmasi), redirect ke berhasil
    if pesanan.status_bayar == 'Sudah Bayar':
        return redirect(f'/berhasil/{kode}')
    return render_template('bayar.html', pesanan=pesanan)

@app.route('/cek-pesanan', methods=['GET','POST'])
def cek_pesanan():
    pesanan = None
    if request.method == 'POST':
        kode = request.form.get('kode','').strip()
        pesanan = Pesanan.query.filter_by(kode=kode).first()
    return render_template('cek_pesanan.html', pesanan=pesanan)

@app.route('/api/produk')
def api_produk():
    """Endpoint Semantic Web JSON-LD"""
    produk = Produk.query.filter(Produk.stok > 0).all()
    items = [{"@type":"Product","@id":f"/produk/{p.id}","name":p.nama,
              "brand":{"@type":"Brand","name":p.brand},"category":p.tipe,
              "offers":{"@type":"Offer","price":p.harga,"priceCurrency":"IDR",
                        "availability":"https://schema.org/InStock"},
              "aggregateRating":{"@type":"AggregateRating","ratingValue":p.rating},
              "identifier":p.bpom_id} for p in produk]
    return jsonify({"@context":"https://schema.org","@type":"ItemList",
                    "name":"Katalog Kosmetik","numberOfItems":len(items),
                    "itemListElement":items})


@app.route('/rating/<kode>', methods=['GET','POST'])
def beri_rating(kode):
    pesanan = Pesanan.query.filter_by(kode=kode).first_or_404()
    if pesanan.status != 'Selesai':
        return redirect(f'/cek-pesanan')

    sudah = Review.query.filter_by(pesanan_id=pesanan.id).first()

    if request.method == 'POST' and not sudah:
        # ── SEBELUM: satu rating/komentar untuk semua produk ──
        # ── SESUDAH: tiap produk punya rating & komentar sendiri ──
        for item in pesanan.items:
            pid = item.produk_id
            # Ambil rating & komentar per produk dari form
            rating_val  = int(request.form.get(f'rating_{pid}', 5))
            komentar_val = request.form.get(f'komentar_{pid}', '').strip()
            if not komentar_val:
                continue  # skip produk yang tidak diisi

            rv = Review(
                pesanan_id=pesanan.id,
                produk_id=pid,
                nama=pesanan.nama_pembeli,
                rating=rating_val,
                komentar=komentar_val,
                tanggal=datetime.now().strftime('%d %b %Y')
            )
            db.session.add(rv)

            # Update rata-rata rating produk
            p = item.produk
            if p:
                semua_review = Review.query.filter_by(produk_id=p.id).all()
                total_r  = sum(r.rating for r in semua_review) + rating_val
                jumlah_r = len(semua_review) + 1
                p.rating = round(total_r / jumlah_r, 1)

        db.session.commit()
        return redirect(f'/rating/{kode}?sukses=1')

    return render_template('rating.html', pesanan=pesanan,
                           sudah=sudah, sukses=request.args.get('sukses'))
    
@app.route('/static/uploads/<filename>')
def gambar_produk(filename):
    """Serve gambar produk dari folder admin (database & gambar dibagi bersama)"""
    from flask import send_from_directory
    folder_gambar = os.path.join(BASE_DIR, '..', 'admin', 'static', 'uploads')
    return send_from_directory(folder_gambar, filename)
# ============================================================
# Tambahkan route ini ke app_user.py
# Letakkan setelah route /cek-pesanan yang sudah ada
# ============================================================

@app.route('/keranjang')
def keranjang():
    """Halaman keranjang belanja (data disimpan di localStorage browser)"""
    return render_template('keranjang.html')

@app.route('/checkout')
def checkout():
    """
    Halaman checkout multi-produk.
    Data produk dibaca dari sessionStorage browser (dikirim oleh keranjang.html).
    Route ini hanya merender template; logika cart ada di JS (checkout.html).
    """
    return render_template('checkout.html')

# ============================================================
# OPSIONAL — jika nanti mau checkout multi-produk dari keranjang
# Data dikirim via POST (JSON) dari JavaScript
# ============================================================

from flask import session

@app.route('/checkout-keranjang', methods=['POST'])
def checkout_keranjang():
    """
    Terima data keranjang dari JS, buat satu Pesanan dengan banyak item.
    Dipanggil dari keranjang.html ketika tombol 'Lanjut ke Pembayaran' diklik
    dan keranjang berisi lebih dari 1 jenis produk.
    """
    from flask import request as req
    data = req.get_json()
    if not data:
        return jsonify({'ok': False, 'pesan': 'Data kosong'}), 400

    items        = data.get('items', [])
    nama         = data.get('nama_pembeli', '').strip()
    email        = data.get('email', '').strip()
    no_hp        = data.get('no_hp', '').strip()
    alamat       = data.get('alamat', '').strip()
    metode_bayar = data.get('metode_bayar', '').strip()

    if not items or not nama or not alamat:
        return jsonify({'ok': False, 'pesan': 'Lengkapi data pembeli'}), 400

    total = 0
    kode  = f"PSN{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    is_cod = metode_bayar == 'Bayar di Tempat (COD)'

    pesanan = Pesanan(
        kode=kode,
        nama_pembeli=nama,
        email=email,
        no_hp=no_hp,
        alamat=alamat,
        total_harga=0,
        status='Menunggu',
        metode_bayar=metode_bayar,
        status_bayar='Sudah Bayar' if is_cod else 'Belum Bayar',
        tanggal=datetime.now().strftime('%d %b %Y %H:%M')
    )
    db.session.add(pesanan)
    db.session.flush()

    for item in items:
        p = Produk.query.get(item['id'])
        if not p:
            continue
        qty = int(item.get('qty', 1))
        if qty > p.stok:
            db.session.rollback()
            return jsonify({'ok': False, 'pesan': f'Stok {p.nama} tidak mencukupi'}), 400
        pi = PesananItem(pesanan_id=pesanan.id, produk_id=p.id,
                         jumlah=qty, harga_saat=p.harga)
        db.session.add(pi)
        p.stok    -= qty
        p.terjual += qty
        total     += qty * p.harga

    pesanan.total_harga = total
    db.session.commit()
    
    # COD → langsung berhasil, Transfer/QRIS → halaman bayar
    if is_cod:
        return jsonify({'ok': True, 'kode': kode, 'redirect': f'/berhasil/{kode}'})
    else:
        return jsonify({'ok': True, 'kode': kode, 'redirect': f'/bayar/{kode}'})
    
@app.route('/beli/<int:id>', methods=['GET','POST'])
def beli(id):
    p = Produk.query.get_or_404(id)

    if request.method == 'POST':

        # ==================================================
        # MODE 1: SINGLE ITEM (default sekarang)
        # ==================================================
        qty = int(request.form.get('jumlah', 1))

        if qty > p.stok:
            return render_template('beli.html', produk=p, error='Stok tidak mencukupi!')

        total = qty * p.harga

        # ==================================================
        # CREATE PESANAN
        # ==================================================
        kode = f"PSN{datetime.now().strftime('%Y%m%d%H%M%S')}"

        pesanan = Pesanan(
            kode=kode,
            nama_pembeli=request.form['nama_pembeli'],
            email=request.form['email'],
            no_hp=request.form['no_hp'],
            alamat=request.form['alamat'],
            total_harga=total,
            status='Menunggu',
            metode_bayar=request.form.get('metode_bayar',''),
            tanggal=datetime.now().strftime('%d %b %Y %H:%M')
        )

        db.session.add(pesanan)
        db.session.flush()

        # item tunggal
        item = PesananItem(
            pesanan_id=pesanan.id,
            produk_id=p.id,
            jumlah=qty,
            harga_saat=p.harga
        )
        db.session.add(item)

        p.stok -= qty
        p.terjual += qty

        db.session.commit()
        metode = request.form.get('metode_bayar', '')
        if metode == 'Bayar di Tempat (COD)':
            return redirect(f'/berhasil/{pesanan.kode}')   # COD → langsung berhasil
        else:
            return redirect(f'/bayar/{pesanan.kode}')       # Transfer/QRIS → halaman bayar

    return render_template('beli.html', produk=p, error='')

def migrasi_otomatis():
    """Tambah kolom baru ke database lama yang belum punya"""
    import sqlalchemy as sa
    inspector = sa.inspect(db.engine)
    # Kolom gambar di tabel produk
    if 'produk' in inspector.get_table_names():
        kolom_ada = [c['name'] for c in inspector.get_columns('produk')]
        if 'gambar' not in kolom_ada:
            with db.engine.connect() as conn:
                conn.execute(sa.text('ALTER TABLE produk ADD COLUMN gambar VARCHAR(200)'))
                conn.commit()
            print("✅ Migrasi: kolom 'gambar' ditambahkan")
    # Kolom metode_bayar di tabel pesanan
    if 'pesanan' in inspector.get_table_names():
        kolom_ada = [c['name'] for c in inspector.get_columns('pesanan')]
        if 'metode_bayar' not in kolom_ada:
            with db.engine.connect() as conn:
                conn.execute(sa.text("ALTER TABLE pesanan ADD COLUMN metode_bayar VARCHAR(50) DEFAULT ''"))
                conn.commit()
            print("✅ Migrasi: kolom 'metode_bayar' ditambahkan")
        if 'status_bayar' not in kolom_ada:
            with db.engine.connect() as conn:
                conn.execute(sa.text("ALTER TABLE pesanan ADD COLUMN status_bayar VARCHAR(20) DEFAULT 'Belum Bayar'"))
                conn.commit()
            print("✅ Migrasi: kolom 'status_bayar' ditambahkan")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        migrasi_otomatis()
    print("=" * 45)
    print("  TOKO USER berjalan di port 5002")
    print("  Buka: http://127.0.0.1:5002")
    print("=" * 45)
    app.run(debug=True, port=5002)
