import secrets
from functools import wraps

from flask import abort, g, session
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

from firebase.firebase_config import get_db


# ============================================================
# FIREBASE TOKEN VERIFICATION
# ============================================================

def verify_firebase_token(id_token):
    """
    Verify a Firebase Authentication ID token.

    Returns:
        decoded Firebase user information
        or None if verification fails.
    """

    if not id_token:
        return None

    try:
        return auth.verify_id_token(
            id_token,
            check_revoked=True
        )

    except (FirebaseError, ValueError):
        return None


# ============================================================
# LOAD USER FROM FIREBASE TOKEN
# ============================================================

def load_user_from_token(id_token):
    """
    Verify Firebase token and determine whether the user
    is an admin or student.
    """

    decoded = verify_firebase_token(id_token)

    if not decoded:
        return None

    uid = decoded.get("uid")

    if not uid:
        return None

    db = get_db()

    # --------------------------------------------------------
    # Check admin collection
    # --------------------------------------------------------

    admin_doc = (
        db.collection("admins")
        .document(uid)
        .get()
    )

    if admin_doc.exists:
        data = admin_doc.to_dict() or {}

        return {
            "uid": uid,
            "role": "admin",
            **data
        }

    # --------------------------------------------------------
    # Check student collection
    # --------------------------------------------------------

    student_doc = (
        db.collection("students")
        .document(uid)
        .get()
    )

    if student_doc.exists:
        data = student_doc.to_dict() or {}

        return {
            "uid": uid,
            "role": "student",
            **data
        }

    return None


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(view):
    """
    Require an authenticated application session.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):

        if not session.get("uid"):
            return abort(401)

        return view(*args, **kwargs)

    return wrapped


# ============================================================
# ROLE REQUIRED
# ============================================================

def role_required(*roles):
    """
    Restrict a route to one or more user roles.
    """

    def decorator(view):

        @wraps(view)
        def wrapped(*args, **kwargs):

            if not session.get("uid"):
                return abort(401)

            if session.get("role") not in roles:
                return abort(403)

            return view(*args, **kwargs)

        return wrapped

    return decorator


# ============================================================
# CUSTOM CSRF TOKEN
# ============================================================

def csrf_token_from_session():
    """
    Create or return a CSRF token stored in the Flask session.

    The token is injected into HTML and sent by JavaScript
    using the X-CSRFToken request header.
    """

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

    return session["csrf_token"]


# ============================================================
# CSRF VALIDATION
# ============================================================

def validate_csrf(request):
    """
    Validate the custom session-based CSRF token.

    Accepted locations:

        X-CSRFToken HTTP header
        csrf_token form field
    """

    expected = session.get("csrf_token")

    supplied = (
        request.headers.get("X-CSRFToken")
        or request.headers.get("X-CSRF-Token")
        or request.form.get("csrf_token")
    )

    if not expected:
        abort(
            400,
            description="CSRF session token is missing."
        )

    if not supplied:
        abort(
            400,
            description="CSRF token is missing."
        )

    if not secrets.compare_digest(
        str(supplied),
        str(expected)
    ):
        abort(
            400,
            description="Invalid CSRF token."
        )

    return True