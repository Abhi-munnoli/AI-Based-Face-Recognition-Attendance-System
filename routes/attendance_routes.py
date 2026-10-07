from flask import Blueprint, current_app, jsonify, request

from ai.face_service import recognize_and_mark_once
from firebase.firebase_config import get_db
from utils.security import role_required, validate_csrf

attendance_bp = Blueprint("attendance", __name__, url_prefix="/api")


def _process_attendance_request(data):
    image = data.get("image") or data.get("face_image")
    if not image:
        return jsonify(
            success=False,
            recognized=False,
            attendance_marked=False,
            already_marked=False,
            message="Face image is missing.",
        ), 400

    db = get_db()
    if db is None:
        return jsonify(
            success=False,
            recognized=False,
            attendance_marked=False,
            already_marked=False,
            message="Firebase database is unavailable.",
        ), 500

    current_app.logger.info("Face attendance recognition attempt started.")
    try:
        result = recognize_and_mark_once(
            db,
            image,
            camera_id=data.get("camera_id", "main"),
            tolerance=0.50,
        )
    except ValueError as error:
        current_app.logger.warning("Face recognition rejected input: %s", error)
        current_app.logger.info(
            "Attendance result: marked=False, already_marked=False, reason=%s",
            error,
        )
        return jsonify(
            success=True,
            recognized=False,
            attendance_marked=False,
            already_marked=False,
            confidence=0,
            face_distance=None,
            tolerance=0.50,
            message=str(error),
        )
    except Exception:
        current_app.logger.exception("Face attendance processing failed.")
        return jsonify(
            success=False,
            recognized=False,
            attendance_marked=False,
            already_marked=False,
            message="Face recognition failed. Check the Flask terminal.",
        ), 500

    current_app.logger.info(
        "Face recognition diagnostic: registered_encodings=%s, "
        "best_candidate=%s, best_face_distance=%s, tolerance=%s, accepted=%s",
        result.get("registered_face_count", 0),
        result.get("_best_candidate"),
        result.get("face_distance"),
        result.get("tolerance", 0.50),
        result.get("recognized", False),
    )
    if result.get("recognized"):
        student = result["student"]
        current_app.logger.info(
            "Face match accepted: student_id=%s, name=%s, roll_number=%s, "
            "face_distance=%s, tolerance=%s",
            student["student_id"],
            student["name"],
            student["roll_number"],
            result.get("face_distance"),
            result.get("tolerance", 0.50),
        )
    else:
        current_app.logger.info(
            "No valid registered match found. face_distance=%s, tolerance=%s",
            result.get("face_distance"),
            result.get("tolerance", 0.50),
        )

    current_app.logger.info(
        "Attendance result: marked=%s, already_marked=%s, message=%s",
        result.get("attendance_marked"),
        result.get("already_marked"),
        result.get("message"),
    )
    return jsonify(
        success=True,
        recognized=result.get("recognized", False),
        attendance_marked=result.get("attendance_marked", False),
        already_marked=result.get("already_marked", False),
        student=result.get("student"),
        confidence=result.get("confidence", 0),
        face_distance=result.get("face_distance"),
        tolerance=result.get("tolerance", 0.50),
        registered_face_count=result.get("registered_face_count", 0),
        message=result.get("message", ""),
        created=result.get("attendance_marked", False),
        attendance_id=result.get("attendance_id"),
    )


@attendance_bp.post("/recognize-face")
@role_required("admin")
def recognize():
    validate_csrf(request)
    return _process_attendance_request(request.get_json(silent=True) or {})


@attendance_bp.post("/mark-attendance")
@role_required("admin")
def mark():
    validate_csrf(request)
    data = request.get_json(silent=True) or {}
    if not (data.get("image") or data.get("face_image")):
        return jsonify(
            success=False,
            created=False,
            attendance_marked=False,
            already_marked=False,
            message="A camera face image is required before marking attendance.",
        ), 400
    return _process_attendance_request(data)
