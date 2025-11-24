#!/bin/bash
# Quick script to test individual flows

echo "=========================================================="
echo "  DST Airlines - Flow Testing Script"
echo "=========================================================="
echo ""
echo "Available flows to test:"
echo "  1. reference_data_flow - Sync reference data (countries, cities, etc.)"
echo "  2. flight_data_flow - Sync flight schedules"
echo "  3. update_actuals_flow - Update flight actuals"
echo "  4. ml_training_flow - Train ML models"
echo ""
echo "Choose a flow number (1-4): "
read -r choice

case $choice in
    1)
        echo "Testing Reference Data Flow..."
        docker exec -it dst-airlines-prefect-agent bash -c "cd /app/prefect_flows && python -c \"
from reference_data_flow import reference_data_sync_flow
print('Starting reference data sync flow...')
reference_data_sync_flow()
print('Flow completed!')
\""
        ;;
    2)
        echo "Testing Flight Data Flow..."
        docker exec -it dst-airlines-prefect-agent bash -c "cd /app/prefect_flows && python -c \"
from flight_data_flow import daily_flight_data_flow
print('Starting flight data flow...')
daily_flight_data_flow()
print('Flow completed!')
\""
        ;;
    3)
        echo "Testing Update Actuals Flow..."
        docker exec -it dst-airlines-prefect-agent bash -c "cd /app/prefect_flows && python -c \"
from update_actuals_flow import update_flight_actuals_flow
print('Starting update actuals flow...')
update_flight_actuals_flow()
print('Flow completed!')
\""
        ;;
    4)
        echo "Testing ML Training Flow..."
        docker exec -it dst-airlines-prefect-agent bash -c "cd /app/prefect_flows && python -c \"
from ml_training_flow import ml_training_flow
print('Starting ML training flow...')
ml_training_flow()
print('Flow completed!')
\""
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac
