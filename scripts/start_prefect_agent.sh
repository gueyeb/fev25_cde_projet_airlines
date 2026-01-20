#!/bin/bash
# Prefect Agent Startup Script
# Runs both the worker (for work pool) and serves flows (for scheduled execution)

set -e

echo "=============================================="
echo "DST Airlines - Prefect Agent Startup"
echo "=============================================="

# Wait for Prefect server to be ready
echo "[INFO] Waiting for Prefect server..."
until python -c "import urllib.request; urllib.request.urlopen('${PREFECT_API_URL}/health')" 2>/dev/null; do
    echo "[INFO] Prefect server not ready, waiting..."
    sleep 5
done
echo "[SUCCESS] Prefect server is ready!"

# Create work pool if it doesn't exist
echo "[INFO] Ensuring work pool 'default' exists..."
prefect work-pool create default --type process 2>/dev/null || echo "[INFO] Work pool 'default' already exists"

# Start worker in background
echo "[INFO] Starting Prefect worker for 'default' pool..."
prefect worker start --pool default &
WORKER_PID=$!
echo "[SUCCESS] Worker started (PID: $WORKER_PID)"

# Give worker time to connect
sleep 5

# Serve flows (this blocks and keeps the container running)
echo "[INFO] Serving Prefect flows..."
python -m prefect_flows.deploy_flows --mode=serve

# If serve exits, also stop the worker
kill $WORKER_PID 2>/dev/null || true
