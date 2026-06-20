"""
==============================================
  APLIKASI ADMIN - Port 5001
  Jalankan: python app_admin.py
  Buka: http://127.0.0.1:5001
==============================================
"""
from flask import Flask, render_template, request, redirect, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import pandas as pd
import numpy as np
import os, io
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'admin_rahasia_2024'
# Database SAMA — pakai path absolut agar admin & user baca DB yang sama
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, '..', 'kosmetik.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# =====================
# MODEL DATABASE (sama dengan user)
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

class Transaksi(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    produk_id  = db.Column(db.Integer, db.ForeignKey('produk.id'))
    jumlah     = db.Column(db.Integer)
    total      = db.Column(db.Float)
    tanggal    = db.Column(db.String(20))
    produk     = db.relationship('Produk', backref='transaksi')

class Pesanan(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    kode         = db.Column(db.String(30), unique=True)
    nama_pembeli = db.Column(db.String(100))
    email        = db.Column(db.String(100))
    no_hp        = db.Column(db.String(20))
    alamat       = db.Column(db.Text)
    total_harga  = db.Column(db.Float)
    status       = db.Column(db.String(20), default='Menunggu')
    tanggal      = db.Column(db.String(30))
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
    rating       = db.Column(db.Integer)
    komentar     = db.Column(db.Text)
    tanggal      = db.Column(db.String(30))
    produk       = db.relationship('Produk', backref='reviews')
    pesanan      = db.relationship('Pesanan', backref='reviews')

# =====================
# IMPORT DATASET
# =====================
def import_dataset():
    if Produk.query.count() > 0:
        return
    path = os.path.join(BASE_DIR, '..', 'Product_Kosmetic.xlsx')
    if not os.path.exists(path):
        return
    df = pd.read_excel(path)
    np.random.seed(42)
    for _, row in df.iterrows():
        p = Produk(
            brand=str(row.get('brand','')), nama=str(row.get('product_name','')),
            tipe=str(row.get('product_type','')), ukuran=str(row.get('size','')),
            harga=float(row.get('normal_price',0)),
            stok=int(np.random.randint(10,100)), terjual=int(np.random.randint(5,80)),
            rating=round(float(np.random.uniform(3.5,5.0)),1),
            bpom_id=str(row.get('bpom_id','')), url=str(row.get('product_url','')),
            deskripsi=str(row.get('description_product','')),
            ingredients=str(row.get('ingredients_list',''))
        )
        db.session.add(p)
    db.session.commit()
    import random
    produk_list = Produk.query.all()
    # =====================
    # TRANSAKSI 2024
    # =====================

    bulan_2024 = [
        '2024-01','2024-02','2024-03','2024-04',
        '2024-05','2024-06','2024-07','2024-08',
        '2024-09','2024-10','2024-11','2024-12'
    ]

    for bulan in bulan_2024:
        for _ in range(random.randint(15,30)):

            p = random.choice(produk_list)
            qty = random.randint(1,5)

            db.session.add(
                Transaksi(
                    produk_id=p.id,
                    jumlah=qty,
                    total=qty * p.harga,
                    tanggal=bulan
                )
            )

    # =====================
    # TRANSAKSI 2025
    # =====================

    bulan_2025 = [
        '2025-01','2025-02','2025-03','2025-04',
        '2025-05','2025-06','2025-07','2025-08',
        '2025-09','2025-10','2025-11','2025-12'
    ]

    for bulan in bulan_2025:
        for _ in range(random.randint(20,40)):

            p = random.choice(produk_list)
            qty = random.randint(1,7)

            db.session.add(
                Transaksi(
                    produk_id=p.id,
                    jumlah=qty,
                    total=qty * p.harga,
                    tanggal=bulan
                )
            )

    # =====================
    # TRANSAKSI 2026
    # =====================

    bulan_2026 = [
        '2026-01',
        '2026-02',
        '2026-03',
        '2026-04',
        '2026-05'
    ]

    for bulan in bulan_2026:
        for _ in range(random.randint(10,25)):

            p = random.choice(produk_list)
            qty = random.randint(1,4)

            db.session.add(
                Transaksi(
                    produk_id=p.id,
                    jumlah=qty,
                    total=qty * p.harga,
                    tanggal=bulan
                )
            )

    db.session.commit()

def cek_login():
    return session.get('login', False)

# =====================
# ROUTES ADMIN
# =====================

@app.route('/', methods=['GET','POST'])
def login():
    error = ''
    if request.method == 'POST':
        if request.form.get('username')=='admin' and request.form.get('password')=='admin123':
            session['login'] = True
            return redirect('/dashboard')
        error = 'Username atau password salah!'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

@app.route('/dashboard')
def dashboard():
    if not cek_login():
        return redirect('/')

    tahun = request.args.get('tahun', '2024')

    total_produk  = Produk.query.count()

    total_brand   = db.session.query(
        func.count(func.distinct(Produk.brand))
    ).scalar()

    total_terjual = db.session.query(
        func.sum(Produk.terjual)
    ).scalar() or 0

    if tahun in ['2024', '2025']:
  
        total_omzet = db.session.query(
            func.sum(Transaksi.total)
        ).filter(
            Transaksi.tanggal.like(f'{tahun}-%')
        ).scalar() or 0

    else:

        omzet_dummy = db.session.query(
            func.sum(Transaksi.total)
        ).filter(
            Transaksi.tanggal.like(f'{tahun}-%')
        ).scalar() or 0

        # Hitung omzet real dari SEMUA pesanan tahun ini (semua status)
        # Format tanggal: "19 Jun 2026 03:33"
        omzet_real = 0
        for p in Pesanan.query.filter(
            Pesanan.tanggal.like(f'%{tahun}%')
        ).all():
            omzet_real += p.total_harga

        total_omzet = omzet_dummy + omzet_real
    stok_menipis  = Produk.query.filter(Produk.stok < 20).count()
    total_pesanan = Pesanan.query.count()
    menunggu      = Pesanan.query.filter_by(status='Menunggu').count()
    bulan_map = {'01':'Jan','02':'Feb','03':'Mar','04':'Apr','05':'Mei','06':'Jun',
                 '07':'Jul','08':'Ags','09':'Sep','10':'Okt','11':'Nov','12':'Des'}
    if tahun in ['2024', '2025']:
  
        rows = db.session.query(
            Transaksi.tanggal,
            func.sum(Transaksi.total)
        )\
        .filter(
            Transaksi.tanggal.like(f'{tahun}-%')
        )\
        .group_by(Transaksi.tanggal)\
        .order_by(Transaksi.tanggal)\
        .all()

    elif tahun == '2026':

        # Data dummy Jan-Mei 2026 dari tabel transaksi
        rows_dummy = db.session.query(
            Transaksi.tanggal,
            func.sum(Transaksi.total)
        )\
        .filter(
            Transaksi.tanggal.in_([
                '2026-01','2026-02','2026-03',
                '2026-04','2026-05'
            ])
        )\
        .group_by(Transaksi.tanggal)\
        .order_by(Transaksi.tanggal)\
        .all()

        # Data REAL Juni 2026 dari tabel pesanan
        # Format tanggal pesanan: "19 Jun 2026 03:33"
        # Ambil semua pesanan yang mengandung "Jun 2026" (semua status)
        semua_pesanan_juni = Pesanan.query.filter(
            Pesanan.tanggal.like('%Jun 2026%')
        ).all()

        total_juni_real = sum(p.total_harga for p in semua_pesanan_juni)

        rows = list(rows_dummy)

        # Selalu tampilkan Juni kalau ada pesanan, 
        # meski totalnya 0 tetap ditampilkan biar grafik konsisten
        if semua_pesanan_juni:
            rows.append(('2026-06', total_juni_real))
    bulan_label = [bulan_map.get(r[0].split('-')[1], r[0]) for r in rows]
    bulan_total = [int(r[1]) for r in rows]
    terlaris = Produk.query.order_by(Produk.terjual.desc()).limit(5).all()
    tipe_rows = db.session.query(Produk.tipe, func.count(Produk.id)).group_by(Produk.tipe).all()
    return render_template('dashboard.html',
        tahun=tahun,
        total_produk=total_produk, total_brand=total_brand,
        total_terjual=total_terjual, total_omzet=total_omzet,
        stok_menipis=stok_menipis, total_pesanan=total_pesanan,
        menunggu=menunggu, terlaris=terlaris,
        bulan_label=bulan_label, bulan_total=bulan_total,
        tipe_label=[r[0] for r in tipe_rows],
        tipe_count=[r[1] for r in tipe_rows])

@app.route('/produk')
def produk():
    if not cek_login(): return redirect('/')
    cari = request.args.get('cari','')
    tipe = request.args.get('tipe','')
    query = Produk.query
    if cari: query = query.filter(Produk.nama.ilike(f'%{cari}%')|Produk.brand.ilike(f'%{cari}%'))
    if tipe: query = query.filter(Produk.tipe==tipe)
    data = query.order_by(Produk.terjual.desc()).all()
    tipe_list = [r[0] for r in db.session.query(func.distinct(Produk.tipe)).all()]
    return render_template('produk.html', produk=data, tipe_list=tipe_list, cari=cari, tipe=tipe)

@app.route('/produk/tambah', methods=['POST'])
def tambah_produk():
    if not cek_login(): return redirect('/')
    p = Produk(brand=request.form['brand'], nama=request.form['nama'],
               tipe=request.form['tipe'], ukuran=request.form['ukuran'],
               harga=float(request.form['harga']), stok=int(request.form['stok']),
               terjual=0, rating=0, bpom_id=request.form.get('bpom_id',''),
               deskripsi=request.form.get('deskripsi',''), ingredients='', url='')
    db.session.add(p); db.session.commit()
    return redirect('/produk')

@app.route('/produk/hapus/<int:id>')
def hapus_produk(id):
    if not cek_login(): return redirect('/')
    p = Produk.query.get_or_404(id)
    db.session.delete(p); db.session.commit()
    return redirect('/produk')

@app.route('/produk/edit/<int:id>', methods=['GET','POST'])
def edit_produk(id):
    if not cek_login(): return redirect('/')
    p = Produk.query.get_or_404(id)
    if request.method == 'POST':
        p.brand=request.form['brand']; p.nama=request.form['nama']
        p.tipe=request.form['tipe']; p.ukuran=request.form['ukuran']
        p.harga=float(request.form['harga']); p.stok=int(request.form['stok'])
        p.bpom_id=request.form.get('bpom_id','')
        p.deskripsi=request.form.get('deskripsi','')
        db.session.commit(); return redirect('/produk')
    return render_template('edit_produk.html', produk=p)

@app.route('/laporan')
def laporan():
    if not cek_login(): return redirect('/')
    tipe_rows = db.session.query(Produk.tipe, func.sum(Transaksi.total), func.sum(Transaksi.jumlah))\
                    .join(Transaksi, Produk.id==Transaksi.produk_id).group_by(Produk.tipe).all()
    brand_rows = db.session.query(Produk.brand, func.sum(Transaksi.total))\
                    .join(Transaksi, Produk.id==Transaksi.produk_id)\
                    .group_by(Produk.brand).order_by(func.sum(Transaksi.total).desc()).limit(10).all()
    transaksi = Transaksi.query.order_by(Transaksi.id.desc()).limit(20).all()
    return render_template('laporan.html', tipe_rows=tipe_rows,
                           brand_rows=brand_rows, transaksi=transaksi)

@app.route('/laporan/export')
def export_excel():
    if not cek_login(): return redirect('/')
    produk = Produk.query.all()
    data = [{'Brand':p.brand,'Nama Produk':p.nama,'Tipe':p.tipe,
             'Ukuran':p.ukuran,'Harga':p.harga,'Stok':p.stok,
             'Terjual':p.terjual,'Rating':p.rating,'BPOM ID':p.bpom_id,
             'Total Omzet':p.harga*p.terjual} for p in produk]
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as w:
        pd.DataFrame(data).to_excel(w, index=False, sheet_name='Produk')
    output.seek(0)
    return send_file(output, download_name='laporan_kosmetik.xlsx',
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@app.route('/pesanan')
def pesanan():
    if not cek_login(): return redirect('/')
    status_filter = request.args.get('status','')
    query = Pesanan.query
    if status_filter: query = query.filter(Pesanan.status==status_filter)
    pesanan_list = query.order_by(Pesanan.id.desc()).all()
    return render_template('admin_pesanan.html', pesanan_list=pesanan_list,
        status_filter=status_filter,
        total_pesanan=Pesanan.query.count(),
        total_menunggu=Pesanan.query.filter_by(status='Menunggu').count(),
        total_diproses=Pesanan.query.filter_by(status='Diproses').count(),
        total_selesai=Pesanan.query.filter_by(status='Selesai').count())

@app.route('/pesanan/export')
def export_pesanan():
    if not cek_login():
        return redirect('/')

    pesanan = Pesanan.query.all()

    data = []

    for p in pesanan:

        # daftar produk
        daftar_produk = []
        for item in p.items:
            daftar_produk.append(
                f"{item.produk.nama} ({item.jumlah}x)"
            )

        # daftar ulasan
        daftar_ulasan = []
        for r in p.reviews:
            daftar_ulasan.append(
                f"{r.nama} | {r.rating}⭐ | {r.komentar}"
            )

        data.append({
            'Kode Pesanan': p.kode,
            'Nama Pembeli': p.nama_pembeli,
            'Email': p.email,
            'No HP': p.no_hp,
            'Produk Dibeli': ', '.join(daftar_produk),
            'Ulasan': ' | '.join(daftar_ulasan),
            'Total Harga': p.total_harga,
            'Status': p.status,
            'Tanggal': p.tanggal
        })

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(
            writer,
            sheet_name='Pesanan',
            index=False
        )

    output.seek(0)

    return send_file(
        output,
        download_name='laporan_pesanan.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/pesanan/update/<int:id>/<status>')
def update_pesanan(id, status):
    if not cek_login(): return redirect('/')
    p = Pesanan.query.get_or_404(id)
    if status in ['Menunggu','Diproses','Dikirim','Selesai','Dibatalkan']:
        p.status = status; db.session.commit()
    return redirect('/pesanan')

@app.route('/database')
def lihat_database():
    if not cek_login(): return redirect('/')
    tabel = request.args.get('tabel','produk')
    data, kolom, total = [], [], 0
    if tabel=='produk':
        items = Produk.query.all()
        kolom = ['ID','Brand','Nama','Tipe','Harga','Stok','Terjual','Rating','BPOM']
        data  = [[p.id,p.brand,p.nama[:40],p.tipe,f"Rp {p.harga:,.0f}",
                  p.stok,p.terjual,p.rating,p.bpom_id] for p in items]
        total = len(items)
    elif tabel=='pesanan':
        items = Pesanan.query.order_by(Pesanan.id.desc()).all()
        kolom = ['ID','Kode','Pembeli','Email','Total','Status','Tanggal']
        data  = [[p.id,p.kode,p.nama_pembeli,p.email,
                  f"Rp {p.total_harga:,.0f}",p.status,p.tanggal] for p in items]
        total = len(items)
    elif tabel=='transaksi':
        items = Transaksi.query.order_by(Transaksi.id.desc()).all()
        kolom = ['ID','Produk','Jumlah','Total','Bulan']
        data  = [[t.id, t.produk.nama[:35] if t.produk else '-',
                  t.jumlah, f"Rp {t.total:,.0f}", t.tanggal] for t in items]
        total = len(items)
    return render_template('lihat_database.html', tabel=tabel,
                           kolom=kolom, data=data, total=total)
    
@app.route('/database/export')
def export_database():

    if not cek_login():
        return redirect('/')

    produk = Produk.query.all()

    data = []

    for p in produk:
        data.append({
            'ID': p.id,
            'Brand': p.brand,
            'Nama Produk': p.nama,
            'Tipe': p.tipe,
            'Ukuran': p.ukuran,
            'Harga': p.harga,
            'Stok': p.stok,
            'Terjual': p.terjual,
            'Rating': p.rating,
            'BPOM ID': p.bpom_id
        })

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(
            writer,
            sheet_name='Database Produk',
            index=False
        )

    output.seek(0)

    return send_file(
        output,
        download_name='database_produk.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# =====================
# ROUTE MACHINE LEARNING
# =====================
@app.route('/ml')
def ml_dashboard():
    if not cek_login(): return redirect('/')
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    import importlib
    import ml_engine as mle
    importlib.reload(mle)

    tab = request.args.get('tab', 'rekomendasi')

    # Data untuk semua produk (dropdown)
    semua_produk = Produk.query.order_by(Produk.terjual.desc()).all()
    produk_id = request.args.get('produk_id', type=int)

    rekomendasi = []
    if produk_id:
        rekomendasi = mle.rekomendasi_produk(produk_id, top=6)

    return render_template('ml_dashboard.html',
        tab=tab,
        semua_produk=semua_produk,
        produk_id=produk_id,
        rekomendasi=rekomendasi,
        sentimen_data=mle.ringkasan_sentimen_produk() if tab=='sentimen' else {'total':0,'positif':0,'netral':0,'negatif':0,'detail':[]},
        clustering_data=mle.clustering_produk() if tab=='clustering' else {'produk':[],'stats':[]},
        prediksi_data=mle.prediksi_penjualan(3) if tab=='prediksi' else {'historis':[],'prediksi_depan':[],'akurasi':0,'r2':0,'mae':0},
        rdf_data=mle.buat_knowledge_graph() if tab=='rdf' else {'triple_count':0,'produk_count':0,'turtle_preview':'','turtle_full':''}
    )

@app.route('/ml/rdf/download')
def download_rdf():
    if not cek_login(): return redirect('/')
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))
    import ml_engine as mle
    kg = mle.buat_knowledge_graph()
    output = io.BytesIO(kg['turtle_full'].encode('utf-8'))
    output.seek(0)
    return send_file(output, download_name='produk_kosmetik.ttl',
                     as_attachment=True, mimetype='text/turtle')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        import_dataset()
    print("=" * 45)
    print("  ADMIN PANEL berjalan di port 5001")
    print("  Buka: http://127.0.0.1:5001")
    print("  Login: admin / admin123")
    print("=" * 45)
    app.run(debug=True, port=5001)
