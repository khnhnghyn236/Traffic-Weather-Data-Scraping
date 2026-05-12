# Urban Traffic & Weather Data Pipeline 

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Data Source](https://img.shields.io/badge/data-TomTom%20%7C%20OpenWeatherMap-orange)

An automated Python data pipeline designed to continuously scrape, fuse, and label real-time urban mobility data. By integrating traffic incident reports with localized environmental metrics, this tool generates high-quality, pre-labeled datasets optimized for machine learning, urban planning, and predictive traffic modeling.

## Overview

Standard traffic APIs often provide either macro-level travel times or isolated weather data. This pipeline bridges that gap by monitoring specific geographic bounding boxes (e.g., major bridges, arterial roads) and capturing the exact environmental conditions at the moment a traffic incident occurs. 

The script runs continuously in the background, executing a complete polling cycle every 20 minutes, and dynamically manages local CSV storage for each monitored route.

## Key Features

* **Real-Time Data Fusion:** Cross-references active traffic incidents with immediate weather conditions (temperature, rainfall, wind speed) at the geometric center of the route.
* **Automated Data Labeling:** Parses raw TomTom incident codes (e.g., `RoadWorks`, `Accident`, `Flooding`) to generate a clean, binary `is_congested` target variable for ML classification tasks.
* **Resilient API Handling:** Includes built-in error handling for 401 Unauthorized, rate limits, and network timeouts to ensure uninterrupted data collection.
* **Dynamic Storage Allocation:** Automatically generates and manages separate CSV files for each monitored bounding box, ensuring data remains clean and compartmentalized.
* **Headless Execution:** Designed to run indefinitely on a local machine, Raspberry Pi, or cloud server (AWS EC2, Heroku) via standard terminal execution.

---

## Data Schema (Data Dictionary)

Each route generates its own `.csv` file with the following engineered schema:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `datetime` | Local ISO-formatted timestamp of the API polling cycle. |
| `route_name` | `string` | The human-readable name of the monitored bounding box. |
| `hour_of_day` | `int` | Extracted hour (0-23) for temporal pattern analysis. |
| `day_of_week` | `string` | Extracted day (e.g., "Monday") for weekly trend mapping. |
| `weather_condition` | `string` | Primary environmental state (e.g., "Clear", "Rain", "Clouds"). |
| `temperature_celsius` | `float` | Ambient temperature at the route's center in Celsius. |
| `rain_1h_mm` | `float` | Recorded rainfall volume over the last hour (mm). |
| `wind_speed_ms` | `float` | Wind speed in meters per second. |
| `is_congested` | `int` | **[Target Variable]** Binary flag: `1` if a target traffic incident is active, `0` otherwise. |
| `incident_type` | `string` | Translated TomTom category (e.g., `Accident`, `Jam`, `RoadClosed`). Returns `None` if clear. |
| `incident_magnitude` | `int` | Severity of the delay from 0 (Unknown) to 4 (Indefinite/Road Closed). |
| `reported_delay_seconds` | `int` | Total delay in seconds caused by active incidents within the bounding box. |

---

## Installation & Configuration

### Prerequisites
* Python 3.8 or higher.
* Active API keys from the [TomTom Developer Portal](https://developer.tomtom.com/) (Traffic Incidents API enabled).
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
Open data_collector.py in your preferred IDE and insert your API keys in the configuration section:
```bash
Python
TOMTOM_KEY = "your_actual_tomtom_key_here"
WEATHER_KEY = "your_actual_openweathermap_key_here"
```

### 4. Define Target Routes
Add your target locations to the ROUTES_BBOX dictionary using the min_lon,min_lat,max_lon,max_lat format:
```bash
Python
ROUTES_BBOX = {
    "Golden Gate Bridge": "-122.485,37.810,-122.470,37.825",
    "Downtown Corridor": "..."
}
```

## Expected Output:
The script will output an execution log to the console and begin populating .csv files in the root directory.

```bash
--- Incident Scan: 2026-05-12 14:41:00 ---
🟢 Golden Gate Bridge: Logged -> Saved to Golden_Gate_Bridge.csv | Type: None | Delay: 0s
🔴 Downtown Corridor: Logged -> Saved to Downtown_Corridor.csv | Type: Accident | Delay: 420s
💾 Scan complete.
💤 Sleeping for 20 minutes...
```

## Roadmap / Future Enhancements
[ ] Database Migration: Transition from local CSV storage to a robust time-series database (e.g., PostgreSQL or InfluxDB).

[ ] Dockerization: Wrap the pipeline in a Docker container for seamless cloud deployment.

[ ] Data Visualization: Build a Streamlit dashboard to visualize the real-time congestion state and historical patterns.

[ ] Predictive Modeling: Train an XGBoost or Random Forest classifier on the generated dataset to predict is_congested probability based purely on weather and temporal features.
