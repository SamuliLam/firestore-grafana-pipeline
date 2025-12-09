#!/bin/bash
#
# Sensor Data System - VM Setup Script
# Run this on a fresh Ubuntu 20.04+ VM
#
# Usage: 
#   curl -fsSL https://raw.githubusercontent.com/SamuliLam/firestore-grafana-pipeline/main/scripts/vm-setup.sh | bash
#   OR
#   chmod +x vm-setup.sh && ./vm-setup.sh
#

set -e  # Exit on any error

echo "=========================================="
echo "  Sensor Data System - VM Setup Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run as root. Run as regular user with sudo access."
    exit 1
fi

echo ""
echo "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install curl
print_status "System updated"

echo ""
echo "Step 2: Installing dependencies..."
sudo apt install -y ca-certificates curl gnupg lsb-release git
print_status "Dependencies installed"

echo ""
echo "Step 3: Installing Docker..."
if command -v docker &> /dev/null; then
    print_warning "Docker already installed, skipping..."
else
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker $USER
    print_status "Docker installed"
    print_warning "You may need to log out and back in for docker group to take effect"
fi

echo ""
echo "Step 4: Installing Node.js 20..."
if command -v node &> /dev/null; then
    print_warning "Node.js already installed ($(node --version)), skipping..."
else
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
    print_status "Node.js $(node --version) installed"
fi

echo ""
echo "Step 5: Creating application directory..."
sudo mkdir -p /opt/sensordata
sudo chown $USER:$USER /opt/sensordata
print_status "Directory /opt/sensordata created"

echo ""
echo "Step 6: Cloning repositories..."
cd /opt/sensordata

if [ -d "firestore-grafana-pipeline" ]; then
    print_warning "firestore-grafana-pipeline already exists, pulling latest..."
    cd firestore-grafana-pipeline && git pull && cd ..
else
    git clone https://github.com/SamuliLam/firestore-grafana-pipeline.git
    print_status "Backend repo cloned"
fi

if [ -d "sensordata-frontend" ]; then
    print_warning "sensordata-frontend already exists, pulling latest..."
    cd sensordata-frontend && git pull && cd ..
else
    git clone https://github.com/SamuliLam/sensordata-frontend.git
    print_status "Frontend repo cloned"
fi

echo ""
echo "Step 7: Setting up backend..."
cd /opt/sensordata/firestore-grafana-pipeline
mkdir -p docker/secrets
if [ ! -f "docker/secrets/normalizer-sa.json" ]; then
    echo "{}" > docker/secrets/normalizer-sa.json
    print_status "Created empty credentials file"
else
    print_warning "Credentials file already exists"
fi

echo ""
echo "Step 8: Starting Docker containers..."
# Use newgrp to get docker group access in this session
if groups | grep -q docker; then
    docker compose up -d
else
    sudo docker compose up -d
fi
print_status "Docker containers starting..."

echo ""
echo "Step 9: Building frontend..."
cd /opt/sensordata/sensordata-frontend
npm install
npm run build
print_status "Frontend built"

echo ""
echo "Step 10: Installing and configuring Nginx..."
sudo apt install -y nginx

sudo tee /etc/nginx/sites-available/sensordata > /dev/null << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    # Frontend React app (SPA)
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

    # Grafana proxy - NO trailing slash on proxy_pass!
    location /grafana/ {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX_EOF

sudo ln -sf /etc/nginx/sites-available/sensordata /etc/nginx/sites-enabled/sensordata
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
print_status "Nginx configured and started"

echo ""
echo "Step 11: Configuring Firewall..."
if command -v ufw &> /dev/null; then
    # Ensure SSH is allowed so we don't lock ourselves out
    sudo ufw allow 22/tcp
    # Allow HTTP traffic
    sudo ufw allow 80/tcp
    print_status "Firewall rules updated (allowed ports 22 and 80)"
else
    print_warning "UFW not found, skipping firewall configuration"
fi

echo ""
echo "Step 12: Waiting for services to be ready..."
sleep 10

# Check services
echo ""
echo "=========================================="
echo "  Checking Services"
echo "=========================================="

if curl -s http://localhost:8080/health | grep -q "ok"; then
    print_status "Backend API is running"
else
    print_warning "Backend API not responding yet (may still be starting)"
fi

if curl -s http://localhost:3000/api/health | grep -q "ok" 2>/dev/null || curl -s http://localhost:3000 | grep -q "Grafana" 2>/dev/null; then
    print_status "Grafana is running"
else
    print_warning "Grafana not responding yet (may still be starting)"
fi

# Get VM IP
VM_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Access your application at:"
echo "  Frontend:  http://${VM_IP}/"
echo "  Grafana:   http://${VM_IP}/grafana/"
echo "  API:       http://${VM_IP}/api/sensor_metadata"
echo ""
echo "Default Grafana credentials: admin / admin"
echo ""
echo "If services aren't responding, wait a minute and check:"
echo "  docker compose ps"
echo "  docker compose logs -f"
echo ""
print_warning "If you just installed Docker, log out and back in, then run:"
print_warning "  cd /opt/sensordata/firestore-grafana-pipeline && docker compose up -d"
echo ""
