#!/bin/bash
#
# Setup Cron Jobs for Flight Delay Prediction Pipeline
#
# This script sets up automated scheduling using cron
#

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCHEDULER_SCRIPT="${PROJECT_DIR}/scripts/orchestration/scheduler.sh"

echo "[INFO] Setting up cron jobs for flight delay prediction pipeline"
echo "[INFO] Project directory: ${PROJECT_DIR}"

# Make scheduler executable
chmod +x "${SCHEDULER_SCRIPT}"

echo ""
echo "Recommended Cron Schedule:"
echo "================================"
echo ""
echo "# Daily data sync at 2:00 AM"
echo "0 2 * * * ${SCHEDULER_SCRIPT} daily >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1"
echo ""
echo "# Update flight actuals every 4 hours (during business hours)"
echo "0 */4 * * * ${SCHEDULER_SCRIPT} hourly >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1"
echo ""
echo "# Train ML model weekly on Sundays at 3:00 AM"
echo "0 3 * * 0 ${SCHEDULER_SCRIPT} train-model >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1"
echo ""
echo "# Health check every hour"
echo "0 * * * * ${SCHEDULER_SCRIPT} health >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1"
echo ""
echo "================================"
echo ""

read -p "Do you want to install these cron jobs now? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Create temporary cron file
    TEMP_CRON=$(mktemp)

    # Get existing crontab
    crontab -l > "${TEMP_CRON}" 2>/dev/null || true

    # Add comment header
    echo "" >> "${TEMP_CRON}"
    echo "# Flight Delay Prediction Pipeline - Auto-generated on $(date)" >> "${TEMP_CRON}"

    # Add cron jobs
    echo "0 2 * * * ${SCHEDULER_SCRIPT} daily >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1" >> "${TEMP_CRON}"
    echo "0 */4 * * * ${SCHEDULER_SCRIPT} hourly >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1" >> "${TEMP_CRON}"
    echo "0 3 * * 0 ${SCHEDULER_SCRIPT} train-model >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1" >> "${TEMP_CRON}"
    echo "0 * * * * ${SCHEDULER_SCRIPT} health >> ${PROJECT_DIR}/logs/orchestration/cron.log 2>&1" >> "${TEMP_CRON}"

    # Install new crontab
    crontab "${TEMP_CRON}"
    rm "${TEMP_CRON}"

    echo "[SUCCESS] Cron jobs installed successfully!"
    echo ""
    echo "View installed cron jobs with: crontab -l"
    echo "View logs at: ${PROJECT_DIR}/logs/orchestration/"
else
    echo "[INFO] Cron jobs not installed. You can manually add them later."
    echo "      Use 'crontab -e' to edit your cron configuration."
fi

echo ""
echo "Next steps:"
echo "1. Test the scheduler manually: ${SCHEDULER_SCRIPT} health"
echo "2. Monitor logs: tail -f ${PROJECT_DIR}/logs/orchestration/scheduler.log"
echo "3. If using systemd, consider creating a systemd timer as an alternative to cron"
