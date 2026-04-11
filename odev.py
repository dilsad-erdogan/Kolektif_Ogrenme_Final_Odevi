import json
import pandas as pd
import math
import matplotlib.pyplot as plt

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

if __name__ == "__main__":
    main()
