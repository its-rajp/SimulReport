"""
models.py — Pydantic schema + MongoDB CRUD helpers.
Replaces the SQLAlchemy ORM class entirely.
All metadata for reports is stored in the MongoDB 'reports' collection.
"""
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from datetime import datetime, timezone
from database import get_reports_collection


# ── Pydantic response schema ──────────────────────────────────────────────────

class ReportModel(BaseModel):
    id: str
    project_name: str
    industry: str
    service: str
    status: str
    file_path: Optional[str] = None
    created_at: str
    dashboard_data: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True


def _serialize(doc: dict) -> dict:
    """Convert a MongoDB document to a clean dict for API responses."""
    if doc is None:
        return None
    return {
        "id": str(doc["_id"]),
        "project_name": doc.get("project_name", ""),
        "industry": doc.get("industry", ""),
        "service": doc.get("service", ""),
        "status": doc.get("status", ""),
        "file_path": doc.get("file_path"),
        "created_at": doc.get("created_at", datetime.now(timezone.utc)).replace(tzinfo=timezone.utc).isoformat(),
        "dashboard_data": doc.get("dashboard_data"),
    }


# ── MongoDB CRUD helpers ──────────────────────────────────────────────────────

def create_report(project_name: str, industry: str, service: str, status: str = "Queued") -> str:
    """Insert a new report document and return its string _id."""
    col = get_reports_collection()
    doc = {
        "project_name": project_name,
        "industry": industry,
        "service": service,
        "status": status,
        "file_path": None,
        "created_at": datetime.now(timezone.utc),
    }
    result = col.insert_one(doc)
    return str(result.inserted_id)


def get_report(report_id: str) -> Optional[dict]:
    """Fetch a single report by its string ObjectId. Returns serialized dict or None."""
    col = get_reports_collection()
    try:
        doc = col.find_one({"_id": ObjectId(report_id)})
    except Exception:
        return None
    return _serialize(doc)


def list_reports() -> list:
    """Return all reports sorted by newest first."""
    col = get_reports_collection()
    docs = col.find({}).sort("created_at", -1)
    return [_serialize(d) for d in docs]


def update_report_status(report_id: str, status: str, file_path: Optional[str] = None, dashboard_data: Optional[dict] = None):
    """Atomically update the status (and optionally file_path, dashboard_data) of a report."""
    col = get_reports_collection()
    update = {"$set": {"status": status}}
    if file_path is not None:
        update["$set"]["file_path"] = file_path
    if dashboard_data is not None:
        update["$set"]["dashboard_data"] = dashboard_data
    col.update_one({"_id": ObjectId(report_id)}, update)
