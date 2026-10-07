from firebase.firebase_config import get_db
from utils.helpers import attendance_doc_id, today_key, time_key, utc_now


def mark_attendance(student, confidence, camera_id='webcam'):
    db = get_db()
    date_key = today_key()
    doc_id = attendance_doc_id(student['uid'], date_key)
    ref = db.collection('attendance').document(doc_id)
    existing = ref.get()
    if existing.exists:
        return False, existing.to_dict() or {}
    record = {
        'attendance_id': doc_id,
        'student_id': student['uid'],
        'student_name': student.get('name', ''),
        'roll_number': student.get('roll_number', ''),
        'date': date_key,
        'time': time_key(),
        'timestamp': utc_now(),
        'status': 'Present',
        'confidence': float(confidence),
        'camera_id': camera_id,
    }
    ref.set(record)
    return True, record
