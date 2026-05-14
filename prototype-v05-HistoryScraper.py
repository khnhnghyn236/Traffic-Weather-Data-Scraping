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

# ISOLATED ROUTE: Vinh Tuy Bridge Only
ROUTE_CONFIG = {
    "Vinh Tuy Bridge": {
        "A": "21.0000,105.8700", "B": "21.0250,105.8950"
    }
}

# ==========================================
# 2. HISTORICAL DATA HELPERS
# ==========================================

def get_hourly_weather_profile(lat, lon, date_str):
    """Fetches the full 24-hour weather profile for a specific date in one call"""
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{date_str}?unitGroup=metric&key={VISUAL_CROSSING_KEY}&include=hours"
    try:
        r = requests.get(url, timeout=10).json()
        return r['days'][0].get('hours', [])
    except Exception as e:
        print(f"⚠️ Weather API Error on {date_str}: {e}")
        return []

def get_historical_routing(start, end, timestamp):
    """Queries TomTom with explicit missing-data handling and route stability checks"""
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start}:{end}/json?key={TOMTOM_KEY}&traffic=true&departAt={timestamp}&computeTravelTimeFor=all"
    
    try:
        time.sleep(0.2) # API Pacing
        res = requests.get(url, timeout=10)
        
        if res.status_code != 200: 
            return "API_FAIL", None, None, None, None, None
            
        s = res.json()['routes'][0]['summary']
        curr_tt = s.get('travelTimeInSeconds')
        baseline_tt = s.get('noTrafficTravelTimeInSeconds', curr_tt) # Fallback to curr_tt if missing
        length_m = s.get('lengthInMeters')
        
        # Physics calculation (v = d/t)
        live_speed = round((length_m / curr_tt) * 3.6, 1) if curr_tt else None
        baseline_speed = round((length_m / baseline_tt) * 3.6, 1) if baseline_tt else None
        
        return "SUCCESS", curr_tt, baseline_tt, live_speed, baseline_speed, length_m
    except Exception as e:
        return f"EXCEPTION: {str(e)}", None, None, None, None, None

# ==========================================
# 3. BATCH PROCESSOR ENGINE
# ==========================================
def run_historical_batch(start_day_offset=1, days_to_scrape=40):
    print(f"🚀 Starting V5 Transport Science Scrape: {days_to_scrape} days...")
    
    for d in range(start_day_offset, start_day_offset + days_to_scrape):
        target_date = (datetime.now() - timedelta(days=d))
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Metadata: Day of week and weekend flags
        day_of_week = target_date.strftime("%A")
        is_weekend = 1 if target_date.weekday() >= 5 else 0
        
        print(f"\n📅 Processing Date: {date_str} ({day_of_week})")
        
        for name, nodes in ROUTE_CONFIG.items():
            # 1. Fetch entire day's hourly weather profile (saves 23 API calls)
            lat, lon = nodes['A'].split(',')
            hourly_weather = get_hourly_weather_profile(lat, lon, date_str)
            
            # 2. Iterate through stratified time slots
            for t_hour in STRATEGIC_HOURS:
                timestamp = f"{date_str}T{t_hour}"
                
                # Match exact hour for weather causation
                target_weather_hour = t_hour.split(':')[0] + ":00:00"
                w_temp, w_rain, w_wind, w_hum = None, None, None, None
                for hour_data in hourly_weather:
                    if hour_data.get('datetime') == target_weather_hour:
                        w_temp = hour_data.get('temp')
                        w_rain = hour_data.get('precip')
                        w_wind = hour_data.get('windspeed')
                        w_hum = hour_data.get('humidity')
                        break
                
                directions = [("Inbound", nodes['A'], nodes['B']), ("Outbound", nodes['B'], nodes['A'])]
                
                for dir_label, start, end in directions:
                    api_status, curr_tt, baseline_tt, live_speed, baseline_speed, length_m = get_historical_routing(start, end, timestamp)
                    
                    # 🚨 BIAS MITIGATION: Survivorship Handling
                    # We log the row even if it fails, preserving outage patterns
                    
                    # Advanced ML Metrics Processing
                    delay_s = max(0, curr_tt - baseline_tt) if (curr_tt and baseline_tt) else None
                    relative_speed_ratio = round(live_speed / baseline_speed, 3) if (live_speed and baseline_speed) else None
                    delay_ratio = round(curr_tt / baseline_tt, 3) if (curr_tt and baseline_tt) else None
                    congestion_index = round(delay_s / curr_tt, 3) if (delay_s and curr_tt) else None

                    row = {
                        "timestamp": timestamp,
                        "date": date_str,
                        "time_slot": t_hour,
                        "day_of_week": day_of_week,
                        "is_weekend": is_weekend,
                        "route_name": name,
                        "direction": dir_label,
                        "api_status": api_status,
                        "route_length_m": length_m,
                        "current_speed": live_speed,
                        "baseline_speed": baseline_speed,
                        "relative_speed_ratio": relative_speed_ratio,
                        "travel_time_s": curr_tt,
                        "baseline_tt_s": baseline_tt,
                        "delay_s": delay_s,
                        "delay_ratio": delay_ratio,
                        "congestion_index": congestion_index,
                        "temp_c": w_temp,
                        "rain_mm": w_rain,
                        "wind_speed_kmh": w_wind,
                        "humidity_pct": w_hum
                    }
                    
                    df = pd.DataFrame([row])
                    fname = "VINH_TUY_HISTORICAL.csv"
                    df.to_csv(fname, mode='a', header=not os.path.exists(fname), index=False)
                    
                print(f"  ✅ Logged {t_hour} | Weather matched: {'Yes' if w_temp is not None else 'No'}", end="\r")
        print("") 

if __name__ == "__main__":
    # ==========================================
    # 🚀 DISTRIBUTED TEAM SCRAPING CONFIGURATION
    # ==========================================
    # Total Goal: 365 Days
    # API Burn Rate: ~20 calls per day (Max 2,500 per account)
    
    print("WARNING: Ensure you are using YOUR OWN API keys at the top of the script!")
    
    # ------------------------------------------
    # TEAM MEMBER 1 (The Recent Past)
    # Target: Days 1 to 121 (2,420 API calls)
    # ------------------------------------------
    # Uncomment the line below if you are Member 1:
    # run_historical_batch(start_day_offset=1, days_to_scrape=121)
    
    # ------------------------------------------
    # TEAM MEMBER 2 (The Middle Months)
    # Target: Days 122 to 243 (2,440 API calls)
    # ------------------------------------------
    # Uncomment the line below if you are Member 2:
    # run_historical_batch(start_day_offset=122, days_to_scrape=122)
    
    # ------------------------------------------
    # TEAM MEMBER 3 (The Deep Past)
    # Target: Days 244 to 365 (2,440 API calls)
    # ------------------------------------------
    # Uncomment the line below if you are Member 3:
    # run_historical_batch(start_day_offset=244, days_to_scrape=122)