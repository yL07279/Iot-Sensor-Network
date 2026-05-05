from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename='server.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Alert thresholds
TEMP_THRESHOLD = 28.0  # temperature alert if above 28°C
HUM_THRESHOLD = 70.0   # humidity alert if above 70%

def get_db_connection():
    """Establish connection to MySQL database"""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'iot_db'),
            auth_plugin='mysql_native_password',
            ssl_disabled=True
        )
        return connection
    except Error as e:
        logging.error(f"Database connection error: {e}")
        print(f"Error connecting to database: {e}")
        return None

def check_and_create_alerts_table():
    """Create alerts table if it doesn't exist"""
    try:
        connection = get_db_connection()
        if not connection:
            return False
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                value FLOAT NOT NULL,
                unit VARCHAR(10),
                location VARCHAR(50),
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_timestamp (timestamp)
            )
        """)
        connection.commit()
        cursor.close()
        connection.close()
        print("Alerts table checked/created successfully")
        return True
    except Exception as e:
        print(f"Error creating alerts table: {e}")
        return False

def add_alert_to_db(sensor_type, value, unit, sensor_id):
    """Add an alert to the database"""
    try:
        connection = get_db_connection()
        if not connection:
            logging.error("Cannot add alert - database connection failed")
            return False
        cursor = connection.cursor()
        message = f"{sensor_type.capitalize()} too high: {value}{unit} at {sensor_id}"
        sql = """
            INSERT INTO alerts (type, value, unit, location, message)
            VALUES (%s, %s, %s, %s, %s)
        """
        vals = (sensor_type, value, unit, sensor_id, message)
        cursor.execute(sql, vals)
        connection.commit()
        alert_id = cursor.lastrowid
        logging.info(f"Alert added to database: ID={alert_id}, {message}")
        print(f" NEW ALERT STORED: {message}")
        cursor.close()
        connection.close()
        return True
    except Exception as e:
        logging.error(f"Error adding alert to database: {e}")
        print(f"Error adding alert to database: {e}")
        return False

def check_thresholds(sensor_type, value, unit, sensor_id):
    """Check if value exceeds threshold and create alert if needed"""
    alert_triggered = False
    if sensor_type == 'temperature' and float(value) > TEMP_THRESHOLD:
        add_alert_to_db(sensor_type, value, unit, sensor_id)
        alert_triggered = True
        print(f"  TEMPERATURE ALERT: {value}{unit} > {TEMP_THRESHOLD}°C")
    elif sensor_type == 'humidity' and float(value) > HUM_THRESHOLD:
        add_alert_to_db(sensor_type, value, unit, sensor_id)
        alert_triggered = True
        print(f"  HUMIDITY ALERT: {value}{unit} > {HUM_THRESHOLD}%")
    return alert_triggered

# 1) Receive data from sensors
@app.route('/api/measurements', methods=['POST'])
def add_measurement():
    """Add new sensor measurement to database"""
    try:
        data = request.json
        logging.info(f"Received data: {data}")
        connection = get_db_connection()
        if not connection:
            logging.error("Database connection failed")
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        cursor = connection.cursor()
        sql = "INSERT INTO measurements (sensor_id, type, value, unit) VALUES (%s, %s, %s, %s)"
        vals = (
            data.get('location', 'unknown'),
            data.get('sensor', 'unknown'),
            data.get('value', 0),
            data.get('unit', '')
        )
        cursor.execute(sql, vals)
        connection.commit()
        logging.info(f"Data inserted successfully: {vals}")
        # Check if this measurement triggers an alert
        check_thresholds(
            data.get('sensor', 'unknown'),
            data.get('value', 0),
            data.get('unit', ''),
            data.get('location', 'unknown')
        )
        cursor.close()
        connection.close()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logging.error(f"Error in add_measurement: {e}")
        print(f"Error in add_measurement: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 2) Get latest values (for dashboard)
@app.route('/api/measurements/latest', methods=['GET'])
def latest():
    """Get the most recent measurement for each sensor type"""
    try:
        connection = get_db_connection()
        if not connection:
            logging.error("Database connection failed in latest()")
            return jsonify({"error": "Database connection failed"}), 500
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT m1.sensor_id, m1.type, m1.value, m1.unit, m1.timestamp
            FROM measurements m1
            INNER JOIN (
                SELECT sensor_id, type, MAX(timestamp) as max_time
                FROM measurements
                GROUP BY sensor_id, type
            ) m2
            ON m1.sensor_id = m2.sensor_id
            AND m1.type = m2.type
            AND m1.timestamp = m2.max_time
            ORDER BY m1.timestamp DESC
        """)
        results = cursor.fetchall()
        cursor.close()
        connection.close()
        logging.info(f"Latest measurements retrieved: {len(results)} records")
        return jsonify(results), 200
    except Exception as e:
        logging.error(f"Error in latest: {e}")
        print(f"Error in latest: {e}")
        return jsonify({"error": str(e)}), 500

# 3) Get history (for graphs) - FIXED TO SHOW RECENT DATA
@app.route('/api/measurements/history', methods=['GET'])
def history():
    """Get historical data for a specific sensor type - MOST RECENT FIRST"""
    try:
        sensor = request.args.get("sensor")
        limit = request.args.get("limit", 50)  # Default to 50 points
        if not sensor:
            logging.warning("History request missing sensor parameter")
            return jsonify({"error": "sensor parameter required"}), 400
        connection = get_db_connection()
        if not connection:
            logging.error("Database connection failed in history()")
            return jsonify({"error": "Database connection failed"}), 500
        cursor = connection.cursor(dictionary=True)
        # Get the most recent records, then reverse them for chronological order
        cursor.execute("""
            SELECT value, unit, timestamp
            FROM measurements
            WHERE type = %s
            ORDER BY timestamp DESC
            LIMIT %s
        """, (sensor, int(limit)))
        results = cursor.fetchall()
        # Reverse to get chronological order (oldest to newest)
        results.reverse()
        cursor.close()
        connection.close()
        logging.info(f"History retrieved for sensor '{sensor}': {len(results)} records")
        return jsonify(results), 200
    except Exception as e:
        logging.error(f"Error in history: {e}")
        print(f"Error in history: {e}")
        return jsonify({"error": str(e)}), 500

# 4) Health check
@app.route('/api/health')
def health():
    """Check if server and database are operational"""
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            logging.info("Health check: OK")
            return jsonify({"server": "running", "database": "connected"}), 200
        else:
            logging.warning("Health check: Database disconnected")
            return jsonify({"server": "running", "database": "disconnected"}), 503
    except Exception as e:
        return jsonify({"server": "running", "database": "error", "message": str(e)}), 503

# 5) Get recent alerts FROM DATABASE
@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get recent alerts from database (last 20)"""
    try:
        connection = get_db_connection()
        if not connection:
            logging.error("Database connection failed in get_alerts()")
            return jsonify([]), 500
        cursor = connection.cursor(dictionary=True)
        # Get the 20 most recent alerts
        cursor.execute("""
            SELECT type, value, unit, location, message, timestamp
            FROM alerts
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        alerts = cursor.fetchall()
        cursor.close()
        connection.close()
        print(f" Alerts requested. Retrieved {len(alerts)} alerts from database")
        if alerts:
            print(f"Latest alert: {alerts[0]['message']}")
        logging.info(f"Alerts retrieved: {len(alerts)} records")
        return jsonify(alerts), 200
    except Exception as e:
        logging.error(f"Error in get_alerts: {e}")
        print(f"Error in get_alerts: {e}")
        return jsonify([]), 500

# 6) Get alert thresholds
@app.route('/api/thresholds', methods=['GET'])
def get_thresholds():
    """Get current alert thresholds"""
    return jsonify({
        "temperature": TEMP_THRESHOLD,
        "humidity": HUM_THRESHOLD
    }), 200

# 7) Clear old alerts (optional - call this to clean up old alerts)
@app.route('/api/alerts/clear', methods=['POST'])
def clear_old_alerts():
    """Clear alerts older than 24 hours"""
    try:
        connection = get_db_connection()
        if not connection:
            return jsonify({"status": "error", "message": "Database connection failed"}), 500
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM alerts
            WHERE timestamp < DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """)
        deleted_count = cursor.rowcount
        connection.commit()
        cursor.close()
        connection.close()
        print(f" Cleared {deleted_count} old alerts")
        return jsonify({"status": "ok", "deleted": deleted_count}), 200
    except Exception as e:
        logging.error(f"Error clearing alerts: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 8) Backward compatibility - keep your original /data endpoint
@app.route('/data', methods=['POST'])
def receive_data():
    """Original endpoint for compatibility with existing sensors"""
    return add_measurement()

if __name__ == '__main__':
    print("=" * 60)
    print("IoT API Server Starting...")
    print("=" * 60)

    # Create alerts table if it doesn't exist
    check_and_create_alerts_table()

    print("Endpoints:")
    print("  POST /api/measurements      - Add sensor data")
    print("  POST /data                  - Add sensor data (legacy)")
    print("  GET  /api/measurements/latest - Get latest readings")
    print("  GET  /api/measurements/history?sensor=temperature - Get history")
    print("  GET  /api/alerts            - Get recent alerts")
    print("  GET  /api/thresholds        - Get alert thresholds")
    print("  POST /api/alerts/clear      - Clear old alerts (24h+)")
    print("  GET  /api/health            - Health check")
    print("=" * 60)

    # Test database connection
    test_conn = get_db_connection()
    if test_conn:
        print("Database connection: OK")
        test_conn.close()
    else:
        print("X Database connection: FAILED")
        print("  Please check your MySQL credentials and database setup")

    print("=" * 60)
    print(f"Alert Thresholds:")
    print(f"  Temperature: > {TEMP_THRESHOLD}°C")
    print(f"  Humidity:    > {HUM_THRESHOLD}%")
    print("=" * 60)
    print("Server running on http://0.0.0.0:5000")
    print("Press CTRL+C to stop")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=True)
