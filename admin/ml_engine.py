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
        return {
            'triple_count': len(g),
            'produk_count': len(df),
            'turtle_preview': ttl[:2000],
            'turtle_full': ttl
        }
    except Exception as e:
        return {'error': str(e), 'triple_count': 0}


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
