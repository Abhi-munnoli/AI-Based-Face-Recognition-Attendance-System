import base64
import binascii
import math
from numbers import Real
from typing import Any, Dict, List, Optional, Tuple

import cv2
import face_recognition
import numpy as np
from firebase_admin import firestore

from utils.helpers import attendance_doc_id, utc_now

FACE_TOLERANCE = 0.50
FACE_ENCODING_LENGTH = 128
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def _valid_encoding(value: Any) -> Optional[np.ndarray]:
    if not isinstance(value, (list, tuple)) or len(value) != FACE_ENCODING_LENGTH:
        return None
    if any(
        isinstance(item, bool)
        or not isinstance(item, (Real, np.integer, np.floating))
        for item in value
    ):
        return None

    try:
        encoding = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError, OverflowError):
        return None
    if encoding.shape != (FACE_ENCODING_LENGTH,) or not np.isfinite(encoding).all():
        return None
    return encoding


def _effective_tolerance(tolerance: float) -> float:
    try:
        value = float(tolerance)
    except (TypeError, ValueError) as error:
        raise ValueError("Face tolerance must be a finite number.") from error
    if not math.isfinite(value) or value < 0:
        raise ValueError("Face tolerance must be a finite, non-negative number.")
    return min(value, FACE_TOLERANCE)


def _encoding_from_rgb(rgb: np.ndarray) -> List[float]:
    locations = face_recognition.face_locations(rgb, model="hog")
    if len(locations) == 0:
        raise ValueError("No face detected.")
    if len(locations) > 1:
        raise ValueError("Multiple faces detected.")

    encodings = face_recognition.face_encodings(rgb, locations, num_jitters=1)
    if len(encodings) != 1:
        raise ValueError("Unable to generate a face encoding.")

    encoding = np.asarray(encodings[0], dtype=np.float64)
    if encoding.shape != (FACE_ENCODING_LENGTH,) or not np.isfinite(encoding).all():
        raise ValueError("Invalid face encoding generated.")
    return encoding.tolist()


def data_url_to_rgb_image(data_url: str) -> np.ndarray:
    if not data_url or not isinstance(data_url, str):
        raise ValueError("Face image is required.")
    if "," not in data_url:
        raise ValueError("Invalid face image format.")

    header, encoded = data_url.split(",", 1)
    if "base64" not in header.lower():
        raise ValueError("Invalid face image encoding.")

    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Invalid face image data.")

    if len(raw) > MAX_IMAGE_SIZE:
        raise ValueError("Face image is too large.")

    array = np.frombuffer(raw, dtype=np.uint8)
    bgr = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Unable to read captured face image.")

    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def data_url_to_bytes(data_url: str) -> bytes:
    if not data_url or not isinstance(data_url, str) or "," not in data_url:
        raise ValueError("Face image is required.")

    header, encoded = data_url.split(",", 1)
    if "base64" not in header.lower():
        raise ValueError("Invalid face image encoding.")

    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Invalid face image data.") from error

    if len(raw) > MAX_IMAGE_SIZE:
        raise ValueError("Face image is too large.")
    return raw


def extract_single_face_encoding(data_url: str) -> List[float]:
    return _encoding_from_rgb(data_url_to_rgb_image(data_url))


def encode_single_face(image_bytes: bytes) -> List[float]:
    if not image_bytes:
        raise ValueError("Face image is required.")
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise ValueError("Face image is too large.")

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    bgr = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("Unable to read captured face image.")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return _encoding_from_rgb(rgb)


def find_duplicate_face(
    db: Any,
    new_encoding: List[float],
    tolerance: float = FACE_TOLERANCE,
) -> Optional[Dict[str, Any]]:
    tolerance = _effective_tolerance(tolerance)
    known_encodings = []
    known_students = []

    for doc in db.collection("students").stream():
        student = doc.to_dict() or {}
        encoding_array = _valid_encoding(student.get("face_encoding"))
        if encoding_array is None:
            continue
        known_encodings.append(encoding_array)
        known_students.append({**student, "id": doc.id, "student_id": doc.id})

    if not known_encodings:
        return None

    new_vector = _valid_encoding(new_encoding)
    if new_vector is None:
        raise ValueError("Invalid face encoding generated.")
    distances = face_recognition.face_distance(known_encodings, new_vector)
    if distances.shape != (len(known_encodings),) or not np.isfinite(distances).all():
        raise ValueError("Unable to compare the face encoding.")
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])

    if best_distance <= tolerance:
        result = known_students[best_index].copy()
        result["face_distance"] = best_distance
        result["confidence"] = max(0.0, min(100.0, (1.0 - best_distance) * 100.0))
        return result

    return None


def duplicate_face(
    db: Any,
    new_encoding: List[float],
    tolerance: float = FACE_TOLERANCE,
) -> Optional[Dict[str, Any]]:
    return find_duplicate_face(db, new_encoding, tolerance)


def recognize_face(
    db: Any,
    data_url: str,
    tolerance: float = FACE_TOLERANCE,
) -> Dict[str, Any]:
    tolerance = _effective_tolerance(tolerance)
    new_encoding = extract_single_face_encoding(data_url)

    known_encodings = []
    students = []

    for doc in db.collection("students").stream():
        student = doc.to_dict() or {}
        status = str(student.get("status", "active")).strip().lower()
        if status not in ("active", "", "activated"):
            continue

        encoding_array = _valid_encoding(student.get("face_encoding"))
        if encoding_array is None:
            continue
        known_encodings.append(encoding_array)
        students.append({**student, "id": doc.id, "student_id": doc.id})

    if not known_encodings:
        return {
            "recognized": False,
            "message": "No registered student face found.",
            "confidence": 0,
            "face_distance": None,
            "tolerance": tolerance,
            "registered_face_count": 0,
            "_best_candidate": None,
        }

    distances = face_recognition.face_distance(
        known_encodings,
        np.asarray(new_encoding, dtype=np.float64),
    )
    if distances.shape != (len(known_encodings),) or not np.isfinite(distances).all():
        return {
            "recognized": False,
            "message": "Face does not match any registered student.",
            "confidence": 0,
            "face_distance": None,
            "tolerance": tolerance,
            "registered_face_count": len(known_encodings),
            "_best_candidate": None,
        }
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])
    student = students[best_index]
    candidate = {
        "student_id": student["id"],
        "name": student.get("name", ""),
        "roll_number": student.get("roll_number", ""),
    }
    confidence = max(0.0, min(100.0, (1.0 - best_distance) * 100.0))

    if best_distance > tolerance:
        return {
            "recognized": False,
            "message": "Face does not match any registered student.",
            "face_distance": best_distance,
            "confidence": round(confidence, 2),
            "tolerance": tolerance,
            "registered_face_count": len(known_encodings),
            "_best_candidate": candidate,
        }

    return {
        "recognized": True,
        "student_id": student["id"],
        "name": student.get("name", ""),
        "roll_number": student.get("roll_number", ""),
        "confidence": round(confidence, 2),
        "face_distance": best_distance,
        "tolerance": tolerance,
        "registered_face_count": len(known_encodings),
        "_best_candidate": candidate,
    }


def find_best_student_match(
    students,
    current_encoding,
    tolerance=FACE_TOLERANCE,
) -> Tuple[Optional[Dict[str, Any]], Optional[float]]:
    tolerance = _effective_tolerance(tolerance)
    known_encodings = []
    valid_students = []

    for student in students:
        encoding_array = _valid_encoding(student.get("data", {}).get("face_encoding"))
        if encoding_array is None:
            continue
        known_encodings.append(encoding_array)
        valid_students.append(student)

    if not known_encodings:
        return None, None

    distances = face_recognition.face_distance(
        known_encodings,
        np.asarray(current_encoding, dtype=np.float64),
    )
    if distances.shape != (len(known_encodings),) or not np.isfinite(distances).all():
        return None, None
    best_index = int(np.argmin(distances))
    best_distance = float(distances[best_index])

    if best_distance > tolerance:
        return None, best_distance

    return valid_students[best_index], best_distance


def mark_present_once(
    db: Any,
    recognition: Dict[str, Any],
    camera_id: str = "main",
) -> Dict[str, Any]:
    if recognition.get("recognized") is not True:
        return {
            "success": False,
            "marked": False,
            "already_marked": False,
            "message": "No registered student face found.",
        }

    try:
        face_distance = float(recognition.get("face_distance"))
    except (TypeError, ValueError):
        face_distance = math.inf
    if not math.isfinite(face_distance) or face_distance > FACE_TOLERANCE:
        return {
            "success": False,
            "marked": False,
            "already_marked": False,
            "message": "Face does not match any registered student.",
        }

    student_id = str(recognition.get("student_id") or "").strip()
    if not student_id:
        return {
            "success": False,
            "marked": False,
            "already_marked": False,
            "message": "Recognized student ID is missing.",
        }

    student_snapshot = db.collection("students").document(student_id).get()
    if not student_snapshot.exists:
        return {
            "success": False,
            "marked": False,
            "already_marked": False,
            "message": "Registered student no longer exists.",
        }
    student_data = student_snapshot.to_dict() or {}
    status = str(student_data.get("status", "active")).strip().lower()
    if status not in ("active", "", "activated"):
        return {
            "success": False,
            "marked": False,
            "already_marked": False,
            "message": "Registered student is inactive.",
        }
    if _valid_encoding(student_data.get("face_encoding")) is None:
        return {
            "success": False,
            "marked": False,
            "already_marked": False,
            "message": "Registered student face encoding is unavailable.",
        }

    now = utc_now()
    today = now.strftime("%Y-%m-%d")
    attendance_id = attendance_doc_id(student_id, today)
    attendance_ref = db.collection("attendance").document(attendance_id)

    deterministic_existing = attendance_ref.get()
    if deterministic_existing.exists:
        return {
            "success": True,
            "marked": False,
            "already_marked": True,
            "message": "Attendance already marked today.",
            "attendance_id": attendance_id,
        }

    existing = (
        db.collection("attendance")
        .where("student_id", "==", student_id)
        .stream()
    )

    for doc in existing:
        record = doc.to_dict() or {}
        if str(record.get("date", "")) == today:
            return {
                "success": True,
                "marked": False,
                "already_marked": True,
                "message": "Attendance already marked today.",
                "attendance_id": doc.id,
            }

    record = {
        "attendance_id": attendance_id,
        "student_id": student_id,
        "name": student_data.get("name", ""),
        "student_name": student_data.get("name", ""),
        "roll_number": student_data.get("roll_number", ""),
        "date": today,
        "time": now.strftime("%H:%M:%S"),
        "timestamp": now,
        "status": "Present",
        "confidence": recognition.get("confidence", 0),
        "face_distance": face_distance,
        "camera_id": camera_id,
        "created_at": firestore.SERVER_TIMESTAMP,
    }

    transaction = db.transaction()

    @firestore.transactional
    def create_attendance_once(transaction):
        existing_snapshot = attendance_ref.get(transaction=transaction)
        if existing_snapshot.exists:
            return False
        transaction.set(attendance_ref, record)
        return True

    marked = create_attendance_once(transaction)
    return {
        "success": True,
        "marked": marked,
        "already_marked": not marked,
        "message": (
            "Attendance marked successfully."
            if marked
            else "Attendance already marked today."
        ),
        "attendance_id": attendance_id,
        "attendance": record,
    }


def recognize_and_mark_once(
    db: Any,
    data_url: str,
    camera_id: str = "main",
    tolerance: float = FACE_TOLERANCE,
) -> Dict[str, Any]:
    tolerance = _effective_tolerance(tolerance)
    recognition = recognize_face(db, data_url, tolerance)
    result = {
        "recognized": recognition.get("recognized", False),
        "attendance_marked": False,
        "already_marked": False,
        "student": None,
        "confidence": recognition.get("confidence", 0),
        "face_distance": recognition.get("face_distance"),
        "tolerance": recognition.get("tolerance", tolerance),
        "registered_face_count": recognition.get("registered_face_count", 0),
        "message": recognition.get("message", ""),
        "_best_candidate": recognition.get("_best_candidate"),
    }

    if not recognition.get("recognized"):
        return result

    attendance = mark_present_once(db, recognition, camera_id)
    result.update({
        "attendance_marked": attendance.get("marked", False),
        "already_marked": attendance.get("already_marked", False),
        "student": {
            "student_id": recognition["student_id"],
            "name": recognition.get("name", ""),
            "roll_number": recognition.get("roll_number", ""),
        },
        "message": attendance.get("message", recognition.get("message", "")),
        "attendance_id": attendance.get("attendance_id"),
    })
    return result


def recognize_data_url(
    db: Any,
    data_url: str,
    tolerance: float = FACE_TOLERANCE,
) -> Dict[str, Any]:
    recognition = recognize_face(db, data_url, tolerance)
    return {
        "recognized": recognition.get("recognized", False),
        "faces": 1,
        "results": [{
            "recognized": recognition.get("recognized", False),
            "confidence": recognition.get("confidence", 0),
            "distance": recognition.get("face_distance"),
            "student": (
                {
                    "id": recognition.get("student_id"),
                    "name": recognition.get("name", ""),
                    "roll_number": recognition.get("roll_number", ""),
                }
                if recognition.get("recognized")
                else None
            ),
        }],
        "message": recognition.get("message", ""),
    }
