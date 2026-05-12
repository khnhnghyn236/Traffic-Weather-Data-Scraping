# Weather Traffic Data Collection - API Data Scraping

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Data Source](https://img.shields.io/badge/data-TomTom%20%7C%20OpenWeatherMap-orange)

An automated Python data pipeline designed to continuously scrape, fuse, and label real-time urban mobility data across Hanoi's critical infrastructure. 

Moving beyond simple incident reporting, this tool integrates real-time routing delays, structural flow analytics (Functional Road Class), and localized weather conditions into a unified, high-fidelity dataset optimized for machine learning, urban planning, and predictive traffic modeling.

## Overview

Standard traffic APIs often provide either macro-level travel times, isolated weather data, or lagging incident reports. This pipeline bridges that gap by monitoring specific route segments (e.g., major bridges, arterial roads) and capturing the exact environmental conditions and "invisible congestion" metrics at any given moment. 

The script runs continuously in the background, executing a complete polling cycle every 20 minutes, and dynamically manages local CSV storage for each monitored route.

## Key Features

* **Real-Time Data Fusion:** Cross-references active traffic metrics with immediate weather conditions (temperature, rainfall, wind speed) at the geographic center of the route.
* **Routing vs. Incidents:** Uses the TomTom Routing API to capture precise delay times by comparing real-time travel times against theoretical free-flow speeds, catching slow-downs before an "Incident" is formally declared.
* **Flow Dynamics:** Captures Functional Road Class (FRC) and live speed limits to provide structural context to traffic anomalies.
* **Volume Proxying:** Implements a Speed Ratio Proxy (`current_speed` / `free_flow_speed`) to estimate road saturation and efficiency without needing physical sensors.
* **Automated Data Labeling:** Parses raw TomTom incident codes to generate a clean, binary `is_congested` target variable alongside specific incident types.
* **Dynamic Storage Allocation:** Automatically generates and appends to separate CSV files for each monitored location, ensuring data remains clean and compartmentalized.

---

## Data Schema (Data Dictionary)

Each route generates its own `_v2_enriched.csv` file with the following engineered schema:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `datetime` | Local ISO-formatted timestamp of the API polling cycle. |
| `route_name` | `string` | The human-readable name of the monitored segment. |
| `frc_class` | `int` | Functional Road Class (0-7). Lower numbers = higher structural importance (e.g., Highway vs Local). |
| `speed_limit_baseline` | `int` | The theoretical free-flow speed (km/h) of the segment. |
| `current_speed` | `int` | The live average speed (km/h) of vehicles currently on the road. |
| `speed_ratio_proxy` | `float` | `current_speed / speed_limit_baseline`. Ratio < 0.5 indicates heavy saturation. |
| `travel_time_s` | `int` | Current time (seconds) it takes to traverse the segment. |
| `free_flow_time_s` | `int` | Time (seconds) it takes to traverse the segment in ideal, empty conditions. |
| `route_delay_s` | `int` | Exact time lost (seconds) across the whole route (`travel_time_s - free_flow_time_s`). |
| `is_congested` | `int` | **[Target Variable]** Binary flag: `1` if a target traffic incident is active, `0` otherwise. |
| `incident_type` | `string` | Translated TomTom category (e.g., `Accident`, `Jam`, `RoadClosed`). Returns `None` if clear. |
| `magnitude` | `int` | Severity of the delay from 0 (Unknown) to 4 (Indefinite/Road Closed). |
| `weather` | `string` | Primary environmental state (e.g., "Clear", "Rain", "Clouds"). |
| `temp` | `float` | Ambient temperature at the route's center in Celsius. |
| `rain_mm` | `float` | Recorded rainfall volume over the last hour (mm). |

---

## Installation & Configuration

### Prerequisites
* Python 3.8 or higher.
* Active API keys from the [TomTom Developer Portal](https://developer.tomtom.com/) (Traffic Incidents, Flow, and Routing APIs enabled).
* Active API key from [OpenWeatherMap](https://openweathermap.org/api).

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git](https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git)

cd YOUR-REPO-NAME
```

### 2. Install Dependencies
```bash
pip install pandas requests
```

### 3. Configure Credentials
Open the main python script in your preferred IDE and insert your API keys:

```bash
TOMTOM_KEY = "your_actual_tomtom_key_here"
WEATHER_KEY = "your_actual_openweathermap_key_here"
```

### 4. Define Target Routes
Configure your target locations in the ROUTE_CONFIG dictionary. You must provide a bounding box (bbox) for incidents, start/end coordinates for routing delays, and a center point for weather and flow data.

```bash
ROUTE_CONFIG = {
    "Golden Gate Bridge": {
        "bbox": "-122.485,37.810,-122.470,37.825",
        "start": "37.807,-122.475", 
        "end": "37.830,-122.479", 
        "point": "37.818,-122.478"
    },
    # Add more routes here...
}
```

### 5. Run the Collector
Bash
python traffic_scanner.py
🖨️ Expected Output
The script will output an execution log to the console and begin populating .csv files in the root directory.

```bash
--- Deep Intelligence Scan: 2026-05-13 14:41:00 ---
🟢 Nhat Tan Bridge | FRC: 1 | Speed: 78/80 | Delay: 0s
🔴 Nguyen Trai Street | FRC: 2 | Speed: 22/50 | Delay: 420s
💾 Scan complete.
💤 Sleeping for 20 minutes...
```

## Roadmap / Future Enhancements
[ ] Database Migration: Transition from local CSV storage to a robust time-series database (e.g., PostgreSQL or InfluxDB).

[ ] Dockerization: Wrap the pipeline in a Docker container for seamless cloud deployment.

[ ] Data Visualization: Build a Streamlit dashboard to visualize real-time congestion states and historical patterns.

[ ] Predictive Modeling: Train an XGBoost or Random Forest classifier on the generated dataset to predict congestion probability based on weather and temporal features.
