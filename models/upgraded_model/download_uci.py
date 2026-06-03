# models/upgraded_model/download_uci.py
"""
Utility script to download the UCI Occupancy Detection dataset containing Temperature, Humidity, and actual CO2.
"""
import urllib.request
import os

def download_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    url = "https://raw.githubusercontent.com/LuisM78/Occupancy-Detection-1/master/datatraining.txt"
    dest_path = os.path.join(data_dir, "uci_occupancy.csv")
    
    print(f"[*] Downloading famous UCI Occupancy dataset from: {url}")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print(f"[+] Download complete! Saved to {dest_path}")
        
        # Read a few lines to check
        with open(dest_path, 'r') as f:
            for _ in range(5):
                print("  ", f.readline().strip())
    except Exception as e:
        print(f"[!] Error downloading dataset: {e}")

if __name__ == "__main__":
    download_data()
