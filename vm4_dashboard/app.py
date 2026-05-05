from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

# Configuration - Your VM3 IoT Server IP
DATA_SERVER_URL = "http://192.168.56.103:5000"

@app.route('/')
def index():
    """Serve the dashboard homepage"""
    return render_template('index.html')

@app.route('/api/latest')
def get_latest():
    """Get latest sensor readings from VM3"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/api/measurements/latest", timeout=5)
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to fetch data", "data": []}), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Cannot connect to IoT server at " + DATA_SERVER_URL, "data": []}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request to IoT server timed out", "data": []}), 504
    except Exception as e:
        return jsonify({"error": str(e), "data": []}), 500

@app.route('/api/history/<sensor_type>')
def get_history(sensor_type):
    """Get historical data for a specific sensor from VM3"""
    try:
        response = requests.get(
            f"{DATA_SERVER_URL}/api/measurements/history",
            params={"sensor": sensor_type},
            timeout=5
        )
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({"error": "Failed to fetch history", "data": []}), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "Cannot connect to IoT server", "data": []}), 503
    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out", "data": []}), 504
    except Exception as e:
        return jsonify({"error": str(e), "data": []}), 500

@app.route('/api/health')
def health_check():
    """Check if VM3 IoT server is accessible"""
    try:
        response = requests.get(f"{DATA_SERVER_URL}/api/health", timeout=5)
        if response.status_code == 200:
            server_health = response.json()
            return jsonify({
                "dashboard": "running",
                "iot_server": "connected",
                "server_status": server_health
            }), 200
        else:
            return jsonify({
                "dashboard": "running",
                "iot_server": "error",
                "status_code": response.status_code
            }), 503
    except requests.exceptions.ConnectionError:
        return jsonify({
            "dashboard": "running",
            "iot_server": "disconnected",
            "error": "Cannot reach IoT server"
        }), 503
    except Exception as e:
        return jsonify({
            "dashboard": "running",
            "iot_server": "error",
            "error": str(e)
        }), 503

if __name__ == '__main__':
    print("=" * 60)
    print(" IoT Dashboard Starting...")
    print("=" * 60)
    print(f" Dashboard URL: http://192.168.56.104:8080")
    print(f" IoT Server:    {DATA_SERVER_URL}")
    print("=" * 60)
    print("Testing connection to IoT server...")

    # Test connection to VM3
    try:
        test_response = requests.get(f"{DATA_SERVER_URL}/api/health", timeout=5)
        if test_response.status_code == 200:
            print(" Connection to IoT server: OK")
        else:
            print(f" Connection to IoT server: ERROR (Status {test_response.status_code})")
    except requests.exceptions.ConnectionError:
        print(f" Cannot connect to IoT server at {DATA_SERVER_URL}")
        print("  Make sure VM3 is running and accessible")
    except Exception as e:
        print(f" Error testing connection: {e}")

    print("=" * 60)
    print("Starting Flask server...")
    print("Press CTRL+C to stop")
    print("=" * 60)

    app.run(host='0.0.0.0', port=8080, debug=True)
