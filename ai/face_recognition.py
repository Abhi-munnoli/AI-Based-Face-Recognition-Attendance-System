import threading
import time
import numpy as np
import face_recognition
from config import Config
from firebase.firebase_config import get_db

_cache_lock = threading.Lock()
_cache = {'loaded_at': 0, 'items': []}


def load_known_faces(force=False):
    now = time.time()
    with _cache_lock:
        if not force and _cache['items'] and now - _cache['loaded_at'] < Config.FACE_CACHE_SECONDS:
            return list(_cache['items'])
        db = get_db()
        items = []
        for doc in db.collection('students').where('status', '==', 'active').stream():
            data = doc.to_dict() or {}
            encoding = data.get('face_encoding')
            if isinstance(encoding, list) and len(encoding) > 0:
                items.append({'uid': doc.id, **data, 'face_encoding': np.array(encoding, dtype=np.float64)})
        _cache['items'] = items
        _cache['loaded_at'] = now
        return list(items)


def invalidate_face_cache():
    with _cache_lock:
        _cache['items'] = []
        _cache['loaded_at'] = 0


def recognize_face(image_bytes):
    from .face_encoding import load_rgb_image
    image = load_rgb_image(image_bytes)
    locations = face_recognition.face_locations(image, model='hog')
    if not locations:
        return {'recognized': False, 'message': 'No face detected', 'faces': 0}
    known = load_known_faces()
    if not known:
        return {'recognized': False, 'message': 'No registered face encodings found', 'faces': len(locations)}
    encodings = face_recognition.face_encodings(image, locations)
    results = []
    for location, encoding in zip(locations, encodings):
        distances = face_recognition.face_distance([x['face_encoding'] for x in known], encoding)
        idx = int(np.argmin(distances))
        distance = float(distances[idx])
        matched = known[idx] if distance <= Config.FACE_DISTANCE_THRESHOLD else None
        confidence = max(0.0, min(100.0, (1.0 - distance) * 100.0))
        results.append({
            'location': location,
            'recognized': bool(matched),
            'student': matched,
            'distance': distance,
            'confidence': round(confidence, 2),
        })
    return {'recognized': any(x['recognized'] for x in results), 'results': results, 'faces': len(locations)}
