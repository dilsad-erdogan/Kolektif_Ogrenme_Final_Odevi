import json
import pandas as pd
import math
import matplotlib.pyplot as plt
import time

def haversine(lon1, lat1, lon2, lat2):
    """İki koordinat (boylam, enlem) arasındaki mesafeyi kilometre cinsinden hesaplar."""
    R = 6371.0 # Dünya'nın yarıçapı (km)
    
    # Dereceleri radyana çevir
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def main():
    tum_metrikler = []
    print("="*50)
    print(" 1. AŞAMA: VERİ KEŞFİ (EDA) ")
    print("="*50)
    
    file_path = 'IETT Bus Stops Data'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Hata: '{file_path}' dosyası bulunamadı. Lütfen dosya yolunu kontrol edin.")
        return

    features = data.get('features', [])
    
    # Tüm verileri DataFrame'e alarak hızlı keşif yapalım
    df_raw = pd.json_normalize([f['properties'] for f in features])
    
    # Eksik koordinat olanları bulmak için kısa bir kontrol
    eksik_koordinat_sayisi = 0
    for f in features:
        geom = f.get('geometry')
        if not geom or geom.get('type') != 'Point' or not geom.get('coordinates'):
            eksik_koordinat_sayisi += 1
            
    print(f"[-] Toplam Satır (Durak) Sayısı (Ham Veri): {len(features)}")
    print(f"[-] Orijinal Veri Setindeki Kolonlar ({len(df_raw.columns)} adet):")
    print("   ", ", ".join(df_raw.columns.tolist()))
    
    # Eksik Veri Özeti
    eksik_veriler = df_raw.isnull().sum()
    if eksik_veriler.sum() == 0:
        print("\n[-] Eksik Veri Durumu: Hiçbir kolonda eksik/boş veri tespit edilmedi.")
    else:
        print("\n[-] Eksik Veri Durumu:")
        print(eksik_veriler[eksik_veriler > 0])
        
    print(f"[-] Geometrisi (Koordinatı) Eksik Durak Sayısı: {eksik_koordinat_sayisi}")

    # ===== TEKRAR EDEN VERİ KONTROLÜ (EDA AŞAMASI) =====
    tam_tekrar_eden_ham = df_raw.duplicated().sum()
    print(f"[-] Birebir Tekrar Eden Kayıt Sayısı (Tüm kolonları aynı olan): {tam_tekrar_eden_ham}")
    # Aynı durak kodu ile tekrar eden var mı diye bakalım
    kod_tekrar_eden = df_raw.duplicated(subset=['DURAK_KODU']).sum()
    if kod_tekrar_eden > 0:
        print(f"[-] Aynı 'DURAK_KODU'na sahip tekrar eden satır sayısı: {kod_tekrar_eden}")

    time.sleep(2)
    print("\n" + "="*50)
    print(" 2. AŞAMA: VERİ FİLTRELEME VE ZENGİNLEŞTİRME ")
    print("="*50)
    
    # Sadece durak adı ve koordinatları ayıklıyoruz
    filtrelenmis_veriler = []

    for f in features:
        durak_adi = f.get('properties', {}).get('ADI', 'Bilinmiyor')
        
        geometry = f.get('geometry')
        if geometry and geometry.get('type') == 'Point':
            coords = geometry.get('coordinates', [None, None])
            longitude_val = coords[0]
            latitude_val = coords[1]
        else:
            continue # Koordinatı olmayanları atlıyoruz

        filtrelenmis_veriler.append({
            'Durak_Adi': durak_adi,
            'Longitude': longitude_val,
            'Latitude': latitude_val
        })

    df_filtered = pd.DataFrame(filtrelenmis_veriler)
    ilk_satir_sayisi = len(df_filtered)
    
    print("[-] Sadece kullanılacak olan [Durak_Adi, Longitude, Latitude] kolonları seçildi.")
    
    # ===== TEKRAR EDEN VERİLERİ TEMİZLEME AŞAMASI =====
    # Aynı isim ve aynı koordinatlara sahip satırları yinelenen (duplicate) kabul ediyoruz:
    tekrar_eden_sayisi = df_filtered.duplicated(subset=['Durak_Adi', 'Longitude', 'Latitude']).sum()
    
    if tekrar_eden_sayisi > 0:
        print(f"[-] Aynı Durak Adı ve Koordinata sahip {tekrar_eden_sayisi} adet yinelenen veri tespit edildi, temizleniyor...")
        df_filtered = df_filtered.drop_duplicates(subset=['Durak_Adi', 'Longitude', 'Latitude'])
    else:
         print("[-] Seçilen kolonlarda mükerrer (yinelenen) kayıt bulunmadı.")
         
    kalan_satir_sayisi = len(df_filtered)
    print(f"[-] Filtreleme ve temizleme sonrası toplam satır sayısı: {ilk_satir_sayisi} -> {kalan_satir_sayisi}")
    
    time.sleep(2)
    print("\n" + "="*50)
    print(" 3. AŞAMA: RASTGELE ÖRNEKLEM SEÇİMİ (20 DURAK) ")
    print("="*50)

    # (Sunumlarda kod her çalıştığında aynı durağı versin ki sürpriz olmasın diye random_state=42 ayarlıyoruz)
    # Veri sayısını arttırıyoruz (örneğin 20) ki modellerin performansı ve tercihleri farklılaşabilsin.
    df_sampled = df_filtered.sample(n=20, random_state=42)

    print("[-] Temizlenmiş veri seti içinden rastgele 20 durak seçildi.")

    # Sadece seçilen 20 satırı kaydet
    kayit_yolu = 'secilmis_veriler.csv'
    df_sampled.to_csv(kayit_yolu, index=False, encoding='utf-8')
    print(f"\n[-] Sadece rastgele seçilen 20 durak '{kayit_yolu}' adıyla başarıyla kaydedildi.")

    time.sleep(2)
    print("\n" + "="*50)
    print(" 4. AŞAMA: MESAFE HESAPLAMA (OSRM YOL MESAFLERİ) ")
    print("="*50)
    
    # nxn Mesafe matrisi oluşturalım
    duraklar = df_sampled.to_dict('records')
    n = len(duraklar)
    durak_isimleri = [d['Durak_Adi'] for d in duraklar]
    
    mesafe_matrisi = pd.DataFrame(index=durak_isimleri, columns=durak_isimleri)
    sure_matrisi = pd.DataFrame(index=durak_isimleri, columns=durak_isimleri)
                                  
    # OSRM Table API'si için koordinatları birleştir (Hem mesafe hem süre istiyoruz)
    coords_str = ";".join([f"{d['Longitude']},{d['Latitude']}" for d in duraklar])
    osrm_url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}?annotations=distance,duration"
    
    import urllib.request
    import numpy as np
    
    osrm_basarili = False
    try:
        print("[-] OSRM API üzerinden gerçek yol mesafeleri ve süreleri çekiliyor...")
        req = urllib.request.Request(osrm_url, headers={'User-Agent': 'KolektifOgrenmeProjesi/1.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('code') == 'Ok':
                distances = data.get('distances', [])
                durations = data.get('durations', [])
                for i in range(n):
                    for j in range(n):
                        # Mesafe (metre -> km)
                        mesafe_matrisi.iloc[i, j] = distances[i][j] / 1000.0 if distances[i][j] is not None else 0.0
                        # Süre (saniye -> dakika)
                        sure_matrisi.iloc[i, j] = durations[i][j] / 60.0 if durations[i][j] is not None else 0.0
                osrm_basarili = True
                print("[-] Gerçek sokak mesafeleri ve süreleri OSRM ile başarıyla hesaplandı.")
            else:
                print(f"[-] OSRM API hatası döndü: {data.get('code')}")
    except Exception as e:
        print(f"[-] OSRM API çağrısında hata oluştu: {e}")
        
    if not osrm_basarili:
        print("[-] DİKKAT: OSRM başarısız oldu. Yedek sistem devreye alınıyor...")
        for i in range(n):
            for j in range(n):
                if i == j:
                    mesafe_matrisi.iloc[i, j] = 0.0
                    sure_matrisi.iloc[i, j] = 0.0
                else:
                    d1 = duraklar[i]
                    d2 = duraklar[j]
                    dist = haversine(d1['Longitude'], d1['Latitude'], d2['Longitude'], d2['Latitude'])
                    mesafe_matrisi.iloc[i, j] = dist
                    sure_matrisi.iloc[i, j] = dist / 40.0 * 60.0 # Ortalama 40km/h hız tahmini
        print("[-] Mesafeler Haversine, süreler ortalama hız tahmini ile hesaplandı.")

    # TRAFİK SİMÜLASYONU: Her yol için rastgele bir trafik yoğunluk katsayısı (0 ile 1.5 arası ek yük)
    np.random.seed(42) # Sonuçların tutarlı olması için
    trafik_matrisi = pd.DataFrame(np.random.uniform(0, 1.5, size=(n, n)), index=durak_isimleri, columns=durak_isimleri)
    for i in range(n): trafik_matrisi.iloc[i, i] = 0 # Kendisine giden yolda trafik olmaz

    # NİHAİ MALİYET MATRİSİ (Ağırlıklı Süre)
    # Rota optimizasyonu artık sadece mesafeye değil, trafikle ağırlandırılmış süreye bakacak.
    maliyet_matrisi = sure_matrisi * (1 + trafik_matrisi)
                
    # Görüntüleme için float yapalım
    mesafe_matrisi = mesafe_matrisi.astype(float)
    sure_matrisi = sure_matrisi.astype(float)
    maliyet_matrisi = maliyet_matrisi.astype(float)
                
    # Görüntüleme için float yapalım
    mesafe_matrisi = mesafe_matrisi.astype(float)
    
    # Matrisi CSV olarak kaydet
    matris_kayit_yolu = 'mesafe_matrisi.csv'
    mesafe_matrisi.to_csv(matris_kayit_yolu, encoding='utf-8')
    print(f"\n[-] Tam Mesafe Matrisi '{matris_kayit_yolu}' adıyla başarıyla kaydedildi.")

    # Mesafe Matrisinin Sıcaklık Haritasını (Heatmap) Çıkaralım
    try:
        import seaborn as sns
        plt.figure(figsize=(12, 10))
        # Durak sayımız (Örn: 20) fazla olabileceği için eksen isimlerini gizliyoruz veya küçültüyoruz
        sns.heatmap(mesafe_matrisi, cmap="YlOrRd", annot=False, xticklabels=False, yticklabels=False)
        plt.title('Duraklar Arası Mesafe Sıcaklık Haritası (Heatmap) (km)', fontsize=15)
        plt.xlabel('Varış Noktası (Duraklar)', fontsize=12)
        plt.ylabel('Kalkış Noktası (Duraklar)', fontsize=12)
        
        heatmap_gorsel_yolu = 'mesafe_sicaklik_matrisi.png'
        plt.savefig(heatmap_gorsel_yolu, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"[-] Uzaklık ve yakınlık bağlarını gösteren sıcaklık haritası '{heatmap_gorsel_yolu}' adıyla başarıyla oluşturuldu.")
    except Exception as e:
        print(f"[-] Sıcaklık haritası çizimi sırasında bir hata oluştu: {e}")
        print("    (Matrisi çok renkli görselleştirmek için 'seaborn' eksik olabilir. Lütfen 'pip install seaborn' yazınız.)")

    time.sleep(2)
    print("\n" + "="*50)
    print(" 5. AŞAMA: DURAKLARIN GÖRSELLEŞTİRİLMESİ ")
    print("="*50)
    
    try:
        plt.figure(figsize=(12, 8))
        # Durakları grafikte nokta (scatter) olarak işaretle
        plt.scatter(df_sampled['Longitude'], df_sampled['Latitude'], c='red', marker='o', s=100, label='Duraklar', zorder=5)
        
        # İsim etiketlerini ekle
        for idx, row in df_sampled.iterrows():
            durak_kisa_adi = str(row['Durak_Adi'])[:20] # Ekrana sığması için 20 karaktere kırpıyoruz
            plt.annotate(durak_kisa_adi, (row['Longitude'], row['Latitude']), 
                         xytext=(5, 5), textcoords='offset points', fontsize=8, zorder=6)
                         
        plt.title(f'Seçilen {len(df_sampled)} İETT Durağının Konum Dağılımı Haritası', fontsize=14)
        plt.xlabel('Boylam (Longitude)', fontsize=12)
        plt.ylabel('Enlem (Latitude)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7, zorder=0)
        plt.legend()
        
        # Görseli çıktı olarak kaydet
        gorsel_yolu = 'secilen_duraklar_haritasi.png'
        plt.savefig(gorsel_yolu, dpi=300, bbox_inches='tight')
        plt.close() # Belleği temizle
        print(f"[-] Seçilen durakların görsel haritası '{gorsel_yolu}' adıyla başarıyla tasarlanıp kaydedildi.")
    except Exception as e:
        print(f"[-] Görselleştirme aşamasında bir hata oluştu: {e}")
        print("    (Büyük ihtimalle matplotlib kütüphanesi eksik. Lütfen 'pip install matplotlib' ile kurun.)")

    time.sleep(2)
    print("\n" + "="*50)
    print(" 6. AŞAMA: ALGORİTMALAR İÇİN EDGE (KENAR) VERİ SETİ OLUŞTURMA ")
    print("="*50)
    
    # Makine öğrenmesi modelleri (RF, XGBoost, Stacking) için node çiftleri (kenarlar) halinde bir veri seti
    edge_data = []
    for i in range(n):
        for j in range(n):
            if i != j:  # Kendisine giden yolları almıyoruz
                d1 = duraklar[i]
                d2 = duraklar[j]
                
                # Kenar özellikleri (Artık Süre ve Trafik de var)
                edge = {
                    'Origin_Node': d1['Durak_Adi'],
                    'Origin_Lon': d1['Longitude'],
                    'Origin_Lat': d1['Latitude'],
                    'Dest_Node': d2['Durak_Adi'],
                    'Dest_Lon': d2['Longitude'],
                    'Dest_Lat': d2['Latitude'],
                    'Distance_km': mesafe_matrisi.iloc[i, j],
                    'Base_Duration_min': sure_matrisi.iloc[i, j],
                    'Traffic_Factor': trafik_matrisi.iloc[i, j],
                    'Total_Cost_Weighted': maliyet_matrisi.iloc[i, j]
                }
                edge_data.append(edge)
                
    df_edges = pd.DataFrame(edge_data)
    
    # KOLEKTİF ÖĞRENME: Çoklu Uzman (Multi-Expert) Etiketleme (TRAFİĞE GÖRE)
    # Sadece bir algoritma yerine 3 farklı heuristiğin "ortak aklını" öğreneceğiz.
    df_edges['Expert_NN'] = 0
    df_edges['Expert_Greedy'] = 0

    # Uzman 1: En Hızlı Komşu (Time-Based Nearest Neighbor)
    def run_time_nn():
        current = 0
        unvisited = set(range(1, n))
        edges = []
        while unvisited:
            nearest = -1
            min_cost = float('inf')
            for cand in unvisited:
                # Mesafe yerine maliyet (trafikli süre) bakıyoruz
                if maliyet_matrisi.iloc[current, cand] < min_cost:
                    min_cost = maliyet_matrisi.iloc[current, cand]
                    nearest = cand
            edges.append((durak_isimleri[current], durak_isimleri[nearest]))
            unvisited.remove(nearest)
            current = nearest
        edges.append((durak_isimleri[current], durak_isimleri[0])) # Kapat
        return edges

    for o, d in run_time_nn():
        df_edges.loc[(df_edges['Origin_Node'] == o) & (df_edges['Dest_Node'] == d), 'Expert_NN'] = 1

    # Uzman 2: Global Greedy (En hızlı yolları seçer, trafiği az olanları tercih eder)
    df_edges['Rank_Origin_Cost'] = df_edges.groupby('Origin_Node')['Total_Cost_Weighted'].rank(method='dense')
    df_edges.loc[df_edges['Rank_Origin_Cost'] == 1, 'Expert_Greedy'] = 1

    # NİHAİ KOLEKTİF HEDEF: Trafik koşullarına göre en mantıklı yollar
    df_edges['Is_On_Optimal_Route'] = ((df_edges['Expert_NN'] + df_edges['Expert_Greedy']) > 0).astype(int)

    edge_csv_path = 'edge_dataset.csv'
    df_edges.to_csv(edge_csv_path, index=False, encoding='utf-8')
    
    print(f"[-] 'Trafik Ağırlıklı Kolektif Konsensüs' yöntemiyle {len(df_edges)} satırlı Edge veri seti oluşturuldu.")
    print(f"[-] Veri setinde 'Pozitif' örnek sayısı: {df_edges['Is_On_Optimal_Route'].sum()}")
    print(f"[-] Veri seti '{edge_csv_path}' adıyla kaydedildi.")

    # --- YENİ EKLENEN ROTA İNŞA FONKSİYONU ---
    def rota_insa_et_ve_ciz(model_name, model, df_edges, X_test, y_test, X_all, n_durak, isimler, matris_df, df_sample):
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        # Test Verisi Üzerinden Gerçek Performans İncelemesi (Ezberi Bozmak İçin)
        preds_test = model.predict(X_test)
        probs_test = model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, preds_test)
        prec = precision_score(y_test, preds_test, zero_division=0)
        rec = recall_score(y_test, preds_test, zero_division=0)
        f1 = f1_score(y_test, preds_test, zero_division=0)
        auc = roc_auc_score(y_test, probs_test)
        
        print(f"\n[+] {model_name} SINIFLANDIRMA PERFORMANSI (Görülmemiş Test Seti):")
        print(f"    - Genel Başarı (Accuracy) : %{acc*100:.2f} (Öğrenilen/Tahmin Edilen Doğru Oranı)")
        print(f"    - Kesinlik (Precision)    : %{prec*100:.2f} (Oluşturduğu rotaya 1 dediğinde ne kadar haklı?)")
        print(f"    - Duyarlılık (Recall)     : %{rec*100:.2f} (Gerçek NN rotasının ne kadarını bulabildi?)")
        print(f"    - F1 Skoru (Denge)        : %{f1*100:.2f} (Harmonik Ortalama)")
        print(f"    - Eğri Altında Kalan Alan : %{auc*100:.2f} (ROC-AUC - Sınıfları Ayırt Edebilme Gücü)")
        
        # Rotayı Çizebilmek İçin Tüm Olasılıkları Çıkar
        probs_all = model.predict_proba(X_all)[:, 1]

        # (N x N) boyutunda olasılık matrisi oluşturalım
        prob_matrix = [[0.0 for _ in range(n_durak)] for _ in range(n_durak)]
        idx = 0
        for i in range(n_durak):
            for j in range(n_durak):
                if i != j:
                    prob_matrix[i][j] = probs_all[idx]
                    idx += 1
                    
        # Hızlı erişim için numpy matrisi
        m_matrix = matris_df.values
        
        best_overall_route = []
        best_overall_distance = float('inf')
        best_overall_start = -1
        
        # Elimizdeki 20 durağın her birini "Acaba buradan başlasak daha kısa sürer mi?" diye deniyoruz
        for start_node in range(n_durak):
            unvisited = set(range(n_durak))
            unvisited.remove(start_node)
            current_node = start_node
            
            route = [start_node]
            total_dist = 0.0
            
            # Açık Uçlu (Open) kapalı olmayan TSP: Tüm noktalara uğrayana kadar
            while unvisited:
                best_next = -1
                best_p = -1.0
                best_d = float('inf')
                
                # Ziyaret edilmemiş duraklar arasında en iyiyi bul
                for candidate in unvisited:
                    p = prob_matrix[current_node][candidate]
                    d = m_matrix[current_node][candidate]
                    
                    # Modelin tahmini (olasılık) yüksekse onu seç. Eşitlikte/kararsızlıkta kısa mesafeye güven!
                    if p > best_p or (p == best_p and d < best_d):
                        best_p = p
                        best_d = d
                        best_next = candidate
                        
                route.append(best_next)
                total_dist += best_d
                unvisited.remove(best_next)
                current_node = best_next
                
            # Eğer bu iterasyon modeli için şimdiye kadarki "En Kısa Rota" ise kaydet.
            if total_dist < best_overall_distance:
                best_overall_distance = total_dist
                best_overall_route = route
                best_overall_start = start_node
                
        # Seçilen Nihai Rotanın Ortalama Olasılık Güvenini (Confidence) Hesapla
        avg_confidence = 0
        total_route_time = 0
        total_route_dist = 0
        
        for i_idx in range(len(best_overall_route) - 1):
            n1 = best_overall_route[i_idx]
            n2 = best_overall_route[i_idx+1]
            avg_confidence += prob_matrix[n1][n2]
            total_route_time += maliyet_matrisi.iloc[n1, n2]
            total_route_dist += mesafe_matrisi.iloc[n1, n2]
            
        if len(best_overall_route) > 1:
            avg_confidence /= (len(best_overall_route) - 1)
                
        print(f"\n[-] {model_name} Tarafından En Uygun Bulunan Başlangıç Noktası (Orijin): {isimler[best_overall_start]}")
        print(f"[-] Bu rotanın model tarafından öngörülen ortalama seçilme olasılığı (Confidence): %{avg_confidence*100:.2f}")
        print(f"[-] Optimize Edilen En Hızlı Rota Toplam Süresi (Trafikli): {total_route_time:.2f} dk")
        print(f"[-] Bu rotanın toplam fiziksel mesafesi: {total_route_dist:.2f} km")
        print("\n[+] Rota İstikamet Adımları:")
        for step, n_idx in enumerate(best_overall_route):
            print(f"    {step+1}. {isimler[n_idx]}")
            
        # Görselleştirme
        plt.figure(figsize=(12, 8))
        plt.scatter(df_sample['Longitude'], df_sample['Latitude'], c='blue', marker='o', s=100, label='Duraklar', zorder=5)
        
        for _, row in df_sample.iterrows():
            kisa_adi = str(row['Durak_Adi'])[:20]
            plt.annotate(kisa_adi, (row['Longitude'], row['Latitude']), 
                         xytext=(5, 5), textcoords='offset points', fontsize=8, zorder=6)
                         
        c_color = 'green' if 'Random Forest' in model_name else ('orange' if 'XGBoost' in model_name else 'purple')
        
        # Tahmin edilen en iyi rotayı sırayla ardışık şekilde çiz
        for i_idx in range(len(best_overall_route) - 1):
            n1 = best_overall_route[i_idx]
            n2 = best_overall_route[i_idx+1]
            n1_lon, n1_lat = duraklar[n1]['Longitude'], duraklar[n1]['Latitude']
            n2_lon, n2_lat = duraklar[n2]['Longitude'], duraklar[n2]['Latitude']
            
            # Çizgi çek
            plt.plot([n1_lon, n2_lon], [n1_lat, n2_lat], c=c_color, linestyle='-', linewidth=2, alpha=0.7, zorder=4)
            
            # Hat boyunca yönü gösteren bir ok işareti ekle
            dx = (n2_lon - n1_lon) * 0.5
            dy = (n2_lat - n1_lat) * 0.5
            plt.arrow(n1_lon, n1_lat, dx, dy, shape='full', lw=0, length_includes_head=True, head_width=0.003, color=c_color, zorder=5)

        # Başlangıç(Start) ve Bitiş(End) Noktasını Simgelerle Göster
        s_idx = best_overall_route[0]
        e_idx = best_overall_route[-1]
        plt.scatter(duraklar[s_idx]['Longitude'], duraklar[s_idx]['Latitude'], c='gold', marker='*', s=350, label='BAŞLANGIÇ', zorder=7)
        plt.scatter(duraklar[e_idx]['Longitude'], duraklar[e_idx]['Latitude'], c='black', marker='X', s=150, label='BİTİŞ', zorder=7)

        plt.title(f'{model_name} Heuristic Rehberliği ile Trafik Ağırlıklı En Hızlı Rota', fontsize=14)
        plt.xlabel('Boylam (Longitude)', fontsize=12)
        plt.ylabel('Enlem (Latitude)', fontsize=12)
        plt.grid(True, linestyle=':', alpha=0.6, zorder=0)
        plt.legend()
        
        # Model ismine göre grafiği kaydet
        if 'Random Forest' in model_name: g_name = 'rf_continuous_route.png'
        elif 'XGBoost' in model_name: g_name = 'xgb_continuous_route.png'
        else: g_name = 'stack_continuous_route.png'
        
        plt.savefig(g_name, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"\n[-] Rota haritası '{g_name}' adıyla başarıyla kaydedildi.")
        
        # Animasyonlu web sunumu için koordinatları listeleyelim
        route_coords = []
        for i in range(len(best_overall_route)):
            n_idx = best_overall_route[i]
            
            # Bir sonraki durağa olan trafik yükünü de ekleyelim (Görselleştirme için)
            t_factor = 0
            if i < len(best_overall_route) - 1:
                next_idx = best_overall_route[i+1]
                t_factor = trafik_matrisi.iloc[n_idx, next_idx]
                
            route_coords.append({
                'name': duraklar[n_idx]['Durak_Adi'],
                'lat': float(duraklar[n_idx]['Latitude']),
                'lng': float(duraklar[n_idx]['Longitude']),
                'trafficFactor': float(t_factor)
            })
            
        return {
            'Model': model_name,
            'Accuracy': acc * 100,
            'Precision': prec * 100,
            'Recall': rec * 100,
            'F1 Skoru': f1 * 100,
            'ROC-AUC': auc * 100,
            'Confidence': avg_confidence * 100,
            'Duration': total_route_time,
            'Distance': total_route_dist,
            'RouteCoords': route_coords
        }


    time.sleep(5)
    print("\n" + "="*50)
    print(" 7. AŞAMA: RANDOM FOREST (BAGGING) İLE KESİNTİSİZ ROTA ÇİZİMİ ")
    print("="*50)

    # Veri setimizi artık modeller farklı özellikler keşfetsin diye bölüyoruz.
    # Böylece modeller tamamen her şeyi ezberleyemeyecek, farklı rotalar bulacaktır.
    from sklearn.model_selection import train_test_split
    
    # Eğitim Özellikleri: Mesafe + Baz Süre + Trafik Katsayısı
    # Bu özellikler modelin trafiğe göre en mantıklı yolu seçmesini sağlar.
    X_tamami = df_edges[['Distance_km', 'Base_Duration_min', 'Traffic_Factor', 'Rank_Origin_Cost']]
    y_hedef = df_edges['Is_On_Optimal_Route']
    
    X_train, X_test, y_train, y_test = train_test_split(X_tamami, y_hedef, test_size=0.3, stratify=y_hedef, random_state=42)

    # --- DENGELİ KOLEKTİF EĞİTİM (OVERSAMPLING) ---
    # Pozitif örnekleri (1) çoğaltarak modellerin (RF, XGB) "tembellik" yapmasını engelliyoruz.
    # Bu adım, bildiri formatındaki raporunuzda 'Veri Dengeleme (Class Balancing)' olarak yer alacak kritik bir adımdır.
    oran = int(y_train.value_counts()[0] / (y_train.value_counts()[1] + 1))
    X_train_pos = X_train[y_train == 1]
    y_train_pos = y_train[y_train == 1]
    
    X_train = pd.concat([X_train] + [X_train_pos] * max(1, oran), ignore_index=True)
    y_train = pd.concat([y_train] + [y_train_pos] * max(1, oran), ignore_index=True)
    try:
        from sklearn.ensemble import RandomForestClassifier
        
        # Modeli kısıtlamak (max_depth) aşırı öğrenmeyi engeller ve modelleri farklılaştırır.
        rf_model = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight='balanced')
        rf_model.fit(X_train, y_train)
        m_rf = rota_insa_et_ve_ciz('Random Forest', rf_model, df_edges, X_test, y_test, X_tamami, n, durak_isimleri, mesafe_matrisi, df_sampled)
        if m_rf: tum_metrikler.append(m_rf)
        
    except Exception as e:
        print(f"[-] Random Forest aşamasında bir hata oluştu: {e}")

    time.sleep(5)
    print("\n" + "="*50)
    print(" 8. AŞAMA: XGBOOST (BOOSTING) İLE KESİNTİSİZ ROTA ÇİZİMİ ")
    print("="*50)

    try:
        from xgboost import XGBClassifier
        
        ratio = float(y_train.value_counts()[0]) / y_train.value_counts()[1]
        xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', max_depth=3, scale_pos_weight=ratio, random_state=42)
        xgb_model.fit(X_train, y_train)
        m_xgb = rota_insa_et_ve_ciz('XGBoost', xgb_model, df_edges, X_test, y_test, X_tamami, n, durak_isimleri, mesafe_matrisi, df_sampled)
        if m_xgb: tum_metrikler.append(m_xgb)
        
    except Exception as e:
        print(f"[-] XGBoost aşamasında bir hata oluştu: {e}")

    time.sleep(5)
    print("\n" + "="*50)
    print(" 9. AŞAMA: STACKING META-MODEL İLE KESİNTİSİZ ROTA ÇİZİMİ ")
    print("="*50)

    try:
        from sklearn.ensemble import StackingClassifier
        from sklearn.linear_model import LogisticRegression
        import warnings
        warnings.filterwarnings("ignore")
        
        base_models = [
            ('rf', RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight='balanced')),
            ('xgb', XGBClassifier(use_label_encoder=False, eval_metric='logloss', max_depth=3, scale_pos_weight=ratio, random_state=42))
        ]
        
        meta_model = LogisticRegression(class_weight='balanced', random_state=42)
        stack_model = StackingClassifier(estimators=base_models, final_estimator=meta_model, cv=5)
        stack_model.fit(X_train, y_train)
        m_stack = rota_insa_et_ve_ciz('Stacking Meta-Model', stack_model, df_edges, X_test, y_test, X_tamami, n, durak_isimleri, mesafe_matrisi, df_sampled)
        if m_stack: tum_metrikler.append(m_stack)
        
    except Exception as e:
        print(f"[-] Stacking aşamasında bir hata oluştu: {e}")

    time.sleep(2)
    print("\n" + "="*50)
    print(" 10. AŞAMA: MODELLERİN PERFORMANS KIYASLAMA GRAFİĞİ ")
    print("="*50)
    
    if len(tum_metrikler) > 0:
        import numpy as np
        df_metrics = pd.DataFrame(tum_metrikler)
        metric_cols = ['Accuracy', 'Precision', 'Recall', 'F1 Skoru', 'ROC-AUC']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        n_models = len(df_metrics)
        width = 0.15
        x = np.arange(len(metric_cols))
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        
        for i, row in df_metrics.iterrows():
            bar_positions = x + (i * width) - (width * (n_models - 1) / 2)
            metrik_degerleri = [row[col] for col in metric_cols]
            ax.bar(bar_positions, metrik_degerleri, width, label=row['Model'], color=colors[i % len(colors)])
                   
        ax.set_ylabel('Yüzde (%)', fontsize=12)
        ax.set_title('Test Verisi Üzerinde Modellerin Sınıflandırma Performansı Karşılaştırması', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(metric_cols, fontsize=11)
        ax.legend(title='Algoritmalar')
        
        plt.ylim(0, 105)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        karsilastirma_gorsel_yolu = 'modellerin_kiyaslamasi.png'
        plt.savefig(karsilastirma_gorsel_yolu, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"[-] Modellerin test seti üzerindeki performans metriklerini kıyaslayan grafik '{karsilastirma_gorsel_yolu}' adıyla oluşturulup kaydedildi.")
        
        # WEB SUNUMU İÇİN DATAYI DIŞARI ÇIKARMA
        try:
            import os
            
            web_folder = 'web_sunum'
            if not os.path.exists(web_folder):
                os.makedirs(web_folder)
                
            web_data = {
                'allStops': duraklar, 
                'models': tum_metrikler
            }
            
            class NumpyEncoder(json.JSONEncoder):
                def default(self, obj):
                    import numpy as np
                    if isinstance(obj, np.floating):
                        return float(obj)
                    if isinstance(obj, np.integer):
                        return int(obj)
                    if isinstance(obj, np.ndarray):
                        return obj.tolist()
                    return super(NumpyEncoder, self).default(obj)
                    
            js_content = "const presentationData = " + json.dumps(web_data, ensure_ascii=False, indent=2, cls=NumpyEncoder) + ";"
            with open(os.path.join(web_folder, 'data.js'), 'w', encoding='utf-8') as f:
                f.write(js_content)
                
            print("[-] Animasyonlu Web Sunumu için 'web_sunum/data.js' dosyası başarıyla üretildi.")
        except Exception as e:
            print(f"[-] Web verisi oluşturulurken hata: {e}")
            
    else:
        print("[-] Metrik verisi bulunamadığı için grafik çizilemedi.")


if __name__ == "__main__":
    main()
