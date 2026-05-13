import requests
import pandas as pd
from datetime import datetime
import time
import os
import numpy as np

# ==========================================
# 1. CREDENTIALS & SETTINGS
# ==========================================
TOMTOM_KEY = "..."
WEATHER_KEY = "..."

# UPDATED: Added Point A, Point B, and multiple flow sampling points
ROUTE_CONFIG = {
    "Long Bien Bridge": {
        "bbox": "105.8483,21.0380,105.8677,21.0480",
        "A": "21.0401,105.8505", "B": "21.0455,105.8652",
        "flow_points": ["21.0410,105.8530", "21.0428,105.8578", "21.0440,105.8620"]
    },
    "Chuong Duong Bridge": {
        "bbox": "105.8529,21.0334,105.8678,21.0419",
        "A": "21.0357,105.8555", "B": "21.0403,105.8658",
        "flow_points": ["21.0365,105.8580", "21.0381,105.8603", "21.0395,105.8630"]
    },
    "Nhat Tan Bridge": {
        "bbox": "105.8134,21.0804,105.8291,21.1169",
        "A": "21.0850,105.8200", "B": "21.1150,105.8250",
        "flow_points": ["21.0900,105.8210", "21.1000,105.8225", "21.1100,105.8240"]
    },
    "Thang Long Bridge": {
        "bbox": "105.7835,21.0853,105.7895,21.1148",
        "A": "21.0870,105.7860", "B": "21.1130,105.7870",
        "flow_points": ["21.0900,105.7862", "21.1000,105.7865", "21.1100,105.7868"]
    },
    "Vinh Tuy Bridge": {
        "bbox": "105.8676,20.9970,105.8972,21.0270",
        "A": "21.0000,105.8700", "B": "21.0250,105.8950",
        "flow_points": ["21.0050,105.8750", "21.0125,105.8825", "21.0200,105.8900"]
    },
    "Thanh Tri Bridge": {
        "bbox": "105.8904,20.9814,105.9146,21.0079",
        "A": "20.9850,105.8950", "B": "21.0050,105.9120",
        "flow_points": ["20.9900,105.8980", "20.9950,105.9035", "21.0000,105.9080"]
    },
    "Xuan Thuy Road": {
        "bbox": "105.7789,21.0342,105.7917,21.0383",
        "A": "21.0365,105.7800", "B": "21.0375,105.7910",
        "flow_points": ["21.0368,105.7820", "21.0370,105.7850", "21.0372,105.7880"]
    },
    "Nguyen Trai Street": {
        "bbox": "105.7993,20.9880,105.8218,21.0050",
        "A": "20.9900,105.8000", "B": "21.0040,105.8200",
        "flow_points": ["20.9930,105.8050", "20.9970,105.8100", "21.0000,105.8150"]
    }
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

                # Mitigation: Expanded Incident Taxonomy
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
        
        # Mitigation: Adaptive Sampling Bias
        now_hour = datetime.now().hour
        # Rush Hour: 7-9 AM, 4-7 PM
        if (7 <= now_hour <= 9) or (16 <= now_hour <= 19):
            total_seconds = 300 # 5 Minute Polling
            print("\n🚨 RUSH HOUR DETECTED: Increasing sampling rate to 5 mins.")
        else:
            total_seconds = 1200 # 20 Minute Polling
        
        print("="*45)
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            print(f"⏳ Next intelligence scan in: {mins:02d}:{secs:02d}", end="\r")
            time.sleep(1)
            total_seconds -= 1
        print("🚀 Executing API requests...             ")