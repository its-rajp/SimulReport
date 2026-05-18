from src.core.file_parser import FileParser
from src.ai.llm_engine import LLLEngine
from src.viz.graph_generator import GraphGenerator
from src.export.pdf_builder import PDFBuilder
from config.settings import PROCESSED_DIR
from database import SessionLocal
from models import Report
from pathlib import Path
from loguru import logger
import traceback

class ReportOrchestrator:
    def __init__(self):
        self.llm = LLLEngine()
        self.file_parser = FileParser()
    
    def generate_full_report(self, file_paths: list, params: dict, db):
        """Main orchestrator workflow"""
        logger.info("Starting report generation...")
        
        # Create db record
        db_report = Report(
            project_name=params.get("project_name", "Untitled"),
            industry=params.get("industry", ""),
            service=params.get("service", ""),
            status="Generating"
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        
        try:
            # 1. Parse all files
            all_data = {}
            for file_path in file_paths:
                file_type = Path(file_path).suffix[1:]
                all_data[file_path] = self.file_parser.parse_file(file_path, file_type)
            
            # 2. Extract Data Insights
            data_insights = {}
            for path, data in all_data.items():
                if "data" in data and not data["data"].empty:
                    df = data["data"]
                    num_df = df.select_dtypes(include=['number'])
                    if not num_df.empty:
                        # Get a clean statistical summary of the data
                        stats = num_df.describe().loc[['mean', 'min', 'max', 'std']].round(2).to_dict()
                        data_insights[Path(path).name] = stats
            
            insights_str = str(data_insights) if data_insights else "No numerical data available for analysis."
            
            # 3. Generate content sections in a single LLM call
            service = params.get("service", "Analysis")
            industry = params.get("industry", "General")
            
            report_content = {
                "full_text": self.llm.generate_report_content(
                    service=service,
                    industry=industry,
                    data_summary=insights_str[:2000] # Provide enough context but cap size
                )
            }
            
            # 3. Generate visualizations
            viz_files = {}
            for file_path, data in all_data.items():
                if "data" in data:
                    service = params.get("service", "Analysis")
                    viz_files.update(GraphGenerator.create_service_visualizations(data["data"], str(PROCESSED_DIR / "viz"), service))
            
            # 4. Generate final report
            pdf_builder = PDFBuilder()
            report_path = pdf_builder.build_report(report_content, viz_files, params)
            
            logger.info(f"Report generated: {report_path}")
            
            db_report.status = "Complete"
            db_report.file_path = str(report_path)
            db.commit()
            
            return str(report_path)
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            logger.error(traceback.format_exc())
            db_report.status = "Failed"
            db.commit()
            raise e
