"""
mongo_storage.py — GridFS file storage, now uses the shared database connection
from database.py to avoid creating multiple MongoClient instances.
"""
from database import get_gridfs
from bson.objectid import ObjectId
from loguru import logger


class MongoStorage:
    @staticmethod
    def save_file(file_content: bytes, filename: str) -> str:
        """Saves a file to GridFS and returns its ObjectId as a string."""
        fs = get_gridfs()
        try:
            file_id = fs.put(file_content, filename=filename)
            logger.info(f"Saved {filename} to GridFS with ID {file_id}")
            return str(file_id)
        except Exception as e:
            logger.error(f"Failed to save {filename} to GridFS: {e}")
            raise e

    @staticmethod
    def get_file(file_id_str: str):
        """Retrieves a file from GridFS by its ObjectId string."""
        import gridfs
        fs = get_gridfs()
        try:
            return fs.get(ObjectId(file_id_str))
        except gridfs.errors.NoFile:
            logger.warning(f"File {file_id_str} not found in GridFS")
            return None

    @staticmethod
    def delete_file(file_id_str: str):
        """Deletes a file from GridFS."""
        fs = get_gridfs()
        try:
            fs.delete(ObjectId(file_id_str))
            logger.info(f"Deleted {file_id_str} from GridFS")
        except Exception as e:
            logger.error(f"Failed to delete {file_id_str} from GridFS: {e}")
