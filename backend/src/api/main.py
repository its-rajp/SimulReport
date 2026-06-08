from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.core.orchestrator import ReportOrchestrator
from src.core.data_validator import DataValidator
from src.core.tasks import generate_report_task
from src.core.firebase_storage import CloudStorage
from models import create_report, get_report, list_reports
import shutil
import tempfile
import pandas as pd
from pathlib import Path
from config.settings import UPLOADS_DIR, PROCESSED_DIR
from fastapi.responses import Response
import datetime

app = FastAPI(title="AI Report Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = ReportOrchestrator()


@app.post("/generate-report")
async def generate_report(
    files: list[UploadFile] = File(...),
    industry: str = Form(...),
    service: str = Form(...),
    project_name: str = Form("Untitled"),
):
    # Save uploaded files to MongoDB GridFS
    uploaded_file_ids = []
    for file in files:
        file_content = await file.read()
        file_id = CloudStorage.save_file(file_content, file.filename)
        uploaded_file_ids.append(file_id)

    # Create MongoDB report record immediately
    report_id = create_report(
        project_name=project_name,
        industry=industry,
        service=service,
        status="Queued",
    )

    # Dispatch Celery background task
    params = {"industry": industry, "service": service, "project_name": project_name}
    generate_report_task.delay(report_id, uploaded_file_ids, params)

    return {
        "status": "success",
        "message": "Report generation queued",
        "job_id": report_id,
    }


@app.get("/job-status/{job_id}")
def get_job_status(job_id: str):
    report = get_report(job_id)
    if not report:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": report["id"],
        "status": report["status"],
        "file_name": Path(report["file_path"]).name if report.get("file_path") else None,
        "download_url": f"/download/{report['file_path']}" if report.get("file_path") else None,
    }


@app.get("/reports")
def list_all_reports():
    reports = list_reports()
    return [
        {
            "id": r["id"],
            "project_name": r["project_name"],
            "industry": r["industry"],
            "service": r["service"],
            "status": r["status"],
            "created_at": r["created_at"],
            "file_name": Path(r["file_path"]).name if r.get("file_path") else None,
            "download_url": f"/download/{r['file_path']}" if r.get("file_path") else None,
        }
        for r in reports
    ]


@app.get("/reports/{report_id}")
def get_single_report(report_id: str):
    r = get_report(report_id)
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": r["id"],
        "project_name": r["project_name"],
        "industry": r["industry"],
        "service": r["service"],
        "status": r["status"],
        "created_at": r["created_at"],
        "file_name": Path(r["file_path"]).name if r.get("file_path") else None,
        "download_url": f"/download/{r['file_path']}" if r.get("file_path") else None,
    }


@app.get("/download/{file_id}")
def download_report(file_id: str):
    file_bytes = CloudStorage.get_file(file_id)
    if not file_bytes:
        return {"error": "File not found"}

    return Response(
        content=file_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_id}"'},
    )


@app.get("/health")
def health_check():
    return {"status": "healthy"}


validator = DataValidator()


@app.post("/validate-files")
async def validate_files(
    files: list[UploadFile] = File(...),
    service: str = Form(...),
):
    """
    Phase 1: Validate uploaded CSVs against service-specific column requirements.
    Returns per-file validation results without running the full report pipeline.
    """
    results = []
    tmp_paths = []
    try:
        for file in files:
            suffix = Path(file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_paths.append(tmp.name)
            result = validator.validate(tmp_paths[-1], service)
            result["filename"] = file.filename
            results.append(result)
    finally:
        import os
        for p in tmp_paths:
            try:
                os.unlink(p)
            except Exception:
                pass

    overall_valid = all(r["valid"] for r in results)
    return {"overall_valid": overall_valid, "files": results}


def clean_nans(obj):
    import math
    if isinstance(obj, list):
        return [clean_nans(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    elif obj is None:
        return None
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return obj


@app.post("/preview-data")
async def preview_data(
    file: UploadFile = File(...),
):
    """
    Phase 2: Return column names and first 100 rows of a CSV for the Data Sandbox.
    """
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        if suffix in [".csv", ".txt"]:
            df = pd.read_csv(tmp_path, nrows=100)
        elif suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(tmp_path, nrows=100)
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported file type: {suffix}")

        df = df.where(pd.notnull(df), None)
        columns = list(df.columns)
        numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
        rows = df.to_dict(orient="records")
        rows = clean_nans(rows)

        return {
            "filename": file.filename,
            "columns": columns,
            "numeric_columns": numeric_columns,
            "row_count": len(rows),
            "rows": rows,
        }
    finally:
        import os
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

