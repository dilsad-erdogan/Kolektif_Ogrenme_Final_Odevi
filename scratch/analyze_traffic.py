
import pandas as pd
import json

def analyze_traffic_data(file_path):
    print(f"Analyzing {file_path}...")
    
    # Read just a subset for quick analysis
    df_sample = pd.read_csv(file_path, nrows=50000)
    
    # Basic Info
    print("\n--- Basic Information ---")
    print(df_sample.info())
    
    # Time Range
    df_sample['DATE_TIME'] = pd.to_datetime(df_sample['DATE_TIME'])
    print(f"\nTime Range (first 50k): {df_sample['DATE_TIME'].min()} to {df_sample['DATE_TIME'].max()}")
    
    # Geographic Range
    print("\n--- Geographic Coverage ---")
    print(f"Latitude:  {df_sample['LATITUDE'].min():.4f} to {df_sample['LATITUDE'].max():.4f}")
    print(f"Longitude: {df_sample['LONGITUDE'].min():.4f} to {df_sample['LONGITUDE'].max():.4f}")
    print(f"Unique Geohashes (Sample): {df_sample['GEOHASH'].nunique()}")
    
    # Average Speeds
    print("\n--- Speed Statistics ---")
    print(df_sample[['MINIMUM_SPEED', 'MAXIMUM_SPEED', 'AVERAGE_SPEED']].describe())
    
    # Check for specific hours (e.g., peak hour)
    peak_hour = df_sample[df_sample['DATE_TIME'].dt.hour == 8]
    if not peak_hour.empty:
        print(f"\nMorning Peak (08:00) Mean Average Speed: {peak_hour['AVERAGE_SPEED'].mean():.2f} km/h")
    
    # Check a late night hour
    night_hour = df_sample[df_sample['DATE_TIME'].dt.hour == 3]
    if not night_hour.empty:
        print(f"Late Night (03:00) Mean Average Speed: {night_hour['AVERAGE_SPEED'].mean():.2f} km/h")

if __name__ == "__main__":
    analyze_traffic_data('IETT Trafik.csv')
