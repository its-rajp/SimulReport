"""
models.py — Pydantic schema + Firebase Firestore CRUD helpers.
Replaces the MongoDB class entirely.
All metadata for reports is stored in the Firestore 'reports' collection.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from database import get_reports_collection
from google.cloud.firestore_v1.base_query import FieldFilter, Query


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


def _serialize(doc_id: str, doc: dict) -> dict:
    """Convert a Firestore document to a clean dict for API responses."""
    if doc is None:
        return None
    
    # Handle Firestore datetime format
    created_at = doc.get("created_at")
    if isinstance(created_at, datetime):
        created_at_str = created_at.astimezone(timezone.utc).isoformat()
    else:
        created_at_str = datetime.now(timezone.utc).isoformat()

    return {
        "id": doc_id,
        "project_name": doc.get("project_name", ""),
        "industry": doc.get("industry", ""),
        "service": doc.get("service", ""),
        "status": doc.get("status", ""),
        "file_path": doc.get("file_path"),
        "created_at": created_at_str,
        "dashboard_data": doc.get("dashboard_data"),
    }


# ── Firestore CRUD helpers ──────────────────────────────────────────────────────

def create_report(project_name: str, industry: str, service: str, status: str = "Queued") -> str:
    """Insert a new report document and return its string ID."""
    col = get_reports_collection()
    doc_ref = col.document() # Generates a random ID
    
    doc = {
        "project_name": project_name,
        "industry": industry,
        "service": service,
        "status": status,
        "file_path": None,
        "created_at": datetime.now(timezone.utc),
    }
    
    doc_ref.set(doc)
    return doc_ref.id


def get_report(report_id: str) -> Optional[dict]:
    """Fetch a single report by its string ID. Returns serialized dict or None."""
    col = get_reports_collection()
    doc_ref = col.document(report_id)
    doc_snap = doc_ref.get()
    
    if doc_snap.exists:
        return _serialize(doc_snap.id, doc_snap.to_dict())
    return None


def list_reports() -> list:
    """Return all reports sorted by newest first."""
    col = get_reports_collection()
    # Order by descending created_at
    docs = col.order_by("created_at", direction=Query.DESCENDING).stream()
    return [_serialize(d.id, d.to_dict()) for d in docs]


def update_report_status(report_id: str, status: str, file_path: Optional[str] = None, dashboard_data: Optional[dict] = None):
    """Atomically update the status (and optionally file_path, dashboard_data) of a report."""
    col = get_reports_collection()
    doc_ref = col.document(report_id)
    
    update = {"status": status}
    if file_path is not None:
        update["file_path"] = file_path
    if dashboard_data is not None:
        update["dashboard_data"] = dashboard_data
        
    doc_ref.update(update)
