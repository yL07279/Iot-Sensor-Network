#!/usr/bin/env python3
"""
Humidity Sensor Simulator — VM2
Generates random humidity readings and sends them to the API server (VM3).
Falls back to direct MySQL insert if HTTP is unavailable.
"""

import random
import time
import requests
from datetime import datetime
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ────────────────────────────────────────────
SERVER_URL  = os.getenv("API_URL", "http://192.168.56.103:5000/api/measurements")
SENSOR_NAME = "humidity"
LOCATION    = "VM2"

# MySQL (used only as fallback when HTTP is unavailable)
DB_HOST     = os.getenv("DB_HOST", "192.168.56.103")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME     = os.getenv("DB_NAME", "iot_db")
# ─────────────────────────────────────────────────────────────

print("=" * 50)
print("  Humidity Sensor — VM2")
print("=" * 50)
print(f"  Server : {SERVER_URL}")
print(f"  Location: {LOCATION}")
print("=" * 50)

# Attempt initial DB connection (fallback only)
db_connection = None
db_cursor = None
try:
    db_connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl_disabled=True,
    )
    db_cursor = db_connection.cursor()
    print("  DB fallback connection: OK")
except Error as e:
    print(f"  DB fallback connection failed: {e}")
    print("  Will only send via HTTP.")


def save_to_db(sensor, value, unit, location):
    """Write directly to MySQL — used only when HTTP fails."""
    if not db_connection or not db_cursor:
        return False
    try:
        sql = "INSERT INTO measurements (sensor_id, type, value, unit) VALUES (%s, %s, %s, %s)"
        db_cursor.execute(sql, (location, sensor, value, unit))
        db_connection.commit()
        return True
    except Error as e:
        print(f"  DB insert error: {e}")
        return False


while True:
    humidity = round(random.uniform(40.0, 80.0), 2)

    payload = {
        "sensor":   SENSOR_NAME,
        "value":    humidity,
        "unit":     "%",
        "location": LOCATION,
    }

    now = datetime.now().strftime("%H:%M:%S")
    http_ok = False

    try:
        response = requests.post(SERVER_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[{now}] Sent: {humidity}%")
            http_ok = True
        else:
            print(f"[{now}] HTTP error {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"[{now}] Server unreachable — will try DB fallback")
    except requests.exceptions.Timeout:
        print(f"[{now}] Request timed out")
    except Exception as e:
        print(f"[{now}] Error: {e}")

    if not http_ok and db_connection:
        if save_to_db(SENSOR_NAME, humidity, "%", LOCATION):
            print(f"[{now}] Saved directly to database (fallback)")
        else:
            print(f"[{now}] Both HTTP and DB failed — data lost for this cycle")

    time.sleep(5)
