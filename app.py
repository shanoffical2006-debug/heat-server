from flask import Flask, request, jsonify
import os
import sys

# Try to initialize Earth Engine non-interactively at startup. This will
# attempt service-account init if EE_SERVICE_ACCOUNT_JSON or
# GOOGLE_APPLICATION_CREDENTIALS is set. If that fails, and EE_FORCE_AUTH is
# truthy, the app will open a browser to let you authenticate interactively.
from gee_utils import initialize_ee, get_heatwave_status, ee_is_initialized, get_heatwave_history
import json
from pathlib import Path

# Locations storage (simple JSON file)
DATA_FILE = Path(__file__).resolve().parent / 'locations.json'
if not DATA_FILE.exists():
    DATA_FILE.write_text('[]')

app = Flask(__name__)

# Attempt initialization (non-fatal). Prefer service-account if provided.
force_auth = os.environ.get('EE_FORCE_AUTH', 'false').lower() in ('1', 'true', 'yes')
# Use EE_PROJECT env var if set, otherwise fall back to the user's provided project id.
# You can change this default or set EE_PROJECT in your environment.
project_id = os.environ.get('EE_PROJECT', 'propane-library-477610-c3')

# Try to read service account key from multiple sources:
# 1. Environment variable (for Cloud Run / local dev with env var)
# 2. Render secret file (Render secret files are mounted at /etc/secrets/)
# 3. Local file (for local dev with sa-key.json in project folder)
service_account_key = os.environ.get('EE_SERVICE_ACCOUNT_JSON')
if not service_account_key:
    # Try Render secret file path
    if os.path.exists('/etc/secrets/sa-key.json'):
        with open('/etc/secrets/sa-key.json', 'r') as f:
            service_account_key = f.read()
    # Try local file
    elif os.path.exists('./sa-key.json'):
        with open('./sa-key.json', 'r') as f:
            service_account_key = f.read()

ok = initialize_ee(force_auth=force_auth, project=project_id, service_account_key=service_account_key)
if not ok:
    print(f"Warning: Earth Engine not initialized (project={project_id}). API endpoints will return an informative error until EE is authenticated.")
    print("To authenticate interactively run: python -c \"import ee; ee.Authenticate()\"")
    print("Or set EE_SERVICE_ACCOUNT_JSON to a service account JSON key and restart the app.")

@app.route('/')
def index():
    return jsonify({"message": "Heat Wave Detection API is running!"})

@app.route('/check_heatwave', methods=['POST'])
def check_heatwave():
    data = request.get_json()
    lat = data.get('lat')
    lon = data.get('lon')

    if lat is None or lon is None:
        return jsonify({"error": "Latitude and longitude required"}), 400

    result = get_heatwave_status(lat, lon)
    return jsonify(result)


@app.route('/locations', methods=['GET'])
def list_locations():
    try:
        data = json.loads(DATA_FILE.read_text())
    except Exception:
        data = []
    return jsonify(data)


@app.route('/locations', methods=['POST'])
def add_location():
    payload = request.get_json() or {}
    name = payload.get('name')
    lat = payload.get('lat')
    lon = payload.get('lon')
    if not name or lat is None or lon is None:
        return jsonify({'error': 'name, lat and lon are required'}), 400
    try:
        data = json.loads(DATA_FILE.read_text())
    except Exception:
        data = []
    entry = {'name': name, 'lat': lat, 'lon': lon}
    data.append(entry)
    DATA_FILE.write_text(json.dumps(data, indent=2))
    return jsonify(entry), 201


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'ee_initialized': ee_is_initialized(), 'project': project_id})


@app.route('/init_ee', methods=['POST'])
def init_ee_endpoint():
    # Accept optional JSON: {"force_auth": bool, "service_account_key": str, "project": str}
    payload = request.get_json() or {}
    force_auth = bool(payload.get('force_auth', False))
    service_account_key = payload.get('service_account_key')
    project = payload.get('project', project_id)
    ok = initialize_ee(force_auth=force_auth, project=project, service_account_key=service_account_key)
    if ok:
        return jsonify({'ok': True, 'message': 'Earth Engine initialized', 'project': project})
    else:
        return jsonify({'ok': False, 'message': 'Initialization failed. See server logs.'}), 500


@app.route('/api', methods=['GET'])
def api_docs():
    routes = [
        {'path': '/', 'method': 'GET', 'description': 'Status message'},
        {'path': '/check_heatwave', 'method': 'POST', 'body': {'lat': 'float', 'lon': 'float'}, 'description': 'Check heatwave status for location'},
        {'path': '/locations', 'method': 'GET', 'description': 'List saved locations'},
        {'path': '/locations', 'method': 'POST', 'body': {'name': 'str','lat':'float','lon':'float'}, 'description': 'Add a saved location'},
        {'path': '/health', 'method': 'GET', 'description': 'Health and EE init status'},
        {'path': '/init_ee', 'method': 'POST', 'body': {'force_auth':'bool','service_account_key':'str','project':'str'}, 'description': 'Attempt to initialize Earth Engine'},
    ]
    return jsonify({'routes': routes})


@app.route('/heatwave_history', methods=['GET'])
def heatwave_history():
    # Query params: lat, lon, years (optional)
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    years = request.args.get('years', default=10, type=int)

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon query parameters are required'}), 400

    result = get_heatwave_history(lat, lon, years=years)
    return jsonify(result)

if __name__ == '__main__':
    # Run the dev server. In production use a WSGI server and ensure EE is
    # initialized non-interactively (service account) or authenticated ahead of time.
    # Disable the reloader to avoid double-initialization of Earth Engine when
    # running in debug mode (which can cause network hangs during startup).
    # Bind to 0.0.0.0 so Android emulators and other devices can reach the
    # host machine. The Android emulator maps the host's localhost to
    # 10.0.2.2 — use http://10.0.2.2:5000 from the emulator to reach this API.
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port, debug=True, use_reloader=False)
