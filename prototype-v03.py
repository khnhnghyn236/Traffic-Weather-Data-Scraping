import requests
import pandas as pd
from datetime import datetime
import time
import os
import sys

# ==========================================
# 1. CREDENTIALS & SETTINGS
# ==========================================
TOMTOM_KEY = "YOUR_TOMTOM_KEY"
WEATHER_KEY = "YOUR_WEATHER_KEY"

ROUTES_BBOX = {
    # "Road_Name": "min_lon,min_lat,max_lon,max_lat",
    #  Example:
    # "Long Bien Bridge": "105.8483,21.0380,105.8677,21.0480",
}

# ==========================================
# 2. LOCALIZED WEATHER FETCHING
# ==========================================
def get_current_weather(lat, lon):
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_KEY}&units=metric"
        response = requests.get(url)
        
        if response.status_code == 200:
            res = response.json()
            weather_desc = res.get('weather', [{}])[0].get('main', 'Clear')
            rain_1h = res.get('rain', {}).get('1h', 0.0) 
            temp = res.get('main', {}).get('temp', 0.0)
            wind_speed = res.get('wind', {}).get('speed', 0.0)
            return weather_desc, rain_1h, temp, wind_speed
        return "Error", 0.0, 0.0, 0.0
    except:
        return "Error", 0.0, 0.0, 0.0

# ==========================================
# 3. PRE-LABELED DATA COLLECTION CYCLE
# ==========================================
def fetch_incident_data():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    hour_of_day = now.hour
    day_of_week = now.strftime("%A") 
    
    print(f"\n--- Incident Scan: {timestamp} ---")

    for route_name, bbox in ROUTES_BBOX.items():
        try:
            # 1. Get approximate center of the bounding box for weather
            parts = bbox.split(',')
            center_lon = (float(parts[0]) + float(parts[2])) / 2
            center_lat = (float(parts[1]) + float(parts[3])) / 2
            
            weather_desc, rain_1h, temp, wind_speed = get_current_weather(center_lat, center_lon)
            
            # 2. Query TomTom Incidents API
            url = f"https://api.tomtom.com/traffic/services/5/incidentDetails?key={TOMTOM_KEY}&bbox={bbox}&fields={'{incidents{properties{iconCategory,magnitudeOfDelay,delay}}}'}&language=en-GB"
            response = requests.get(url)
            data = response.json()
            
            if response.status_code == 200:
                incidents = data.get('incidents', [])
                
                # 3. PARSE TRUE LABELS
                # Default states (Clear traffic)
                is_congested = 0
                incident_types_found = []
                magnitude = 0
                delay_seconds = 0
                
                # Full map of TomTom Integer IDs to Strings based on API documentation
                TARGET_CATEGORIES = {
                    0: "Unknown",
                    1: "Accident",
                    2: "Fog",
                    3: "DangerousConditions",
                    4: "Rain",
                    5: "Ice",
                    6: "Jam",
                    7: "LaneClosed",
                    8: "RoadClosed",
                    9: "RoadWorks",
                    10: "Wind",
                    11: "Flooding",
                    14: "BrokenDownVehicle"
                }
                
                # If there are incidents inside our box, process them
                if len(incidents) > 0:
                    for inc in incidents:
                        props = inc['properties']
                        cat_id = props.get('iconCategory', -1)
                        
                        # Check if the integer ID is in our target list
                        if cat_id in TARGET_CATEGORIES:
                            is_congested = 1
                            incident_types_found.append(TARGET_CATEGORIES[cat_id])
                            
                            # Safely handle 'None' values by falling back to 0
                            mag = props.get('magnitudeOfDelay') or 0
                            magnitude = max(magnitude, mag)
                            
                            delay = props.get('delay') or 0
                            delay_seconds = max(delay_seconds, delay)
                            
                # Join multiple incident types if they exist (e.g., "Jam, RoadWorks"), otherwise "None"
                # Using set() removes duplicates so we don't get "Jam, Jam"
                final_incident_type = ", ".join(set(incident_types_found)) if incident_types_found else "None"

                # 4. COMPILE ROW
                row_data = {
                    "timestamp": timestamp,
                    "route_name": route_name,
                    "hour_of_day": hour_of_day,
                    "day_of_week": day_of_week,
                    "weather_condition": weather_desc,
                    "temperature_celsius": temp,
                    "rain_1h_mm": rain_1h,
                    "wind_speed_ms": wind_speed,
                    "is_congested": is_congested,
                    "incident_type": final_incident_type,
                    "incident_magnitude": magnitude,
                    "reported_delay_seconds": delay_seconds
                }
                
                # 5. DYNAMIC CSV SAVING
                safe_filename = route_name.replace(' ', '_') + ".csv"
                df = pd.DataFrame([row_data])
                df.to_csv(safe_filename, mode='a', header=not os.path.exists(safe_filename), index=False)
                
                status_icon = "🔴" if is_congested == 1 else "🟢"
                print(f"{status_icon} {route_name}: Logged -> Saved to {safe_filename} | Type: {final_incident_type} | Delay: {delay_seconds}s")
                
            else:
                print(f"❌ {route_name} error {response.status_code}.")
                
        except Exception as e:
            print(f"⚠️ {route_name} failed: {e}")
            
    print("💾 Scan complete.")

if __name__ == "__main__":
    while True:
        fetch_incident_data()
        
        total_seconds = 1200 # 20 minutes
        
        print("\n" + "="*30)
        while total_seconds > 0:
            mins, secs = divmod(total_seconds, 60)
            timer = f"⏳ Next scan in: {mins:02d}:{secs:02d}"
            print(timer, end="\r")
            
            time.sleep(1)
            total_seconds -= 1
            
        # Clear the countdown line before the next scan starts
        print("🚀 Starting new scan...          ")