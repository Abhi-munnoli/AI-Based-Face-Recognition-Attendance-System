from flask import (
    Blueprint,
    current_app,
    jsonify,
    render_template,
    request,
)

from firebase.firebase_config import get_db
from utils.security import role_required, validate_csrf
from ai.face_service import recognize_and_mark_once


camera_bp = Blueprint("camera", __name__)


# ============================================================
# CAMERA PAGE
# ============================================================

@camera_bp.get("/camera")
@role_required("admin")
def camera_page():
    return render_template("camera.html")


# ============================================================
# FACE RECOGNITION API
# ============================================================

@camera_bp.post("/api/recognize-face")
@role_required("admin")
def recognize_face_api():
    try:
        validate_csrf(request)
        data = request.get_json(silent=True) or {}
        image_data = data.get("image") or data.get("face_image")
        if not image_data:
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
                image_data,
                camera_id="main",
                tolerance=0.50,
            )
        except ValueError as error:
            current_app.logger.warning(
                "Face recognition rejected input: %s", error
            )
            current_app.logger.info(
                "Attendance result: marked=False, already_marked=False, "
                "reason=%s",
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
            current_app.logger.exception(
                "Face encoding/recognition error."
            )
            return jsonify(
                success=False,
                recognized=False,
                attendance_marked=False,
                already_marked=False,
                message="Unable to process the face. Check the Flask terminal.",
            ), 500

        current_app.logger.info(
            "Face recognition diagnostic: registered_encodings=%s, "
            "best_candidate=%s, best_face_distance=%s, tolerance=%s, "
            "accepted=%s",
            result.get("registered_face_count", 0),
            result.get("_best_candidate"),
            result.get("face_distance"),
            result.get("tolerance", 0.50),
            result.get("recognized", False),
        )
        if result.get("recognized"):
            current_app.logger.info(
                "Face match accepted: student_id=%s, name=%s, "
                "roll_number=%s, face_distance=%s, tolerance=%s",
                result["student"]["student_id"],
                result["student"]["name"],
                result["student"]["roll_number"],
                result.get("face_distance"),
                result.get("tolerance", 0.50),
            )
        else:
            current_app.logger.info(
                "No valid registered match found. face_distance=%s, "
                "tolerance=%s",
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
        )
    except Exception:
        current_app.logger.exception(
            "Face recognition API error"
        )
        return jsonify(
            success=False,
            recognized=False,
            attendance_marked=False,
            already_marked=False,
            message="Face recognition failed. Check the Flask terminal.",
        ), 500