
from pathlib import Path

# Main project directory
BASE_DIR = Path(__file__).resolve().parent

# Database files
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "healthcare_pm.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"

# Initial project information
PROJECT_NAME = (
    "Smart Healthcare Project Management and Monitoring System"
)

DEFAULT_BUDGET = 5_000_000
DEFAULT_DURATION_WEEKS = 16
