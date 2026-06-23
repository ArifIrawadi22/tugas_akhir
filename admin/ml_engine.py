"""
==============================================
  ML ENGINE — Model Machine Learning
  untuk Proyek Semantic Web Kosmetik
==============================================
  1. Content-Based Filtering (Rekomendasi)
  2. Sentiment Analysis (Ulasan)
  3. K-Means Clustering (Segmen Produk)
  4. Prediksi Penjualan (Linear Regression)
  5. Knowledge Graph RDF (Semantic Web)
==============================================
"""
import pandas as pd
import numpy as np
import sqlite3
import os

# Path database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, '..', 'kosmetik.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

# =============================================
# 1. CONTENT-BASED FILTERING
# =============================================
def rekomendasi_produk(produk_id, top=5):
    """
    Rekomendasikan produk serupa berdasarkan
    kemiripan fitur: tipe, brand, ingredients, harga
    Menggunakan TF-IDF + Cosine Similarity
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.preprocessing import MinMaxScaler

    conn = get_conn()
    df = pd.read_sql("SELECT * FROM produk", conn)
    conn.close()

    if df.empty or produk_id not in df['id'].values:
        return []

    # Gabung fitur teks
    df['fitur_teks'] = (
        df['brand'].fillna('') + ' ' +
        df['tipe'].fillna('') + ' ' +
        df['deskripsi'].fillna('') + ' ' +
        df['ingredients'].fillna('')
    )

    # TF-IDF untuk fitur teks
    tfidf = TfidfVectorizer(max_features=500, stop_words='english')
    mat_teks = tfidf.fit_transform(df['fitur_teks'])

    # Normalisasi fitur numerik (harga & rating)
    scaler = MinMaxScaler()
    mat_num = scaler.fit_transform(df[['harga','rating']].fillna(0))

    # Gabung similarity teks (bobot 70%) + numerik (30%)
    from scipy.sparse import hstack, csr_matrix
    mat_gabung = hstack([mat_teks * 0.7, csr_matrix(mat_num) * 0.3])
    sim = cosine_similarity(mat_gabung)

    idx = df[df['id'] == produk_id].index[0]
    skor = list(enumerate(sim[idx]))
    skor = sorted(skor, key=lambda x: x[1], reverse=True)
    # Skip diri sendiri (skor[0])
    skor_top = [s for s in skor if df.iloc[s[0]]['id'] != produk_id][:top]

    hasil = []
    for i, score in skor_top:
        row = df.iloc[i]
        hasil.append({
            'id': int(row['id']),
            'nama': row['nama'],
            'brand': row['brand'],
            'tipe': row['tipe'],
            'harga': float(row['harga']),
            'rating': float(row['rating']),
            'similarity': round(float(score) * 100, 1)
        })
    return hasil


# =============================================
# 2. SENTIMENT ANALYSIS
# =============================================
def analisis_sentimen(teks):
    """
    Analisis sentimen teks ulasan
    Menggunakan TextBlob (polarity score)
    Return: dict dengan label, skor, dan emoji
    """
    try:
        from textblob import TextBlob
        # TextBlob bekerja lebih baik dengan bahasa Inggris
        # Untuk bahasa Indonesia, kita tambahkan aturan kata kunci
        kata_positif = ['bagus','suka','cocok','mantap','keren','oke','enak',
                        'lembab','cerah','bersih','halus','wangi','recommended',
                        'rekomen','puas','senang','good','nice','great','love']
        kata_negatif = ['jelek','buruk','kecewa','mahal','gak cocok','tidak cocok',
                        'tidak suka','bau','kasar','lengket','berminyak','iritasi',
                        'gatal','merah','perih','bad','worst','terrible','hate']

        teks_lower = teks.lower()
        skor_manual = 0
        for k in kata_positif:
            if k in teks_lower:
                skor_manual += 0.3
        for k in kata_negatif:
            if k in teks_lower:
                skor_manual -= 0.3

        # Gabungkan dengan TextBlob
        blob = TextBlob(teks)
        skor_blob = blob.sentiment.polarity
        skor_final = (skor_manual * 0.6) + (skor_blob * 0.4)

        if skor_final > 0.1:
            return {'label': 'Positif', 'skor': round(skor_final, 2), 'emoji': '😊', 'warna': 'success'}
        elif skor_final < -0.1:
            return {'label': 'Negatif', 'skor': round(skor_final, 2), 'emoji': '😞', 'warna': 'danger'}
        else:
            return {'label': 'Netral',  'skor': round(skor_final, 2), 'emoji': '😐', 'warna': 'warning'}
    except Exception as e:
        return {'label': 'Netral', 'skor': 0, 'emoji': '😐', 'warna': 'warning'}


def ringkasan_sentimen_produk():
    """Hitung sentimen semua ulasan dari database"""
    conn = get_conn()
    try:
        df = pd.read_sql("""
            SELECT r.produk_id, r.komentar, r.rating, p.nama, p.tipe
            FROM review r
            JOIN produk p ON r.produk_id = p.id
        """, conn)
    except:
        df = pd.DataFrame()
    conn.close()

    if df.empty:
        return {'positif': 0, 'netral': 0, 'negatif': 0, 'total': 0, 'detail': []}

    hasil = []
    pos = net = neg = 0
    for _, row in df.iterrows():
        s = analisis_sentimen(str(row['komentar']))
        hasil.append({
            'produk': row['nama'],
            'tipe': row['tipe'],
            'komentar': row['komentar'][:80],
            'sentimen': s['label'],
            'emoji': s['emoji'],
            'warna': s['warna'],
            'rating': row['rating']
        })
        if s['label'] == 'Positif': pos += 1
        elif s['label'] == 'Negatif': neg += 1
        else: net += 1

    return {
        'positif': pos, 'netral': net, 'negatif': neg,
        'total': len(hasil), 'detail': hasil
    }


# =============================================
# 3. K-MEANS CLUSTERING
# =============================================
def clustering_produk(n_clusters=3):
    """
    Kelompokkan produk ke dalam segmen:
    Budget / Menengah / Premium
    Menggunakan K-Means clustering
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    conn = get_conn()
    df = pd.read_sql("SELECT id, nama, brand, tipe, harga, rating, terjual FROM produk", conn)
    conn.close()

    if len(df) < n_clusters:
        return []

    # Fitur untuk clustering
    X = df[['harga', 'rating', 'terjual']].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['klaster'] = kmeans.fit_predict(X_scaled)

    # Tentukan label klaster berdasarkan rata-rata harga
    harga_per_klaster = df.groupby('klaster')['harga'].mean().sort_values()
    label_map = {}
    labels = ['Budget 💚', 'Menengah 💛', 'Premium 💜']
    for i, (klaster_id, _) in enumerate(harga_per_klaster.items()):
        label_map[klaster_id] = labels[i]

    df['segmen'] = df['klaster'].map(label_map)

    # Statistik per segmen
    stats = df.groupby('segmen').agg(
        jumlah=('id','count'),
        harga_rata=('harga','mean'),
        rating_rata=('rating','mean'),
        terjual_total=('terjual','sum')
    ).reset_index()

    return {
        'produk': df[['id','nama','brand','tipe','harga','rating','terjual','segmen']].to_dict('records'),
        'stats': stats.to_dict('records')
    }


# =============================================
# 4. PREDIKSI PENJUALAN
# =============================================
def prediksi_penjualan(bulan_ke_depan=3):
    """
    Prediksi omzet penjualan bulan-bulan ke depan
    Menggunakan Linear Regression dari data transaksi historis
    """
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_absolute_error, r2_score

    conn = get_conn()
    df = pd.read_sql("""
        SELECT tanggal, SUM(total) as omzet, SUM(jumlah) as unit
        FROM transaksi
        GROUP BY tanggal
        ORDER BY tanggal
    """, conn)
    conn.close()

    if len(df) < 3:
        return {'error': 'Data transaksi kurang, minimal 3 bulan'}

    df['bulan_ke'] = range(1, len(df) + 1)
    X = df[['bulan_ke']]
    y = df['omzet']

    model = LinearRegression()
    model.fit(X, y)

    y_pred_train = model.predict(X)
    mae = mean_absolute_error(y, y_pred_train)
    r2  = r2_score(y, y_pred_train)

    # Prediksi bulan ke depan
    bulan_map = {
        '2024-01':'Jan 2024','2024-02':'Feb 2024','2024-03':'Mar 2024',
        '2024-04':'Apr 2024','2024-05':'Mei 2024','2024-06':'Jun 2024',
        '2024-07':'Jul 2024','2024-08':'Ags 2024','2024-09':'Sep 2024',
        '2024-10':'Okt 2024','2024-11':'Nov 2024','2024-12':'Des 2024',
        '2025-01':'Jan 2025','2025-02':'Feb 2025','2025-03':'Mar 2025',
        '2025-04':'Apr 2025','2025-05':'Mei 2025','2025-06':'Jun 2025',
        '2025-07':'Jul 2025','2025-08':'Ags 2025','2025-09':'Sep 2025',
        '2025-10':'Okt 2025','2025-11':'Nov 2025','2025-12':'Des 2025',
        '2026-01':'Jan 2026','2026-02':'Feb 2026','2026-03':'Mar 2026',
        '2026-04':'Apr 2026','2026-05':'Mei 2026','2026-06':'Jun 2026',
    }
    nama_bulan_urut = ['Jan','Feb','Mar','Apr','Mei','Jun',
                       'Jul','Ags','Sep','Okt','Nov','Des']

    historis = []
    for _, row in df.iterrows():
        historis.append({
            'bulan': bulan_map.get(row['tanggal'], row['tanggal']),
            'omzet': round(float(row['omzet']), 0),
            'prediksi': round(float(y_pred_train[row['bulan_ke']-1]), 0)
        })

    # Prediksi ke depan
    max_bln = len(df)
    prediksi_depan = []
    bulan_terakhir = df['tanggal'].iloc[-1]
    thn = int(bulan_terakhir[:4])
    bln = int(bulan_terakhir[5:7])
    for i in range(1, bulan_ke_depan + 1):
        bln += 1
        if bln > 12:
            bln = 1
            thn += 1
        bln_ke = max_bln + i
        omzet_pred = float(model.predict([[bln_ke]])[0])
        prediksi_depan.append({
            'bulan': f"{nama_bulan_urut[bln-1]} {thn}",
            'prediksi': max(omzet_pred, 0)
        })

    return {
        'historis': historis,
        'prediksi_depan': prediksi_depan,
        'mae': float(mae),
        'r2': round(float(r2), 3),
        'akurasi': round(max(0, r2) * 100, 1)
    }


# =============================================
# 5. KNOWLEDGE GRAPH (SEMANTIC WEB)
# =============================================
def buat_knowledge_graph():
    """
    Buat Knowledge Graph RDF dari data produk
    Menggunakan Schema.org ontologi
    Return: string Turtle RDF + statistik
    """
    try:
        from rdflib import Graph, Literal, Namespace, URIRef
        from rdflib.namespace import RDF, XSD

        conn = get_conn()
        df = pd.read_sql("SELECT * FROM produk LIMIT 91", conn)
        conn.close()

        g = Graph()
        SCHEMA = Namespace("https://schema.org/")
        TOKO   = Namespace("http://tokokosmetik.id/")

        g.bind("schema", SCHEMA)
        g.bind("toko",   TOKO)

        for _, row in df.iterrows():
            produk_uri = TOKO[f"produk/{int(row['id'])}"]
            brand_uri  = TOKO[f"brand/{row['brand'].replace(' ','_')}"]

            # Entitas Produk
            g.add((produk_uri, RDF.type,        SCHEMA.Product))
            g.add((produk_uri, SCHEMA.name,      Literal(str(row['nama']))))
            g.add((produk_uri, SCHEMA.category,  Literal(str(row['tipe']))))
            g.add((produk_uri, SCHEMA.identifier,Literal(str(row['bpom_id']))))
            g.add((produk_uri, SCHEMA.size,      Literal(str(row['ukuran']))))

            # Harga (Offer)
            offer_uri = TOKO[f"offer/{int(row['id'])}"]
            g.add((produk_uri, SCHEMA.offers,    offer_uri))
            g.add((offer_uri,  RDF.type,         SCHEMA.Offer))
            g.add((offer_uri,  SCHEMA.price,     Literal(float(row['harga']), datatype=XSD.decimal)))
            g.add((offer_uri,  SCHEMA.priceCurrency, Literal("IDR")))
            avail = "InStock" if row['stok'] > 0 else "OutOfStock"
            g.add((offer_uri,  SCHEMA.availability, SCHEMA[avail]))

            # Rating
            rating_uri = TOKO[f"rating/{int(row['id'])}"]
            g.add((produk_uri, SCHEMA.aggregateRating, rating_uri))
            g.add((rating_uri, RDF.type,          SCHEMA.AggregateRating))
            g.add((rating_uri, SCHEMA.ratingValue, Literal(float(row['rating']), datatype=XSD.decimal)))
            g.add((rating_uri, SCHEMA.bestRating,  Literal(5)))

            # Brand
            g.add((produk_uri, SCHEMA.brand, brand_uri))
            g.add((brand_uri,  RDF.type,     SCHEMA.Brand))
            g.add((brand_uri,  SCHEMA.name,  Literal(str(row['brand']))))

            # Deskripsi
            if pd.notna(row.get('deskripsi')) and str(row['deskripsi']) not in ['', 'nan']:
                g.add((produk_uri, SCHEMA.description, Literal(str(row['deskripsi'])[:200])))

        ttl = g.serialize(format='turtle')

        # ============================================
        # SAMPLE NODE & EDGE NYATA untuk visualisasi graf
        # Diambil dari 4 produk pertama agar tidak terlalu padat
        # ============================================
        graph_nodes = []
        graph_edges = []
        for _, row in df.head(4).iterrows():
            pid = int(row['id'])
            produk_node_id = f"produk_{pid}"
            brand_node_id  = f"brand_{row['brand'].replace(' ', '_')}"
            harga_node_id  = f"harga_{pid}"
            rating_node_id = f"rating_{pid}"
            bpom_node_id   = f"bpom_{pid}"

            graph_nodes.append({'id': produk_node_id, 'label': str(row['nama'])[:30], 'tipe': 'Product'})
            graph_nodes.append({'id': brand_node_id, 'label': str(row['brand']), 'tipe': 'Brand'})
            graph_nodes.append({'id': harga_node_id, 'label': f"Rp {int(row['harga']):,}", 'tipe': 'Offer'})
            graph_nodes.append({'id': rating_node_id, 'label': f"★ {row['rating']}", 'tipe': 'Rating'})
            graph_nodes.append({'id': bpom_node_id, 'label': str(row['bpom_id']), 'tipe': 'Identifier'})

            graph_edges.append({'from': produk_node_id, 'to': brand_node_id, 'label': 'brand'})
            graph_edges.append({'from': produk_node_id, 'to': harga_node_id, 'label': 'offers'})
            graph_edges.append({'from': produk_node_id, 'to': rating_node_id, 'label': 'aggregateRating'})
            graph_edges.append({'from': produk_node_id, 'to': bpom_node_id, 'label': 'identifier'})

        # Hilangkan node brand duplikat (kalau 2 produk brand sama)
        seen = set()
        graph_nodes_unik = []
        for n in graph_nodes:
            if n['id'] not in seen:
                seen.add(n['id'])
                graph_nodes_unik.append(n)

        return {
            'triple_count': len(g),
            'produk_count': len(df),
            'turtle_preview': ttl[:2000],
            'turtle_full': ttl,
            'graph_nodes': graph_nodes_unik,
            'graph_edges': graph_edges
        }
    except Exception as e:
        return {'error': str(e), 'triple_count': 0, 'graph_nodes': [], 'graph_edges': []}



if __name__ == '__main__':
    print("=== TEST ML ENGINE ===")

    print("\n[1] Content-Based Filtering")
    hasil = rekomendasi_produk(produk_id=1, top=3)
    for h in hasil:
        print(f"  → {h['nama'][:40]} | similarity: {h['similarity']}%")

    print("\n[2] Sentiment Analysis")
    contoh = ["produknya bagus banget cocok di kulit saya", "kecewa mahal tapi gak cocok"]
    for t in contoh:
        s = analisis_sentimen(t)
        print(f"  → '{t[:40]}' → {s['label']} {s['emoji']}")

    print("\n[3] K-Means Clustering")
    cl = clustering_produk()
    for s in cl['stats']:
        print(f"  → {s['segmen']}: {s['jumlah']} produk | rata Rp {s['harga_rata']:,.0f}")

    print("\n[4] Prediksi Penjualan")
    pred = prediksi_penjualan(3)
    print(f"  → Akurasi model: {pred['akurasi']}% (R²={pred['r2']})")
    for p in pred['prediksi_depan']:
        print(f"  → {p['bulan']}: Rp {p['prediksi']:,.0f}")

    print("\n[5] Knowledge Graph")
    kg = buat_knowledge_graph()
    print(f"  → {kg['triple_count']} triple RDF dari {kg['produk_count']} produk")


# =============================================
# 6. PREDIKSI STOK PER PRODUK (BULAN DEPAN)
# =============================================
def prediksi_stok_produk():
    """
    Prediksi berapa unit tiap produk akan terjual bulan depan,
    dibandingkan dengan stok saat ini.
    Menggunakan rata-rata tren penjualan 3 bulan terakhir + regresi sederhana.
    Output: rekomendasi RESTOCK / AMAN / KELEBIHAN STOK
    """
    from sklearn.linear_model import LinearRegression

    conn = get_conn()
    df_trans = pd.read_sql("""
        SELECT t.produk_id, t.tanggal, t.jumlah
        FROM transaksi t ORDER BY t.tanggal
    """, conn)
    df_produk = pd.read_sql("SELECT id, nama, brand, tipe, harga, stok FROM produk", conn)

    # Tambahkan juga penjualan dari pesanan user (real time)
    try:
        df_pesanan_item = pd.read_sql("""
            SELECT pi.produk_id, p.tanggal, pi.jumlah
            FROM pesanan_item pi JOIN pesanan p ON pi.pesanan_id = p.id
            WHERE p.status != 'Dibatalkan'
        """, conn)
        # Ekstrak tahun-bulan dari format "19 Jun 2026 03:33"
        bulan_id = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','Mei':'05','Jun':'06',
                    'Jul':'07','Ags':'08','Sep':'09','Okt':'10','Nov':'11','Des':'12'}
        def parse_bulan(s):
            try:
                parts = s.split()
                bln = bulan_id.get(parts[1], '01')
                return f"{parts[2]}-{bln}"
            except:
                return None
        if not df_pesanan_item.empty:
            df_pesanan_item['tanggal'] = df_pesanan_item['tanggal'].apply(parse_bulan)
            df_pesanan_item = df_pesanan_item.dropna(subset=['tanggal'])
            df_pesanan_item = df_pesanan_item.rename(columns={'jumlah':'jumlah'})
            df_trans = pd.concat([df_trans, df_pesanan_item[['produk_id','tanggal','jumlah']]], ignore_index=True)
    except Exception:
        pass

    conn.close()

    if df_trans.empty:
        return []

    hasil = []
    bulan_unik = sorted(df_trans['tanggal'].unique())
    bulan_terakhir_3 = bulan_unik[-3:] if len(bulan_unik) >= 3 else bulan_unik

    for _, prod in df_produk.iterrows():
        pid = prod['id']
        data_produk = df_trans[df_trans['produk_id'] == pid].groupby('tanggal')['jumlah'].sum().reset_index()
        data_produk = data_produk.sort_values('tanggal')

        if len(data_produk) == 0:
            prediksi_unit = 0
            tren = 'Belum ada data'
        elif len(data_produk) == 1:
            prediksi_unit = int(data_produk['jumlah'].iloc[0])
            tren = 'Data terbatas'
        else:
            # Regresi sederhana pakai urutan bulan
            data_produk['bulan_ke'] = range(1, len(data_produk)+1)
            X = data_produk[['bulan_ke']]
            y = data_produk['jumlah']
            try:
                model = LinearRegression()
                model.fit(X, y)
                pred = model.predict(pd.DataFrame({'bulan_ke':[len(data_produk)+1]}))[0]
                prediksi_unit = max(0, int(round(pred)))
                rata2_lama = data_produk['jumlah'].mean()
                if prediksi_unit > rata2_lama * 1.15:
                    tren = 'Naik 📈'
                elif prediksi_unit < rata2_lama * 0.85:
                    tren = 'Turun 📉'
                else:
                    tren = 'Stabil ➡️'
            except Exception:
                prediksi_unit = int(data_produk['jumlah'].mean())
                tren = 'Stabil ➡️'

        stok_sekarang = int(prod['stok'])
        selisih = stok_sekarang - prediksi_unit

        if prediksi_unit == 0:
            status, warna = 'Tidak Perlu Restock', 'gray'
        elif selisih < 0:
            status, warna = 'PERLU RESTOCK', 'danger'
        elif selisih < prediksi_unit * 0.3:
            status, warna = 'Stok Pas-pasan', 'warning'
        elif selisih > prediksi_unit * 2:
            status, warna = 'KELEBIHAN STOK', 'info'
        else:
            status, warna = 'Stok Aman', 'success'

        hasil.append({
            'id': int(pid),
            'nama': prod['nama'],
            'brand': prod['brand'],
            'tipe': prod['tipe'],
            'harga': float(prod['harga']),
            'stok_sekarang': stok_sekarang,
            'prediksi_terjual': prediksi_unit,
            'tren': tren,
            'selisih': selisih,
            'rekomendasi_beli': max(0, prediksi_unit - stok_sekarang + 5),  # +5 buffer aman
            'status': status,
            'warna': warna
        })

    # Urutkan: yang perlu restock duluan
    urutan_prioritas = {'PERLU RESTOCK':0, 'Stok Pas-pasan':1, 'Stok Aman':2, 'KELEBIHAN STOK':3, 'Tidak Perlu Restock':4}
    hasil.sort(key=lambda x: urutan_prioritas.get(x['status'], 5))
    return hasil


# =============================================
# 7. RINCIAN PRODUK TERLARIS PER BULAN
# =============================================
def rincian_penjualan_per_bulan():
    """
    Breakdown lengkap per bulan (Jan 2024 - sekarang):
    - Total omzet bulan itu
    - Per kategori (serum/toner/facial wash): unit terjual & omzet
    - Produk terlaris di bulan itu
    """
    conn = get_conn()
    df_trans = pd.read_sql("""
        SELECT t.tanggal, t.produk_id, t.jumlah, t.total, p.nama, p.brand, p.tipe
        FROM transaksi t JOIN produk p ON t.produk_id = p.id
    """, conn)

    # Gabung juga dengan pesanan user real (2026 dst)
    try:
        df_pesanan = pd.read_sql("""
            SELECT p.tanggal as tgl_pesanan, pi.produk_id, pi.jumlah,
                   (pi.jumlah * pi.harga_saat) as total, pr.nama, pr.brand, pr.tipe
            FROM pesanan_item pi
            JOIN pesanan p ON pi.pesanan_id = p.id
            JOIN produk pr ON pi.produk_id = pr.id
            WHERE p.status != 'Dibatalkan'
        """, conn)
        bulan_id = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','Mei':'05','Jun':'06',
                    'Jul':'07','Ags':'08','Sep':'09','Okt':'10','Nov':'11','Des':'12'}
        def parse_bulan(s):
            try:
                parts = s.split()
                bln = bulan_id.get(parts[1], '01')
                return f"{parts[2]}-{bln}"
            except:
                return None
        if not df_pesanan.empty:
            df_pesanan['tanggal'] = df_pesanan['tgl_pesanan'].apply(parse_bulan)
            df_pesanan = df_pesanan.dropna(subset=['tanggal'])
            df_trans = pd.concat([
                df_trans,
                df_pesanan[['tanggal','produk_id','jumlah','total','nama','brand','tipe']]
            ], ignore_index=True)
    except Exception:
        pass

    conn.close()

    if df_trans.empty:
        return []

    bulan_map = {'01':'Januari','02':'Februari','03':'Maret','04':'April',
                 '05':'Mei','06':'Juni','07':'Juli','08':'Agustus',
                 '09':'September','10':'Oktober','11':'November','12':'Desember'}

    hasil = []
    for bulan in sorted(df_trans['tanggal'].unique()):
        df_bulan = df_trans[df_trans['tanggal'] == bulan]
        total_omzet = float(df_bulan['total'].sum())
        total_unit = int(df_bulan['jumlah'].sum())

        # Per kategori
        per_kategori = df_bulan.groupby('tipe').agg(
            unit=('jumlah','sum'), omzet=('total','sum')
        ).reset_index().sort_values('omzet', ascending=False)
        kategori_list = [{
            'tipe': row['tipe'],
            'unit': int(row['unit']),
            'omzet': float(row['omzet'])
        } for _, row in per_kategori.iterrows()]

        # Produk terlaris bulan ini (top 5)
        per_produk = df_bulan.groupby(['nama','brand','tipe']).agg(
            unit=('jumlah','sum'), omzet=('total','sum')
        ).reset_index().sort_values('unit', ascending=False).head(5)
        produk_terlaris = [{
            'nama': row['nama'],
            'brand': row['brand'],
            'tipe': row['tipe'],
            'unit': int(row['unit']),
            'omzet': float(row['omzet'])
        } for _, row in per_produk.iterrows()]

        thn, bln = bulan.split('-')
        hasil.append({
            'kode_bulan': bulan,
            'label': f"{bulan_map.get(bln, bln)} {thn}",
            'total_omzet': total_omzet,
            'total_unit': total_unit,
            'kategori': kategori_list,
            'produk_terlaris': produk_terlaris
        })

    return list(reversed(hasil))  # Terbaru duluan
