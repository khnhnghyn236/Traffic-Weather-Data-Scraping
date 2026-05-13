# Traffic-Weather Data Collector - V3

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Data Source](https://img.shields.io/badge/data-TomTom%20%7C%20OpenWeatherMap-orange)

An automated Python data pipeline designed to continuously scrape, fuse, and label real-time urban mobility data across Hanoi's critical infrastructure. 

Built for machine learning and predictive traffic modeling, this **V3 Research-Grade** pipeline actively mitigates spatial, directional, and temporal biases common in standard API scraping. It integrates bidirectional routing delays, multi-point flow aggregation, adaptive polling, and localized weather metrics into a unified, high-fidelity dataset.

## Overview

Standard traffic APIs often provide lagging incident reports or macro-level travel times that fail to capture the asymmetric nature of urban traffic. This pipeline monitors specific geographic corridors, capturing the exact environmental conditions and "invisible congestion" metrics in real-time. 

The script runs continuously, utilizing an adaptive sampling rate (e.g., polling every 5 minutes during rush hour and 20 minutes off-peak) to capture rapid congestion onset without burning through API quotas.

## Key Upgrades & Bias Mitigation

*   **Bidirectional Routing (Directional Bias):** Captures traffic flowing in both directions (Inbound vs. Outbound) simultaneously, recognizing that morning and evening commutes have opposite congestion profiles.
*   **Multi-Point Flow Aggregation (Spatial Bias):** Instead of relying on a single coordinate that might sit on an empty ramp or a red light, the pipeline samples 3 distinct points along the route and calculates the median speed and baseline.
*   **Adaptive Temporal Sampling (Temporal Bias):** Automatically detects Hanoi rush hours (7-9 AM, 4-7 PM) and accelerates the data collection frequency from 20 minutes to 5 minutes to capture sudden traffic spikes.
*   **Volume Proxying:** Implements a Speed Ratio Proxy (`current_speed` / `free_flow_speed`) to mathematically estimate road saturation levels without physical sensors.
*   **Expanded Environmental Context:** Captures extended weather variables like humidity and visibility, which strongly dictate motorcycle braking distances and behavior in Southeast Asia.
*   **Fail-Safe Integrity (Survivorship Bias):** Uses `None` rather than `0` for API timeouts, preventing models from learning impossible "zero-speed, zero-delay" states during network outages.

---

## Data Schema (Data Dictionary)

Each route generates a dynamic `_v3_intelligence.csv` file with the following engineered schema:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `datetime` | Local ISO-formatted timestamp of the API polling cycle. |
| `route_name` | `string` | The human-readable name of the monitored segment. |
| `direction` | `string` | `Inbound` or `Outbound` relative to the defined A/B nodes. |
| `is_weekend` | `int` | Binary flag: `1` if Saturday/Sunday, `0` otherwise. |
| `hour_of_day` | `int` | Extracted hour (0-23) for temporal pattern analysis. |
| `frc_class` | `int` | Median Functional Road Class (0-7) across sampled points. |
| `speed_limit_baseline` | `float` | Median theoretical free-flow speed (km/h) of the segment. |
| `current_speed` | `float` | Median live speed (km/h) across the segment points. |
| `speed_ratio_proxy` | `float` | `current_speed / speed_limit_baseline`. Ratio < 0.6 indicates saturation. |
| `travel_time_s` | `int` | Current time (seconds) to traverse the route. |
| `free_flow_time_s` | `int` | Time (seconds) to traverse the route in ideal, empty conditions. |
| `route_delay_s` | `int` | Exact time lost (seconds) across the whole route. |
| `is_congested` | `int` | **[Target Variable]** Binary flag: `1` if an incident exists OR `speed_ratio` < 0.6. |
| `incident_type` | `string` | Categorized event (e.g., `Accident`, `Jam`, `Flooding`, `Roadworks`). |
| `magnitude` | `int` | Severity of the delay from 0 (Unknown) to 4 (Road Closed). |
| `weather` | `string` | Primary environmental state (e.g., "Clear", "Rain"). |
| `temp` | `float` | Ambient temperature in Celsius. |
| `rain_mm` | `float` | Recorded rainfall volume over the last hour (mm). |
| `humidity` | `int` | Relative humidity percentage. |
| `visibility` | `int` | Visibility distance in meters (max 10,000). |

---

## Installation & Configuration

### Prerequisites
*   Python 3.8 or higher.
*   Active API keys from the [TomTom Developer Portal](https://developer.tomtom.com/) (Traffic Incidents, Flow, and Routing APIs enabled).
*   Active API key from [OpenWeatherMap](https://openweathermap.org/api).

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git](https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git)
cd YOUR-REPO-NAME
```

### 2. Install Dependencies
```bash
pip install pandas requests numpy
```

### 3. Configure Credentials
Open the main python script in your preferred IDE and insert your API keys:

```bash
TOMTOM_KEY = "your_actual_tomtom_key_here"
WEATHER_KEY = "your_actual_openweathermap_key_here"
```

### 4. Define Target Routes
Configure your target locations in the ROUTE_CONFIG dictionary. Provide a bounding box (bbox) for incidents, A/B endpoints for bidirectional routing, and an array of flow_points for spatial median aggregation.

```bash
ROUTE_CONFIG = {
    "Golden Gate Bridge": {
        "bbox": "-122.485,37.810,-122.470,37.825",
        "A": "37.807,-122.475", 
        "B": "37.830,-122.479",
        "flow_points": ["37.810,-122.476", "37.818,-122.478", "37.825,-122.478"]
    }
}
```

### 5. Run the Collector
```bash
python traffic_scanner.py
```

## Expected Output
The script will output an execution log to the console and begin populating .csv files in the root directory.

```bash
--- Intelligence Scan: 2026-05-14 17:35:00 ---
🟢 Nhat Tan Bridge (Inbound) | Speed: 78/80 | Delay: 0s
🔴 Nhat Tan Bridge (Outbound) | Speed: 32/80 | Delay: 184s
🔴 Nguyen Trai Street (Inbound) | Speed: 15/50 | Delay: 420s
🟢 Nguyen Trai Street (Outbound) | Speed: 42/50 | Delay: 12s

🚨 RUSH HOUR DETECTED: Increasing sampling rate to 5 mins.
=============================================
⏳ Next intelligence scan in: 04:59
```

## Roadmap / Future Enhancements
[ ] Database Migration: Transition from local CSV storage to a robust time-series database (e.g., PostgreSQL or InfluxDB).

[ ] Dockerization: Wrap the pipeline in a Docker container for seamless cloud deployment.

[ ] Data Visualization: Build a Streamlit dashboard to map the real-time congestion state of the city.

[ ] Predictive Modeling: Train an XGBoost or Random Forest classifier on the generated dataset to forecast congestion probability 30 minutes into the future based on weather and temporal trends.
