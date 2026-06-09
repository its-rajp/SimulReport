"""
database.py — MongoDB-native connection module.
Replaces the old SQLAlchemy engine/session entirely.
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
import gridfs
import os
from loguru import logger

_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/report_generator")

_client = None
_db = None
_fs = None

def _connect():
    global _client, _db, _fs
    if _client is None:
        try:
            _client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=5000, connect=False)
            _db = _client.get_default_database()
            _fs = gridfs.GridFS(_db)
            logger.info(f"Connected to MongoDB at {_MONGO_URI}")
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            raise RuntimeError("MongoDB is not running.") from e

def get_db():
    """Returns the main MongoDB database instance."""
    _connect()
    return _db

def get_reports_collection():
    """Returns the 'reports' collection with indexes ensured."""
    _connect()
    col = _db["reports"]
    # Ensure efficient indexes on frequently-queried fields
    col.create_index([("created_at", DESCENDING)])
    col.create_index([("status", ASCENDING)])
    return col

def get_gridfs():
    """Returns the GridFS instance for binary file storage."""
    _connect()
    return _fs
