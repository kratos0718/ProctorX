import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'exam-proctor-secret-2024-dev')
    _db_url = os.environ.get('DATABASE_URL', 'sqlite:///exam.db')
    # Render/Railway give postgres:// but SQLAlchemy needs postgresql://
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/screenshots'

    RISK_LOW = 30
    RISK_MEDIUM = 60
    RISK_HIGH = 80

    VIOLATION_WEIGHTS = {
        'no_face': 10,
        'multiple_faces': 20,
        'looking_away': 5,
        'head_turned': 5,
        'phone_detected': 35,
        'book_detected': 25,
        'person_detected': 40,
        'talking': 10,
        'loud_audio': 10,
        'tab_switch': 15,
        'clipboard_access': 15,
        'window_focus_lost': 10,
        'rapid_tab_switch': 15,
        'multiple_monitor_suspected': 20,
        'fullscreen_exit': 20,
    }
