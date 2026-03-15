"""
tests/test_analytics.py
─────────────────────────────────────────────────────────────
Tests for Feature 2: Student Behaviour Analytics
Verifies the /student/analytics_data endpoint returns correct
JSON with integrity_score, violation_counts, etc.
"""
import json
import pytest
from models import db, User, ExamSession, Violation


class TestAnalyticsEndpoint:

    def test_returns_json(self, auth_client):
        r = auth_client.get('/student/analytics_data')
        assert r.status_code == 200
        assert r.content_type.startswith('application/json')

    def test_response_has_required_keys(self, auth_client):
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        required = {
            'integrity_score', 'most_common_violation',
            'violation_counts', 'risk_history',
            'total_exams', 'total_violations',
        }
        assert required.issubset(d.keys())

    def test_integrity_score_is_integer_in_range(self, auth_client):
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        score = d['integrity_score']
        assert isinstance(score, int)
        assert 0 <= score <= 100

    def test_integrity_score_formula(self, auth_client, app):
        """integrity = 100 - avg_risk_score (rounded, clamped 0-100)."""
        with app.app_context():
            u = User.query.filter_by(username='teststu').first()
            sessions = ExamSession.query.filter_by(user_id=u.id).all()
            avg = sum(s.final_risk_score or 0 for s in sessions) / len(sessions)
            expected = max(0, min(100, round(100 - avg)))

        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        assert d['integrity_score'] == expected

    def test_most_common_violation_correct(self, auth_client):
        # conftest seeds 2x clipboard_access, 1x window_focus_lost
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        assert d['most_common_violation'] == 'clipboard_access'

    def test_violation_counts_structure(self, auth_client):
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        vc = d['violation_counts']
        assert isinstance(vc, dict)
        # At minimum clipboard_access should appear (seeded twice)
        assert vc.get('clipboard_access', 0) >= 2

    def test_risk_history_is_list(self, auth_client):
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        assert isinstance(d['risk_history'], list)

    def test_risk_history_entries_have_required_fields(self, auth_client):
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        for entry in d['risk_history']:
            assert 'exam' in entry
            assert 'risk' in entry
            assert 'date' in entry

    def test_total_exams_matches_db(self, auth_client, app):
        with app.app_context():
            u = User.query.filter_by(username='teststu').first()
            count = ExamSession.query.filter_by(user_id=u.id).count()
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        assert d['total_exams'] == count

    def test_total_violations_matches_db(self, auth_client, app):
        with app.app_context():
            u = User.query.filter_by(username='teststu').first()
            sids = [s.id for s in ExamSession.query.filter_by(user_id=u.id).all()]
            count = Violation.query.filter(Violation.session_id.in_(sids)).count()
        r = auth_client.get('/student/analytics_data')
        d = json.loads(r.data)
        assert d['total_violations'] == count

    def test_unauthenticated_redirected(self, client):
        r = client.get('/student/analytics_data')
        assert r.status_code in (302, 401)

    def test_empty_sessions_returns_defaults(self, app, client):
        """A student with no sessions gets safe defaults."""
        from werkzeug.security import generate_password_hash
        with app.app_context():
            if not User.query.filter_by(username='newstu').first():
                u = User(username='newstu', email='new@test.com',
                         password=generate_password_hash('pass'), role='student')
                db.session.add(u)
                db.session.commit()
            u = User.query.filter_by(username='newstu').first()
            with client.session_transaction() as sess:
                sess['_user_id'] = str(u.id)
                sess['_fresh'] = True

        r = client.get('/student/analytics_data')
        d = json.loads(r.data)
        assert d['integrity_score'] == 100
        assert d['most_common_violation'] is None
        assert d['violation_counts'] == {}
        assert d['total_exams'] == 0
        assert d['total_violations'] == 0
