# Traffic-Weather Historical Data Scraper - Vinh Tuy Bridge

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![TomTom Routing API](https://img.shields.io/badge/API-TomTom%20Routing-red.svg)](https://developer.tomtom.com/routing-api/documentation)
[![Visual Crossing Weather API](https://img.shields.io/badge/API-Visual%20Crossing-orange.svg)](https://www.visualcrossing.com/resources/documentation/weather-api/timeline-weather-api/)
[![Output](https://img.shields.io/badge/output-CSV-green)](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html)

A Python batch scraper for collecting historical traffic and weather features for **Vinh Tuy Bridge, Hanoi**.

This project combines:

- **TomTom Routing API** for route travel time, free-flow travel time, route length, and speed estimation.
- **Visual Crossing Weather API** for hourly weather data.
- A fixed set of strategic sampling times across each day.
- Bidirectional route collection: **Inbound** and **Outbound**.
- CSV output designed for machine learning traffic-congestion analysis.

---

## What This Version Does

This version is not a continuous real-time scanner. It is a **historical batch scraper**.

For each target date, the script:

1. Selects one historical date using a day offset from the current date.
2. Fetches one full-day hourly weather profile from Visual Crossing.
3. Samples traffic at fixed strategic hours.
4. Calls TomTom Routing API for both route directions.
5. Calculates traffic features such as route delay, speed ratio, and congestion label.
6. Appends each result row to a CSV file.

---

## Current Route Configuration

The current script is configured for **Vinh Tuy Bridge**.

```python
ROUTE_CONFIG = {
    "Vinh Tuy Bridge": {
        "A": "21.0041,105.8778",
        "B": "21.0223,105.8931",
        "frc": 2
    }
}
```

Direction meaning:

| Direction | Start | End |
| :--- | :--- | :--- |
| `Inbound` | Point A | Point B |
| `Outbound` | Point B | Point A |

---

## Strategic Sampling Hours

The scraper collects data at exactly these 10 times per day:

```python
STRATEGIC_HOURS = [
    "03:00:00",
    "07:10:00",
    "07:30:00",
    "10:00:00",
    "12:00:00",
    "15:00:00",
    "16:00:00",
    "17:10:00",
    "20:00:00",
    "22:30:00"
]
```

These times are designed to capture early morning, rush-hour, midday, afternoon, evening, and late-night conditions.

---

## Key Features

### 1. Historical Batch Collection

The function below controls which historical days are collected:

```python
run_historical_batch(start_day_offset=82, days_to_scrape=142)
```

Example:

| Setting | Meaning |
| :--- | :--- |
| `start_day_offset=82` | Start from 82 days before today |
| `days_to_scrape=142` | Scrape 142 days |
| Output file | `VINH_TUY_OFFSET_82.csv` |

---

### 2. Bidirectional Routing

For every timestamp, the script collects both:

```python
directions = [
    ("Inbound", nodes["A"], nodes["B"]),
    ("Outbound", nodes["B"], nodes["A"])
]
```

This is important because traffic patterns can be very different in opposite directions.

---

### 3. Nearest-Hour Weather Alignment

Visual Crossing returns weather by hour. The script matches each traffic sample to the closest available weather hour:

```python
wh = get_nearest_weather(hourly_weather, t_hour)
```

This reduces temporal mismatch between traffic and weather data.

---

### 4. Congestion Labeling

The script calculates:

```python
speed_ratio = current_speed / speed_limit_baseline
```

Then it labels congestion using:

```python
is_congested = 1 if speed_ratio < 0.65 else 0
```

The output values are:

| Value | Meaning |
| :--- | :--- |
| `1` | Congested |
| `0` | Not congested |

---

### 5. CSV Output

The script writes rows into a CSV file named by offset:

```python
VINH_TUY_OFFSET_{start_day_offset}.csv
```

Example:

```text
VINH_TUY_OFFSET_82.csv
```

The file is appended continuously as the scraper runs.

---

## Data Schema

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `datetime/string` | Date and time of the traffic sample. |
| `route_name` | `string` | Route name, currently `Vinh Tuy Bridge`. |
| `direction` | `string` | `Inbound` or `Outbound`. |
| `is_weekend` | `int` | `1` if Saturday/Sunday, otherwise `0`. |
| `hour_of_day` | `int` | Hour extracted from the sample time. |
| `frc_class` | `int` | Functional road class from the route config. |
| `speed_limit_baseline` | `float` | Estimated free-flow speed in km/h. |
| `current_speed` | `float` | Estimated current/historical route speed in km/h. |
| `speed_ratio_proxy` | `float` | `current_speed / speed_limit_baseline`. |
| `travel_time_s` | `int` | TomTom travel time in seconds. |
| `free_flow_time_s` | `int` | TomTom no-traffic travel time in seconds. |
| `route_delay_s` | `int` | `travel_time_s - free_flow_time_s`, never below `0`. |
| `is_congested` | `int` | Target label: `1` if speed ratio is below `0.65`, otherwise `0`. |
| `incident_type` | `string` | `Congested` or `None`. |
| `magnitude` | `int` | `2` for congested, `0` for none. |
| `weather` | `string` | Weather condition from Visual Crossing. |
| `temp` | `float` | Temperature in Celsius. |
| `rain_mm` | `float` | Precipitation in millimeters. |
| `humidity` | `float` | Relative humidity percentage. |
| `visibility` | `float` | Visibility converted to meters. |

---

## Installation

### Prerequisites

- Python 3.8 or higher
- TomTom API key
- Visual Crossing API key

---

### 1. Open the Project Folder

In PowerShell:

```powershell
cd "YOUR_DIRECTORY"
```

---

### 2. Create a Virtual Environment

```powershell
& "YOUR_DIRECTORY\Python\Python313\python.exe" -m venv .venv
```

If your Python path is different, replace it with your actual Python path.

---

### 3. Activate the Virtual Environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& ".\.venv\Scripts\Activate.ps1"
```

After activation, the terminal should show:

```text
(.venv) PS YOUR_DIRECTORY>
```

---

### 4. Install Dependencies

```powershell
& ".\.venv\Scripts\python.exe" -m pip install requests pandas
```

If your project has a `requirements.txt` file, use:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

---

## API Key Configuration

Open the Python script and set your keys:

```python
TOMTOM_KEY = "your_tomtom_key_here"
VISUAL_CROSSING_KEY = "your_visual_crossing_key_here"
```

---

## Running the Scraper

Run the script from the project folder:

```powershell
& ".\.venv\Scripts\python.exe" ".\prototype-v05-HistoryScraper.py"
```

---

## Changing the Historical Batch

At the bottom of the script, the active batch is:

```python
run_historical_batch(start_day_offset=82, days_to_scrape=142)
```

This means:

```text
Start: 82 days before today
Total: 142 days
Range: offsets 82 to 223
Output: VINH_TUY_OFFSET_82.csv
```

To scrape the deeper history batch, comment Partner A and uncomment Partner B:

```python
# run_historical_batch(start_day_offset=82, days_to_scrape=142)
run_historical_batch(start_day_offset=224, days_to_scrape=142)
```

This will generate:

```text
VINH_TUY_OFFSET_224.csv
```

---

## Expected Console Output

During a successful run, the console should show messages like:

```text
📅 Processing Date: 2026-02-21
  ✅ Logged 03:00:00
  ✅ Logged 07:10:00
  ✅ Logged 07:30:00
```

If an API request fails, the script may show:

```text
❌ API Error 403 at 2026-02-21T07:10:00
```

or:

```text
❌ Weather API Error 403 on 2026-02-21
Message from server: ...
```

---

## Testing the Visual Crossing Weather API

Create a file named:

```text
test_weather_api.py
```

Paste:

```python
import requests

VISUAL_CROSSING_KEY = "PASTE_YOUR_VISUAL_CROSSING_KEY_HERE"

lat = "21.0041"
lon = "105.8778"
date_str = "2026-05-14"

url = (
    f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
    f"{lat},{lon}/{date_str}?unitGroup=metric&key={VISUAL_CROSSING_KEY}&include=hours"
)

res = requests.get(url, timeout=10)

print("Status code:", res.status_code)
print("Server message:")
print(res.text[:1000])
```

Run:

```powershell
& ".\.venv\Scripts\python.exe" ".\test_weather_api.py"
```

A working key should return:

```text
Status code: 200
```

---

## Testing the TomTom Routing API

Create a file named:

```text
test_tomtom_api.py
```

Paste:

```python
import requests

TOMTOM_KEY = "PASTE_YOUR_TOMTOM_KEY_HERE"

url = (
    "https://api.tomtom.com/routing/1/calculateRoute/"
    "21.0041,105.8778:21.0223,105.8931/json"
    f"?key={TOMTOM_KEY}&traffic=true&computeTravelTimeFor=all"
)

res = requests.get(url, timeout=10)

print("Status code:", res.status_code)
print("Server message:")
print(res.text[:1000])
```

Run:

```powershell
& ".\.venv\Scripts\python.exe" ".\test_tomtom_api.py"
```

A working key should return:

```text
Status code: 200
```

---

## Troubleshooting

### Error: `ModuleNotFoundError: No module named 'requests'`

Install the missing package inside the virtual environment:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install requests pandas
```

---

### Error: `python was not found`

Use the full Python path instead of `python`:

```powershell
& "C:\Users\ADMIN\AppData\Local\Programs\Python\Python313\python.exe" -m pip install requests pandas
```

---

### Error: `.venv\Scripts\python.exe is not recognized`

You are probably not inside the project folder.

Run:

```powershell
cd "C:\Users\ADMIN\Downloads\Traffic-Weather-Data-Scraping-main\Traffic-Weather-Data-Scraping-main"
```

Then try again:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install requests pandas
```

---

### Error: `API Error 403`

A `403` error usually means the API request was refused.

Check:

- The API key is correct.
- The correct key is used for the correct service.
- TomTom key is used for TomTom.
- Visual Crossing key is used for Visual Crossing.
- The key has permission for the endpoint being called.
- The account has not exceeded its allowed quota.
- The key has no extra spaces before or after it.

To reveal the TomTom server message, update this part of the code:

```python
if res.status_code != 200:
    print(f"\n❌ TomTom API Error {res.status_code} at {timestamp}")
    print("URL without key:", url.replace(TOMTOM_KEY, "HIDDEN_KEY"))
    print("Server message:", res.text)
    return None, None, None, None
```

Do not share your API key publicly.

---

## Project Files

Recommended structure:

```text
Traffic-Weather-Data-Scraping-main/
│
├── prototype-v05-HistoryScraper.py
├── README.md
├── requirements.txt
├── .venv/
├── VINH_TUY_OFFSET_82.csv
└── VINH_TUY_OFFSET_224.csv
```

---

## Notes

This README matches the current historical scraper version of the project.

Major changes from the older README:

- Replaced OpenWeatherMap with Visual Crossing.
- Removed real-time adaptive polling language.
- Removed multi-point flow aggregation.
- Removed incident bbox configuration.
- Updated route example from Golden Gate Bridge to Vinh Tuy Bridge.
- Updated run command to use `prototype-v05-HistoryScraper.py`.
- Updated output file name to `VINH_TUY_OFFSET_{start_day_offset}.csv`.
- Added Windows PowerShell virtual environment commands.
- Added API test scripts and 403 troubleshooting.

