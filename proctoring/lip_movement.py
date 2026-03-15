import numpy as np

class LipMovementDetector:
    UPPER_LIP = [13, 312, 311, 310, 415, 308]
    LOWER_LIP = [14, 317, 402, 318, 324, 78]
    LIP_LEFT = 61
    LIP_RIGHT = 291
    MAR_THRESHOLD = 0.05
    TALKING_FRAMES = 10

    def __init__(self):
        self.talking_frames = 0
        self.total_talking_events = 0

    def _mar(self, landmarks, w, h):
        upper_y = np.mean([landmarks.landmark[i].y * h for i in self.UPPER_LIP])
        lower_y = np.mean([landmarks.landmark[i].y * h for i in self.LOWER_LIP])
        left_x = landmarks.landmark[self.LIP_LEFT].x * w
        right_x = landmarks.landmark[self.LIP_RIGHT].x * w
        mouth_height = abs(lower_y - upper_y)
        mouth_width = abs(right_x - left_x)
        return mouth_height / (mouth_width + 1e-6)

    def analyze(self, frame, landmarks):
        if landmarks is None:
            return {'talking': False, 'mar': 0, 'events': self.total_talking_events, 'alerts': []}
        h, w = frame.shape[:2]
        alerts = []
        try:
            mar = self._mar(landmarks, w, h)
            if mar > self.MAR_THRESHOLD:
                self.talking_frames += 1
                if self.talking_frames == self.TALKING_FRAMES:
                    self.total_talking_events += 1
                    alerts.append(('talking', 'Lip movement detected!', 'medium'))
            else:
                self.talking_frames = max(0, self.talking_frames - 1)
            return {'talking': self.talking_frames >= self.TALKING_FRAMES, 'mar': round(mar, 4), 'events': self.total_talking_events, 'alerts': alerts}
        except Exception:
            return {'talking': False, 'mar': 0, 'events': self.total_talking_events, 'alerts': []}
