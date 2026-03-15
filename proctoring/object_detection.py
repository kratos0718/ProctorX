import cv2
import numpy as np

# YOLO class IDs to category names (COCO dataset)
# Class 67 = cell phone, Class 0 = person, Class 73 = book
PHONE_CLASSES = {'cell phone'}


SUSPICIOUS_OBJECTS = {
    'cell phone': ('phone_detected', '📱 Phone detected!', 'high'),
    'book': ('book_detected', '📖 Book detected!', 'high')
}

class ObjectDetector:
    def __init__(self):
        self.model = None
        self.initialized = False
        self.multi_person_frames = 0
        # Smoothed bounding box memory {class_name: [x1,y1,x2,y2]}
        self.smooth_boxes = {}
        self.SMOOTH_ALPHA = 0.5 # 0.0 = no movement, 1.0 = no smoothing
        self._init_model()

    def _init_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO('yolov8s.pt')
            self.initialized = True
            print('[ObjectDetector] YOLOv8 loaded OK')
        except Exception as e:
            print(f'[ObjectDetector] Not available: {e}')
            self.initialized = False

    def _preprocess_for_dark_objects(self, frame):
        """Apply CLAHE to improve detection of dark/backlit objects."""
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)
        enhanced = cv2.merge([l_channel, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    def _smooth_box(self, key, box):
        """Apply exponential moving average to reduce bounding box flicker."""
        if key not in self.smooth_boxes:
            self.smooth_boxes[key] = list(box)
            return box
        s = self.smooth_boxes[key]
        alpha = self.SMOOTH_ALPHA
        smoothed = [int(alpha * n + (1 - alpha) * o) for n, o in zip(box, s)]
        self.smooth_boxes[key] = smoothed
        return tuple(smoothed)

    def detect(self, frame):
        alerts = []
        detections = []
        if not self.initialized:
            return frame, detections, alerts

        try:
            # Use enhanced frame for detection to catch dark/backside phones
            enhanced = self._preprocess_for_dark_objects(frame)
            results = self.model(enhanced, conf=0.20, iou=0.40, verbose=False)
            # Lower confidence to 0.30 to catch phone backsides and phone-in-hand
            
            person_count = 0
            detected_classes = set()

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = self.model.names[cls_id].lower()
                    conf = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    # Apply bounding box smoothing per class
                    x1, y1, x2, y2 = self._smooth_box(cls_name, (x1, y1, x2, y2))

                    detections.append({'class': cls_name, 'confidence': round(conf, 2), 'bbox': (x1, y1, x2, y2)})

                    if cls_name == 'person':
                        person_count += 1
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f'person {conf:.2f}', (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

                    elif cls_name in SUSPICIOUS_OBJECTS:
                        if cls_name not in detected_classes:  # De-duplicate per frame
                            alerts.append(SUSPICIOUS_OBJECTS[cls_name])
                            detected_classes.add(cls_name)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 50, 255), 2)
                        label = f'⚠ {cls_name} {conf:.2f}'
                        cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 50, 255), 1)

            if person_count > 1:
                self.multi_person_frames += 1
                if self.multi_person_frames >= 5:
                    alerts.append(('person_detected', f'👤 {person_count} persons in frame!', 'high'))
            else:
                self.multi_person_frames = 0

        except Exception as e:
            print(f'[ObjectDetector] Error: {e}')

        return frame, detections, alerts

