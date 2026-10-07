from flask import (
    Blueprint,
    jsonify,
    request,
    session,
    render_template,
    current_app
)

from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

from firebase.firebase_config import get_db

from utils.security import (
    validate_csrf,
    csrf_token_from_session
)


auth_bp = Blueprint("auth", __name__)


# ============================================================
# LOGIN PAGE
# ============================================================

@auth_bp.get("/login")
def login_page():
    """
    Display Firebase login page.
    """

    csrf_token_from_session()

    return render_template("login.html")


# ============================================================
# CREATE FLASK SESSION FROM FIREBASE LOGIN
# ============================================================

@auth_bp.post("/api/session")
def create_session():

    # --------------------------------------------------------
    # CSRF
    # --------------------------------------------------------

    validate_csrf(request)

    payload = request.get_json(silent=True) or {}

    # Accept both names for compatibility.
    id_token = (
        payload.get("id_token")
        or payload.get("idToken")
    )

    if not id_token:

        return jsonify({
            "success": False,
            "message": "Firebase ID token is missing."
        }), 400


    # --------------------------------------------------------
    # VERIFY FIREBASE TOKEN
    # --------------------------------------------------------

    try:

        decoded = auth.verify_id_token(
            id_token,
            check_revoked=False
        )

    except auth.ExpiredIdTokenError:

        return jsonify({
            "success": False,
            "message": (
                "Firebase session expired. "
                "Please sign in again."
            )
        }), 401

    except auth.RevokedIdTokenError:

        return jsonify({
            "success": False,
            "message": (
                "Firebase session was revoked. "
                "Please sign in again."
            )
        }), 401

    except ValueError:

        return jsonify({
            "success": False,
            "message": "Invalid Firebase authentication token."
        }), 401

    except FirebaseError as error:

        current_app.logger.error(
            "Firebase token verification failed: %s",
            error
        )

        return jsonify({
            "success": False,
            "message": (
                "Firebase authentication could not be verified."
            )
        }), 401

    except Exception as error:

        current_app.logger.exception(
            "Unexpected Firebase authentication error"
        )

        return jsonify({
            "success": False,
            "message": (
                "Authentication service error. "
                "Check the Flask terminal."
            )
        }), 500


    # --------------------------------------------------------
    # FIREBASE USER INFORMATION
    # --------------------------------------------------------

    uid = decoded.get("uid")

    email = (
        decoded.get("email")
        or ""
    ).strip().lower()

    name = (
        decoded.get("name")
        or email.split("@")[0]
        or "User"
    )


    if not uid:

        return jsonify({
            "success": False,
            "message": "Firebase UID is missing."
        }), 401


    # --------------------------------------------------------
    # FIREBASE CUSTOM CLAIMS
    # --------------------------------------------------------

    claims = decoded.get(
        "claims",
        {}
    )

    role = decoded.get(
        "role"
    )

    if not role:
        role = claims.get("role")


    if decoded.get("admin") is True:
        role = "admin"


    # --------------------------------------------------------
    # FIRESTORE ROLE LOOKUP
    # --------------------------------------------------------

    db = get_db()

    admin_record = None
    student_record = None
    user_record = None


    if db:

        # ----------------------------------------------------
        # 1. Check admins/{uid}
        # ----------------------------------------------------

        try:

            admin_ref = (
                db.collection("admins")
                .document(uid)
                .get()
            )

            if admin_ref.exists:

                admin_record = (
                    admin_ref.to_dict()
                    or {}
                )

        except Exception as error:

            current_app.logger.error(
                "Admin UID lookup failed: %s",
                error
            )


        # ----------------------------------------------------
        # 2. Check admins collection by email
        # ----------------------------------------------------

        if not admin_record and email:

            try:

                admin_docs = (
                    db.collection("admins")
                    .where(
                        "email",
                        "==",
                        email
                    )
                    .limit(1)
                    .stream()
                )

                for doc in admin_docs:

                    admin_record = (
                        doc.to_dict()
                        or {}
                    )

                    break

            except Exception as error:

                current_app.logger.error(
                    "Admin email lookup failed: %s",
                    error
                )


        # ----------------------------------------------------
        # 3. Check users/{uid}
        # ----------------------------------------------------

        try:

            user_ref = (
                db.collection("users")
                .document(uid)
                .get()
            )

            if user_ref.exists:

                user_record = (
                    user_ref.to_dict()
                    or {}
                )

        except Exception as error:

            current_app.logger.error(
                "User lookup failed: %s",
                error
            )


        # ----------------------------------------------------
        # 4. Check students/{uid}
        # ----------------------------------------------------

        try:

            student_ref = (
                db.collection("students")
                .document(uid)
                .get()
            )

            if student_ref.exists:

                student_record = (
                    student_ref.to_dict()
                    or {}
                )

        except Exception as error:

            current_app.logger.error(
                "Student lookup failed: %s",
                error
            )


    # --------------------------------------------------------
    # DETERMINE ROLE
    # --------------------------------------------------------

    if admin_record:

        role = "admin"

        name = (
            admin_record.get("name")
            or admin_record.get("display_name")
            or name
        )

    elif role == "admin":

        role = "admin"

    elif student_record:

        role = "student"

        name = (
            student_record.get("name")
            or name
        )

    elif user_record:

        role = (
            user_record.get("role")
            or "student"
        )

        name = (
            user_record.get("name")
            or name
        )

    else:

        # ----------------------------------------------------
        # Optional admin-email fallback
        #
        # This allows the configured admin account to log in
        # even if the admin Firestore document was not created.
        # ----------------------------------------------------

        configured_admins = current_app.config.get(
            "ADMIN_EMAILS",
            ""
        )

        if isinstance(
            configured_admins,
            str
        ):

            admin_emails = {
                item.strip().lower()
                for item in configured_admins.split(",")
                if item.strip()
            }

        else:

            admin_emails = set()


        if email in admin_emails:

            role = "admin"

        else:

            return jsonify({
                "success": False,
                "message": (
                    "Firebase authentication succeeded, "
                    "but this account is not registered "
                    "as an administrator or student."
                )
            }), 403


    # --------------------------------------------------------
    # CREATE FLASK SESSION
    # --------------------------------------------------------

    session.clear()

    session["uid"] = uid
    session["email"] = email
    session["name"] = name
    session["role"] = role

    # Create a fresh CSRF token for the new session.
    session["csrf_token"] = (
        csrf_token_from_session()
    )


    # --------------------------------------------------------
    # REDIRECT
    # --------------------------------------------------------

    if role == "admin":

        redirect_url = "/admin/dashboard"

    else:

        redirect_url = "/student/dashboard"


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return jsonify({

        "success": True,

        "user": {
            "uid": uid,
            "email": email,
            "name": name,
            "role": role
        },

        "role": role,

        "name": name,

        "redirect": redirect_url

    })


# ============================================================
# LOGOUT
# ============================================================

@auth_bp.post("/api/logout")
def logout():

    validate_csrf(request)

    session.clear()

    return jsonify({
        "success": True,
        "message": "Logged out successfully."
    })


# ============================================================
# CURRENT SESSION
# ============================================================

@auth_bp.get("/api/me")
def me():

    if not session.get("uid"):

        return jsonify({
            "authenticated": False
        })


    return jsonify({

        "authenticated": True,

        "uid": session.get("uid"),

        "email": session.get("email"),

        "role": session.get("role"),

        "name": session.get("name", "")

    })


# ============================================================
# FIREBASE WEB CONFIG
# ============================================================

@auth_bp.get("/api/firebase-config")
def firebase_config():

    cfg = current_app.config

    return jsonify({

        "apiKey":
            cfg["FIREBASE_WEB_API_KEY"],

        "authDomain":
            cfg["FIREBASE_AUTH_DOMAIN"],

        "projectId":
            cfg["FIREBASE_PROJECT_ID"],

        "storageBucket":
            cfg["FIREBASE_STORAGE_BUCKET_WEB"],

        "messagingSenderId":
            cfg["FIREBASE_MESSAGING_SENDER_ID"],

        "appId":
            cfg["FIREBASE_APP_ID"]

    })