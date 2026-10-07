from utils.helpers import attendance_doc_id

def test_attendance_doc_id():
    assert attendance_doc_id('abc','2026-10-04') == 'abc_2026-10-04'
