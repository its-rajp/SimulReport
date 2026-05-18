import pandas as pd
import PyPDF2
import os
from pathlib import Path
from loguru import logger
import sys

# Ensure config can be found
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.settings import UPLOADS_DIR, PROCESSED_DIR

class FileParser:
    @staticmethod
    def parse_file(file_path: str, file_type: str):
        """Parse different file types"""
        processed_data = {}
        
        if file_type == "csv":
            processed_data["data"] = pd.read_csv(file_path)
        elif file_type == "excel" or file_type == "xlsx":
            processed_data["data"] = pd.read_excel(file_path)
        elif file_type == "pdf":
            processed_data["text"] = FileParser._extract_pdf_text(file_path)
        elif file_type == "txt":
            with open(file_path, 'r') as f:
                processed_data["text"] = f.read()
        
        # Save processed data
        output_path = PROCESSED_DIR / Path(file_path).name
        if "data" in processed_data:
            processed_data["data"].to_csv(output_path.with_suffix('.csv'), index=False)
        
        logger.info(f"Parsed {file_path} -> {output_path}")
        return processed_data
    
    @staticmethod
    def _extract_pdf_text(pdf_path: str) -> str:
        """Extract text from PDF"""
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
        return text
