from datetime import datetime, timedelta

from functools import wraps



from flask import Blueprint, jsonify, render_template, session, current_app, request, redirect, url_for



from firebase.firebase_config import get_db

from ai.face_service import (
    extract_single_face_encoding,
    find_duplicate_face,
)
from utils.security import validate_csrf



admin_bp = Blueprint("admin", __name__)





def _wants_json():

    return request.accept_mimetypes.best == "application/json"





def admin_required(view_function):

    @wraps(view_function)

    def wrapper(*args, **kwargs):

        uid = session.get("uid")

        role = str(session.get("role", "")).strip().lower()

        if not uid:

            if _wants_json():

                return jsonify(success=False, message="Authentication required."), 401

            return redirect(url_for("auth.login_page"))

        if role != "admin":

            if _wants_json():

                return jsonify(success=False, message="Admin access required."), 403

            return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

        return view_function(*args, **kwargs)

    return wrapper





def _safe_iso(value):

    if value is None:

        return None

    if hasattr(value, "isoformat"):

        try:

            return value.isoformat()

        except Exception:

            pass

    return str(value)





def _today_key():

    try:

        from utils.helpers import today_key

        return str(today_key())

    except Exception:

        return datetime.now().date().isoformat()





def _load_students(db, active_only=False):

    students = []

    for doc in db.collection("students").stream():

        data = doc.to_dict() or {}

        status = str(data.get("status", "active")).strip().lower()

        if active_only and status not in ("active", "", "activated"):

            continue

        data["id"] = doc.id

        students.append(data)

    return students





def _load_attendance(db):

    records = []

    for doc in db.collection("attendance").stream():

        data = doc.to_dict() or {}

        data["id"] = doc.id

        if "timestamp" in data:

            data["timestamp"] = _safe_iso(data.get("timestamp"))

        records.append(data)

    return records





def _attendance_date(row):

    value = row.get("date")

    if value is not None and str(value).strip():

        return str(value).strip()[:10]

    value = row.get("timestamp")

    return str(value)[:10] if value else ""





def _student_key(row):

    return row.get("student_id") or row.get("roll_number") or row.get("student_name") or row.get("id")





def _build_dashboard_data(db):

    today = _today_key()

    students = _load_students(db, active_only=True)

    attendance = _load_attendance(db)

    total_students = len(students)



    today_rows = [r for r in attendance if _attendance_date(r) == today]

    present_keys = {str(_student_key(r)) for r in today_rows if str(r.get("status", "")).lower() == "present" and _student_key(r)}

    present_today = len(present_keys)

    absent_today = max(total_students - present_today, 0)

    rate = round((present_today / total_students) * 100, 2) if total_students else 0



    dates = [(datetime.now().date() - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    daily = {d: set() for d in dates}

    for row in attendance:

        d = _attendance_date(row)

        if d in daily and str(row.get("status", "")).lower() == "present" and _student_key(row):

            daily[d].add(str(_student_key(row)))



    weekly_present = [len(daily[d]) for d in dates]

    weekly_absent = [max(total_students - x, 0) for x in weekly_present]

    analysis = [{"date": d, "present": weekly_present[i], "absent": weekly_absent[i], "total": total_students} for i, d in enumerate(dates)]



    recent = sorted(attendance, key=lambda r: (_attendance_date(r), str(r.get("time", "")), str(r.get("timestamp", ""))), reverse=True)[:10]



    classes = []

    try:

        for doc in db.collection("classes").stream():

            data = doc.to_dict() or {}

            data["id"] = doc.id

            classes.append(data)

    except Exception as exc:

        current_app.logger.warning("Unable to load classes: %s", exc)



    today_name = datetime.now().strftime("%A")

    today_classes = [c for c in classes if not str(c.get("day", "")).strip() or str(c.get("day", "")).strip().lower() == today_name.lower()]

    today_classes.sort(key=lambda x: str(x.get("start_time") or x.get("time") or ""))



    return {

        "success": True,

        "total_students": total_students,

        "present_today": present_today,

        "absent_today": absent_today,

        "attendance_rate": rate,

        "total_attendance_records": len(attendance),

        "weekly": {"present": weekly_present, "absent": weekly_absent, "dates": dates},

        "stats": {"total_students": total_students, "today_present": present_today, "today_absent": absent_today, "attendance_percentage": rate, "total_records": len(attendance)},

        "attendance_analysis": analysis,

        "today_attendance": {"present": present_today, "absent": absent_today, "total": total_students, "percentage": rate},

        "recent_attendance": recent,

        "today_classes": today_classes,

    }





# ---------------- Dashboard ----------------

@admin_bp.get("/admin/dashboard")

@admin_required

def admin_dashboard():

    return render_template("admin/dashboard.html")





@admin_bp.get("/api/admin/dashboard")

@admin_required

def dashboard_data():

    try:

        db = get_db()

        if db is None:

            return jsonify(success=False, message="Database connection is unavailable."), 503

        return jsonify(_build_dashboard_data(db))

    except Exception:

        current_app.logger.exception("Dashboard data error")

        return jsonify(success=False, message="Unable to load dashboard data."), 500





@admin_bp.get("/api/dashboard-data")

@admin_required

def dashboard_data_legacy():

    return dashboard_data()





# ---------------- Students ----------------

@admin_bp.get("/admin/students")

@admin_required

def students_page():

    try:

        students = _load_students(get_db())

    except Exception:

        current_app.logger.exception("Student list error")

        students = []

    return render_template("admin/students.html", students=students)





@admin_bp.route("/admin/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "GET":
        return render_template("admin/add_student.html", form={}, error=None)

    validate_csrf(request)

    try:
        db = get_db()
        if db is None:
            return render_template("admin/add_student.html", form=request.form, error="Firebase database is unavailable."), 503

        form = request.form
        name = form.get("name", "").strip()
        roll = form.get("roll_number", "").strip()
        email = form.get("email", "").strip().lower()
        phone = form.get("phone", "").strip()
        department = form.get("department", "").strip()
        semester = form.get("semester", "").strip()
        section = form.get("section", "").strip()
        face_image = form.get("face_image", "").strip()

        form_data = {
            "name": name, "roll_number": roll, "email": email,
            "phone": phone, "department": department,
            "semester": semester, "section": section,
        }

        if not name or not roll or not email:
            return render_template("admin/add_student.html", error="Name, roll number and email are required.", form=form_data), 400

        if not face_image:
            return render_template("admin/add_student.html", error="Please capture the student's face before registering.", form=form_data), 400

        existing = list(db.collection("students").where("roll_number", "==", roll).limit(1).stream())
        if existing:
            return render_template("admin/add_student.html", error="Roll number already exists.", form=form_data), 409

        try:
            face_encoding = extract_single_face_encoding(face_image)
        except ValueError as error:
            return render_template("admin/add_student.html", error=str(error), form=form_data), 400

        if not isinstance(face_encoding, list) or len(face_encoding) != 128:
            return render_template("admin/add_student.html", error="Invalid face encoding. Please capture the face again.", form=form_data), 400

        duplicate_face = find_duplicate_face(db, face_encoding, tolerance=0.50)
        if duplicate_face:
            return render_template(
                "admin/add_student.html",
                error="This face is already registered to another student.",
                form=form_data,
            ), 409

        doc_ref = db.collection("students").document()
        doc_ref.set({
            "student_id": doc_ref.id,
            "name": name, "roll_number": roll, "email": email, "phone": phone,
            "department": department, "semester": semester, "section": section,
            "status": "active",
            "face_encoding": face_encoding,
            "face_registered": True,
            "photo_url": "",
            "created_at": datetime.utcnow(),
        })

        current_app.logger.info("Student %s registered with face encoding.", doc_ref.id)
        return redirect(url_for("admin.students_page"))

    except Exception:
        current_app.logger.exception("Student creation error")
        return render_template("admin/add_student.html", error="Unable to create student. Check the Flask terminal.", form=request.form), 500


@admin_bp.post("/admin/students/delete/<student_id>")

@admin_required

def delete_student(student_id):

    try:

        get_db().collection("students").document(student_id).delete()

        return redirect(url_for("admin.students_page"))

    except Exception:

        current_app.logger.exception("Student deletion error")

        return "Unable to delete student", 500





# ---------------- Attendance ----------------

@admin_bp.get("/admin/attendance")

@admin_required

def attendance_page():

    try:

        records = _load_attendance(get_db())

        query = request.args.get("q", "").strip().lower()

        date_filter = request.args.get("date", "").strip()

        status_filter = request.args.get("status", "").strip().lower()

        if query:

            records = [r for r in records if query in str(r.get("student_name", "")).lower() or query in str(r.get("roll_number", "")).lower()]

        if date_filter:

            records = [r for r in records if _attendance_date(r) == date_filter]

        if status_filter:

            records = [r for r in records if str(r.get("status", "")).lower() == status_filter]

        records.sort(key=lambda r: (_attendance_date(r), str(r.get("time", ""))), reverse=True)

    except Exception:

        current_app.logger.exception("Attendance page error")

        records = []

    return render_template("admin/attendance.html", records=records, today=_today_key())





@admin_bp.post("/admin/attendance/delete/<record_id>")

@admin_required

def delete_attendance(record_id):

    try:

        get_db().collection("attendance").document(record_id).delete()

        return redirect(url_for("admin.attendance_page"))

    except Exception:

        current_app.logger.exception("Attendance deletion error")

        return "Unable to delete attendance record", 500





# ---------------- Classes ----------------

@admin_bp.get("/admin/classes")

@admin_required

def classes_page():

    classes = []

    try:

        for doc in get_db().collection("classes").stream():

            data = doc.to_dict() or {}

            data["id"] = doc.id

            classes.append(data)

    except Exception:

        current_app.logger.exception("Classes page error")

    return render_template("admin/classes.html", classes=classes)





# ---------------- AI / Camera ----------------

def _render_existing_or_fallback(template_name, title, message):

    try:

        return render_template(template_name)

    except Exception:

        return render_template("admin/feature.html", title=title, message=message)





@admin_bp.get("/admin/face-recognition")

@admin_required

def face_recognition_page():

    return _render_existing_or_fallback("admin/face_recognition.html", "Face Recognition", "Use the camera to register and recognize student faces.")





@admin_bp.get("/admin/live-attendance")

@admin_required

def live_attendance_page():

    return _render_existing_or_fallback("admin/live_attendance.html", "Live Attendance", "Start the live camera attendance workflow.")





@admin_bp.get("/admin/security")

@admin_required

def security_page():

    return render_template("admin/security.html", admin_email=session.get("email", ""))





# ---------------- Reports ----------------

@admin_bp.get("/admin/reports")

@admin_required

def reports_page():
    try:
        records = _load_attendance(get_db())
        students = _load_students(get_db(), active_only=True)
        present = sum(1 for r in records if str(r.get("status", "")).lower() == "present")
        return render_template(
            "admin/reports.html",
            records=records,
            students=students,
            present=present,
            report_date=_today_key(),
        )
    except Exception:
        current_app.logger.exception("Reports page error")
        return render_template(
            "admin/reports.html",
            records=[],
            students=[],
            present=0,
            report_date=_today_key(),
        )





@admin_bp.get("/admin/reports/export")

@admin_required

def export_report():
    import csv
    from io import StringIO
    from flask import Response

    records = _load_attendance(get_db())

    output = StringIO()

    writer = csv.writer(output)

    writer.writerow(["Student", "Roll Number", "Date", "Time", "Status", "Confidence"])

    for r in records:
        writer.writerow([r.get("student_name", ""), r.get("roll_number", ""), _attendance_date(r), r.get("time", ""), r.get("status", ""), r.get("confidence", "")])

    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})


@admin_bp.get("/admin/reports/daily-export")
@admin_required
def export_daily_report():
    import csv
    from io import StringIO
    from flask import Response

    report_date = request.args.get("date", "").strip()
    try:
        parsed_date = datetime.strptime(report_date, "%Y-%m-%d")
    except ValueError:
        return jsonify(
            success=False,
            message="Select a valid report date in YYYY-MM-DD format.",
        ), 400
    if parsed_date.strftime("%Y-%m-%d") != report_date:
        return jsonify(
            success=False,
            message="Select a valid report date in YYYY-MM-DD format.",
        ), 400

    records = [
        record
        for record in _load_attendance(get_db())
        if _attendance_date(record) == report_date
    ]
    records.sort(key=lambda record: str(record.get("time", "")))

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Student ID",
        "Student",
        "Roll Number",
        "Date",
        "Time",
        "Status",
        "Confidence",
        "Face Distance",
        "Camera ID",
        "Created At",
    ])
    for record in records:
        writer.writerow([
            record.get("student_id", ""),
            record.get("name") or record.get("student_name", ""),
            record.get("roll_number", ""),
            _attendance_date(record),
            record.get("time", ""),
            record.get("status", ""),
            record.get("confidence", ""),
            record.get("face_distance", ""),
            record.get("camera_id", ""),
            _safe_iso(record.get("created_at")) or "",
        ])

    filename = f"attendance_report_{report_date}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )




# ---------------- Settings ----------------

@admin_bp.route("/admin/settings", methods=["GET", "POST"])

@admin_required

def settings_page():

    if request.method == "POST":

        session["dashboard_refresh"] = request.form.get("refresh_interval", "30000")

        return redirect(url_for("admin.settings_page"))

    return render_template("admin/settings.html", refresh_interval=session.get("dashboard_refresh", "30000"), admin_email=session.get("email", ""))
