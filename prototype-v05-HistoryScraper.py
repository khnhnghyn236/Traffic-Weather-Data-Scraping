import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# ==========================================
# 1. CREDENTIALS & SETTINGS
# ==========================================
TOMTOM_KEY = "YOUR_TOMTOM_KEY_HERE"
VISUAL_CROSSING_KEY = "YOUR_VISUAL_CROSSING_KEY_HERE"

# STRATIFIED SAMPLING: Added baseline and off-peak transition hours
STRATEGIC_HOURS = [
    "03:00:00", # Absolute overnight baseline
    "07:10:00", # Morning peak
    "07:30:00", # Morning peak 2
    "10:00:00", # Morning post-peak transition
    "12:00:00", # Midday baseline
    "15:00:00", # Afternoon pre-peak transition
    "16:00:00", # Afternoon peak
    "17:10:00", # Evening peak
    "20:00:00", # Evening recovery
    "22:30:00"  # Late night baseline
]

ROUTE_CONFIG = {
    "Vinh Tuy Bridge": {
        "A": "21.0000,105.8700", "B": "21.0250,105.8950",
        "frc": 2  # Hardcoded structural FRC for Vinh Tuy
    }
}

# ==========================================
# 2. HISTORICAL DATA HELPERS
# ==========================================
def get_hourly_weather_profile(lat, lon, date_str):
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{date_str}?unitGroup=metric&key={VISUAL_CROSSING_KEY}&include=hours"
    try:
        r = requests.get(url, timeout=10).json()
        return r['days'][0].get('hours', [])
    except: return []

def get_historical_routing(start, end, timestamp):
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start}:{end}/json?key={TOMTOM_KEY}&traffic=true&departAt={timestamp}&computeTravelTimeFor=all"
    try:
        time.sleep(0.2) 
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return None, None, None, None
            
        s = res.json()['routes'][0]['summary']
        curr_tt = s.get('travelTimeInSeconds')
        free_tt = s.get('noTrafficTravelTimeInSeconds', curr_tt) 
        length_m = s.get('lengthInMeters')
        
        live_speed = round((length_m / curr_tt) * 3.6, 1) if curr_tt else None
        free_speed = round((length_m / free_tt) * 3.6, 1) if free_tt else None
        
        return curr_tt, free_tt, live_speed, free_speed
    except: return None, None, None, None

# ==========================================
# 3. BATCH PROCESSOR ENGINE
# ==========================================
def run_historical_batch(start_day_offset=1, days_to_scrape=120):
    for d in range(start_day_offset, start_day_offset + days_to_scrape):
        target_date = (datetime.now() - timedelta(days=d))
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Match original schema datatypes
        is_weekend = 1 if target_date.weekday() >= 5 else 0
        
        print(f"\n📅 Processing Date: {date_str}")
        
        for name, nodes in ROUTE_CONFIG.items():
            lat, lon = nodes['A'].split(',')
            hourly_weather = get_hourly_weather_profile(lat, lon, date_str)
            frc = nodes['frc']
            
            for t_hour in STRATEGIC_HOURS:
                timestamp = f"{date_str}T{t_hour}"
                ts = f"{date_str} {t_hour}" # Original timestamp format
                hour_of_day = int(t_hour.split(':')[0])
                
                # Extract strict weather metrics
                w_desc = "Clear"
                temp = rain = hum = vis = 0.0
                for hour_data in hourly_weather:
                    if hour_data.get('datetime') == f"{hour_of_day:02d}:00:00":
                        w_desc = hour_data.get('conditions', "Clear")
                        temp = float(hour_data.get('temp', 0.0))
                        rain = float(hour_data.get('precip', 0.0))
                        hum = float(hour_data.get('humidity', 0.0))
                        vis = float(hour_data.get('visibility', 10.0) * 1000) # Convert km to meters
                        break
                
                directions = [("Inbound", nodes['A'], nodes['B']), ("Outbound", nodes['B'], nodes['A'])]
                
                for dir_label, start, end in directions:
                    curr_tt, free_tt, live_speed, free_speed = get_historical_routing(start, end, timestamp)
                    
                    if curr_tt is None: continue 
                    
                    route_delay = max(0, curr_tt - free_tt)
                    speed_ratio = round(live_speed / free_speed, 2) if free_speed else 1.0
                    
                    # Heuristic fallback for incidents (Since historical APIs lack live incidents)
                    is_congested = 1 if speed_ratio < 0.6 else 0
                    inc_types = "Historical Jam" if is_congested else "None"
                    mag = 2 if is_congested else 0

                    # EXACT ORIGINAL DICTIONARY PRESERVED
                    row = {
                        "timestamp": ts,
                        "route_name": name,
                        "direction": dir_label,
                        "is_weekend": is_weekend,
                        "hour_of_day": hour_of_day,
                        "frc_class": frc,                     
                        "speed_limit_baseline": free_speed,   
                        "current_speed": live_speed,
                        "speed_ratio_proxy": speed_ratio,     
                        "travel_time_s": curr_tt,             
                        "free_flow_time_s": free_tt,          
                        "route_delay_s": route_delay,         
                        "is_congested": is_congested,
                        "incident_type": inc_types,
                        "magnitude": mag,
                        "weather": w_desc,
                        "temp": temp,
                        "rain_mm": rain,
                        "humidity": hum,
                        "visibility": vis
                    }
                    
                    df = pd.DataFrame([row])
                    fname = "VINH_TUY_HISTORICAL_MASTER.csv"
                    df.to_csv(fname, mode='a', header=not os.path.exists(fname), index=False)
                    
                print(f"  ✅ Logged {t_hour}", end="\r")

if __name__ == "__main__":
    # --- TEAM MEMBER 1 ---
    # run_historical_batch(start_day_offset=1, days_to_scrape=121)
    
    # --- TEAM MEMBER 2 ---
    # run_historical_batch(start_day_offset=122, days_to_scrape=122)
    
    # --- TEAM MEMBER 3 ---
    # run_historical_batch(start_day_offset=244, days_to_scrape=122)
    
    pass # Remove 'pass' and uncomment your assigned line above!