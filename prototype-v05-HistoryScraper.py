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

# Stratified hours exactly as specified in your design
STRATEGIC_HOURS = [
    "03:00:00", "07:10:00", "07:30:00", "10:00:00", "12:00:00", 
    "15:00:00", "16:00:00", "17:10:00", "20:00:00", "22:30:00"
]

# SPATIAL REFINEMENT: Updated A/B to cover the bridge deck span specifically
# South (Hai Ba Trung end) to North (Long Bien end)
ROUTE_CONFIG = {
    "Vinh Tuy Bridge": {
        "A": "21.0041,105.8778", 
        "B": "21.0223,105.8931",
        "frc": 2
    }
}

# ==========================================
# 2. ENHANCED LOGIC HELPERS
# ==========================================

def get_nearest_weather(hourly_data, target_time_str):
    """Mitigates Temporal Bias: Finds weather hour closest to the traffic sample"""
    if not hourly_data: return {}
    
    target_dt = datetime.strptime(target_time_str, "%H:%M:%S")
    
    # Find the weather hour with the smallest time difference
    closest_hour = min(
        hourly_data,
        key=lambda h: abs(
            datetime.strptime(h['datetime'], "%H:%M:%S") - target_dt
        )
    )
    return closest_hour

def get_historical_routing(start, end, timestamp):
    """Paced Historical Routing with Error Logging"""
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start}:{end}/json?key={TOMTOM_KEY}&traffic=true&departAt={timestamp}&computeTravelTimeFor=all"
    try:
        time.sleep(0.25) # Increased pacing for stability
        res = requests.get(url, timeout=12)
        if res.status_code != 200: 
            print(f"❌ API Error {res.status_code} at {timestamp}")
            return None, None, None, None
            
        s = res.json()['routes'][0]['summary']
        curr_tt = s.get('travelTimeInSeconds')
        free_tt = s.get('noTrafficTravelTimeInSeconds', curr_tt) 
        length_m = s.get('lengthInMeters')
        
        live_speed = round((length_m / curr_tt) * 3.6, 1) if curr_tt else None
        free_speed = round((length_m / free_tt) * 3.6, 1) if free_tt else None
        
        return curr_tt, free_tt, live_speed, free_speed
    except Exception as e:
        print(f"⚠️ Connection Error: {e}")
        return None, None, None, None

# ==========================================
# 3. BATCH PROCESSOR ENGINE
# ==========================================
def run_historical_batch(start_day_offset, days_to_scrape):
    for d in range(start_day_offset, start_day_offset + days_to_scrape):
        target_date = (datetime.now() - timedelta(days=d))
        date_str = target_date.strftime("%Y-%m-%d")
        is_weekend = 1 if target_date.weekday() >= 5 else 0
        
        print(f"\n📅 Processing Date: {date_str}")
        
        for name, nodes in ROUTE_CONFIG.items():
            lat, lon = nodes['A'].split(',')
            
            # Fetch weather profile once per day
            w_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{date_str}?unitGroup=metric&key={VISUAL_CROSSING_KEY}&include=hours"
            hourly_weather = requests.get(w_url).json().get('days', [{}])[0].get('hours', [])
            
            for t_hour in STRATEGIC_HOURS:
                timestamp = f"{date_str}T{t_hour}"
                ts = f"{date_str} {t_hour}"
                hour_val = int(t_hour.split(':')[0])
                
                # Logic Fix 1: Nearest-Hour Weather Alignment
                wh = get_nearest_weather(hourly_weather, t_hour)
                
                w_desc = wh.get('conditions', "Clear")
                temp = float(wh.get('temp', 0.0))
                rain = float(wh.get('precip', 0.0)) # Note: interpreted as hourly accumulation
                hum = float(wh.get('humidity', 0.0))
                vis = float(wh.get('visibility', 10.0) * 1000)
                
                directions = [("Inbound", nodes['A'], nodes['B']), ("Outbound", nodes['B'], nodes['A'])]
                
                for dir_label, start, end in directions:
                    curr_tt, free_tt, live_speed, free_speed = get_historical_routing(start, end, timestamp)
                    
                    if curr_tt is None: continue 
                    
                    route_delay = max(0, curr_tt - free_tt)
                    speed_ratio = round(live_speed / free_speed, 2) if (free_speed and free_speed > 0) else 1.0
                    
                    # Logic Fix 2: Refined Congestion Interpretation (Avoiding name changes)
                    is_congested = 1 if speed_ratio < 0.65 else 0
                    inc_types = "Congested" if is_congested else "None"
                    mag = 2 if is_congested else 0

                    row = {
                        "timestamp": ts,
                        "route_name": name,
                        "direction": dir_label,
                        "is_weekend": is_weekend,
                        "hour_of_day": hour_val,
                        "frc_class": nodes['frc'],                     
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
                    fname = f"VINH_TUY_OFFSET_{start_day_offset}.csv"
                    df.to_csv(fname, mode='a', header=not os.path.exists(fname), index=False)
                    
                print(f"  ✅ Logged {t_hour}", end="\r")

if __name__ == "__main__":
    # --- TEAM MEMBER 1 (The Recent Past) ---
    # run_historical_batch(start_day_offset=1, days_to_scrape=121)
    
    # --- TEAM MEMBER 2 (The Middle Months) ---
    # run_historical_batch(start_day_offset=122, days_to_scrape=122)
    
    # --- TEAM MEMBER 3 (The Deep Past) ---
    # run_historical_batch(start_day_offset=244, days_to_scrape=122)
    
    pass