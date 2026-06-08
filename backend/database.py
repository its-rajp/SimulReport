"""
database.py — Firebase connection module.
Replaces the old MongoDB connection entirely.
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
import os
from loguru import logger

_db = None
_bucket = None
_initialized = False

def _connect():
    global _db, _bucket, _initialized
    if not _initialized:
        try:
            # We will use the default app credentials if FIREBASE_CREDENTIALS_PATH is not set
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./serviceAccountKey.json")
            bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "your-project-id.appspot.com")
            
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': bucket_name
                })
            else:
                logger.warning(f"Firebase credentials not found at {cred_path}. Trying default application credentials.")
                firebase_admin.initialize_app(options={'storageBucket': bucket_name})
                
            _db = firestore.client()
            _bucket = storage.bucket()
            _initialized = True
            logger.info("Connected to Firebase")
        except Exception as e:
            logger.error(f"Could not connect to Firebase: {e}")
            raise RuntimeError("Firebase is not initialized.") from e

def get_db():
    """Returns the main Firestore database instance."""
    _connect()
    return _db

def get_reports_collection():
    """Returns the 'reports' Firestore collection reference."""
    _connect()
    return _db.collection('reports')

def get_storage_bucket():
    """Returns the Firebase Storage bucket instance."""
    _connect()
    return _bucket
