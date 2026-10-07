from firebase_admin import auth
from firebase.firebase_config import get_db


def get_student_count():
    return len(list(get_db().collection('students').where('status', '==', 'active').stream()))


def create_student_auth(email, password, display_name):
    user = auth.create_user(email=email, password=password, display_name=display_name)
    return user.uid


def delete_auth_user(uid):
    try:
        auth.delete_user(uid)
    except Exception:
        pass
