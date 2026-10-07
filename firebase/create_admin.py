"""Create the first Firebase Auth admin and matching Firestore document.
Run after placing serviceAccountKey.json and setting ADMIN_EMAIL/ADMIN_PASSWORD/ADMIN_NAME in .env.
"""
import os
from firebase_admin import auth
from firebase.firebase_config import get_db, initialize_firebase

initialize_firebase()
email=os.environ['ADMIN_EMAIL'].strip().lower()
password=os.environ['ADMIN_PASSWORD']
name=os.environ.get('ADMIN_NAME','System Administrator').strip()
try:
    user=auth.get_user_by_email(email)
except auth.UserNotFoundError:
    user=auth.create_user(email=email,password=password,display_name=name)

db=get_db()
db.collection('admins').document(user.uid).set({'uid':user.uid,'name':name,'email':email,'role':'admin','status':'active'})
print('Admin ready:', email)
