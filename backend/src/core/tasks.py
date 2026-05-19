import os
import sys
from pathlib import Path

# Ensure the backend directory is in the python path for Celery imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from celery import Celery
from loguru import logger
from database import SessionLocal
from src.core.orchestrator import ReportOrchestrator
from models import Report

# Initialize Celery app with Redis broker
celery_app = Celery(
    "report_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
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
def generate_report_task(self, report_id: int, file_paths: list, params: dict):
    """
    Background task to process files, run LLM, and generate PDF.
    Updates the database with 'Complete' or 'Failed' status.
    """
    db = SessionLocal()
    try:
        db_report = db.query(Report).filter(Report.id == report_id).first()
        if not db_report:
            logger.error(f"Report {report_id} not found in DB.")
            return {"status": "error", "message": "Report not found"}

        db_report.status = "Generating"
        db.commit()

        # Call orchestrator. Note: we pass report_id to orchestrator so it doesn't create a new DB record.
        report_path = orchestrator.generate_full_report_with_id(report_id, file_paths, params, db)
        
        return {"status": "success", "report_path": str(report_path)}
    except Exception as e:
        logger.error(f"Task failed for report {report_id}: {e}")
        db_report = db.query(Report).filter(Report.id == report_id).first()
        if db_report:
            db_report.status = "Failed"
            db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
