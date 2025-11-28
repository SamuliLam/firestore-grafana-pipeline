#!/bin/bash
set -e

echo "📥 Pulling latest code..."
git pull

echo "🐳 Building Docker images..."
docker compose build

echo "🔄 Restarting..."
docker compose down
docker compose up -d

echo "✨ Deploy ready!"
