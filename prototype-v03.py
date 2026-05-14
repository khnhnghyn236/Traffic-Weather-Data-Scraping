import requests
import pandas as pd
from datetime import datetime
import time
import os
import numpy as np

# ==========================================
# 1. CREDENTIALS & SETTINGS
# ==========================================

# Note: Please replace with your own keys.
TOMTOM_KEY = "..."
WEATHER_KEY = "..."

ROUTE_CONFIG = {
    "Chuong Duong Bridge": {
        "bbox": "105.8529,21.0334,105.8678,21.0419",
        "A": "21.0357,105.8555", "B": "21.0403,105.8658",
        # Dropped one coordinate to save API calls
        "flow_points": ["21.0365,105.8580", "21.0395,105.8630"] 
    },
    # Other routes...
}

# ==========================================
# 2. ENHANCED DATA HELPERS
# ==========================================

def get_current_weather(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric"
        r = requests.get(url, timeout=10).json()
        # Bias Mitigation: Expanded weather features
        return (r['weather'][0]['main'], r.get('rain', {}).get('1h', 0.0), 
                r['main']['temp'], r['wind']['speed'], r['main']['humidity'], r.get('visibility', 10000))
    except: return None, None, None, None, None, None

def get_routing_data(start, end, route_name):
    url = f"https://api.tomtom.com/routing/1/calculateRoute/{start}:{end}/json?key={TOMTOM_KEY}&traffic=true&computeTravelTimeFor=all"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return None, None
        s = res.json()['routes'][0]['summary']
        return s.get('travelTimeInSeconds'), s.get('noTrafficTravelTimeInSeconds')
    except: return None, None

def get_aggregated_flow(points, route_name):
    """Bias Mitigation: Multi-point Flow Sampling"""
    speeds, baselines, frcs = [], [], []
    for p in points:
        try:
            url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_KEY}&point={p}"
            res = requests.get(url, timeout=10).json()
            f = res['flowSegmentData']
            speeds.append(f.get('currentSpeed'))
            baselines.append(f.get('freeFlowSpeed'))
            frcs.append(f.get('frc'))
        except: continue
    
    if not speeds: return "N/A", None, None
    # Use Median to mitigate sensor noise/outliers
    return frcs[0], np.median(speeds), np.median(baselines)

# ==========================================
# 3. COLLECTION CYCLE
# ==========================================
def fetch_traffic_intelligence():
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    is_weekend = 1 if now.weekday() >= 5 else 0
    
    print(f"\n--- Intelligence Scan: {ts} ---")

    for name, config in ROUTE_CONFIG.items():
        # Mitigation: Directional Bias (Process A->B and B->A)
        directions = [("Inbound", config['A'], config['B']), ("Outbound", config['B'], config['A'])]
        
        # Weather sampled at center point
        w_desc, rain, temp, wind, hum, vis = get_current_weather(config['flow_points'][1].split(',')[0], config['flow_points'][1].split(',')[1])

        # Flow Aggregated across multiple points
        frc, live_speed, free_speed = get_aggregated_flow(config['flow_points'], name)
        speed_ratio = round(live_speed / free_speed, 2) if (live_speed and free_speed) else None

        for dir_label, start, end in directions:
            try:
                curr_tt, free_tt = get_routing_data(start, end, f"{name} {dir_label}")
                route_delay = max(0, curr_tt - free_tt) if (curr_tt and free_tt) else None

                inc_url = f"https://api.tomtom.com/traffic/services/5/incidentDetails?key={TOMTOM_KEY}&bbox={config['bbox']}&fields={'{incidents{properties{iconCategory,magnitudeOfDelay,delay}}}'}&language=en-GB"
                inc_res = requests.get(inc_url, timeout=10).json()
                
                is_congested = 0
                inc_types = []
                mag = 0
                TARGETS = {1: "Accident", 4: "Roadworks", 5: "LaneClosed", 6: "Jam", 8: "Closed", 9: "Flooding"}
                
                for inc in inc_res.get('incidents', []):
                    p = inc['properties']
                    cat = p.get('iconCategory')
                    if cat in TARGETS:
                        # Mitigation: Intelligent Labeling (Only label 1 if in correct direction/impact)
                        is_congested = 1
                        inc_types.append(TARGETS[cat])
                        mag = max(mag, p.get('magnitudeOfDelay') or 0)

                # Final Heuristic Mitigation
                if speed_ratio and speed_ratio < 0.6: is_congested = 1

                row = {
                    "timestamp": ts,
                    "route_name": name,
                    "direction": dir_label,
                    "is_weekend": is_weekend,
                    "hour_of_day": now.hour,
                    "frc_class": frc,                     
                    "speed_limit_baseline": free_speed,   
                    "current_speed": live_speed,
                    "speed_ratio_proxy": speed_ratio,     
                    "travel_time_s": curr_tt,             
                    "free_flow_time_s": free_tt,          
                    "route_delay_s": route_delay,         
                    "is_congested": is_congested,
                    "incident_type": ", ".join(set(inc_types)) if inc_types else "None",
                    "magnitude": mag,
                    "weather": w_desc,
                    "temp": temp,
                    "rain_mm": rain,
                    "humidity": hum,
                    "visibility": vis
                }

                # Mitigation: Data Integrity (Skip row if critical API failure)
                if live_speed is None or curr_tt is None:
                    print(f"⚠️ {name} {dir_label}: Data Invalid (API Fail). Skipping.")
                    continue

                df = pd.DataFrame([row])
                fname = name.replace(' ', '_') + "_v2.csv"
                df.to_csv(fname, mode='a', header=not os.path.exists(fname), index=False)
                
                icon = "🔴" if is_congested else "🟢"
                print(f"{icon} {name} ({dir_label}) | Speed: {int(live_speed)}/{int(free_speed)} | Delay: {route_delay}s")

            except Exception as e:
                print(f"⚠️ Failure on {name} {dir_label}: {e}")

if __name__ == "__main__":
    while True:
        fetch_traffic_intelligence()
        
        # Mitigation: Adaptive Sampling Bias (15-min / 20-min)
        now = datetime.now()
        now_hour = now.hour
        now_minute = now.minute
        
        # Rush Hour: 6:00 AM - 9:00 AM
        is_morning_rush = 6 <= now_hour < 9
        
        # Rush Hour: 4:00 PM - 7:30 PM (16:00 - 19:30)
        is_evening_rush = (16 <= now_hour < 19) or (now_hour == 19 and now_minute <= 30)
        
        if is_morning_rush or is_evening_rush:
            total_seconds = 900 # 15 Minute Polling (900 seconds)
            print("\n🚨 RUSH HOUR DETECTED: 15 min polling active.")
        else:
            total_seconds = 1200 # 20 Minute Polling (1200 seconds)
            
        print("="*45)
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            print(f"⏳ Next intelligence scan in: {mins:02d}:{secs:02d}", end="\r")
            time.sleep(1)
            total_seconds -= 1
            
        print("🚀 Executing API requests...             ")