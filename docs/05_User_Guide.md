# Sensor Data System - Installation & User Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Local Installation](#local-installation)
3. [VM Installation (Ubuntu)](#vm-installation)
4. [User Guide](#user-guide)
5. [API Reference](#api-reference)
6. [Troubleshooting](#troubleshooting)

---

## System Overview

The sensor data system is a full-stack application for collecting, storing, and visualizing IoT sensor data. It uses Docker containers for easy deployment and includes a React frontend, Python FastAPI backend, TimescaleDB for time-series data, and Grafana for visualization.

### Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ (HTTP:80 - Nginx reverse proxy)
       ▼
┌─────────────────────────────────────┐
│  Nginx (Frontend + API Gateway)     │
├─────────────────────────────────────┤
│ ├─ / → React Frontend (dist)        │
│ ├─ /api/ → Backend API (8080)       │
│ ├─ /grafana/ → Grafana (3000)       │
│ └─ /webhook → Webhook endpoint      │
└──────┬──────────────────────────────┘
       │
   ┌───┴──────────────────────┬──────────────────┐
   ▼                          ▼                  ▼
┌──────────┐          ┌─────────────┐    ┌──────────────┐
│ FastAPI  │          │TimescaleDB  │    │  Grafana     │
│Backend   │◄────────►│(PostgreSQL) │    │ Dashboards   │
│(8080)    │          │  (5432)     │    │  (3000)      │
└──────────┘          └─────────────┘    └──────────────┘
```

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| Grafana | `admin` | `admin` |
| TimescaleDB | `admin` | `admin` |

### Service Ports

| Service | Port | Local URL | VM URL (via Nginx) |
|---------|------|-----------|--------|
| Frontend | 5173 | http://localhost:5173 | http://VM-IP/ |
| Backend API | 8080 | http://localhost:8080 | http://VM-IP/api/ |
| TimescaleDB | 5432 | localhost:5432 | localhost:5432 | psql only
| Grafana | 3000 | http://localhost:3000 | http://VM-IP/grafana/ |

---

## Local Installation

### Prerequisites

- **Docker Desktop**
- **Node.js 18+**
- **Git**

### Step 1: Clone Repositories

```bash
cd ~/projects  # or any working directory
git clone https://github.com/SamuliLam/firestore-grafana-pipeline.git
git clone https://github.com/SamuliLam/sensordata-frontend.git
```

### Step 2: Setup Backend

```bash
cd firestore-grafana-pipeline

# Create credentials directory and file
mkdir -p docker/secrets
echo "{}" > docker/secrets/normalizer-sa.json
```
**Important:** For Firestore integration, replace `docker/secrets/normalizer-sa.json` with your Google Cloud service account JSON file.

### Step 3: Start Docker Services

```bash
# Start all containers (timescaledb, backend API, grafana)
docker compose up -d

# Wait ~30 seconds, then verify all services are running
docker compose ps
```

Expected output:
```
NAME                STATUS
timescaledb         Up (healthy)
normalizer-api      Up
grafana             Up
```

### Step 4: Setup Frontend

Open a **new terminal** window:

```bash
cd ~/projects/sensordata-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

You should see:
```
  ➜  Local:   http://localhost:5173/
```

### Step 5: Verify Installation

| URL | Expected Result |
|-----|-----------------|
| http://localhost:5173 | React frontend with sensor management UI |
| http://localhost:3000 | Grafana login page (admin/admin) |
| http://localhost:8080/health | `{"status":"ok"}` |

---

## VM Installation (Ubuntu 20.04+)

This guide deploys the system to a production Ubuntu VM with Nginx as reverse proxy.

### Prerequisites

- Ubuntu 20.04 or newer
- SSH access to the VM
- VM IP address (e.g., `10.120.36.70`)

### Quick Setup (Automated Script)

For a fast, automated installation, SSH into your VM and run:

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install curl

curl -fsSL https://raw.githubusercontent.com/SamuliLam/firestore-grafana-pipeline/main/scripts/vm-setup.sh | bash
```

This script will:
1. Install Docker, Node.js, and Nginx
2. Clone both repositories
3. Start all services
4. Configure Nginx reverse proxy

After running, access your app at `http://VM-IP/`

---

## User Guide

### Dashboard Overview

The frontend provides a sensor management interface with:

- **Left Panel**: Add, remove, or import sensors
- **Right Panel**: Table of all sensors with details
- **Top Bar**: Load historical data from Firestore
- **Embedded Grafana**: Visualizations (map, charts) displayed inline

### Adding a Sensor

1. Open http://VM-IP/ in your browser
2. In the **left panel**, find "Add New Sensor"
3. Fill in:
   - **Sensor ID**: Unique identifier (e.g., `sensor-001`)
   - **Latitude**: Y-coordinate (e.g., `60.1699`)
   - **Longitude**: X-coordinate (e.g., `24.9384`)
   - **Sensor Type**: Select from dropdown
4. Click **"Add Sensor"**

### Removing a Sensor

1. Find "Remove Sensor" section in the left panel
2. Enter the Sensor ID
3. Click **"Remove Sensor"**

⚠️ **Warning:** This permanently deletes the sensor and all its data.

### Importing from CSV

Prepare a CSV with headers:
```csv
sensor_id,latitude,longitude,sensor_type
sensor-001,60.1699,24.9384,urban
sensor-002,60.1710,24.9400,park
```

1. Click **"Choose file"** in the Import section
2. Select your CSV file
3. Click **"Import CSV"**

### Loading Historical Data

> Requires valid Firestore credentials in `docker/secrets/normalizer-sa.json`

1. Click **"Load History"** button
2. Wait for sync to complete
3. Data appears in Grafana dashboards

### Viewing Grafana Dashboards

Direct access: http://VM-IP/grafana/

Available dashboards:
- **Main Dashboard** (`/grafana/d/ad8fclh/main-dashboard`) - Overview with map
- **Sensor View** (`/grafana/d/ad6d5kp/sensori-kohtainen-nakyma`) - Per-sensor details
- **Overview** (`/grafana/d/adlcv8h/yleisnakyma`) - All sensors summary

---

## API Reference

All API endpoints use relative paths (e.g., `/api/...`).

### Health Check
```bash
GET /health
# Response: {"status":"ok"}
```

### List Sensors
```bash
GET /api/sensor_metadata
# Response: [{"sensor_id": "...", "latitude": ..., "longitude": ..., "sensor_type": "..."}]
```

### Add Sensor
```bash
POST /api/sensors
Content-Type: application/json

{"sensor_id": "sensor-001", "latitude": 60.17, "longitude": 24.94, "sensor_type": "urban"}
```

### Delete Sensor
```bash
DELETE /api/sensors/{sensor_id}
```

### Import CSV
```bash
POST /api/sensors/import
Content-Type: multipart/form-data
file=<csv_file>
```

### Load Firestore History
```bash
POST /api/history
```

### Check History Status
```bash
GET /api/history/status
# Response: {"status": "loading", "progress": 45} or {"status": "completed", "records_loaded": 12345}
```

---

## Troubleshooting

### Grafana Shows "Failed to load application files"

This is the most common issue. It means Grafana's subpath configuration is wrong.

**Symptoms:**
- Accessing http://VM-IP/grafana/ shows orange error page
- URL redirects to `/grafana/grafana/` (double path)

**Solution:**

1. **Check Grafana environment variables** in `docker-compose.yml`:
   ```yaml
   - GF_SERVER_ROOT_URL=http://localhost:3000/grafana/   # MUST have trailing slash!
   - GF_SERVER_SERVE_FROM_SUB_PATH=true
   ```

2. **Check Nginx proxy_pass** - must NOT have trailing slash:
   ```nginx
   location /grafana/ {
       proxy_pass http://localhost:3000;   # NO trailing slash!
   }
   ```

3. **Restart both services:**
   ```bash
   cd /opt/sensordata/firestore-grafana-pipeline
   docker compose down grafana
   docker compose up -d grafana
   sudo systemctl reload nginx
   ```

### Grafana Dashboard Not Found (404)

**Symptoms:**
- `curl http://localhost:3000/api/search` returns `[]`
- Dashboard URLs return 404

**Solution:**
Check dashboard provisioning:
```bash
# Verify dashboard files exist
ls -la /opt/sensordata/firestore-grafana-pipeline/grafana/provisioning/dashboards/

# Check Grafana logs
docker logs grafana --tail 50

# Force reload dashboards
docker compose restart grafana
sleep 5
curl http://localhost:3000/api/search
```

### Frontend Shows But Grafana Embeds Don't Load

**Symptoms:**
- Frontend UI loads correctly
- Grafana iframe area shows error or is blank

**Solution:**
1. Open browser DevTools (F12) → Network tab
2. Look for failed requests to `/grafana/...`
3. Check the error - usually 404 or CORS

Verify Grafana allows embedding:
```yaml
# In docker-compose.yml grafana section:
- GF_SECURITY_ALLOW_EMBEDDING=true
- GF_AUTH_ANONYMOUS_ENABLED=true
```

### Nginx Redirect Loop

**Symptoms:**
- Browser shows "too many redirects"
- Nginx error log: `rewrite or internal redirection cycle`

**Solution:**
Use `error_page` instead of `try_files` for SPA routing:
```nginx
location / {
    root /opt/sensordata/sensordata-frontend/dist;
    try_files $uri $uri/ =404;
    error_page 404 =200 /index.html;
}
```

### Default Nginx Page Shows Instead of Frontend

**Symptoms:**
- Accessing http://VM-IP/ shows "Welcome to nginx!" page
- Your custom config isn't being used

**Solution:**
```bash
# Check if your config is enabled
ls -la /etc/nginx/sites-enabled/

# If sensordata is missing, re-enable it
sudo ln -sf /etc/nginx/sites-available/sensordata /etc/nginx/sites-enabled/sensordata

# Remove default if it exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

### API Calls Fail (CORS or Connection Refused)

**Symptoms:**
- Browser console shows CORS errors
- Network requests to `/api/` fail

**Solution:**
1. Verify backend is running: `curl http://localhost:8080/health`
2. Check Nginx config routes `/api/` correctly
3. Ensure frontend uses relative paths (`/api/...`) not `localhost:8080`

### Useful Debug Commands

```bash
# Check all services
docker compose ps
docker compose logs -f [service_name]

# Test API directly
curl http://localhost:8080/health
curl http://localhost:8080/api/sensor_metadata

# Test Grafana directly
curl http://localhost:3000/api/search

# Check Nginx
sudo nginx -t
sudo systemctl status nginx
sudo tail -50 /var/log/nginx/error.log

# Restart everything
docker compose down
docker compose up -d
sudo systemctl restart nginx
```

---

## Quick Reference: Grafana + Nginx Configuration

The correct configuration for Grafana behind Nginx at `/grafana/`:

**docker-compose.yml (Grafana service):**
```yaml
environment:
  - GF_SERVER_ROOT_URL=http://localhost:3000/grafana/
  - GF_SERVER_SERVE_FROM_SUB_PATH=true
  - GF_SECURITY_ALLOW_EMBEDDING=true
  - GF_AUTH_ANONYMOUS_ENABLED=true
```

**Nginx config:**
```nginx
location /grafana/ {
    proxy_pass http://localhost:3000;    # NO trailing slash!
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Why this works:**
- Nginx receives `/grafana/d/xxx/dashboard` 
- `proxy_pass http://localhost:3000` (no trailing slash) forwards as `/grafana/d/xxx/dashboard`
- Grafana with `SERVE_FROM_SUB_PATH=true` expects and handles the `/grafana/` prefix
- `ROOT_URL` tells Grafana to generate links with `/grafana/` prefix

---

*Last updated: December 2025*
