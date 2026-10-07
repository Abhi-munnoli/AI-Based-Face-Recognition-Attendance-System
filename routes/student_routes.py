from flask import Blueprint, render_template, jsonify
from firebase.firebase_config import get_db
from utils.security import role_required
from utils.helpers import today_key

student_bp=Blueprint('student', __name__, url_prefix='/student')

@student_bp.get('/dashboard')
@role_required('student')
def dashboard():
    return render_template('student/dashboard.html')

@student_bp.get('/profile')
@role_required('student')
def profile():
    return render_template('student/profile.html')

@student_bp.get('/attendance')
@role_required('student')
def attendance_page():
    return render_template('student/attendance.html')

@student_bp.get('/api/data')
@role_required('student')
def data():
    db=get_db(); uid=__import__('flask').session['uid']
    student=db.collection('students').document(uid).get().to_dict() or {}
    rows=[d.to_dict() or {} for d in db.collection('attendance').where('student_id','==',uid).stream()]
    present=len([r for r in rows if r.get('status')=='Present'])
    return jsonify(success=True,student={k:v for k,v in student.items() if k!='face_encoding'},attendance=rows,stats={'total':len(rows),'present':present,'absent':0,'percentage':round(present/len(rows)*100,2) if rows else 0})
