# camera.py
import cv2
import platform
import mediapipe as mp
import threading
import time
import os

class CameraPresenceTracker:
    def __init__(self, check_interval=2.0, absence_timeout=10.0, pause_callback=None, resume_callback=None, status_callback=None):
        self.check_interval = check_interval
        self.absence_timeout = absence_timeout
        self.pause_callback = pause_callback
        self.resume_callback = resume_callback
        self.status_callback = status_callback
        
        self.is_running = False
        self.user_present = True
        self.last_seen_time = time.time()
        self._thread = None
        self._stop_event = threading.Event()  # signals the loop to exit immediately

        
        self.model_path = os.path.join(os.path.dirname(__file__), "models", "face_detector.task")

        if not os.path.exists(self.model_path):
            print(f"[Warning] Could not find model at: {self.model_path}")

    def _update_status(self, text):
        """Safely relays status strings back to the UI Options panel badge."""
        if self.status_callback:
            self.status_callback(text)

    def start(self):
        if not self.is_running:
            if not os.path.exists(self.model_path):
                print(f"[Camera] Error: Missing model asset at {self.model_path}")
                self._update_status("Error: Missing face_detector.task")
                return

            self.is_running = True
            self._stop_event.clear()
            self.last_seen_time = time.time()
            self._update_status("Initializing camera...")
          
            self._thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.is_running = False
        self._stop_event.set()  
        if self._thread and self._thread.is_alive():
          
            self._thread.join(timeout=self.check_interval + 3.0)
            if self._thread.is_alive():
                print("[Camera] Warning: thread did not exit cleanly within timeout")
        self._thread = None
        self._stop_event.clear()
        self._update_status("Camera Off")

    def _tracking_loop(self):
        # MediaPipe Tasks API
        BaseOptions = mp.tasks.BaseOptions
        FaceDetector = mp.tasks.vision.FaceDetector
        FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = FaceDetectorOptions(
            base_options=BaseOptions(model_asset_path=self.model_path),
            running_mode=VisionRunningMode.IMAGE,
            min_detection_confidence=0.5,
        )

        # OS-specific backend
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) if platform.system() == "Windows" else cv2.VideoCapture(0)

        if not cap.isOpened():
            self._update_status("Error: Camera Unavailable")
            self.is_running = False
            return

        self._update_status("Active - User Present")

        try:
            with FaceDetector.create_from_options(options) as detector:
                while self.is_running:
                    ret, frame = cap.read()
                    if not ret:
                        self._update_status("Warning: Frame drop")
                        self._stop_event.wait(timeout=self.check_interval)
                        continue

                    # BGR -> RGB -> MediaPipe wrapper
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

                    try:
                   
                        detection_result = detector.detect(mp_image)
                    except Exception as e:
                        print(f"[Camera] Inference error: {e}")
                        self._stop_event.wait(timeout=self.check_interval)
                        continue

                    current_time = time.time()

                    if detection_result.detections:
                        self.last_seen_time = current_time
                        if not self.user_present:
                           
                            self.user_present = True
                            if self.resume_callback:
                                self.resume_callback()
                        self._update_status("Active - User Present")
                    else:
                        time_absent = current_time - self.last_seen_time

                        if self.user_present and time_absent >= self.absence_timeout:
                            self.user_present = False
                            self._update_status("Active - User Away (Paused)")
                            if self.pause_callback:
                                self.pause_callback()
                        elif self.user_present:
                            countdown = int(self.absence_timeout - time_absent)
                            self._update_status(f"Active - Searching ({countdown}s left)")
                        # If user_present is already False, stay quiet — already paused

                    self._stop_event.wait(timeout=self.check_interval)

        except Exception as e:
        
            print(f"[Camera] Fatal tracker error: {e}")
            self._update_status("Error: Tracker crashed")
            self.is_running = False
        finally:
            cap.release()
            print("[Camera] Presence Tracker thread terminated.")