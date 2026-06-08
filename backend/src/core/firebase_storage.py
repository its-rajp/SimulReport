"""
firebase_storage.py — Firebase Cloud Storage file storage.
Replaces the old mongo_storage.py which used GridFS.
"""
from database import get_storage_bucket
from loguru import logger
import uuid


class CloudStorage:
    @staticmethod
    def save_file(file_content: bytes, filename: str) -> str:
        """Saves a file to Firebase Storage and returns its path as the ID."""
        bucket = get_storage_bucket()
        # Generate a unique path to avoid collisions
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        try:
            blob = bucket.blob(unique_filename)
            blob.upload_from_string(file_content)
            logger.info(f"Saved {filename} to Firebase Storage as {unique_filename}")
            return unique_filename
        except Exception as e:
            logger.error(f"Failed to save {filename} to Firebase Storage: {e}")
            raise e

    @staticmethod
    def get_file(file_id_str: str) -> bytes:
        """Retrieves a file from Firebase Storage by its filename ID."""
        bucket = get_storage_bucket()
        try:
            blob = bucket.blob(file_id_str)
            if not blob.exists():
                logger.warning(f"File {file_id_str} not found in Firebase Storage")
                return None
            return blob.download_as_bytes()
        except Exception as e:
            logger.error(f"Failed to retrieve {file_id_str} from Firebase Storage: {e}")
            return None

    @staticmethod
    def delete_file(file_id_str: str):
        """Deletes a file from Firebase Storage."""
        bucket = get_storage_bucket()
        try:
            blob = bucket.blob(file_id_str)
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted {file_id_str} from Firebase Storage")
            else:
                logger.warning(f"File {file_id_str} not found in Firebase Storage for deletion")
        except Exception as e:
            logger.error(f"Failed to delete {file_id_str} from Firebase Storage: {e}")
