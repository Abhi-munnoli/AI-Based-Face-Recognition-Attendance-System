import base64
import io
import numpy as np
from PIL import Image
import face_recognition


def image_bytes_from_data_url(data_url):
    if not data_url:
        raise ValueError('Image data is required')
    if ',' in data_url:
        data_url = data_url.split(',', 1)[1]
    return base64.b64decode(data_url)


def load_rgb_image(image_bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    return np.array(image)


def encode_single_face(image_bytes):
    image = load_rgb_image(image_bytes)
    locations = face_recognition.face_locations(image, model='hog')
    if len(locations) == 0:
        raise ValueError('No face detected')
    if len(locations) > 1:
        raise ValueError('Multiple faces detected. Keep exactly one face in the camera.')
    encodings = face_recognition.face_encodings(image, locations, num_jitters=1)
    if not encodings:
        raise ValueError('Could not generate a face encoding')
    return encodings[0].tolist(), locations[0]
