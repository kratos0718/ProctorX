"""Shared pytest fixtures for exam_proctor tests."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from werkzeug.security import generate_password_hash

# Patch heavy AI imports so tests don't need GPU/camera hardware
import unittest.mock as mock
for mod in [
    'cv2', 'numpy', 'mediapipe',
    'proctoring.face_detection', 'proctoring.eye_tracker',
    'proctoring.head_pose', 'proctoring.lip_movement',
    'proctoring.object_detection', 'proctoring.audio_monitor',
    'proctoring.risk_scorer', 'proctoring.report_generator',
]:
    sys.modules.setdefault(mod, mock.MagicMock())

from app import app as flask_app
from models import db, User, ExamSession, Violation


@pytest.fixture(scope='session')
def app():
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': False,
    })
    with flask_app.app_context():
        db.create_all()
        _seed(flask_app)
    yield flask_app


def _seed(app):
    if not User.query.filter_by(username='teststu').first():
        u = User(username='teststu', email='stu@test.com',
                 password=generate_password_hash('pass'), role='student')
        db.session.add(u)
        db.session.commit()

    u = User.query.filter_by(username='teststu').first()
    s = ExamSession(user_id=u.id, exam_name='Test Exam',
                    status='completed', final_risk_score=40.0,
                    total_violations=2)
    db.session.add(s)
    db.session.commit()

    for vtype in ['clipboard_access', 'clipboard_access', 'window_focus_lost']:
        v = Violation(session_id=s.id, violation_type=vtype,
                      severity='medium', details='test')
        db.session.add(v)
    db.session.commit()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """Returns a client already logged in as teststu."""
    with app.app_context():
        u = User.query.filter_by(username='teststu').first()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(u.id)
            sess['_fresh'] = True
    return client


@pytest.fixture
def session_id(app):
    with app.app_context():
        u = User.query.filter_by(username='teststu').first()
        s = ExamSession.query.filter_by(user_id=u.id).first()
        return s.id
