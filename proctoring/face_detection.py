import cv2
import numpy as np

class FaceDetector:
    def __init__(self):
        self.initialized = False
        self.use_cascade = False
        try:
            import mediapipe as mp
            self.mp = mp
            self.face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.6
            )
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=3,
                refine_landmarks=True,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6
            )
            self.mp_draw = mp.solutions.drawing_utils
            self.initialized = True
            print('[FaceDetector] MediaPipe loaded OK')
        except Exception as e:
            print(f'[FaceDetector] MediaPipe not available: {e}. Falling back to Haar Cascade.')
            self.cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            self.use_cascade = True
            
        self.missing_face_frames = 0
        self.multiple_face_frames = 0

    def detect(self, frame):
        alerts = []
        face_count = 0
        landmarks = None
        # Resize frame for faster processing without modifying original display aspect deeply
        proc_frame = cv2.resize(frame, (640, 480))
        annotated = proc_frame.copy()

        if self.use_cascade:
            gray = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2GRAY)
            faces = self.cascade.detectMultiScale(gray, 1.3, 5)
            face_count = len(faces)
            for (x, y, w, h) in faces:
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            if face_count == 0:
                self.missing_face_frames += 1
                if self.missing_face_frames >= 2:
                    alerts.append(('no_face', 'No face detected!', 'high'))
            else:
                self.missing_face_frames = 0
                
            if face_count > 1:
                alerts.append(('multiple_faces', str(face_count) + ' faces detected!', 'high'))
                
            return face_count, landmarks, annotated, alerts

        if not self.initialized:
            alerts.append(('no_face', 'Face detection unavailable', 'high'))
            return face_count, landmarks, annotated, alerts

        try:
            rgb = cv2.cvtColor(proc_frame, cv2.COLOR_BGR2RGB)
            det_result = self.face_detection.process(rgb)
            if det_result.detections:
                # Count faces only if confidence > 0.6
                face_count = sum(1 for det in det_result.detections if det.score[0] > 0.6)
                for det in det_result.detections:
                    if det.score[0] > 0.6:
                        self.mp_draw.draw_detection(annotated, det)

            mesh_result = self.face_mesh.process(rgb)
            if mesh_result.multi_face_landmarks:
                landmarks = mesh_result.multi_face_landmarks[0]

            if face_count == 0:
                self.missing_face_frames += 1
                self.multiple_face_frames = 0
                if self.missing_face_frames >= 2:
                    alerts.append(('no_face', 'No face detected!', 'high'))
            else:
                self.missing_face_frames = 0
                
            if face_count > 1:
                if not hasattr(self, 'multiple_face_frames'): self.multiple_face_frames = 0
                self.multiple_face_frames += 1
                if self.multiple_face_frames >= 5:
                    alerts.append(('multiple_faces', str(face_count) + ' faces detected!', 'high'))
            else:
                self.multiple_face_frames = 0

        except Exception as e:
            import traceback
            print(f'[FaceDetector] Error in detect(): {e}')
            traceback.print_exc()

        return face_count, landmarks, annotated, alerts
