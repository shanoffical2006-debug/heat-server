import ee
import datetime

# Do NOT call ee.Initialize() at import time. This file exposes a helper
# to initialize Earth Engine when the application is ready to authenticate.

import ee
import datetime
import os

# Do NOT call ee.Initialize() at import time. This file exposes a helper
# to initialize Earth Engine when the application is ready to authenticate.

_ee_initialized = False


def initialize_ee(force_auth=False, project=None, service_account_key=None):
    """Attempt to initialize the Earth Engine API.

    Tries these methods in order:
      1. If `service_account_key` or env var `EE_SERVICE_ACCOUNT_JSON` or
         `GOOGLE_APPLICATION_CREDENTIALS` is set, attempt service-account
         non-interactive initialization.
      2. Try normal `ee.Initialize()` (user credentials already present).
      3. If `force_auth=True`, call `ee.Authenticate()` and retry.

    Returns:
        bool: True if initialized successfully, False otherwise.
    """
    global _ee_initialized
    if _ee_initialized:
        return True

    # 1) Try service-account JSON key (non-interactive)
    key_path = service_account_key or os.environ.get('EE_SERVICE_ACCOUNT_JSON') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if key_path:
        try:
            # Import here to avoid making it a hard dependency unless used
            from google.oauth2 import service_account

            scopes = [
                'https://www.googleapis.com/auth/earthengine',
                'https://www.googleapis.com/auth/cloud-platform',
            ]
            creds = service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
            if project:
                ee.Initialize(credentials=creds, project=project)
            else:
                ee.Initialize(credentials=creds)
            _ee_initialized = True
            return True
        except Exception:
            # Fall through to other initialization methods
            pass

    # 2) Try default initialization (maybe authenticated in this env)
    try:
        if project:
            ee.Initialize(project=project)
        else:
            ee.Initialize()
        _ee_initialized = True
        return True
    except Exception:
        # 3) Optionally invoke interactive authentication and retry
        if force_auth:
            try:
                ee.Authenticate()
                if project:
                    ee.Initialize(project=project)
                else:
                    ee.Initialize()
                _ee_initialized = True
                return True
            except Exception:
                return False

        return False


# Thresholds for heatwave detection
TEMP_THRESHOLD = 35.0  # Celsius
DURATION_DAYS = 3       # Consecutive days above threshold


def get_heatwave_status(lat, lon):
    # If Earth Engine isn't initialized, return a structured error so the API
    # can remain available and clients receive a helpful message.
    if not _ee_initialized:
        return {
            "error": "Earth Engine not initialized",
            "message": "Authenticate Earth Engine on this machine (run `python -c \"import ee; ee.Authenticate()\"`) or set EE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS to a service account JSON and restart the app.",
            "location": {"lat": lat, "lon": lon}
        }

    point = ee.Geometry.Point([lon, lat])

    # Use ERA5 daily temperature data (mean temperature)
    dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
        .filterDate('2025-01-01', datetime.date.today().isoformat()) \
        .select('temperature_2m')

    # Convert from Kelvin to Celsius
    temp_c = dataset.map(lambda img: img.subtract(273.15)
                         .copyProperties(img, ['system:time_start']))

    # Extract time series for the location
    temps = temp_c.getRegion(point, 1000).getInfo()

    # Convert to list of (date, temp)
    values = []
    for row in temps[1:]:
        try:
            date = datetime.datetime.utcfromtimestamp(row[0]/1000)
            temp = row[4]
            if temp is not None:
                values.append((date, temp))
        except Exception:
            continue

    # Detect heat wave pattern
    heatwave_detected = False
    count = 0
    for _, temp in values[-30:]:  # Check last 30 days
        if temp > TEMP_THRESHOLD:
            count += 1
            if count >= DURATION_DAYS:
                heatwave_detected = True
                break
        else:
            count = 0

    return {
        "location": {"lat": lat, "lon": lon},
        "heatwave": heatwave_detected,
        "threshold": TEMP_THRESHOLD,
        "duration_days": DURATION_DAYS
    }


def ee_is_initialized():
    """Return True if Earth Engine has been initialized in this process."""
    return _ee_initialized


def get_heatwave_history(lat, lon, years=10):
    """Return a simple year-by-year heatwave summary for the past `years` years.

    The summary per year contains:
      - year
      - days_above_threshold: number of days with max temp > TEMP_THRESHOLD
      - longest_run: longest consecutive run of days above TEMP_THRESHOLD
      - mean_temp: mean of daily temps (C)

    This is a lightweight endpoint suitable for charts. If Earth Engine is not
    initialized this returns an error dict.
    """
    if not _ee_initialized:
        return {
            "error": "Earth Engine not initialized",
            "message": "Authenticate Earth Engine on this machine (run `python -c \"import ee; ee.Authenticate()\"`) or set EE_SERVICE_ACCOUNT_JSON/GOOGLE_APPLICATION_CREDENTIALS to a service account JSON and restart the app.",
        }

    today = datetime.date.today()
    end_year = today.year
    start_year = end_year - int(years) + 1

    summaries = []
    point = ee.Geometry.Point([lon, lat])

    for y in range(start_year, end_year + 1):
        start = f"{y}-01-01"
        end = f"{y}-12-31"

        dataset = ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR") \
            .filterDate(start, end) \
            .select('temperature_2m')

        temp_c = dataset.map(lambda img: img.subtract(273.15).copyProperties(img, ['system:time_start']))

        # getRegion returns a list of rows; first row is header
        try:
            rows = temp_c.getRegion(point, 1000).getInfo()
        except Exception as e:
            # If a remote call fails for a year, skip with an error note
            summaries.append({
                'year': y,
                'error': f'Failed to fetch data: {e}'
            })
            continue

        values = []
        for r in rows[1:]:
            try:
                temp = r[4]
                if temp is not None:
                    values.append(temp)
            except Exception:
                continue

        # Convert Kelvin->C already done above
        # Compute stats
        days_above = 0
        longest = 0
        current = 0
        for t in values:
            if t > TEMP_THRESHOLD:
                days_above += 1
                current += 1
                if current > longest:
                    longest = current
            else:
                current = 0

        mean_temp = None
        if values:
            mean_temp = sum(values) / len(values)

        summaries.append({
            'year': y,
            'days_above_threshold': days_above,
            'longest_run': longest,
            'mean_temp_c': mean_temp,
            'samples': len(values)
        })

    return summaries
