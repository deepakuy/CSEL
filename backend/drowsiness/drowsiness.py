"""
Standalone Drowsiness Detection System using Eye Aspect Ratio (EAR) method.

Detects drowsiness via laptop webcam using dlib's facial landmark detection
and Eye Aspect Ratio computation.

Usage:
    python drowsiness.py

Press 'q' to quit.
"""

import cv2
import dlib
import numpy as np
import os
import sys

# Import EAR computation from utils module
from utils import compute_eye_aspect_ratio


# Configuration constants
EAR_THRESHOLD = 0.25
CONSECUTIVE_FRAMES_THRESHOLD = 20
CAMERA_INDEX = 0

# dlib indices for eye landmarks
LEFT_EYE_START = 36
LEFT_EYE_END = 42
RIGHT_EYE_START = 42
RIGHT_EYE_END = 48


class DrowsinessDetector:
    """
    Real-time drowsiness detection system using Eye Aspect Ratio (EAR) method.
    
    Uses dlib's 68-point facial landmark detector to extract eye landmarks
    and computes EAR to determine if a person is drowsy.
    """
    
    def __init__(
        self,
        predictor_path="shape_predictor_68_face_landmarks.dat",
        ear_threshold=EAR_THRESHOLD,
        consecutive_frames_threshold=CONSECUTIVE_FRAMES_THRESHOLD,
    ):
        """
        Initialize the drowsiness detector.
        
        Parameters
        ----------
        predictor_path : str
            Path to dlib's 68-point facial landmark predictor model file
        ear_threshold : float
            EAR threshold below which eyes are considered closed (default: 0.25)
        consecutive_frames_threshold : int
            Number of consecutive frames below threshold to trigger alert (default: 20)
        """
        self.ear_threshold = ear_threshold
        self.consecutive_frames_threshold = consecutive_frames_threshold
        self.consecutive_frames = 0
        
        # Initialize dlib face detector and landmark predictor
        print("Loading dlib models...")
        self.detector = dlib.get_frontal_face_detector()
        
        # Check if predictor file exists
        if not os.path.exists(predictor_path):
            raise FileNotFoundError(
                f"Predictor file not found: {predictor_path}\n"
                f"Download from: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
            )
        
        self.predictor = dlib.shape_predictor(predictor_path)
        print("Models loaded successfully")
    
    def extract_eye_landmarks(self, frame, dlib_landmarks):
        """
        Extract left and right eye landmarks from dlib's 68-point detector.
        
        Parameters
        ----------
        frame : np.ndarray
            Video frame (used for debugging/visualization)
        dlib_landmarks : dlib.full_object_detection
            68-point facial landmarks from dlib predictor
        
        Returns
        -------
        tuple
            (left_eye, right_eye) where each is a (6, 2) numpy array of
            eye landmark coordinates. Returns (None, None) if extraction fails.
        """
        try:
            # Extract left eye landmarks (dlib indices 36-41)
            left_eye = np.array([
                (dlib_landmarks.part(i).x, dlib_landmarks.part(i).y)
                for i in range(LEFT_EYE_START, LEFT_EYE_END)
            ], dtype=np.float32)
            
            # Extract right eye landmarks (dlib indices 42-47)
            right_eye = np.array([
                (dlib_landmarks.part(i).x, dlib_landmarks.part(i).y)
                for i in range(RIGHT_EYE_START, RIGHT_EYE_END)
            ], dtype=np.float32)
            
            return left_eye, right_eye
        except (AttributeError, IndexError) as e:
            print(f"Error extracting eye landmarks: {e}")
            return None, None
    
    def process_frame(self, frame):
        """
        Process a single video frame for drowsiness detection.
        
        Parameters
        ----------
        frame : np.ndarray
            Video frame in BGR format (from OpenCV)
        
        Returns
        -------
        dict
            Results dictionary containing:
            - 'frame': Annotated frame with visualizations
            - 'left_ear': Left eye EAR value
            - 'right_ear': Right eye EAR value
            - 'avg_ear': Average EAR value
            - 'drowsy': Boolean indicating drowsiness alert
            - 'face_detected': Boolean indicating if face was detected
        """
        # Initialize result dictionary
        result = {
            'frame': frame.copy(),
            'left_ear': 0.0,
            'right_ear': 0.0,
            'avg_ear': 0.0,
            'drowsy': False,
            'face_detected': False,
        }
        
        # Convert frame to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces in the frame
        rects = self.detector(gray, 0)
        
        if len(rects) == 0:
            # No face detected - reset counter
            self.consecutive_frames = 0
            return result
        
        # Process the first detected face
        face_rect = rects[0]
        result['face_detected'] = True
        
        # Get facial landmarks
        dlib_landmarks = self.predictor(gray, face_rect)
        
        # Extract eye landmarks
        left_eye, right_eye = self.extract_eye_landmarks(frame, dlib_landmarks)
        
        if left_eye is None or right_eye is None:
            # Failed to extract landmarks - reset counter
            self.consecutive_frames = 0
            return result
        
        # Compute EAR for both eyes
        left_ear = compute_eye_aspect_ratio(left_eye)
        right_ear = compute_eye_aspect_ratio(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0
        
        result['left_ear'] = left_ear
        result['right_ear'] = right_ear
        result['avg_ear'] = avg_ear
        
        # Update consecutive frames counter
        if avg_ear < self.ear_threshold:
            self.consecutive_frames += 1
        else:
            # Reset counter immediately when EAR >= threshold
            self.consecutive_frames = 0
        
        # Determine if drowsy
        if self.consecutive_frames >= self.consecutive_frames_threshold:
            result['drowsy'] = True
        
        # Annotate the frame
        result['frame'] = self._annotate_frame(
            frame, face_rect, left_eye, right_eye, left_ear, right_ear,
            result['drowsy']
        )
        
        return result
    
    def _annotate_frame(self, frame, face_rect, left_eye, right_eye,
                       left_ear, right_ear, drowsy):
        """
        Draw face bounding box, eye landmarks, EAR values, and alerts on frame.
        
        Parameters
        ----------
        frame : np.ndarray
            Video frame to annotate
        face_rect : dlib.rectangle
            Bounding box of detected face
        left_eye : np.ndarray
            Left eye landmark coordinates
        right_eye : np.ndarray
            Right eye landmark coordinates
        left_ear : float
            Left eye EAR value
        right_ear : float
            Right eye EAR value
        drowsy : bool
            Whether drowsiness alert is active
        
        Returns
        -------
        np.ndarray
            Annotated frame
        """
        frame = frame.copy()
        
        # Draw face bounding box
        x1, y1 = face_rect.left(), face_rect.top()
        x2, y2 = face_rect.right(), face_rect.bottom()
        
        face_color = (0, 0, 255) if drowsy else (0, 255, 0)  # Red if drowsy, green otherwise
        cv2.rectangle(frame, (x1, y1), (x2, y2), face_color, 2)
        
        # Draw eye landmarks
        eye_color = (0, 0, 255) if drowsy else (0, 255, 0)
        
        # Draw left eye contour
        left_eye_int = left_eye.astype(np.int32)
        cv2.polylines(frame, [left_eye_int], True, eye_color, 2)
        
        # Draw right eye contour
        right_eye_int = right_eye.astype(np.int32)
        cv2.polylines(frame, [right_eye_int], True, eye_color, 2)
        
        # Display EAR values
        avg_ear = (left_ear + right_ear) / 2.0
        ear_text = f"L-EAR: {left_ear:.2f} | R-EAR: {right_ear:.2f} | AVG: {avg_ear:.2f}"
        cv2.putText(frame, ear_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (0, 255, 0), 2)
        
        # Display drowsiness alert
        if drowsy:
            alert_text = "DROWSINESS ALERT"
            cv2.putText(frame, alert_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX,
                       1.2, (0, 0, 255), 3)
            
            # Draw alert box
            cv2.rectangle(frame, (5, 50), (400, 90), (0, 0, 255), 2)
        
        # Display threshold indicator
        threshold_text = f"Threshold: {self.ear_threshold} | Frames: {self.consecutive_frames}/{self.consecutive_frames_threshold}"
        cv2.putText(frame, threshold_text, (10, frame.shape[0] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        return frame


def main():
    """
    Main execution function for the drowsiness detection system.
    
    Opens webcam, processes frames in real-time, and displays drowsiness alerts.
    Press 'q' to quit.
    """
    print("=" * 70)
    print("DROWSINESS DETECTION SYSTEM")
    print("=" * 70)
    print(f"EAR Threshold: {EAR_THRESHOLD}")
    print(f"Consecutive Frames Threshold: {CONSECUTIVE_FRAMES_THRESHOLD}")
    print("\nControls:")
    print("  Press 'q' to quit")
    print("=" * 70)
    
    # Initialize detector
    try:
        detector = DrowsinessDetector(
            ear_threshold=EAR_THRESHOLD,
            consecutive_frames_threshold=CONSECUTIVE_FRAMES_THRESHOLD,
        )
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("\nPlease download the predictor file:")
        print("  URL: http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2")
        print("  Extract and place in the current directory")
        sys.exit(1)
    
    # Open webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)
    
    if not cap.isOpened():
        print(f"\nERROR: Cannot open camera device {CAMERA_INDEX}")
        sys.exit(1)
    
    print(f"\nCamera opened successfully")
    print(f"Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
          f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print(f"FPS: {cap.get(cv2.CAP_PROP_FPS):.1f}")
    print("\nProcessing video stream...\n")
    
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print("ERROR: Failed to read frame from camera")
                break
            
            frame_count += 1
            
            # Process frame for drowsiness detection
            result = detector.process_frame(frame)
            
            # Display the annotated frame
            cv2.imshow("Drowsiness Detection (press 'q' to quit)", result['frame'])
            
            # Print status periodically (commented out for cleaner output)
            # if frame_count % 30 == 0:
            #     status = "ALERT" if result['drowsy'] else "OK"
            #     print(f"Frame {frame_count} | EAR: {result['avg_ear']:.3f} | "
            #           f"Status: {status} | Counter: {detector.consecutive_frames}")
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nQuitting...")
                break
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nProcessed {frame_count} frames total")
        print("Resources released. Exiting.")


if __name__ == "__main__":
    main()
