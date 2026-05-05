# IoT Sensor Network — Distributed Linux VM Project

A full distributed IoT monitoring platform built on **4 interconnected Linux virtual machines**. The system collects real-time temperature and humidity data from simulated sensors, stores everything in a MySQL database, and displays it on a live web dashboard with automatic alert generation.

> Developed for the **Operating Systems** module at **ENSAM Rabat** (2025/2026)  
> Authors: **Yasmine LAHLAOI** & **Alae MOUHSSINE** 

---

## Architecture

```
VM1 (Temp Sensor)  ──┐
                     ├──► HTTP POST ──► VM3 (Flask API + MySQL)
VM2 (Humidity)     ──┘                        │
                                               │ HTTP GET
                                              ▼
                                     VM4 (Dashboard)
                                              │
                                         Browser UI
```

All 4 VMs communicate over a private host-only network: **192.168.56.0/24**

| VM  | IP Address      | Role                                    |
|-----|-----------------|-----------------------------------------|
| VM1 | 192.168.56.101  | Temperature sensor simulator            |
| VM2 | 192.168.56.102  | Humidity sensor simulator               |
| VM3 | 192.168.56.103  | Flask REST API + MySQL database         |
| VM4 | 192.168.56.104  | Web dashboard (live visualization)      |

Sensors push a reading every **5 seconds** via HTTP. If the API is unreachable, they fall back to writing directly to MySQL to avoid data loss.

---

## Tech Stack

| Layer          | Technology                          |
|----------------|-------------------------------------|
| Sensor scripts | Python 3, `requests`                |
| API server     | Python 3, Flask, mysql-connector    |
| Database       | MySQL 8                             |
| Dashboard UI   | HTML / CSS / JavaScript, Chart.js   |
| Infrastructure | Ubuntu VMs on VirtualBox (host-only network) |

---

## Project Structure

```
iot-sensor-network/
│
├── vm1_temperature_sensor/
│   ├── temp_sensor.py        # Reads temp, POSTs to API, falls back to DB
│   └── requirements.txt
│
├── vm2_humidity_sensor/
│   ├── humidity_sensor.py    # Reads humidity, same architecture as VM1
│   └── requirements.txt
│
├── vm3_api_server/
│   ├── api.py                # Flask REST API — ingest, query, alert logic
│   ├── schema.sql            # MySQL table definitions + user setup
│   └── requirements.txt
│
├── vm4_dashboard/
│   ├── app.py                # Flask proxy — forwards requests to VM3
│   ├── templates/
│   │   └── index.html        # Live dashboard with Chart.js graphs
│   └── requirements.txt
│
├── .env.example              # Template for credentials — copy to .env
├── .gitignore
└── README.md
```

---

## Setup & Deployment

### Step 1 — Network Configuration

Assign static IPs to each VM using `netplan` (or your distro's network manager):

```
VM1 → 192.168.56.101
VM2 → 192.168.56.102
VM3 → 192.168.56.103
VM4 → 192.168.56.104
```

All VMs must be on the same **host-only adapter** in VirtualBox.

---

### Step 2 — Configure Credentials

On **every VM**, copy the environment template and fill in your values:

```bash
cp .env.example .env
nano .env   # set DB_PASSWORD and confirm other values
```

> ⚠️ **Never commit `.env` to Git.** It is already excluded in `.gitignore`.

---

### Step 3 — Database Setup (VM3 only)

Install MySQL, then run the schema script:

```bash
# Replace 'your_secure_password_here' in schema.sql with your actual password first
mysql -u root -p < vm3_api_server/schema.sql
```

This creates the `iot_db` database, both tables (`measurements` and `alerts`), and the `iot_user` account.

---

### Step 4 — Install Dependencies

Run this on each VM inside its respective folder:

```bash
pip3 install -r requirements.txt
```

---

### Step 5 — Start Everything

Launch services **in this order**:

**VM3 — API server:**
```bash
cd vm3_api_server
python3 api.py
```

**VM4 — Dashboard:**
```bash
cd vm4_dashboard
python3 app.py
```

**VM1 — Temperature sensor:**
```bash
cd vm1_temperature_sensor
python3 temp_sensor.py
```

**VM2 — Humidity sensor:**
```bash
cd vm2_humidity_sensor
python3 humidity_sensor.py
```

Then open your browser and navigate to:

```
http://192.168.56.104:8080
```

---

## API Reference

All endpoints are served by **VM3 on port 5000**.

| Method | Endpoint                          | Description                          |
|--------|-----------------------------------|--------------------------------------|
| POST   | `/api/measurements`               | Receive a sensor reading             |
| GET    | `/api/measurements/latest`        | Latest reading per sensor type       |
| GET    | `/api/measurements/history`       | Historical data (`?sensor=temperature`) |
| GET    | `/api/alerts`                     | Last 20 alerts                       |
| GET    | `/api/thresholds`                 | Current alert thresholds             |
| POST   | `/api/alerts/clear`               | Delete alerts older than 24 h        |
| GET    | `/api/health`                     | Server + database health check       |

### Example payload (POST `/api/measurements`)

```json
{
  "sensor":   "temperature",
  "value":    26.4,
  "unit":     "°C",
  "location": "VM1"
}
```

---

## Alert Thresholds

Alerts are generated automatically and stored in the database:

| Sensor      | Threshold |
|-------------|-----------|
| Temperature | > 28 °C   |
| Humidity    | > 70 %    |

Alerts appear in the dashboard's alert panel and are cleared by the `/api/alerts/clear` endpoint.

---

## Known Limitations

This is an **academic project**. The following items are intentionally simplified:

- No authentication on any endpoint
- Plain HTTP (no TLS/HTTPS)
- No API rate limiting
- Sensors produce **simulated** random data, not real hardware readings
- Credentials must be managed manually via `.env`

---

## Future Improvements

- Add ML-based anomaly detection on sensor streams
- Deploy to a cloud provider (AWS / Azure / GCP) instead of local VMs
- Support additional sensor types (CO₂, pressure, light)
- Build a mobile app for remote monitoring
- Add JWT authentication and HTTPS for production readiness

---

## License

Built for academic purposes at **ENSAM Rabat**. Free to use as a reference for IoT and Linux systems learning projects.
