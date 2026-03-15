"""
tests/test_violations.py
─────────────────────────────────────────────────────────────
Tests for Feature 1: Anti-Cheating Browser Detection
Verifies that new violation types are accepted, stored, and
weighted correctly by the backend.
"""
import json
import pytest
from config import Config
from models import db, ExamSession, Violation


# ── Weight configuration tests ────────────────────────────────
class TestViolationWeights:
    def test_clipboard_weight(self):
        assert Config.VIOLATION_WEIGHTS['clipboard_access'] == 15

    def test_window_focus_lost_weight(self):
        assert Config.VIOLATION_WEIGHTS['window_focus_lost'] == 10

    def test_rapid_tab_switch_weight(self):
        assert Config.VIOLATION_WEIGHTS['rapid_tab_switch'] == 15

    def test_multiple_monitor_weight(self):
        assert Config.VIOLATION_WEIGHTS['multiple_monitor_suspected'] == 20

    def test_all_new_types_present(self):
        new_types = {
            'clipboard_access', 'window_focus_lost',
            'rapid_tab_switch', 'multiple_monitor_suspected',
        }
        missing = new_types - set(Config.VIOLATION_WEIGHTS.keys())
        assert not missing, f'Missing weights for: {missing}'

    def test_existing_weights_unchanged(self):
        assert Config.VIOLATION_WEIGHTS['tab_switch'] == 15
        assert Config.VIOLATION_WEIGHTS['no_face'] == 10
        assert Config.VIOLATION_WEIGHTS['phone_detected'] == 35


# ── Endpoint acceptance tests ─────────────────────────────────
class TestBrowserViolationEndpoint:

    def _post(self, auth_client, session_id, payload):
        return auth_client.post(
            f'/browser/violation/{session_id}',
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_clipboard_access_accepted(self, auth_client, session_id):
        r = self._post(auth_client, session_id, {
            'violation_type': 'clipboard_access',
            'timestamp': '2025-01-01T00:00:00Z',
            'details': 'Copy attempt',
        })
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data['status'] == 'ok'

    def test_window_focus_lost_accepted(self, auth_client, session_id):
        r = self._post(auth_client, session_id, {
            'violation_type': 'window_focus_lost',
            'details': 'Window blurred',
        })
        assert r.status_code == 200

    def test_rapid_tab_switch_accepted(self, auth_client, session_id):
        r = self._post(auth_client, session_id, {
            'violation_type': 'rapid_tab_switch',
            'details': '3 switches in 30s',
        })
        assert r.status_code == 200

    def test_multiple_monitor_accepted(self, auth_client, session_id):
        r = self._post(auth_client, session_id, {
            'violation_type': 'multiple_monitor_suspected',
            'details': 'availWidth 3840 > width 1920',
        })
        assert r.status_code == 200

    def test_unknown_type_rejected(self, auth_client, session_id):
        r = self._post(auth_client, session_id, {
            'violation_type': 'unknown_hack_attempt',
            'details': 'should be rejected',
        })
        assert r.status_code == 400

    def test_unauthenticated_rejected(self, client, session_id):
        r = client.post(
            f'/browser/violation/{session_id}',
            data=json.dumps({'violation_type': 'clipboard_access', 'details': ''}),
            content_type='application/json',
        )
        # Flask-Login redirects unauthenticated requests
        assert r.status_code in (302, 401)

    def test_violation_stored_in_db(self, auth_client, session_id, app):
        with app.app_context():
            before = Violation.query.filter_by(
                session_id=session_id,
                violation_type='rapid_tab_switch',
            ).count()

        self._post(auth_client, session_id, {
            'violation_type': 'rapid_tab_switch',
            'details': 'DB storage test',
        })

        with app.app_context():
            after = Violation.query.filter_by(
                session_id=session_id,
                violation_type='rapid_tab_switch',
            ).count()
        assert after == before + 1

    def test_severity_derived_from_weight(self, auth_client, session_id, app):
        """multiple_monitor_suspected weight=20 → severity='high'"""
        self._post(auth_client, session_id, {
            'violation_type': 'multiple_monitor_suspected',
            'details': 'severity test',
        })
        with app.app_context():
            v = Violation.query.filter_by(
                session_id=session_id,
                violation_type='multiple_monitor_suspected',
            ).order_by(Violation.id.desc()).first()
        assert v is not None
        assert v.severity == 'high'

    def test_session_total_violations_incremented(self, auth_client, session_id, app):
        with app.app_context():
            before = ExamSession.query.get(session_id).total_violations or 0

        self._post(auth_client, session_id, {
            'violation_type': 'clipboard_access',
            'details': 'counter test',
        })

        with app.app_context():
            after = ExamSession.query.get(session_id).total_violations
        assert after == before + 1

    def test_details_truncated_at_500_chars(self, auth_client, session_id, app):
        long_detail = 'X' * 600
        self._post(auth_client, session_id, {
            'violation_type': 'window_focus_lost',
            'details': long_detail,
        })
        with app.app_context():
            v = Violation.query.filter_by(
                session_id=session_id,
                violation_type='window_focus_lost',
            ).order_by(Violation.id.desc()).first()
        assert v is not None
        assert len(v.details) <= 500
