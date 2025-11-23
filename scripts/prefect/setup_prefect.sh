#!/bin/bash
#
# Prefect Setup Script
# Sets up Prefect for the flight delay prediction pipeline
#

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[INFO] Setting up Prefect for Flight Delay Prediction"
echo "Project directory: ${PROJECT_DIR}"
echo ""

# Change to project directory
cd "${PROJECT_DIR}"

# Step 1: Install Prefect
echo "[STEP 1/6] Installing Prefect..."
${PYTHON_BIN} -m pip install -r requirements.txt

# Step 2: Check Prefect installation
echo ""
echo "[STEP 2/6] Checking Prefect installation..."
if ${PYTHON_BIN} -c "import prefect; print(f'Prefect version: {prefect.__version__}')" 2>/dev/null; then
    echo "[SUCCESS] Prefect installed successfully"
else
    echo "[ERROR] Prefect installation failed"
    exit 1
fi

# Step 3: Start Prefect server (or connect to Prefect Cloud)
echo ""
echo "[STEP 3/6] Prefect Server Configuration"
echo "Choose your Prefect backend:"
echo "  1) Local server (recommended for development)"
echo "  2) Prefect Cloud (recommended for production)"
echo ""
read -p "Select option (1 or 2): " -n 1 -r
echo

if [[ $REPLY == "1" ]]; then
    echo "[INFO] Using local Prefect server"
    echo "[INFO] Starting Prefect server in background..."

    # Check if server is already running
    if curl -s http://localhost:4200/api/health > /dev/null 2>&1; then
        echo "[SUCCESS] Prefect server already running at http://localhost:4200"
    else
        # Start server in background
        nohup prefect server start > "${PROJECT_DIR}/logs/prefect-server.log" 2>&1 &
        SERVER_PID=$!
        echo "[INFO] Prefect server started (PID: ${SERVER_PID})"
        echo "[INFO] Waiting for server to be ready..."
        sleep 10

        # Verify server is running
        if curl -s http://localhost:4200/api/health > /dev/null 2>&1; then
            echo "[SUCCESS] Prefect server running at http://localhost:4200"
            echo "[INFO] UI available at: http://localhost:4200"
        else
            echo "[ERROR] Failed to start Prefect server"
            echo "Check logs at: ${PROJECT_DIR}/logs/prefect-server.log"
            exit 1
        fi
    fi

    # Set API URL
    prefect config set PREFECT_API_URL="http://localhost:4200/api"

elif [[ $REPLY == "2" ]]; then
    echo "[INFO] Using Prefect Cloud"
    echo "Please log in to Prefect Cloud:"
    prefect cloud login
else
    echo "[ERROR] Invalid option"
    exit 1
fi

# Step 4: Create work pool
echo ""
echo "[STEP 4/6] Creating work pool..."
if prefect work-pool create default --type process 2>/dev/null; then
    echo "[SUCCESS] Work pool 'default' created"
else
    echo "[INFO] Work pool 'default' already exists"
fi

# Step 5: Create storage block
echo ""
echo "[STEP 5/6] Creating storage block..."
cat > /tmp/create_storage.py << 'EOF'
from prefect.filesystems import LocalFileSystem
import sys

try:
    storage = LocalFileSystem(basepath=".")
    storage.save("local-storage", overwrite=True)
    print("[SUCCESS] Storage block 'local-storage' created")
except Exception as e:
    if "already exists" in str(e).lower():
        print("[INFO] Storage block 'local-storage' already exists")
    else:
        print(f"[ERROR] Failed to create storage block: {e}")
        sys.exit(1)
EOF

${PYTHON_BIN} /tmp/create_storage.py
rm /tmp/create_storage.py

# Step 6: Deploy flows
echo ""
echo "[STEP 6/6] Deploying flows..."
cd "${PROJECT_DIR}/prefect_flows"
${PYTHON_BIN} deploy_flows.py

echo ""
echo "=" * 60
echo "[COMPLETE] Prefect setup completed successfully!"
echo ""
echo "Next steps:"
echo "  1. View deployments: prefect deployment ls"
echo "  2. Start an agent: prefect agent start -q default"
echo "  3. View UI: http://localhost:4200 (if using local server)"
echo ""
echo "Manual flow execution:"
echo "  - Reference data:  python -m prefect_flows.reference_data_flow"
echo "  - Daily pipeline:  python -m prefect_flows.flight_data_flow"
echo "  - Update actuals:  python -m prefect_flows.update_actuals_flow"
echo "  - Train ML model:  python -m prefect_flows.ml_training_flow"
echo ""
echo "To run a deployment on-demand:"
echo "  prefect deployment run '<flow-name>/<deployment-name>'"
echo "  Example: prefect deployment run 'daily-flight-data-pipeline/daily-flight-pipeline'"
