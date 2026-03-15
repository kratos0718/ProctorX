import cv2
import numpy as np

class EyeTracker:
    LEFT_EAR_PTS = [362, 385, 387, 263, 373, 380]
    RIGHT_EAR_PTS = [33, 160, 158, 133, 153, 144]
    LEFT_IRIS = [474, 475, 476, 477]
    RIGHT_IRIS = [469, 470, 471, 472]
    LEFT_EYE = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]

    EAR_THRESHOLD = 0.22
    BLINK_CONSEC_FRAMES = 3
    GAZE_THRESHOLD = 0.22

    def __init__(self):
        self.blink_counter = 0
        self.total_blinks = 0
        self.gaze_away_frames = 0
        self.GAZE_AWAY_LIMIT = 2

    def _ear(self, landmarks, eye_pts, w, h):
        pts = []
        for idx in eye_pts:
            lm = landmarks.landmark[idx]
            pts.append((lm.x * w, lm.y * h))
        pts = np.array(pts)
        A = np.linalg.norm(pts[1] - pts[5])
        B = np.linalg.norm(pts[2] - pts[4])
        C = np.linalg.norm(pts[0] - pts[3])
        return (A + B) / (2.0 * C)

    def _iris_position(self, landmarks, iris_pts, eye_pts, w, h):
        iris_cx = np.mean([landmarks.landmark[i].x * w for i in iris_pts])
        eye_left = landmarks.landmark[eye_pts[0]].x * w
        eye_right = landmarks.landmark[eye_pts[8]].x * w
        eye_width = eye_right - eye_left
        if eye_width == 0:
            return 0.5
        return (iris_cx - eye_left) / eye_width

    def analyze(self, frame, landmarks):
        if landmarks is None:
            return {'blinks': self.total_blinks, 'gaze': 'unknown', 'alerts': []}

        h, w = frame.shape[:2]
        alerts = []

        # Blink detection
        left_ear = self._ear(landmarks, self.LEFT_EAR_PTS, w, h)
        right_ear = self._ear(landmarks, self.RIGHT_EAR_PTS, w, h)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < self.EAR_THRESHOLD:
            self.blink_counter += 1
        else:
            if self.blink_counter >= self.BLINK_CONSEC_FRAMES:
                self.total_blinks += 1
            self.blink_counter = 0

        # Gaze tracking
        try:
            left_ratio = self._iris_position(landmarks, self.LEFT_IRIS, self.LEFT_EYE, w, h)
            right_ratio = self._iris_position(landmarks, self.RIGHT_IRIS, self.RIGHT_EYE, w, h)
            avg_ratio = (left_ratio + right_ratio) / 2.0

            if avg_ratio < self.GAZE_THRESHOLD:
                gaze = 'looking_left'
            elif avg_ratio > (1 - self.GAZE_THRESHOLD):
                gaze = 'looking_right'
            else:
                gaze = 'center'

            if gaze != 'center':
                self.gaze_away_frames += 1
                if self.gaze_away_frames >= self.GAZE_AWAY_LIMIT:
                    alerts.append(('looking_away', f'Student {gaze.replace("_", " ")}!', 'medium'))
            else:
                self.gaze_away_frames = max(0, self.gaze_away_frames - 2)

        except Exception:
            gaze = 'unknown'

        return {
            'blinks': self.total_blinks,
            'ear': round(avg_ear, 3),
            'gaze': gaze,
            'alerts': alerts
        }