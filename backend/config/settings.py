import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
TEMPLATES_DIR = DATA_DIR / "templates"
DB_DIR = BASE_DIR / "db"

# Ensure directories exist
for directory in [DATA_DIR, UPLOADS_DIR, PROCESSED_DIR, TEMPLATES_DIR, DB_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
INDUSTRIES = ["Oil & Gas", "Chemicals", "Pharmaceuticals", "Food & Beverages", "Metal & Mining", "Power Generation"]
SERVICES = ["CFD", "FEA", "DEM", "Process Modeling", "EFD"]
DATABASE_URL = f"sqlite:///{DB_DIR}/reports.db"
