# AI Attendance System Using Face Recognition

A Flask + OpenCV + face-recognition application with Firebase Firestore persistence. It provides admin authentication, student registration with webcam face encoding, real-time recognition, duplicate-safe attendance marking, dashboards and CSV reporting.

## Important compatibility note
The `face-recognition` package depends on dlib. On Windows, installation can be difficult with very new Python versions. If `pip install -r requirements.txt` cannot install dlib/face-recognition, use Python 3.10 or 3.11 in a fresh virtual environment and reinstall the requirements.

## 1. Firebase setup
1. Create a Firebase project.
2. Enable Firestore Database.
3. Enable Authentication → Sign-in method → Email/Password.
4. Create a Web App and copy its public Firebase web configuration values into `.env`.
5. Create a Firebase service account in Project Settings → Service Accounts.
6. Download the JSON key and save it as `firebase/serviceAccountKey.json`.
7. If using Firebase Storage, enable it and set the bucket in `.env`.
8. Apply `firestore.rules` and `firebase/storage.rules` in the Firebase console.

## 2. Installation
```bash
python -m venv venv
# Windows
venv\\Scripts\\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```
Edit `.env` and set real values. Generate a strong `SECRET_KEY`.

## 3. Create the first admin
Set these temporarily in `.env`:
```text
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=ChangeThisToAStrongPassword123!
ADMIN_NAME=System Administrator
```
Then run:
```bash
python -m firebase.create_admin
```
Remove the three ADMIN_* variables after the admin document is created if desired.

## 4. Run
```bash
python app.py
```
Open http://127.0.0.1:5000

## 5. Workflow
1. Sign in as admin.
2. Register a student and capture exactly one face.
3. Start the AI Attendance Camera.
4. The system detects exactly one face and compares its 128-value encoding with active student encodings in Firestore.
5. A match is accepted only when its face distance is at most `0.50`; confidence is display-only.
6. Only an accepted face match is checked against today's attendance record. Unmatched faces never create or update attendance.
7. A student can be marked Present only once per UTC day.
8. The dashboard and attendance page read live data from Firestore.

## Firestore collections
- `admins/{uid}`
- `students/{uid}`
- `attendance/{student_uid_YYYY-MM-DD}`
- `users/{uid}` (optional)
- `system_logs/{id}` (optional)

Passwords are handled by Firebase Authentication and are never stored in Firestore.

## Security
- Service account credentials remain server-side.
- Firebase Auth ID tokens are verified by Flask.
- Admin/student authorization is checked server-side.
- State-changing requests use the existing session-based CSRF token validation.
- Firestore rules restrict direct client access.
- Student face encodings are treated as sensitive biometric data; deploy only with appropriate consent, retention and access controls.
- This camera flow compares still frames; it is not a liveness or anti-spoofing check and cannot distinguish a live registered face from a photograph of that same face.

## Troubleshooting
### Camera blocked
Use localhost or HTTPS and allow browser camera permission.

### No face detected
Use good lighting, keep one face centered, and move closer to the camera.

### Multiple faces detected during registration
Only one face may be visible while registering a student.

### dlib/face-recognition installation failure
Use Python 3.10/3.11 and a fresh virtual environment. On Windows, ensure the required native build tooling is available if pip cannot find a compatible wheel.

### Firebase credential error
Check that `firebase/serviceAccountKey.json` exists and that `FIREBASE_CREDENTIALS` points to it.
