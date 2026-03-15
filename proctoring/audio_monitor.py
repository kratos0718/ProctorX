import threading
import time

class AudioMonitor:
    def __init__(self):
        self.running = False
        self.current_level = 0
        self.alert_count = 0
        self.thread = None
        self.pyaudio_available = False
        
        # New Tuning Parameters
        self.baseline = None
        self.calibrating = True
        self.calibration_samples = []
        self.start_time = 0
        self.consecutive_loud_frames = 0
        self.LOUD_DURATION_LIMIT = 25     # ~2.5 seconds continuous loud audio
        self.MULTIPLIER = 3.8             # much higher threshold
        
        self._check_pyaudio()

    def _check_pyaudio(self):
        try:
            import pyaudio
            self.pyaudio_available = True
        except ImportError:
            print("[AudioMonitor] PyAudio not available. Audio monitoring disabled.")

    def start(self):
        if not self.pyaudio_available:
            return
        self.running = True
        self.start_time = time.time()
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _monitor(self):
        try:
            import pyaudio
            import array
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024
            )
            while self.running:
                try:
                    data = stream.read(1024, exception_on_overflow=False)
                    audio_data = array.array('h', data)
                    rms = (sum(x**2 for x in audio_data) / len(audio_data)) ** 0.5
                    
                    # Exponential smoothing
                    self.current_level = (self.current_level * 0.7) + (rms * 0.3)
                    
                    if self.calibrating:
                        self.calibration_samples.append(rms)
                        if time.time() - self.start_time > 4.0: # 4 seconds calibration
                            self.baseline = max(sum(self.calibration_samples) / len(self.calibration_samples), 100)
                            self.calibrating = False
                    else:
                        threshold = self.baseline * self.MULTIPLIER
                        if self.current_level > threshold:
                            self.consecutive_loud_frames += 1
                        else:
                            self.consecutive_loud_frames = max(0, self.consecutive_loud_frames - 2)

                        if self.consecutive_loud_frames > self.LOUD_DURATION_LIMIT:
                            self.alert_count += 1
                except Exception:
                    pass
                time.sleep(0.1)
            stream.stop_stream()
            stream.close()
            p.terminate()
        except Exception as e:
            print(f"[AudioMonitor] Error: {e}")

    def get_status(self):
        alerts = []
        if not self.calibrating and self.consecutive_loud_frames > self.LOUD_DURATION_LIMIT + 5:
            alerts.append(('loud_audio',
                           f'Loud noise detected ({int(self.current_level)} over base {int(self.baseline)})',
                           'medium'))
            
            # Reset slightly so it doesn't spam infinitely
            self.consecutive_loud_frames = self.LOUD_DURATION_LIMIT - 5

        return {
            'level': int(self.current_level),
            'alert_count': self.alert_count,
            'alerts': alerts,
            'calibrating': self.calibrating
        }