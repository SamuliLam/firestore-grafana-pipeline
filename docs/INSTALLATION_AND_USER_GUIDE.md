# Sensor Data System - Installation & User Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Local Installation (Windows/Mac)](#local-installation)
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

| Service | Username | Password | Access |
|---------|----------|----------|--------|
| Grafana | `admin` | `admin` | http://10.120.36.69/grafana/ |
| TimescaleDB | `admin` | `admin` | psql connection only |

### Service Ports

| Service | Port | Local URL | VM URL |
|---------|------|-----------|--------|
| Frontend | 5173 | http://localhost:5173 | http://10.120.36.69/ |
| Backend API | 8080 | http://localhost:8080 | http://10.120.36.69/api |
| TimescaleDB | 5432 | localhost:5432 | localhost:5432 |
| Grafana | 3000 | http://localhost:3000 | http://10.120.36.69/grafana/ |
| Nginx | 80 | N/A (local) | http://10.120.36.69/ |

---

## Local Installation

### Prerequisites

- **Docker Desktop** (Windows/Mac): https://www.docker.com/products/docker-desktop
- **Node.js 18+**: https://nodejs.org/ (LTS version recommended)
- **Git**: https://git-scm.com/
- **Text Editor**: VS Code or similar

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

> **Optional:** For Firestore integration, replace `docker/secrets/normalizer-sa.json` with your Google Cloud service account JSON file.

### Step 3: Start Docker Services

```bash
# Start all containers (timescaledb, backend API, grafana)
docker compose up -d

# Wait ~30 seconds, then verify all services are running
docker compose ps
```

Expected output:
```
NAME                      STATUS
timescaledb               Up (healthy)
firestore-grafana-...     Up
grafana                   Up
normalizer-api            Up
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

Open these URLs in your browser:

| URL | Expected Result |
|-----|-----------------|
| http://localhost:5173 | React frontend loads (sensor management UI) |
| http://localhost:3000 | Grafana login page (admin/admin) |
| http://localhost:8080/health | `{"status":"ok"}` |

### Step 6: First Steps

1. **Add a test sensor** in the frontend:
   - Sensor ID: `test-sensor-01`
   - Latitude: `60.1699`
   - Longitude: `24.9384`
   - Type: `urban`

2. **View in Grafana**:
   - Go to http://localhost:3000
   - Login with admin/admin
   - Navigate to Dashboards → MainDashboard

### Optional: Load Firestore History

If you have Firestore credentials:

1. Replace `docker/secrets/normalizer-sa.json` with your service account JSON
2. Restart backend: `docker compose restart normalizer-api`
3. Click **"Load History"** button in the frontend

---

## VM Installation (Ubuntu 20.04+)

This guide deploys the system to a production Ubuntu VM. It uses Nginx as a reverse proxy to serve the frontend and route API requests on a single port (80).

### Prerequisites

- Ubuntu 20.04 or newer
- SSH access to the VM
- Credentials: `username` and `password`
- VM IP address (e.g., `10.120.36.69`)

### Step 1: Connect to VM

```bash
ssh username@10.120.36.69
```

When prompted, enter your password.

### Step 2: Install Docker

Run these commands **one at a time**:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y
```

```bash
# Install Docker dependencies
sudo apt install -y ca-certificates curl gnupg lsb-release git
```

```bash
# Install curl
sudo apt install curl
```

```bash
# Add Docker's GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
```

```bash
# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

```bash
# Add your user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker $USER
```

**⚠️ Important:** You must log out and log back in for the group change to take effect:

```bash
exit
# Then reconnect:
ssh username@10.120.36.69
```

### Step 3: Install Node.js

```bash
# Add NodeSource repository for Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Install Node.js and npm
sudo apt install -y nodejs
```

Verify installation:
```bash
node --version   # Should show v20.x.x
npm --version    # Should show 10.x.x
```

### Step 4: Clone and Setup Repositories

```bash
# Create application directory
sudo mkdir -p /opt/sensordata
sudo chown $USER:$USER /opt/sensordata
cd /opt/sensordata

# Clone both repositories
git clone https://github.com/SamuliLam/firestore-grafana-pipeline.git
git clone https://github.com/SamuliLam/sensordata-frontend.git

# Create credentials file
cd firestore-grafana-pipeline
mkdir -p docker/secrets
echo "{}" > docker/secrets/normalizer-sa.json
```

> **For Firestore integration:** Replace `docker/secrets/normalizer-sa.json` with your service account JSON file.

### Step 5: Start Backend Services

```bash
cd /opt/sensordata/firestore-grafana-pipeline

# Start all containers
docker compose up -d

# Wait ~60 seconds, then verify
docker compose ps
```

All containers should show "Up" or "Up (healthy)":
```
NAME                    STATUS
timescaledb             Up (healthy)
normalizer-api          Up
grafana                 Up
```

Test the API:
```bash
curl http://localhost:8080/health
```

Should return: `{"status":"ok"}`

### Step 6: Build Frontend

```bash
cd /opt/sensordata/sensordata-frontend

# Install dependencies
npm install

# Build for production (creates dist/ folder)
npm run build
```

This creates optimized static files in the `dist/` directory that Nginx will serve.

### Step 7: Install and Configure Nginx

```bash
# Install Nginx
sudo apt install -y nginx

# Create Nginx configuration
sudo tee /etc/nginx/sites-available/sensordata > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Frontend React app
    location / {
        root /opt/sensordata/sensordata-frontend/dist;
        try_files $uri $uri/ =404;
        error_page 404 =200 /index.html;
    }

    # API proxy to backend
    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Webhook proxy
    location /webhook {
        proxy_pass http://localhost:8080/webhook;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Grafana proxy
    location /grafana/ {
        proxy_pass http://localhost:3000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

Enable the configuration:
```bash
# Create symbolic link to enable the site
sudo ln -sf /etc/nginx/sites-available/sensordata /etc/nginx/sites-enabled/sensordata

# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t
# Should output: "syntax is ok" and "test is successful"

# Start Nginx and enable auto-start on reboot
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Step 8: Configure Firewall

If firewall is enabled (`ufw`), allow traffic:

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 5432/tcp  # PostgreSQL (optional, for external access)
```

### Step 9: Access the Application

From your local machine, open these URLs in a browser:

| Application | URL |
|-------------|-----|
| **Frontend** | http://10.120.36.69/ |
| **Grafana** | http://10.120.36.69/grafana/ (login: admin/admin) |
| **API** | http://10.120.36.69/api/sensor_metadata |

---

## Updating the Deployment

When you make changes to the code:

### Update Frontend Code

```bash
# On your local machine, commit and push changes to Git
git add .
git commit -m "Update frontend"
git push origin fix-frontend-build-types

# On the VM, pull changes and rebuild
cd /opt/sensordata/sensordata-frontend
git pull origin fix-frontend-build-types
npm run build

# Reload Nginx to serve new files
sudo systemctl reload nginx
```

### Update Backend Code

```bash
# On your local machine
git add .
git commit -m "Update backend"
git push origin main

# On the VM, pull and restart
cd /opt/sensordata/firestore-grafana-pipeline
git pull origin main
docker compose up -d --build
```

---

## User Guide

### Dashboard Overview

The frontend provides a sensor management interface with:

- **Left Panel**: Add, remove, or import sensors
- **Right Panel**: Table of all sensors with details
- **Top Bar**: Load historical data from Firestore
- **Grafana Embeds**: View visualizations below the table

### Adding a Sensor

1. Open http://10.120.36.69/ in your browser
2. In the **left panel**, find the "Add New Sensor" section
3. Fill in the form:
   - **Sensor ID**: Unique identifier (e.g., `sensor-001`)
   - **Latitude**: Y-coordinate (e.g., `60.1699`)
   - **Longitude**: X-coordinate (e.g., `24.9384`)
   - **Sensor Type**: Select from dropdown (e.g., `urban`, `park`, `road`)
4. Click **"Add Sensor"**
5. The sensor appears in the table on the right

### Removing a Sensor

1. In the **left panel**, find the "Remove Sensor" section
2. Enter the Sensor ID you want to delete
3. Click **"Remove Sensor"**

⚠️ **This is permanent** — the sensor and all its data will be deleted.

### Importing Sensors from CSV

Bulk import sensors from a CSV file:

1. Prepare a CSV file with headers:
   ```csv
   sensor_id,latitude,longitude,sensor_type
   sensor-001,60.1699,24.9384,urban
   sensor-002,60.1710,24.9400,park
   sensor-003,60.1650,24.9450,road
   ```

2. In the **left panel**, find the "Import from CSV" section
3. Click **"Choose file"** and select your CSV
4. Click **"Import CSV"**
5. All sensors are added to the system

### Loading Historical Data from Firestore

> **Note:** Requires valid Firestore credentials in `docker/secrets/normalizer-sa.json`

1. Click the **"Load History"** button at the top of the page
2. The button will show a loading indicator
3. Wait for the sync to complete (may take several minutes depending on data size)
4. Status message appears:
   - ✅ **"Historical data loaded successfully"** → Data was imported
   - ❌ **"Error loading historical data"** → Check credentials or logs

### Viewing Sensor Details

**In the frontend table:**
- Click any row to see full sensor metadata
- Sensor ID, location (lat/lon), type, and creation timestamp

**In Grafana:**
1. Navigate to http://10.120.36.69/grafana/
2. Login with `admin` / `admin`
3. Go to **Dashboards** → **MainDashboard** or **Sensors_dashboard**
4. Use the **time picker** (top right) to select date range
5. Sensor graphs show temperature, humidity, and other metrics

---

## API Reference

All API calls use relative paths, which Nginx routes to the backend on port 8080.

### Health Check

```bash
GET /health
```

**Response:**
```json
{"status":"ok"}
```

### Sensor Management

#### List All Sensors
```bash
GET /api/sensor_metadata
```

**Response:**
```json
[
  {
    "sensor_id": "sensor-001",
    "latitude": 60.1699,
    "longitude": 24.9384,
    "sensor_type": "urban"
  }
]
```

#### Add a Sensor
```bash
POST /api/sensors
Content-Type: application/json

{
  "sensor_id": "sensor-001",
  "latitude": 60.1699,
  "longitude": 24.9384,
  "sensor_type": "urban"
}
```

**Response:**
```json
{"message": "Sensor added successfully"}
```

#### Delete a Sensor
```bash
DELETE /api/sensors/{sensor_id}
```

**Response:**
```json
{"message": "Sensor deleted successfully"}
```

### Bulk Operations

#### Import CSV
```bash
POST /api/sensors/import
Content-Type: multipart/form-data

file=<csv_file>
```

**CSV Format:**
```
sensor_id,latitude,longitude,sensor_type
sensor-001,60.1699,24.9384,urban
```

### Firestore History

#### Start Historical Data Load
```bash
POST /api/history
```

**Response:**
```json
{"message": "Historical data loading started"}
```

#### Check Load Status
```bash
GET /api/history/status
```

**Response:**
```json
{
  "status": "loading",
  "progress": 45
}
```

or

```json
{
  "status": "completed",
  "records_loaded": 12345
}
```

### Webhook

#### Receive Sensor Data
```bash
POST /webhook
Content-Type: application/json

{
  "sensor_id": "sensor-001",
  "temperature": 22.5,
  "humidity": 45.2,
  "timestamp": "2025-12-08T20:30:00Z"
}
```

---

## Troubleshooting

### Connection Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Cannot connect to http://10.120.36.69/ | VM not reachable or Nginx not running | `ssh` into VM, check: `sudo systemctl status nginx` |
| Page loads but shows "Cannot GET /" | Frontend not built | Run `npm run build` in frontend directory, reload Nginx |
| API calls fail (CORS errors) | Relative paths not used in frontend code | Check frontend code uses `/api/` not `http://localhost:8080/api/` |
| Infinite redirect loop (browser spinning) | Bad Nginx try_files configuration | Ensure `error_page 404 =200 /index.html;` is used, not `try_files $uri $uri/ /index.html;` |

### Backend/Database Issues

| Problem | Solution |
|---------|----------|
| `docker compose ps` shows container "Exited" | Check logs: `docker compose logs normalizer-api` |
| "Failed to add sensor" error | Backend API not responding. Verify: `curl http://localhost:8080/health` |
| "Connection refused" on port 8080 | Backend container crashed. Restart: `docker compose restart normalizer-api` |
| Database locked/slow queries | Verify TimescaleDB is healthy: `docker compose logs timescaledb` |

### Frontend Issues

| Problem | Solution |
|---------|----------|
| "Sensor ID is required" | Leave the Sensor ID field empty. It's a required field. |
| "Latitude/Longitude must be a number" | Enter valid numbers, e.g., 60.17 not "sixty" |
| Form submissions don't work | Check browser console (F12) for error messages. Verify API calls in Network tab. |
| CSV import fails | Ensure CSV has correct headers: `sensor_id,latitude,longitude,sensor_type` |
| "Failed to load historical data" | Firestore credentials missing or invalid. Check `docker/secrets/normalizer-sa.json` exists. |

### Nginx Configuration Issues

| Problem | Cause | Solution |
|---------|-------|---------|
| 502 Bad Gateway | Backend not responding at http://localhost:8080 | Verify backend is running: `docker compose ps` |
| 404 on /api/ endpoints | API route misconfigured | Check Nginx config: `sudo cat /etc/nginx/sites-available/sensordata` |
| Grafana returns 502 | Grafana container crashed | Restart: `docker compose restart grafana` |

### Useful Commands

```bash
# VM - Check service status
docker compose ps
docker compose logs -f [service_name]

# VM - Nginx diagnostics
sudo systemctl status nginx
sudo nginx -t
sudo cat /var/log/nginx/error.log | tail -50

# VM - Restart services
docker compose restart
sudo systemctl reload nginx

# VM - View frontend files
ls -la /opt/sensordata/sensordata-frontend/dist/

# Local - Check backend on VM
curl http://10.120.36.69/api/sensor_metadata
curl http://10.120.36.69/health
```

### Common Error Messages

**"connect ECONNREFUSED 127.0.0.1:8080"**
- Backend API not running
- Run: `docker compose restart normalizer-api`

**"Rewrite or internal redirection cycle"** (in nginx/error.log)
- Bad try_files configuration
- Fix: Use `error_page 404 =200 /index.html;` instead of `try_files $uri $uri/ /index.html;`

**"Cannot GET /api/sensors"**
- API route not configured in Nginx
- Verify: `sudo cat /etc/nginx/sites-available/sensordata | grep -A 5 "location /api"`

---

## Architecture Notes

### Frontend-Backend Communication

- **Local Dev**: Frontend on `localhost:5173` calls `http://localhost:8080/api/...`
- **VM Production**: Frontend on `10.120.36.69/` calls `/api/...` (Nginx proxies to backend)

### Why Relative Paths in Production?

When deployed on the VM, the frontend HTML and the backend API are served from different applications but accessed through a single Nginx gateway on port 80. Using relative paths (`/api/...`) ensures Nginx can intercept and route the requests correctly.

### Database Persistence

TimescaleDB data is stored in a Docker volume named `firestore-grafana-pipeline_timescaledb-data`. This persists across container restarts but will be deleted if you run `docker compose down -v`.

---

*Last updated: December 2025*
