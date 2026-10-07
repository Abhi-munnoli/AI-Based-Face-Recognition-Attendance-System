from datetime import datetime, timezone
import io
import csv


def utc_now():
    return datetime.now(timezone.utc)


def today_key():
    return utc_now().strftime('%Y-%m-%d')


def time_key():
    return utc_now().strftime('%H:%M:%S')


def attendance_doc_id(student_id, date_key):
    return f'{student_id}_{date_key}'


def csv_bytes(rows, fieldnames):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')
