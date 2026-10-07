import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-in-production')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS', str(BASE_DIR / 'firebase' / 'serviceAccountKey.json'))
    FIREBASE_STORAGE_BUCKET = os.getenv('FIREBASE_STORAGE_BUCKET', '')
    FIREBASE_WEB_API_KEY = os.getenv('FIREBASE_WEB_API_KEY', '')
    FIREBASE_AUTH_DOMAIN = os.getenv('FIREBASE_AUTH_DOMAIN', '')
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', '')
    FIREBASE_STORAGE_BUCKET_WEB = os.getenv('FIREBASE_STORAGE_BUCKET_WEB', '')
    FIREBASE_MESSAGING_SENDER_ID = os.getenv('FIREBASE_MESSAGING_SENDER_ID', '')
    FIREBASE_APP_ID = os.getenv('FIREBASE_APP_ID', '')
    FACE_DISTANCE_THRESHOLD = float(os.getenv('FACE_DISTANCE_THRESHOLD', '0.50'))
    FACE_CACHE_SECONDS = int(os.getenv('FACE_CACHE_SECONDS', '300'))
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    ADMIN_EMAILS = os.getenv("ADMIN_EMAILS", "")
