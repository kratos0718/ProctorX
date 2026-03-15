import cv2
import numpy as np

class HeadPoseEstimator:
    MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),
        (0.0, -330.0, -65.0),
        (-225.0, 170.0, -135.0),
        (225.0, 170.0, -135.0),
        (-150.0, -150.0, -125.0),
        (150.0, -150.0, -125.0),
    ], dtype=np.float64)

    LANDMARK_INDICES = [1, 152, 226, 446, 57, 287]
    PITCH_THRESHOLD = 20
    YAW_THRESHOLD = 25

    def __init__(self):
        self.away_frames = 0
        self.AWAY_LIMIT = 15

    def estimate(self, frame, landmarks):
        if landmarks is None:
            return {'pitch': 0, 'yaw': 0, 'roll': 0, 'direction': 'forward', 'alerts': []}

        h, w = frame.shape[:2]
        alerts = []

        image_points = []
        for idx in self.LANDMARK_INDICES:
            lm = landmarks.landmark[idx]
            image_points.append((lm.x * w, lm.y * h))
        image_points = np.array(image_points, dtype=np.float64)

        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))

        try:
            success, rotation_vec, translation_vec = cv2.solvePnP(
                self.MODEL_POINTS, image_points,
                camera_matrix, dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            rmat, _ = cv2.Rodrigues(rotation_vec)
            angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)

            pitch = angles[0]
            yaw = angles[1]
            roll = angles[2]

            if abs(yaw) > self.YAW_THRESHOLD:
                direction = 'left' if yaw < 0 else 'right'
            elif pitch < -self.PITCH_THRESHOLD:
                direction = 'down'
            elif pitch > self.PITCH_THRESHOLD:
                direction = 'up'
            else:
                direction = 'forward'

            if direction != 'forward':
                self.away_frames += 1
                if self.away_frames >= self.AWAY_LIMIT:
                    alerts.append(('head_turned',
                                   f'Head turned {direction}!',
                                   'medium'))
            else:
                self.away_frames = max(0, self.away_frames - 1)

            return {
                'pitch': round(pitch, 1),
                'yaw': round(yaw, 1),
                'roll': round(roll, 1),
                'direction': direction,
                'alerts': alerts
            }

        except Exception:
            return {'pitch': 0, 'yaw': 0, 'roll': 0, 'direction': 'unknown', 'alerts': []}