import re
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def clean_text(value, max_length=120):
    value = (value or '').strip()
    return value[:max_length]


def valid_email(value):
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', (value or '').strip()))


def valid_phone(value):
    return bool(re.fullmatch(r'[0-9+()\-\s]{7,20}', (value or '').strip()))


def allowed_image(filename):
    name = secure_filename(filename or '')
    return '.' in name and name.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS
