# DST Airlines - Flight Delay Predictor Web Application

A full-stack web application for predicting flight delays using machine learning.

## Features

- **Real-time Predictions**: Predict flight delays based on route, time, and other factors
- **Airport Database Integration**: Pull airport data directly from PostgreSQL
- **Interactive UI**: Modern, responsive interface built with Bootstrap
- **ML-Ready**: Infrastructure ready for production ML models
- **Containerized**: Full Docker setup for easy deployment

## Quick Start

### Option 1: Local Development (without Docker)

1. **Install Dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

2. **Set Environment Variables**:
Make sure your database is running (use root docker-compose.yml):
```bash
# From project root
docker-compose up -d postgres mongo
```

3. **Run the Backend**:
```bash
# From backend directory
python app.py
```

4. **Access the App**:
Open your browser to: http://localhost:8000

### Option 2: Docker Compose (Recommended)

1. **Build and Run**:
```bash
docker-compose up --build
```

2. **Access the App**:
Open your browser to: http://localhost:8000

## Project Structure

```
flight-delay-predictor/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Backend container image
│   ├── models/             # ML models (PKL files)
│   └── utils/              # Utility functions
├── frontend/
│   ├── static/
│   │   ├── css/styles.css  # Custom styles
│   │   └── js/script.js    # Frontend logic
│   └── templates/
│       └── index.html      # Main page
├── docker-compose.yml      # Full stack orchestration
└── README.md              # This file
```

## API Endpoints

### GET `/`
Serve the main web interface

### GET `/api/airports`
Get list of airports from the database
**Response**: `Array of {code, name, city, country}`

### POST `/api/predict`
Predict flight delay

**Request Body**:
```json
{
  "flight_number": "LH400",
  "airline": "LH",
  "departure_airport": "FRA",
  "arrival_airport": "JFK",
  "scheduled_departure": "2025-10-15T10:30:00"
}
```

**Response**:
```json
{
  "prediction": 25.5,
  "delay_probability": 0.7,
  "factors": {
    "Time of Day": 0.35,
    "Day of Week": 0.25,
    "Route Congestion": 0.20,
    "Weather Conditions": 0.15,
    "Historical Delays": 0.05
  },
  "message": "Moderate delay risk"
}
```

### GET `/api/health`
Health check endpoint

**Response**:
```json
{
  "status": "healthy",
  "model_loaded": false,
  "database_connected": true
}
```

## ML Model Integration

The app is designed to integrate trained ML models:

1. **Train your model** using the scripts in `src/ml/`
2. **Save the model** as a `.pkl` file using joblib
3. **Place it in** `backend/models/flight_delay_model.pkl`
4. **Restart the app** - the model will be loaded automatically

Current prediction logic is a mock implementation for demonstration purposes.

## Environment Variables

Create a `.env` file in the `backend/` directory:

```env
PG_HOST=localhost
PG_PORT=5438
PG_DB=dst_airlines
PG_USER=dst_user
PG_PASSWORD=dst_password

MONGO_URI=mongodb://localhost:27018
MONGO_DB=dst_airlines
```

## Development

### Adding New Features

1. **Backend**: Edit `backend/app.py` to add new endpoints
2. **Frontend**: Modify `frontend/templates/index.html` and `frontend/static/js/script.js`
3. **Styles**: Update `frontend/static/css/styles.css`

### Hot Reload

When running locally with `python app.py`, the server automatically reloads on file changes.

## Database Setup

Ensure your databases are initialized:

```bash
# From project root
docker-compose up -d

# Run migrations
psql -h localhost -p 5438 -U dst_user -d dst_airlines -f database/migrations/1_create_tables.sql

# Sync reference data
python -m src.jobs.sync_airlines
python -m src.jobs.sync_airports
python -m src.jobs.sync_aircrafts
```

## Technology Stack

- **Backend**: FastAPI, Python 3.11, SQLAlchemy
- **Frontend**: HTML5, Bootstrap 5, Vanilla JavaScript, Chart.js
- **Database**: PostgreSQL 15, MongoDB 7
- **ML**: scikit-learn, pandas, numpy
- **Deployment**: Docker, docker-compose

## Troubleshooting

**Database Connection Error**:
- Ensure PostgreSQL is running on port 5438
- Check your `.env` file or environment variables

**Import Errors**:
- Make sure you're running from the correct directory
- The app needs access to `src/` modules

**Port Already in Use**:
- Change the port in `app.py`: `uvicorn.run(..., port=8001)`
- Or in docker-compose.yml: `"8001:8000"`

## Next Steps

- [ ] Integrate real ML model from `src/ml/`
- [ ] Add user authentication
- [ ] Implement flight search with autocomplete
- [ ] Add historical delay visualization
- [ ] Deploy to production (AWS/Azure/GCP)

## License

DST Airlines - Data Engineering Project
