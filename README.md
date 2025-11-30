
# Heat waves tracker — README

This project provides a small Flask API that uses the Google Earth Engine Python API to check for simple heatwave conditions at a location.

Setup
1. Install dependencies (use python -m pip if `pip` is not on PATH):

```powershell
python -m pip install -r requirements.txt
```

2. Authenticate Earth Engine (developer machine) — one-time interactive flow:

```powershell
python -c "import ee; ee.Authenticate()"
```

3. Or use a service account for non-interactive server deployment:

```powershell
# Create a service account in Google Cloud with Earth Engine and Cloud Platform access,
# download the JSON key and set:
$env:EE_SERVICE_ACCOUNT_JSON = 'C:\path\to\sa-key.json'
python app.py
```

Running the app

```powershell
# from the repo root
python app.py
```

API Endpoints

- GET / — basic status message
- POST /check_heatwave — body: {"lat": number, "lon": number} — returns heatwave status or error if Earth Engine not initialized
- GET /locations — list saved locations (stored in locations.json)
- POST /locations — add location: {"name": str, "lat": number, "lon": number}
- GET /health — returns {"ee_initialized": bool, "project": str}
- POST /init_ee — body optional {"force_auth": bool, "service_account_key": str, "project": str} — attempt to initialize Earth Engine
- GET /api — returns a small machine-readable list of supported routes

Notes
- After running `ee.Authenticate()` you must restart the Flask server so the process picks up the authenticated credentials.
- For production use, initialize Earth Engine non-interactively using a service account and run the Flask app under a production WSGI server.

If you want, I can add unit tests for the endpoints and a small script to boot the dev server in the background.

Android emulator note
---------------------

If you debug an Android app using the default Android emulator, the emulator maps the host machine's localhost to the special IP 10.0.2.2. When running the Flask dev server on your machine use:

 - Host: http://10.0.2.2
 - Port: 5000 (default)

Example base URL from the emulator:

```
http://10.0.2.2:5000
```

If you need the server to be reachable from other devices on your LAN, set the `HOST` and `PORT` environment variables before starting the server (the app defaults to host 0.0.0.0 and port 5000):

```powershell
$env:HOST = '0.0.0.0'
$env:PORT = '5000'
python app.py
```
