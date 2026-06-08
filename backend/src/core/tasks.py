import os
import sys
from pathlib import Path

# Ensure the backend directory is in the python path for Celery imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from celery import Celery
from loguru import logger
from models import update_report_status
from src.core.orchestrator import ReportOrchestrator

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app with Redis broker
celery_app = Celery(
    "report_tasks",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

orchestrator = ReportOrchestrator()


@celery_app.task(bind=True, name="generate_report_task")
def generate_report_task(self, report_id: str, file_ids: list, params: dict):
    """
    Background Celery task — processes files, runs LLM, generates PDF.
    Updates Firestore report document with 'Complete' or 'Failed' status.
    """
    try:
        report_path = orchestrator.generate_full_report_with_id(report_id, file_ids, params)
        return {"status": "success", "report_path": str(report_path)}
    except Exception as e:
        logger.error(f"Task failed for report {report_id}: {e}")
        update_report_status(report_id, "Failed")
        return {"status": "error", "message": str(e)}
