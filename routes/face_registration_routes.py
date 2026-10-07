from functools import wraps

from flask import Blueprint, current_app, jsonify, render_template, request, session
from firebase_admin import firestore

from firebase.firebase_config import get_db
from utils.security import validate_csrf
from ai.face_recognition import invalidate_face_cache
from ai.face_service import (
    data_url_to_bytes,
    encode_single_face,
    find_duplicate_face,
    recognize_and_mark_once,
    recognize_face as recognize_registered_face,
)

face_registration_bp = Blueprint("face_registration", __name__)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            return jsonify(success=False, message="Authentication required."), 401
        if session.get("role") != "admin":
            return jsonify(success=False, message="Admin access required."), 403
        return view(*args, **kwargs)
    return wrapped


def clean(value):
    return str(value or "").strip()


@face_registration_bp.get("/admin/face-registration")
@admin_required
def face_registration_page():
    return render_template("admin/face_registration.html")


@face_registration_bp.post("/api/admin/face-registration")
@admin_required
def register_student_with_face():
    validate_csrf(request)
    data = request.get_json(silent=True) or {}

    fields = ["name", "roll_number", "email", "phone", "department", "semester", "section"]
    values = {key: clean(data.get(key)) for key in fields}
    if any(not values[key] for key in fields):
        return jsonify(success=False, message="All student fields are required."), 400

    image = data.get("face_image") or data.get("image")
    if not image:
        return jsonify(success=False, message="Capture a face before registering the student."), 400

    db = get_db()
    roll_exists = list(db.collection("students").where("roll_number", "==", values["roll_number"]).limit(1).stream())
    if roll_exists:
        return jsonify(success=False, message="Roll number already exists."), 409

    email_exists = list(db.collection("students").where("email", "==", values["email"].lower()).limit(1).stream())
    if email_exists:
        return jsonify(success=False, message="Email already exists."), 409

    try:
        image_bytes = data_url_to_bytes(image)
        encoding = encode_single_face(image_bytes)

        duplicate = find_duplicate_face(db, encoding, tolerance=0.50)
        if duplicate:
            return jsonify(
                success=False,
                message="This face is already registered to another student.",
            ), 409

        ref = db.collection("students").document()
        student = {
            "student_id": ref.id,
            **values,
            "email": values["email"].lower(),
            "face_encoding": encoding,
            "face_registered": True,
            "photo_url": "",
            "status": "active",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        ref.set(student)
        invalidate_face_cache()

        return jsonify(success=True, message="Student registered successfully with face.", student_id=ref.id), 201
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400
    except Exception:
        current_app.logger.exception("Face registration failed.")
        return jsonify(success=False, message="Unable to register the student. Please try again."), 500


@face_registration_bp.post("/api/face-registration/recognize")
@admin_required
def recognize_face():
    validate_csrf(request)
    data = request.get_json(silent=True) or {}
    try:
        db = get_db()
        result = recognize_registered_face(db, data.get("image", ""), tolerance=0.50)
        student = {
            "id": result.get("student_id"),
            "name": result.get("name", ""),
            "roll_number": result.get("roll_number", ""),
        } if result.get("recognized") else None
        public = [{
            "recognized": result.get("recognized", False),
            "confidence": result.get("confidence", 0),
            "distance": result.get("face_distance"),
            "student": student,
        }]
        return jsonify(
            success=True,
            recognized=result.get("recognized", False),
            faces=1,
            results=public,
            message=result.get("message", ""),
        )
    except ValueError as exc:
        return jsonify(success=False, message=str(exc)), 400
    except Exception:
        return jsonify(success=False, message="Face recognition failed."), 500


@face_registration_bp.post("/api/face-registration/mark-attendance")
@admin_required
def mark_face_attendance():
    validate_csrf(request)
    data = request.get_json(silent=True) or {}
    image = data.get("image") or data.get("face_image")
    if not image:
        return jsonify(
            success=False,
            created=False,
            message="A camera face image is required before marking attendance.",
        ), 400

    try:
        result = recognize_and_mark_once(
            get_db(),
            image,
            camera_id=data.get("camera_id", "webcam"),
            tolerance=0.50,
        )
    except ValueError as error:
        return jsonify(success=False, created=False, message=str(error)), 400
    except Exception:
        current_app.logger.exception("Face attendance processing failed.")
        return jsonify(
            success=False,
            created=False,
            message="Face recognition failed. Check the Flask terminal.",
        ), 500

    return jsonify(
        success=True,
        recognized=result.get("recognized", False),
        attendance_marked=result.get("attendance_marked", False),
        already_marked=result.get("already_marked", False),
        created=result.get("attendance_marked", False),
        student=result.get("student"),
        face_distance=result.get("face_distance"),
        confidence=result.get("confidence", 0),
        message=result.get("message", ""),
        attendance_id=result.get("attendance_id"),
    )
