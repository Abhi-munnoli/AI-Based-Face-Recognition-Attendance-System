SMARTATTEND FACE REGISTRATION AND ATTENDANCE

The Add Student page captures one webcam image. Flask accepts it only when
exactly one face is detected and stores the finite 128-number face encoding
in that student's existing Firestore document under face_encoding.

Attendance compares the current frame's encoding with registered active
student encodings. The strict face-distance threshold is 0.50 and cannot be
increased above that value. Attendance is created only after an accepted
face match, and the same student is marked no more than once per UTC day.
Unknown and unmatched faces do not create or update attendance records.

IMPORTANT:
1. Restart Flask after updating the application files.
2. Re-register any student whose Firestore face_encoding is empty or invalid.
3. Confirm students/<student_id>/face_encoding contains exactly 128 numeric
   values.
4. Test the registered student's face in /camera.
5. Test an unregistered face; it must remain unknown and must not mark
   attendance.

This implementation matches still camera frames. It is not a liveness or
anti-spoofing check, so a photograph of the same registered person's face
cannot be reliably distinguished from that person being present.
