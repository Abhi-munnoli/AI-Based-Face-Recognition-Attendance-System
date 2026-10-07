from functools import lru_cache
from pathlib import Path
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from config import Config


def initialize_firebase():
    if not firebase_admin._apps:
        cred_path = Path(Config.FIREBASE_CREDENTIALS)
        if not cred_path.exists():
            raise FileNotFoundError(
                f'Firebase service account file not found: {cred_path}. '
                'Copy serviceAccountKey.json there or set FIREBASE_CREDENTIALS.'
            )
        options = {}
        if Config.FIREBASE_STORAGE_BUCKET:
            options['storageBucket'] = Config.FIREBASE_STORAGE_BUCKET
        firebase_admin.initialize_app(credentials.Certificate(str(cred_path)), options or None)
    return firestore.client()


def get_db():
    return initialize_firebase()


def get_auth():
    initialize_firebase()
    return auth


def get_storage_bucket():
    initialize_firebase()
    return storage.bucket()


def server_timestamp():
    return SERVER_TIMESTAMP
