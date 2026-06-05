import pandas as pd
import PyPDF2
from pathlib import Path
from loguru import logger
import sys

# Ensure config can be found
sys.path.append(str(Path(__file__).parent.parent.parent))


class FileParser:
    """
    Parses uploaded files (CSV, Excel, PDF, TXT) into usable data structures.
    Does NOT write to PROCESSED_DIR — all persistence is handled via MongoDB GridFS.
    """

    @staticmethod
    def parse_file(file_path: str, file_type: str) -> dict:
        """
        Parse different file types into a dict:
          - CSV/Excel  → {"data": pd.DataFrame}
          - PDF/TXT    → {"text": str}
        """
        ext = Path(file_path).suffix.lstrip(".").lower()
        # Allow caller to pass either extension or explicit type
        resolved = ext if ext else file_type.lower()

        processed_data = {}

        if resolved in ("csv", "txt"):
            try:
                processed_data["data"] = pd.read_csv(file_path)
            except Exception:
                # Some .txt files use tab/semicolon separators
                processed_data["data"] = pd.read_csv(file_path, sep=None, engine="python")

        elif resolved in ("xlsx", "xls", "excel"):
            processed_data["data"] = pd.read_excel(file_path)

        elif resolved == "pdf":
            processed_data["text"] = FileParser._extract_pdf_text(file_path)

        else:
            logger.warning(f"Unsupported file type '{resolved}' for {file_path}. Skipping.")

        logger.info(f"Parsed {Path(file_path).name} (type: {resolved})")
        return processed_data

    @staticmethod
    def _extract_pdf_text(pdf_path: str) -> str:
        """Extract text from PDF using PyPDF2."""
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text()
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return text
