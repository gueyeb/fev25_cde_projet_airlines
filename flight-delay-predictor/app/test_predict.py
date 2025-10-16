"""
Test script for /api/predict endpoint
Simulates the prediction logic without dependencies
"""

from datetime import datetime

def test_predict():
    # Simulate request data
    scheduled_departure = "2025-10-20T10:30:00"

    try:
        # Parse the scheduled departure datetime
        scheduled_dt = datetime.fromisoformat(scheduled_departure)

        # Extract features for prediction
        features = {
            "hour": scheduled_dt.hour,
            "day_of_week": scheduled_dt.weekday(),
            "month": scheduled_dt.month,
            "day": scheduled_dt.day,
            "departure_airport": "FRA",
            "arrival_airport": "JFK",
        }

        print(f"✓ Parsed datetime: {scheduled_dt}")
        print(f"✓ Features: {features}")

        # Mock prediction logic
        import random
        base_delay = 0
        delay_probability = 0.3

        # Higher delays during rush hours
        if 7 <= features["hour"] <= 9 or 17 <= features["hour"] <= 19:
            base_delay = random.randint(15, 45)
            delay_probability = 0.7
        elif 6 <= features["hour"] <= 22:
            base_delay = random.randint(0, 20)
            delay_probability = 0.4
        else:
            base_delay = random.randint(0, 10)
            delay_probability = 0.2

        # Higher delays on Fridays and Sundays
        if features["day_of_week"] in [4, 6]:
            base_delay += 10
            delay_probability += 0.1

        # Add some randomness
        predicted_delay = max(0, base_delay + random.randint(-5, 10))
        delay_probability = min(1.0, delay_probability + random.uniform(-0.1, 0.1))

        # Mock factors
        factors = {
            "Time of Day": 0.35,
            "Day of Week": 0.25,
            "Route Congestion": 0.20,
            "Weather Conditions": 0.15,
            "Historical Delays": 0.05,
        }

        message = "Prediction generated successfully"
        if predicted_delay > 30:
            message = "High delay risk detected"
        elif predicted_delay > 15:
            message = "Moderate delay risk"
        else:
            message = "Low delay risk"

        response = {
            "prediction": float(predicted_delay),
            "delay_probability": float(delay_probability),
            "factors": factors,
            "message": message,
        }

        print(f"\n✓ Prediction successful!")
        print(f"  - Delay: {response['prediction']} minutes")
        print(f"  - Probability: {response['delay_probability']:.2%}")
        print(f"  - Message: {response['message']}")

        return response

    except ValueError as e:
        print(f"✗ Invalid datetime format: {e}")
        return None
    except Exception as e:
        print(f"✗ Prediction error: {e}")
        return None

if __name__ == "__main__":
    print("Testing /api/predict logic...\n")
    test_predict()
