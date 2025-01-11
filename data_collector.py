import os
import pandas as pd

# Ana klasörün yolunu belirtin
ana_klasor = r'C:\Users\aatak\Desktop\workspace\KETI'

# Birleştirilmiş veriler için liste
merged_data = []

# Alt klasörleri döngüyle gez
for alt_klasor in os.listdir(ana_klasor):
    alt_klasor_yolu = os.path.join(ana_klasor, alt_klasor)
    if os.path.isdir(alt_klasor_yolu):  # Alt klasörse
        try:
            # Dosyaları oku
            co2 = pd.read_csv(os.path.join(alt_klasor_yolu, 'co2.csv'), header=None, names=['timestamp', 'co2'])
            light = pd.read_csv(os.path.join(alt_klasor_yolu, 'light.csv'), header=None, names=['timestamp', 'light'])
            temperature = pd.read_csv(os.path.join(alt_klasor_yolu, 'temperature.csv'), header=None, names=['timestamp', 'temp'])
            humidity = pd.read_csv(os.path.join(alt_klasor_yolu, 'humidity.csv'), header=None, names=['timestamp', 'humidity'])
            pir = pd.read_csv(os.path.join(alt_klasor_yolu, 'pir.csv'), header=None, names=['timestamp', 'pir'])
            
            # Tüm dosyaları zaman damgasına (timestamp) göre birleştir
            df = co2.merge(light, on='timestamp').merge(temperature, on='timestamp').merge(humidity, on='timestamp').merge(pir, on='timestamp')
            
            # Oda bilgisini ekle
            df['room'] = alt_klasor

            # Zaman damgasını okunabilir formata çevir
            df['event_ts_min'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Dakika bazında yuvarlama
            df['event_ts_min'] = df['event_ts_min'].dt.floor('T')

            # Zaman damgasını UNIX'e dönüştür
            df['ts_min_bignt'] = df['event_ts_min'].astype(int) // 10**9
            
            # Dakika bazında gruplama ve ortalamaları alma
            grouped = df.groupby(['event_ts_min', 'ts_min_bignt', 'room']).mean().reset_index()

            # Listeye ekle
            merged_data.append(grouped)
        except Exception as e:
            print(f"{alt_klasor} için hata: {e}")

# Tüm grupları birleştir
final_df = pd.concat(merged_data, ignore_index=True)

# Sonucu bir CSV dosyasına kaydet
final_df.to_csv(r'C:\Users\aatak\Desktop\workspace\merged_sensor_data_grouped.csv', index=False)

print("Birleştirme ve gruplama işlemi tamamlandı, dosya kaydedildi.")
