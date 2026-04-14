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

    time.sleep(5)
    print("\n" + "="*50)
    print(" 7. AŞAMA: RANDOM FOREST İLE MODEL EĞİTİMİ (BAGGING) ")
    print("="*50)

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
        
        # Özellikler (Features) ve Hedef (Target)
        X = df_edges[['Origin_Lon', 'Origin_Lat', 'Dest_Lon', 'Dest_Lat', 'Distance_km']]
        y = df_edges['Is_On_Optimal_Route']
        
        # Train-Test Split (%80 Eğitim, %20 Test)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Model Tanımlama ve Eğitme
        # Dengesiz veri setlerinde (az sayıda 1, çok sayıda 0) class_weight='balanced' kullanmak performansı artırır.
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        rf_model.fit(X_train, y_train)
        
        # Tahminler
        y_pred = rf_model.predict(X_test)
        
        # Sonuç Tabloları
        print("\n[-] Random Forest Sınıflandırma Raporu (Classification Report):\n")
        print(classification_report(y_test, y_pred, zero_division=0))
        
        print("\n[-] Karmaşıklık Matrisi (Confusion Matrix):\n")
        print(confusion_matrix(y_test, y_pred))
        
        # Özellik Önem Dereceleri (Feature Importances)
        feature_importances = pd.DataFrame(rf_model.feature_importances_, index=X.columns, columns=['Importance']).sort_values('Importance', ascending=False)
        print("\n[-] Özellik Önem Dereceleri:\n")
        print(feature_importances)
        
        # Tahmin Edilen Rota'yı Görselleştirelim
        # Algoritmanın tüm veri seti üzerinde (test ve train birlikte) neyi 1 olarak nitelendirdiğini görelim
        df_edges['RF_Prediction'] = rf_model.predict(X)
        
        # Tahmin edilen rota kenarları (Tahmini 1 olanlar)
        predicted_edges = df_edges[df_edges['RF_Prediction'] == 1]
        
        plt.figure(figsize=(12, 8))
        # Durakları grafikte nokta olarak işaretle
        plt.scatter(df_sampled['Longitude'], df_sampled['Latitude'], c='blue', marker='o', s=100, label='Duraklar', zorder=5)
        
        # İsim etiketleri
        for idx, row in df_sampled.iterrows():
            durak_kisa_adi = str(row['Durak_Adi'])[:20]
            plt.annotate(durak_kisa_adi, (row['Longitude'], row['Latitude']), 
                         xytext=(5, 5), textcoords='offset points', fontsize=8, zorder=6)
                         
        # Tahmin Edilen Kenarları (Rotayı) Bağla
        for _, edge in predicted_edges.iterrows():
            plt.plot([edge['Origin_Lon'], edge['Dest_Lon']], 
                     [edge['Origin_Lat'], edge['Dest_Lat']], 
                     c='green', linestyle='-', linewidth=2, alpha=0.7, zorder=4)
                     
        # Gerçek (En Yakın Komşu) rotasını da kıyaslamak için hafif şeffaf kırmızı çizgilerle ekleyelim (Opsiyonel)
        real_edges = df_edges[df_edges['Is_On_Optimal_Route'] == 1]
        for _, edge in real_edges.iterrows():
            plt.plot([edge['Origin_Lon'], edge['Dest_Lon']], 
                     [edge['Origin_Lat'], edge['Dest_Lat']], 
                     c='red', linestyle=':', linewidth=1, alpha=0.5, zorder=3)
                     
        # Grafiğin görsel özellikleri için legend'a manuel elemanlar ekleyelim
        plt.plot([], [], c='green', linestyle='-', linewidth=2, label='RF Tahmini (Prediction=1)')
        plt.plot([], [], c='red', linestyle=':', linewidth=1, label='Gerçek (Is_Optimal=1)')
        
        plt.title('Random Forest Sınıflandırıcısı ile Tahmin Edilen Kenarlar (Rota Öğrenimi)', fontsize=14)
        plt.xlabel('Boylam (Longitude)', fontsize=12)
        plt.ylabel('Enlem (Latitude)', fontsize=12)
        plt.grid(True, linestyle=':', alpha=0.6, zorder=0)
        plt.legend()
        
        # Görseli çıktı olarak kaydet
        rf_gorsel_yolu = 'rf_predicted_route.png'
        plt.savefig(rf_gorsel_yolu, dpi=300, bbox_inches='tight')
        plt.close() # Belleği temizle
        print(f"\n[-] Random Forest tarafından tahmin edilen rotanın görsel haritası '{rf_gorsel_yolu}' adıyla başarıyla kaydedildi.")
        
    except ImportError:
        print("[-] Hata: 'scikit-learn' kütüphanesi eksik. Lütfen 'pip install scikit-learn' komutu ile yükleyin ve tekrar deneyin.")

    time.sleep(5)
    print("\n" + "="*50)
    print(" 8. AŞAMA: XGBOOST İLE MODEL EĞİTİMİ (BOOSTING) ")
    print("="*50)

    try:
        from xgboost import XGBClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report, confusion_matrix
        
        # Önceden hazırlanan veriyi kullanalım
        X = df_edges[['Origin_Lon', 'Origin_Lat', 'Dest_Lon', 'Dest_Lat', 'Distance_km']]
        y = df_edges['Is_On_Optimal_Route']
        
        # Train-Test Split (%80 Eğitim, %20 Test)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Model Tanımlama ve Eğitme
        # Dengesizlik (Imbalance) ile mücadele etmek için scale_pos_weight kullanıyoruz
        # scale_pos_weight = (Sınıf 0 Sayısı) / (Sınıf 1 Sayısı)
        ratio = float(y_train.value_counts()[0]) / y_train.value_counts()[1]
        
        xgb_model = XGBClassifier(use_label_encoder=False, eval_metric='logloss', scale_pos_weight=ratio, random_state=42)
        xgb_model.fit(X_train, y_train)
        
        # Tahminler
        y_pred_xgb = xgb_model.predict(X_test)
        
        # Sonuç Tabloları
        print("\n[-] XGBoost Sınıflandırma Raporu (Classification Report):\n")
        print(classification_report(y_test, y_pred_xgb, zero_division=0))
        
        print("\n[-] Karmaşıklık Matrisi (Confusion Matrix):\n")
        print(confusion_matrix(y_test, y_pred_xgb))
        
        # Özellik Önem Dereceleri (Feature Importances)
        xgb_feature_importances = pd.DataFrame(xgb_model.feature_importances_, index=X.columns, columns=['Importance']).sort_values('Importance', ascending=False)
        print("\n[-] Özellik Önem Dereceleri:\n")
        print(xgb_feature_importances)
        
        # Tahmin Edilen Rota'yı Görselleştirelim
        df_edges['XGB_Prediction'] = xgb_model.predict(X)
        predicted_edges_xgb = df_edges[df_edges['XGB_Prediction'] == 1]
        
        plt.figure(figsize=(12, 8))
        plt.scatter(df_sampled['Longitude'], df_sampled['Latitude'], c='blue', marker='o', s=100, label='Duraklar', zorder=5)
        
        for idx, row in df_sampled.iterrows():
            durak_kisa_adi = str(row['Durak_Adi'])[:20]
            plt.annotate(durak_kisa_adi, (row['Longitude'], row['Latitude']), 
                         xytext=(5, 5), textcoords='offset points', fontsize=8, zorder=6)
                         
        for _, edge in predicted_edges_xgb.iterrows():
            plt.plot([edge['Origin_Lon'], edge['Dest_Lon']], 
                     [edge['Origin_Lat'], edge['Dest_Lat']], 
                     c='orange', linestyle='-', linewidth=2, alpha=0.7, zorder=4)
                     
        real_edges = df_edges[df_edges['Is_On_Optimal_Route'] == 1]
        for _, edge in real_edges.iterrows():
            plt.plot([edge['Origin_Lon'], edge['Dest_Lon']], 
                     [edge['Origin_Lat'], edge['Dest_Lat']], 
                     c='red', linestyle=':', linewidth=1, alpha=0.5, zorder=3)
                     
        plt.plot([], [], c='orange', linestyle='-', linewidth=2, label='XGBoost Tahmini (Prediction=1)')
        plt.plot([], [], c='red', linestyle=':', linewidth=1, label='Gerçek Rota (Is_Optimal=1)')
        
        plt.title('XGBoost Sınıflandırıcısı ile Tahmin Edilen Kenarlar', fontsize=14)
        plt.xlabel('Boylam (Longitude)', fontsize=12)
        plt.ylabel('Enlem (Latitude)', fontsize=12)
        plt.grid(True, linestyle=':', alpha=0.6, zorder=0)
        plt.legend()
        
        xgb_gorsel_yolu = 'xgb_predicted_route.png'
        plt.savefig(xgb_gorsel_yolu, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"\n[-] XGBoost tarafından tahmin edilen rotanın görsel haritası '{xgb_gorsel_yolu}' adıyla başarıyla kaydedildi.")
        
    except ImportError:
        print("[-] Hata: 'xgboost' kütüphanesi eksik. Lütfen 'pip install xgboost' komutu ile yükleyin ve tekrar deneyin.")


if __name__ == "__main__":
    main()
