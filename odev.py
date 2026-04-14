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

    print("\n[-] Temizlenmiş DataFrame'in İlk 5 Satırı:\n")
    print(df_filtered.head())
    
    time.sleep(2)
    print("\n" + "="*50)
    print(" 3. AŞAMA: RASTGELE ÖRNEKLEM SEÇİMİ (20 DURAK) ")
    print("="*50)

    # 20 adet rastgele durak seç

    #rastgelelik
    # # Artık 'random_state' sabitlemesi YOK, yani kodu her çağırdığınızda yepyeni 20 durak seçecek.
    # df_sampled = df_filtered.sample(n=20)

    # (Sunumlarda kod her çalıştığında aynı 20 durağı versin ki sürpriz olmasın diye random_state=42 ayarlıyoruz)
    df_sampled = df_filtered.sample(n=20, random_state=42)

    print("[-] Temizlenmiş veri seti içinden rastgele 20 durak seçildi.")
    print("[-] Seçilen 20 durağın ilk 5 satırı:\n")
    print(df_sampled.head())

    # Sadece seçilen 20 satırı kaydet
    kayit_yolu = 'secilmis_veriler.csv'
    df_sampled.to_csv(kayit_yolu, index=False, encoding='utf-8')
    print(f"\n[-] Sadece rastgele seçilen 20 durak '{kayit_yolu}' adıyla başarıyla kaydedildi.")

    time.sleep(2)
    print("\n" + "="*50)
    print(" 4. AŞAMA: MESAFE HESAPLAMA (HAVERSINE MATRİSİ) ")
    print("="*50)
    
    # nxn Mesafe matrisi oluşturalım
    duraklar = df_sampled.to_dict('records')
    n = len(duraklar)
    durak_isimleri = [d['Durak_Adi'] for d in duraklar]
    
    mesafe_matrisi = pd.DataFrame(index=durak_isimleri, columns=durak_isimleri)
                                  
    for i in range(n):
        for j in range(n):
            if i == j:
                mesafe_matrisi.iloc[i, j] = 0.0
            else:
                d1 = duraklar[i]
                d2 = duraklar[j]
                dist = haversine(d1['Longitude'], d1['Latitude'], d2['Longitude'], d2['Latitude'])
                mesafe_matrisi.iloc[i, j] = dist
                
    # Görüntüleme için float yapalım
    mesafe_matrisi = mesafe_matrisi.astype(float)
                
    print("[-] Seçilen 20 durak arasındaki mesafeler Haversine formülü ile başarıyla hesaplandı.")
    print("[-] Örnek olarak ilk 5 durağın birbirine olan mesafesi (km) tablosu:\n")
    print(mesafe_matrisi.iloc[:5, :5].round(2))
    
    # Matrisi CSV olarak kaydet
    matris_kayit_yolu = 'mesafe_matrisi.csv'
    mesafe_matrisi.to_csv(matris_kayit_yolu, encoding='utf-8')
    print(f"\n[-] 20x20 Tam Mesafe Matrisi '{matris_kayit_yolu}' adıyla başarıyla kaydedildi.")

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
                         
        plt.title('Seçilen 20 İETT Durağının Konum Dağılımı Haritası', fontsize=14)
        plt.xlabel('Boylam (Longitude)', fontsize=12)
        plt.ylabel('Enlem (Latitude)', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7, zorder=0)
        plt.legend()
        
        # Görseli çıktı olarak kaydet
        gorsel_yolu = 'secilen_duraklar_haritasi.png'
        plt.savefig(gorsel_yolu, dpi=300, bbox_inches='tight')
        plt.close() # Belleği temizle
        print(f"[-] 20 durağın görsel haritası '{gorsel_yolu}' adıyla başarıyla tasarlanıp kaydedildi.")
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
                
                # Kenar özellikleri
                edge = {
                    'Origin_Node': d1['Durak_Adi'],
                    'Origin_Lon': d1['Longitude'],
                    'Origin_Lat': d1['Latitude'],
                    'Dest_Node': d2['Durak_Adi'],
                    'Dest_Lon': d2['Longitude'],
                    'Dest_Lat': d2['Latitude'],
                    'Distance_km': mesafe_matrisi.iloc[i, j]
                }
                edge_data.append(edge)
                
    df_edges = pd.DataFrame(edge_data)
    
    # Basit bir rota tahmini yapabilmek için 'Target' (Hedef) değişkenine ihtiyacımız olacak.
    # Şimdilik tüm hedef değişkenleri 0 olarak atıyoruz. 
    # Bir TSP çözümleyici (örn. En Yakın Komşu veya OR-Tools) eklendiğinde rota üzerindeki kenarlar '1' yapılabilir.
    df_edges['Is_On_Optimal_Route'] = 0 
    
    # Nearest Neighbor ile kabaca bir rota bulup bu rotadaki kenarları hedef=1 yapalım
    # Başlangıç durağı ilk durak (indeks 0)
    # Gidilmeyen duraklar kümesi (kalan 19 durak)
    current_node_idx = 0
    unvisited = set(range(1, n))
    route_edges = []
    
    while unvisited:
        # En yakın durağı bul
        nearest_node_idx = None
        min_dist = float('inf')
        for neighbor_idx in unvisited:
            dist = mesafe_matrisi.iloc[current_node_idx, neighbor_idx]
            if dist < min_dist:
                min_dist = dist
                nearest_node_idx = neighbor_idx
                
        # Rotaya kenarı ekle (current -> nearest)
        route_edges.append((durak_isimleri[current_node_idx], durak_isimleri[nearest_node_idx]))
        
        current_node_idx = nearest_node_idx
        unvisited.remove(nearest_node_idx)
        
    # Rotayı kapat (Son duraktan ilk durağa dön)
    route_edges.append((durak_isimleri[current_node_idx], durak_isimleri[0]))
    
    # route_edges içindeki Origin-Dest çiftlerini df_edges'te 1 olarak etiketle
    for origin, dest in route_edges:
        df_edges.loc[(df_edges['Origin_Node'] == origin) & (df_edges['Dest_Node'] == dest), 'Is_On_Optimal_Route'] = 1

    edge_csv_path = 'edge_dataset.csv'
    df_edges.to_csv(edge_csv_path, index=False, encoding='utf-8')
    
    print(f"[-] Bagging, Boosting ve Stacking için {len(df_edges)} satırlı Edge (Kenar) Veri Seti oluşturuldu.")
    print("[-] En Yakın Komşu (Nearest Neighbor) algoritması temel alınarak 'Is_On_Optimal_Route' hedefi(1 veya 0) belirlendi.")
    print(f"[-] Veri seti '{edge_csv_path}' adıyla kaydedildi.")
    print("\n[-] Veri Setinden İlk 5 Satır:\n")
    print(df_edges.head())

    # --- YENİ EKLENEN ROTA İNŞA FONKSİYONU ---
    def rota_insa_et_ve_ciz(model_name, model, df_edges, X_all, n_durak, isimler, matris_df, df_sample):
        # Tüm veri üzerinden modelin olasılık tahminlerini al (sınıf "1" dendiği durumların olasılığı)
        probs = model.predict_proba(X_all)[:, 1]
        
        # (N x N) boyutunda olasılık matrisi oluşturalım
        prob_matrix = [[0.0 for _ in range(n_durak)] for _ in range(n_durak)]
        idx = 0
        for i in range(n_durak):
            for j in range(n_durak):
                if i != j:
                    prob_matrix[i][j] = probs[idx]
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
                
        print(f"\n[-] {model_name} Tarafından En Uygun Bulunan Başlangıç Noktası (Orijin): {isimler[best_overall_start]}")
        print(f"[-] Optimize Edilen En Kısa Açık Uçlu Rota Toplam Mesafesi: {best_overall_distance:.2f} km")
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

        plt.title(f'{model_name} Heuristic Rehberliği ile Kesintisiz En Kısa Rota', fontsize=14)
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
        print(f"\n[-] Kesintisiz rota haritası '{g_name}' adıyla başarıyla kaydedildi.")


    time.sleep(5)
    print("\n" + "="*50)
    print(" 7. AŞAMA: RANDOM FOREST (BAGGING) İLE KESİNTİSİZ ROTA ÇİZİMİ ")
    print("="*50)

    try:
        from sklearn.ensemble import RandomForestClassifier
        
        # Makine öğrenmesini "değerlendirici" (Heuristic Critic) olarak tüm veri setiyle eğitiyoruz. 
        # Train/Test ayırmıyoruz, amacımız bu 20 duraklık haritada en iyi kuralı(path'i) buldurtmak.
        X_tamami = df_edges[['Origin_Lon', 'Origin_Lat', 'Dest_Lon', 'Dest_Lat', 'Distance_km']]
        y_hedef = df_edges['Is_On_Optimal_Route']
        
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        rf_model.fit(X_tamami, y_hedef)
        
        rota_insa_et_ve_ciz('Random Forest', rf_model, df_edges, X_tamami, n, durak_isimleri, mesafe_matrisi, df_sampled)
        
    except Exception as e:
        print(f"[-] Random Forest aşamasında bir hata oluştu: {e}")

    time.sleep(5)
    print("\n" + "="*50)
    print(" 8. AŞAMA: XGBOOST (BOOSTING) İLE KESİNTİSİZ ROTA ÇİZİMİ ")
    print("="*50)

    try:
        from xgboost import XGBClassifier
        
        ratio = float(y_hedef.value_counts()[0]) / y_hedef.value_counts()[1]
        xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', scale_pos_weight=ratio, random_state=42)
        xgb_model.fit(X_tamami, y_hedef)
        
        rota_insa_et_ve_ciz('XGBoost', xgb_model, df_edges, X_tamami, n, durak_isimleri, mesafe_matrisi, df_sampled)
        
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
            ('rf', RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')),
            ('xgb', XGBClassifier(use_label_encoder=False, eval_metric='logloss', scale_pos_weight=ratio, random_state=42))
        ]
        
        meta_model = LogisticRegression(class_weight='balanced', random_state=42)
        stack_model = StackingClassifier(estimators=base_models, final_estimator=meta_model, cv=5)
        stack_model.fit(X_tamami, y_hedef)
        
        rota_insa_et_ve_ciz('Stacking Meta-Model', stack_model, df_edges, X_tamami, n, durak_isimleri, mesafe_matrisi, df_sampled)
        
    except Exception as e:
        print(f"[-] Stacking aşamasında bir hata oluştu: {e}")


if __name__ == "__main__":
    main()
