from flask import Flask, render_template, jsonify, request
from config import Config
from firebase.firebase_config import initialize_firebase
from utils.security import csrf_token_from_session

from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.student_routes import student_bp
from routes.attendance_routes import attendance_bp
from routes.camera_routes import camera_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ---------------------------------------------------------
    # CSRF
    # ---------------------------------------------------------
    # This project uses a custom session-based CSRF system.
    # Do NOT initialize Flask-WTF CSRFProtect here because it
    # would conflict with the custom X-CSRFToken validation.
    # ---------------------------------------------------------

    app.jinja_env.globals["csrf_token"] = csrf_token_from_session

    # ---------------------------------------------------------
    # Blueprints
    # ---------------------------------------------------------
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(camera_bp)

    # ---------------------------------------------------------
    # Home
    # ---------------------------------------------------------
    @app.get("/")
    def index():
        return render_template("index.html")

    # ---------------------------------------------------------
    # Error handlers
    # ---------------------------------------------------------
    # IMPORTANT:
    # accept_mimetypes belongs to Flask's request object,
    # not the Flask application object.
    # ---------------------------------------------------------

    @app.errorhandler(400)
    def bad_request(error):
        message = getattr(error, "description", "Bad request")

        if request.accept_mimetypes.best == "application/json":
            return jsonify(
                success=False,
                message=message
            ), 400

        return render_template(
            "error.html",
            code=400,
            message=message
        ), 400

    @app.errorhandler(401)
    def unauthorized(error):
        if request.accept_mimetypes.best == "application/json":
            return jsonify(
                success=False,
                message="Authentication required."
            ), 401

        return render_template(
            "error.html",
            code=401,
            message="Authentication required."
        ), 401

    @app.errorhandler(403)
    def forbidden(error):
        if request.accept_mimetypes.best == "application/json":
            return jsonify(
                success=False,
                message="You do not have permission to access this page."
            ), 403

        return render_template(
            "error.html",
            code=403,
            message="You do not have permission to access this page."
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        if request.accept_mimetypes.best == "application/json":
            return jsonify(
                success=False,
                message="Page not found."
            ), 404

        return render_template(
            "error.html",
            code=404,
            message="Page not found."
        ), 404

    @app.errorhandler(413)
    def request_too_large(error):
        if request.accept_mimetypes.best == "application/json":
            return jsonify(
                success=False,
                message="Uploaded file is too large."
            ), 413

        return render_template(
            "error.html",
            code=413,
            message="Uploaded file is too large."
        ), 413

    return app


app = create_app()


if __name__ == "__main__":
    # Initialize Firebase before starting Flask.
    initialize_firebase()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
