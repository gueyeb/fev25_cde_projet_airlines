from dotenv import load_dotenv
from pathlib import Path

def load_env():
    dotenv_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path)