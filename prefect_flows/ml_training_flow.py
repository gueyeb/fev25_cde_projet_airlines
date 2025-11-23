"""
ML Model Training Flow
Trains machine learning models for flight delay prediction
Schedule: Weekly (Sundays at 3:00 AM)
"""
from prefect import flow, task
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@task(
    name="train-classification-model",
    description="Train classification model to predict if flight will be delayed",
    retries=1,
    retry_delay_seconds=300,
    log_prints=True,
    timeout_seconds=3600  # 1 hour timeout
)
def train_classification_model_task():
    """
    Train the classification model.

    This model predicts whether a flight will be delayed (binary classification).
    """
    from src.ml.ml_classification import main as train_classification

    print("[INFO] Starting classification model training...")
    train_classification()
    print("[SUCCESS] Classification model trained")


@task(
    name="train-regression-model",
    description="Train regression model to predict delay duration",
    retries=1,
    retry_delay_seconds=300,
    log_prints=True,
    timeout_seconds=3600  # 1 hour timeout
)
def train_regression_model_task():
    """
    Train the regression model.

    This model predicts the delay duration in minutes.
    """
    from src.ml.ml_regression import main as train_regression

    print("[INFO] Starting regression model training...")
    train_regression()
    print("[SUCCESS] Regression model trained")


@task(
    name="validate-models",
    description="Validate that trained models can be loaded and used",
    retries=0,
    log_prints=True
)
def validate_models_task():
    """
    Validate that the trained models are loadable and functional.
    """
    import joblib
    from pathlib import Path

    model_dir = PROJECT_ROOT / "flight-delay-predictor" / "app" / "models"
    model_path = model_dir / "flight_delay_model.pkl"

    print("[INFO] Validating trained models...")

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Try to load the model
    try:
        model = joblib.load(model_path)
        print(f"[SUCCESS] Model loaded successfully from {model_path}")
        print(f"[INFO] Model type: {type(model).__name__}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        raise


@flow(
    name="ml-training-pipeline",
    description="Train and validate ML models for flight delay prediction",
    log_prints=True
)
def ml_training_flow(train_both_models: bool = False):
    """
    Flow to train ML models.

    Args:
        train_both_models: If True, trains both classification and regression models.
                          If False, trains only classification model (default).

    This flow:
    1. Trains classification model (always)
    2. Optionally trains regression model
    3. Validates that models can be loaded

    Schedule: Weekly on Sundays at 3:00 AM
    """
    print("[FLOW START] ML Model Training Pipeline")
    print("=" * 60)

    # Train classification model
    print("[STEP 1] Training classification model...")
    train_classification_model_task()

    # Optionally train regression model
    if train_both_models:
        print("[STEP 2] Training regression model...")
        train_regression_model_task()
    else:
        print("[SKIP] Regression model training skipped")

    # Validate models
    print("[STEP 3] Validating models...")
    validate_models_task()

    print("=" * 60)
    print("[FLOW COMPLETE] ML training pipeline completed successfully")


if __name__ == "__main__":
    # For testing: train only classification model
    ml_training_flow(train_both_models=False)
