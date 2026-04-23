
import pandas as pd
import os

def preprocess_traffic(input_file, output_file, target_hour=8):
    print(f"Loading {input_file} for preprocessing...")
    
    # Read the data
    # 135MB fits in memory, but we can use usecols to be efficient
    cols = ['DATE_TIME', 'LATITUDE', 'LONGITUDE', 'AVERAGE_SPEED', 'MAXIMUM_SPEED', 'NUMBER_OF_VEHICLES']
    df = pd.read_csv(input_file, usecols=cols)
    
    print("Converting DATE_TIME...")
    df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'])
    
    print(f"Filtering for hour {target_hour}...")
    df_hour = df[df['DATE_TIME'].dt.hour == target_hour].copy()
    
    if df_hour.empty:
        print(f"Warning: No data found for hour {target_hour}. Using all data as fallback.")
        df_hour = df.copy()
    
    print("Aggregating by location...")
    # Group by Lat/Lon to get a spatial profile
    traffic_profile = df_hour.groupby(['LATITUDE', 'LONGITUDE']).agg({
        'AVERAGE_SPEED': 'mean',
        'MAXIMUM_SPEED': 'max',
        'NUMBER_OF_VEHICLES': 'mean'
    }).reset_index()
    
    print(f"Processed into {len(traffic_profile)} unique locations.")
    traffic_profile.to_csv(output_file, index=False)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    preprocess_traffic('IETT Trafik.csv', 'traffic_summary_hour8.csv', target_hour=8)
