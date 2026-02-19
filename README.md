# MTA Subway Live Arrivals - Union Street

This Python script fetches real-time arrival information for MTA subway trains at Union Street stations in Brooklyn, NY.

## Union Street Stations Covered

- **Union St (R/W lines)** - Station ID: R20
- **Union St-4th Ave (D/N/R/W lines)** - Station ID: D24

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Script
```bash
python mta_arrivals.py
```

## Features

- ✅ Real-time arrival data from MTA GTFS feeds
- ✅ Shows next 5 arrivals per station/direction
- ✅ Displays time until arrival in minutes
- ✅ Covers all subway lines serving Union Street
- ✅ Optional continuous monitoring mode

## Usage Examples

### Single Update
```bash
python mta_arrivals.py
```

### Continuous Monitoring
Uncomment this line in the script:
```python
mta.monitor_arrivals(30)  # Updates every 30 seconds
```

## Sample Output

```
🚇 MTA Live Arrivals - Union Street Stations
==================================================
Last updated: 02:30:15 PM

📍 Union St-4th Ave (D/N/R/W) - Northbound
----------------------------------------
  🚊 D train: 02:32 PM (2 mins)
  🚊 N train: 02:35 PM (5 mins)
  🚊 R train: 02:38 PM (8 mins)

📍 Union St (R/W) - Southbound
----------------------------------------
  🚊 R train: 02:33 PM (3 mins)
  🚊 W train: 02:37 PM (7 mins)
```

## Notes

- Data comes directly from MTA's official GTFS-realtime feeds
- Arrival times are estimates and may change
- Service disruptions may affect data availability
- The script handles both Union Street stations in the area

## Troubleshooting

If you see "No arrival data found":
1. Verify internet connection
2. Check for MTA service alerts
3. Station IDs may need updates if MTA changes them

## Rate Limits

For continuous monitoring, don't refresh more frequently than every 30 seconds to avoid overloading the MTA servers.