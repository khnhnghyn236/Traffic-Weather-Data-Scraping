import requests
import pandas as pd
from datetime import datetime
import time
import os

# ==========================================
# 1. CREDENTIALS & SETTINGS
# ==========================================
TOMTOM_KEY = "..."
WEATHER_KEY = "..."

# Added Start/End points for Routing and a Point-on-Road for Flow/FRC data
ROUTE_CONFIG = {
    "Long Bien Bridge": {
        "bbox": "105.8483,21.0380,105.8677,21.0480",
        "start": "21.0401,105.8505", "end": "21.0455,105.8652", "point": "21.0428,105.8578"
    },
    "Chuong Duong Bridge": {
        "bbox": "105.8529,21.0334,105.8678,21.0419",
        "start": "21.0361,105.8551", "end": "21.0402,105.8655", "point": "21.0381,105.8603"
    },
    "Nhat Tan Bridge": {
        "bbox": "105.8134,21.0804,105.8291,21.1169",
        "start": "21.0850,105.8200", "end": "21.1150,105.8250", "point": "21.1000,105.8225"
    },
    "Thang Long Bridge": {
        "bbox": "105.7835,21.0853,105.7895,21.1148",
        "start": "21.0870,105.7860", "end": "21.1130,105.7870", "point": "21.1000,105.7865"
    },
    "Vinh Tuy Bridge": {
        "bbox": "105.8676,20.9970,105.8972,21.0270",
        "start": "21.0000,105.8700", "end": "21.0250,105.8950", "point": "21.0125,105.8825"
    },
    "Thanh Tri Bridge": {
        "bbox": "105.8904,20.9814,105.9146,21.0079",
        "start": "20.9850,105.8950", "end": "21.0050,105.9120", "point": "20.9950,105.9035"
    },
    "Xuan Thuy Road": {
        "bbox": "105.7789,21.0342,105.7917,21.0383",
        "start": "21.0365,105.7800", "end": "21.0375,105.7910", "point": "21.0370,105.7850"
    },
    "Nguyen Trai Street": {
        "bbox": "105.7993,20.9880,105.8218,21.0050",
        "start": "20.9900,105.8000", "end": "21.0040,105.8200", "point": "20.9970,105.8100"
    }
}

# ==========================================
# 2. DATA FETCHING HELPERS
# ==========================================

def get_current_weather(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric"
        r = requests.get(url).json()
        return r['weather'][0]['main'], r.get('rain', {}).get('1h', 0.0), r['main']['temp'], r['wind']['speed']
    except: return "Error", 0.0, 0.0, 0.0

def get_routing_data(start, end):
    """Features 2: Travel Time & Delay"""
    try:
        url = f"https://api.tomtom.com/routing/1/calculateRoute/{start}:{end}/json?key={TOMTOM_KEY}&traffic=true"
        r = requests.get(url).json()
        summary = r['routes'][0]['summary']
        return summary['travelTimeInSeconds'], summary['noTrafficTravelTimeInSeconds']
    except: return 0, 0

def get_flow_data(point):
    """Features 1 & 4: FRC, Speed Limit, and Historical Context"""
    try:
        # Using flowSegmentData to get FRC, Speed Limits and Live vs FreeFlow speeds
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_KEY}&point={point}"
        r = requests.get(url).json()
        flow = r['flowSegmentData']
        # FRC is Functional Road Class, currentSpeed vs freeFlowSpeed acts as volume proxy
        return flow.get('frc', 'N/A'), flow.get('currentSpeed', 0), flow.get('freeFlowSpeed', 0)
    except: return "N/A", 0, 0

# ==========================================
# 3. COLLECTION CYCLE
# ==========================================
def fetch_traffic_intelligence():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n--- Deep Intelligence Scan: {timestamp} ---")

    for name, config in ROUTE_CONFIG.items():
        try:
            # 1. Weather
            lat, lon = config['point'].split(',')
            w_desc, rain, temp, wind = get_current_weather(lat, lon)

            # 2. Routing (Travel Times)
            curr_tt, free_tt = get_routing_data(config['start'], config['end'])
            route_delay = max(0, curr_tt - free_tt)

            # 3. Flow (Road Context & Volume Proxies)
            frc, live_speed, free_speed = get_flow_data(config['point'])
            # Probe Proxy: The ratio of live speed to free flow speed is a standard proxy 
            # for probe density in modern traffic modeling.
            speed_ratio = round(live_speed / free_speed, 2) if free_speed > 0 else 1

            # 4. Incidents (BBOX)
            inc_url = f"https://api.tomtom.com/traffic/services/5/incidentDetails?key={TOMTOM_KEY}&bbox={config['bbox']}&fields={'{incidents{properties{iconCategory,magnitudeOfDelay,delay}}}'}&language=en-GB"
            inc_data = requests.get(inc_url).json()
            
            is_congested = 0
            inc_types = []
            mag = 0
            reported_delay = 0  # <--- ADD THIS VARIABLE
            
            TARGETS = {1: "Accident", 6: "Jam", 8: "Closed"}
            for inc in inc_data.get('incidents', []):
                p = inc['properties']
                if p.get('iconCategory') in TARGETS:
                    is_congested = 1
                    inc_types.append(TARGETS[p['iconCategory']])
                    mag = max(mag, p.get('magnitudeOfDelay') or 0)
                    reported_delay = max(reported_delay, p.get('delay') or 0) # <--- EXTRACT DELAY HERE

            # 5. COMPILE ENRICHED ROW
            row = {
                "timestamp": timestamp,
                "route_name": name,
                "frc_class": frc,                     
                "speed_limit_baseline": free_speed,   
                "current_speed": live_speed,
                "speed_ratio_proxy": speed_ratio,     
                "travel_time_s": curr_tt,             
                "free_flow_time_s": free_tt,          
                "route_delay_s": route_delay,         
                "is_congested": is_congested,
                "incident_type": ", ".join(set(inc_types)) if inc_types else "None",
                "incident_magnitude": mag,            # <--- RENAMED
                "reported_delay_seconds": reported_delay, # <--- ADDED
                "weather": w_desc,
                "temp": temp,
                "rain_mm": rain
            }

            # 6. SAVE
            df = pd.DataFrame([row])
            fname = name.replace(' ', '_') + ".csv"
            df.to_csv(fname, mode='a', header=not os.path.exists(fname), index=False)
            
            icon = "🔴" if is_congested or speed_ratio < 0.7 else "🟢"
            print(f"{icon} {name} | FRC: {frc} | Speed: {live_speed}/{free_speed} | Delay: {route_delay}s")

        except Exception as e:
            print(f"⚠️ {name} failed: {e}")


if __name__ == "__main__":
    while True:
        # Run the V2 intelligence scan
        fetch_traffic_intelligence()
        
        total_seconds = 1200 # 20 minutes
        
        print("\n" + "="*45)
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer = f"⏳ Next deep scan in: {mins:02d}:{secs:02d}"
            # end="\r" forces the cursor back to the start of the line
            print(timer, end="\r")
            
            time.sleep(1)
            total_seconds -= 1
            
        # The extra spaces here clear the remaining characters from the timer string
        print("🚀 Executing API requests...             ")