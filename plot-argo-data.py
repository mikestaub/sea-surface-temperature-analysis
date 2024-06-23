import argopy
from argopy import DataFetcher as ArgoDataFetcher
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import pickle
import os
import argparse

def fetch_argo_data(date, argo_loader, max_depth):
    ds = argo_loader.region([-180, 180, -60, 60, 0, max_depth,
                             date.strftime("%Y-%m-%d"),
                             (date + timedelta(days=1)).strftime("%Y-%m-%d")]).to_xarray()
    df = ds.to_dataframe().reset_index()
    df = df[(df['PRES'] >= 0) & (df['PRES'] <= max_depth)]
    return df

def load_cached_day(date, cache_dir):
    cache_file = os.path.join(cache_dir, f"argo_data_{date.strftime('%Y%m%d')}.pkl")
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return None

def save_cached_day(data, date, cache_dir):
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file = os.path.join(cache_dir, f"argo_data_{date.strftime('%Y%m%d')}.pkl")
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)

def main(days_to_plot, rolling_window):
    argo_loader = ArgoDataFetcher(src='argovis', parallel=True, progress=True)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days_to_plot + rolling_window - 1)  # Extend start date for rolling average

    cache_dir = 'argo_data_cache'

    all_data = []
    current_date = start_date
    while current_date <= end_date:
        print(f"Processing date: {current_date}")
        daily_data = load_cached_day(current_date, cache_dir)
        if daily_data is None:
            print("  Fetching from Argo...")
            daily_data = fetch_argo_data(current_date, argo_loader, 20)
            save_cached_day(daily_data, current_date, cache_dir)
        else:
            print("  Loaded from cache.")
        all_data.append(daily_data)
        current_date += timedelta(days=1)

    df = pd.concat(all_data, ignore_index=True)

    print("Processing data...")
    df['TIME'] = pd.to_datetime(df['TIME'])
    df['date'] = df['TIME'].dt.date
    daily_temp = df.groupby('date')['TEMP'].mean().reset_index()
    
    # Calculate rolling average
    daily_temp['rolling_avg'] = daily_temp['TEMP'].rolling(window=rolling_window, center=True).mean()
    
    # Trim the data to the requested number of days
    daily_temp = daily_temp.iloc[-(days_to_plot):]

    print("Creating plot...")
    plt.figure(figsize=(15, 10))
    plt.plot(daily_temp['date'], daily_temp['TEMP'], label='Daily Average', alpha=0.5)
    plt.plot(daily_temp['date'], daily_temp['rolling_avg'], label=f'{rolling_window}-day Rolling Average', linewidth=2)
    plt.title(f'Sea Surface Temperature, World (60°S-60°N, 0-360°E)\nLast {days_to_plot} days', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Temperature (°C)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.text(0.02, 0.02, 'Dataset: Argo float data (Argovis)', transform=plt.gca().transAxes, fontsize=8)
    
    # Save the plot as sst.png
    plt.savefig('sst.png')
    plt.show()

    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot sea surface temperature for a specified number of days with rolling average.")
    parser.add_argument("days", type=int, help="Number of days to plot")
    parser.add_argument("--window", type=int, default=7, help="Size of the rolling average window (default: 7)")
    args = parser.parse_args()
    
    main(args.days, args.window)